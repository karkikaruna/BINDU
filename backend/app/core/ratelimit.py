"""Small in-memory sliding-window limiter for expensive AI endpoints.

Per-process only; behind several workers use a shared store (e.g. Redis) instead.
"""
from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import Depends, HTTPException, Request, status

from app.core.config import Settings, get_settings
from app.core.security import AuthUser, optional_user


class SlidingWindowLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str, limit: int, window_s: float = 60.0, now: float | None = None) -> float | None:
        """Record a hit. Returns None if allowed, else seconds until the oldest hit expires."""
        now = time.monotonic() if now is None else now
        q = self._hits[key]
        while q and now - q[0] >= window_s:
            q.popleft()
        if len(q) >= limit:
            return window_s - (now - q[0])
        q.append(now)
        return None

    def reset(self) -> None:
        self._hits.clear()


limiter = SlidingWindowLimiter()


def ai_rate_limit(
    request: Request,
    user: AuthUser | None = Depends(optional_user),
    settings: Settings = Depends(get_settings),
) -> None:
    key = f"user:{user.id}" if user else f"ip:{request.client.host if request.client else 'unknown'}"
    retry = limiter.check(key, settings.ai_rate_limit_per_minute)
    if retry is not None:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Too many AI requests. Please wait a moment and try again.",
            headers={"Retry-After": str(int(retry) + 1)},
        )
