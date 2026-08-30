
from __future__ import annotations

from datetime import date, datetime, timezone

from bindu.data.local_cache import LocalCache
from bindu.data.supabase_client import get_client
from bindu.domain import gamification
from bindu.domain.models import UserStats


class ProgressRepository:
    def __init__(self, cache: LocalCache):
        self.cache = cache



    def get_or_create_stats(self, user_id: str) -> UserStats:
        row = self.cache.get_stats(user_id)
        if row is not None:
            return _row_to_stats(row)
        fresh = UserStats(
            user_id=user_id,
            hearts=gamification.MAX_HEARTS,
            xp=0,
            streak=0,
            last_active=None,
            hearts_last_refill=datetime.now(timezone.utc).isoformat(),
        )
        self.cache.upsert_stats(
            fresh.user_id, fresh.hearts, fresh.xp, fresh.streak,
            fresh.last_active, fresh.hearts_last_refill,
        )
        return fresh

    def deduct_heart(self, user_id: str) -> UserStats:
        current = self.get_or_create_stats(user_id)
        updated = gamification.deduct_heart(current)
        self._persist_stats(updated)
        return updated

    def add_xp(self, user_id: str, amount: int) -> UserStats:
        current = self.get_or_create_stats(user_id)
        updated = gamification.add_xp(current, amount)
        self._persist_stats(updated)
        return updated

    def refill_hearts_if_due(self, user_id: str) -> UserStats:
        current = self.get_or_create_stats(user_id)
        new_hearts, new_refill = gamification.refill_hearts_if_due(
            current.hearts, datetime.fromisoformat(current.hearts_last_refill)
        )

        if new_hearts == current.hearts:
            return current
        updated = _replace(current, hearts=new_hearts, hearts_last_refill=new_refill.isoformat())
        self._persist_stats(updated)
        return updated

    def record_activity_and_update_streak(self, user_id: str) -> UserStats:
        current = self.get_or_create_stats(user_id)
        last_active_date = date.fromisoformat(current.last_active) if current.last_active else None
        today = datetime.now(timezone.utc).date()
        new_streak = gamification.update_streak(last_active_date, today, current.streak)
        updated = _replace(current, streak=new_streak, last_active=today.isoformat())
        self._persist_stats(updated)
        return updated

    # -- lesson progress --------------------------------------------------

    def mark_lesson_complete(self, user_id: str, lesson_id: int, stars: int) -> None:
        self.cache.upsert_progress(user_id, lesson_id, completed=True, stars=stars, pending_sync=True)
        self._push_progress(user_id, lesson_id, True, stars)

    def get_progress_for_user(self, user_id: str) -> dict[int, dict]:
        return {
            row["lesson_id"]: {"completed": bool(row["completed"]), "stars": row["stars"]}
            for row in self.cache.get_progress_for_user(user_id)
        }

    def sync_pending_writes(self) -> None:
        """Retries any rows that failed to sync earlier — call periodically or
        whenever connectivity is confirmed."""
        for row in self.cache.get_pending_progress():
            self._push_progress(row["user_id"], row["lesson_id"], bool(row["completed"]), row["stars"])
        for row in self.cache.get_pending_stats():
            self._push_stats(_row_to_stats(row))

    # -- internals ----------------------------------------------------------

    def _persist_stats(self, stats: UserStats) -> None:
        self.cache.upsert_stats(
            stats.user_id, stats.hearts, stats.xp, stats.streak,
            stats.last_active, stats.hearts_last_refill, pending_sync=True,
        )
        self._push_stats(stats)

    def _push_stats(self, stats: UserStats) -> None:
        try:
            get_client().table("user_stats").upsert({
                "user_id": stats.user_id,
                "hearts": stats.hearts,
                "xp": stats.xp,
                "streak": stats.streak,
                "last_active": stats.last_active,
                "hearts_last_refill": stats.hearts_last_refill,
            }).execute()
            self.cache.upsert_stats(
                stats.user_id, stats.hearts, stats.xp, stats.streak,
                stats.last_active, stats.hearts_last_refill, pending_sync=False,
            )
        except Exception:
            pass  

    def _push_progress(self, user_id: str, lesson_id: int, completed: bool, stars: int) -> None:
        try:
            get_client().table("user_progress").upsert({
                "user_id": user_id,
                "lesson_id": lesson_id,
                "completed": completed,
                "stars": stars,
            }).execute()
            self.cache.upsert_progress(user_id, lesson_id, completed, stars, pending_sync=False)
        except Exception:
            pass 


def _row_to_stats(row) -> UserStats:
    return UserStats(
        user_id=row["user_id"], hearts=row["hearts"], xp=row["xp"], streak=row["streak"],
        last_active=row["last_active"], hearts_last_refill=row["hearts_last_refill"],
    )


def _replace(stats: UserStats, **changes) -> UserStats:
    from dataclasses import replace
    return replace(stats, **changes)
