"""Google Gemini provider (free-tier friendly, for testing).

Reuses every prompt and parser from MetaProvider and only swaps the transport: this talks to the native
Gemini REST API (generateContent) instead of the OpenAI-style Chat Completions API.

- POST {base}/models/{model}:generateContent, auth via `x-goog-api-key` header
- `developer`/`system` messages -> `systemInstruction`; `assistant` role -> `model`
- Images -> `inlineData` parts
- JSON mode via `responseMimeType=application/json`; the target schema is also spelled out in the system
  prompt, and the result is still validated by pydantic, so a bad answer becomes a clean 502, never garbage.

NOT verified live in this repo (no key available): covered by mocked-transport tests only.
"""
from __future__ import annotations

import base64
import json
import logging
from typing import Any

import httpx
from pydantic import BaseModel

from app.core.config import Settings
from app.services.ai.base import (
    AINotConfiguredError, AIRateLimitedError, AIResponseError, AITimeoutError, AIUnavailableError,
)
from app.services.ai.meta_provider import MetaProvider, inline_schema

log = logging.getLogger("bindu.ai.gemini")
MAX_OUTPUT_TOKENS = 4000  # Gemini 2.5 "thinking" tokens count toward this budget


class GeminiProvider(MetaProvider):
    name = "gemini"

    def __init__(self, settings: Settings, transport: httpx.AsyncBaseTransport | None = None) -> None:
        if not settings.gemini_api_key:
            raise AINotConfiguredError("GEMINI_API_KEY is not set")
        self._s = settings
        self._transport = transport
        self.model = settings.gemini_model_name

    @staticmethod
    def _convert(messages: list[dict[str, Any]], schema_model: type[BaseModel]) -> tuple[str, list[dict[str, Any]]]:
        system_parts: list[str] = []
        contents: list[dict[str, Any]] = []
        for m in messages:
            role, content = m["role"], m["content"]
            if role in ("developer", "system"):
                system_parts.append(content if isinstance(content, str) else "")
                continue
            parts: list[dict[str, Any]] = []
            if isinstance(content, str):
                parts.append({"text": content})
            else:
                for p in content:
                    if p["type"] == "text":
                        parts.append({"text": p["text"]})
                    elif p["type"] == "image_url":
                        header, b64 = p["image_url"]["url"].split(",", 1)
                        mime = header.removeprefix("data:").split(";")[0]
                        parts.append({"inlineData": {"mimeType": mime, "data": b64}})
            contents.append({"role": "model" if role == "assistant" else "user", "parts": parts})
        system_parts.append(
            "Respond with ONLY a single JSON object (no markdown fences) matching this JSON Schema:\n"
            + json.dumps(inline_schema(schema_model))
        )
        return "\n\n".join(system_parts), contents

    async def _chat(self, messages: list[dict[str, Any]], schema_name: str, schema_model: type[BaseModel]) -> str:
        system, contents = self._convert(messages, schema_model)
        body = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": contents,
            "generationConfig": {"responseMimeType": "application/json", "maxOutputTokens": MAX_OUTPUT_TOKENS},
        }
        url = f"{self._s.gemini_api_base_url.rstrip('/')}/models/{self.model}:generateContent"
        headers = {"x-goog-api-key": self._s.gemini_api_key, "Content-Type": "application/json"}
        try:
            async with httpx.AsyncClient(timeout=self._s.ai_request_timeout_seconds, transport=self._transport) as client:
                resp = await client.post(url, json=body, headers=headers)
        except httpx.TimeoutException as exc:
            raise AITimeoutError("Gemini API timed out") from exc
        except httpx.TransportError as exc:
            raise AIUnavailableError(f"Gemini API unreachable: {type(exc).__name__}") from exc

        # Never log request bodies (user photos) or the API key.
        if resp.status_code == 429:
            raise AIRateLimitedError("Gemini API rate limit (free tier quota?)")
        if resp.status_code in (401, 403):
            raise AINotConfiguredError("Gemini API rejected the credentials")
        if resp.status_code == 504:
            raise AITimeoutError("Gemini API gateway timeout")
        if resp.status_code >= 500:
            raise AIUnavailableError(f"Gemini API error {resp.status_code}")
        if resp.status_code >= 400:
            log.warning("Gemini API rejected request: status=%s body=%s", resp.status_code, resp.text[:300])
            raise AIResponseError(f"Gemini API rejected the request ({resp.status_code})")

        try:
            cand = resp.json()["candidates"][0]
            text = "".join(p.get("text", "") for p in cand["content"]["parts"])
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise AIResponseError("Unexpected Gemini API response shape (blocked or empty?)") from exc
        if cand.get("finishReason") == "MAX_TOKENS":
            raise AIResponseError("Model output was truncated")
        if not text.strip():
            raise AIResponseError("Empty model output")
        return text


__all__ = ["GeminiProvider"]