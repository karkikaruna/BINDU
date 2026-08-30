from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from bindu.domain.models import UserStats

MAX_HEARTS = 5
HEART_REFILL_PERIOD_HOURS = 4
XP_PER_LEVEL = 100


def deduct_heart(stats: UserStats) -> UserStats:
    """Returns stats after deducting one heart, or the same stats if already at 0."""
    if stats.hearts <= 0:
        return stats
    return _replace(stats, hearts=stats.hearts - 1)


def add_xp(stats: UserStats, amount: int) -> UserStats:
    if amount < 0:
        raise ValueError("XP amount must be non-negative")
    return _replace(stats, xp=stats.xp + amount)


def level_for_xp(xp: int) -> int:
    return (xp // XP_PER_LEVEL) + 1


def refill_hearts_if_due(
    current_hearts: int,
    hearts_last_refill: datetime,
    now: datetime | None = None,
) -> tuple[int, datetime]:
    """How many hearts should be refilled given elapsed time.

    Capped at MAX_HEARTS. Returns (new_heart_count, new_refill_instant) —
    new_refill_instant only advances by whole refill periods consumed, so
    partial progress toward the next heart isn't lost.
    """
    now = now or datetime.now(timezone.utc)
    if current_hearts >= MAX_HEARTS:
        return MAX_HEARTS, now

    elapsed_hours = (now - hearts_last_refill).total_seconds() / 3600
    periods_elapsed = int(elapsed_hours // HEART_REFILL_PERIOD_HOURS)
    if periods_elapsed <= 0:
        return current_hearts, hearts_last_refill

    new_hearts = min(current_hearts + periods_elapsed, MAX_HEARTS)
    consumed = timedelta(hours=periods_elapsed * HEART_REFILL_PERIOD_HOURS)
    new_refill_instant = hearts_last_refill + consumed
    return new_hearts, new_refill_instant


def hours_until_next_heart(
    current_hearts: int,
    hearts_last_refill: datetime,
    now: datetime | None = None,
) -> int:
    """Hours remaining until the next heart refill; 0 if hearts are already full."""
    now = now or datetime.now(timezone.utc)
    if current_hearts >= MAX_HEARTS:
        return 0
    elapsed_hours = int((now - hearts_last_refill).total_seconds() // 3600)
    remainder = elapsed_hours % HEART_REFILL_PERIOD_HOURS
    return max(0, min(HEART_REFILL_PERIOD_HOURS, HEART_REFILL_PERIOD_HOURS - remainder))


def update_streak(
    last_active: date | None,
    today: date | None = None,
    current_streak: int = 0,
) -> int:
    """Updates the streak given the last-active date and today's date (UTC).

    - Same day as last active: streak unchanged (floored at 1).
    - Exactly one day after last active: streak increments.
    - Any bigger gap (or no prior activity): streak resets to 1.
    """
    today = today or datetime.now(timezone.utc).date()
    if last_active is None:
        return 1
    days_since = (today - last_active).days
    if days_since == 0:
        return max(current_streak, 1)
    if days_since == 1:
        return current_streak + 1
    return 1


def should_remind_streak(last_active: date | None, today: date | None = None) -> bool:
    """True if the user has not practiced yet today — a streak reminder should fire."""
    today = today or datetime.now(timezone.utc).date()
    return last_active is None or last_active < today


def _replace(stats: UserStats, **changes) -> UserStats:
    """dataclasses.replace, kept local so this file has no import beyond models."""
    from dataclasses import replace
    return replace(stats, **changes)
