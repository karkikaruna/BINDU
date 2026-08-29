from datetime import datetime, timedelta, timezone

from bindu.domain import gamification
from bindu.domain.models import UserStats


def make_stats(hearts: int = 5, xp: int = 0) -> UserStats:
    return UserStats(
        user_id="u1", hearts=hearts, xp=xp, streak=0,
        last_active=None, hearts_last_refill=datetime.now(timezone.utc).isoformat(),
    )


def test_deduct_heart_reduces_by_one():
    result = gamification.deduct_heart(make_stats(hearts=3))
    assert result.hearts == 2


def test_deduct_heart_does_not_go_below_zero():
    result = gamification.deduct_heart(make_stats(hearts=0))
    assert result.hearts == 0


def test_add_xp_increases_total():
    result = gamification.add_xp(make_stats(xp=50), 10)
    assert result.xp == 60


def test_level_for_xp_computes_tiers():
    assert gamification.level_for_xp(0) == 1
    assert gamification.level_for_xp(100) == 2
    assert gamification.level_for_xp(250) == 3


def test_refill_hearts_if_due_grants_a_heart_after_one_period():
    start = datetime.now(timezone.utc) - timedelta(hours=4, minutes=1)
    hearts, new_instant = gamification.refill_hearts_if_due(3, start)
    assert hearts == 4
    assert new_instant > start


def test_refill_hearts_if_due_caps_at_max_hearts():
    start = datetime.now(timezone.utc) - timedelta(hours=20)
    hearts, _ = gamification.refill_hearts_if_due(3, start)
    assert hearts == gamification.MAX_HEARTS


def test_refill_hearts_if_due_does_nothing_before_a_full_period_elapses():
    start = datetime.now(timezone.utc) - timedelta(hours=1)  # period is 4h
    hearts, _ = gamification.refill_hearts_if_due(2, start)
    assert hearts == 2


def test_update_streak_increments_on_consecutive_day():
    today = datetime.now(timezone.utc).date()
    yesterday = today - timedelta(days=1)
    new_streak = gamification.update_streak(yesterday, today, current_streak=4)
    assert new_streak == 5


def test_update_streak_resets_after_a_gap():
    today = datetime.now(timezone.utc).date()
    three_days_ago = today - timedelta(days=3)
    new_streak = gamification.update_streak(three_days_ago, today, current_streak=10)
    assert new_streak == 1


def test_update_streak_unchanged_on_same_day():
    today = datetime.now(timezone.utc).date()
    new_streak = gamification.update_streak(today, today, current_streak=4)
    assert new_streak == 4


def test_should_remind_streak_true_when_never_active():
    assert gamification.should_remind_streak(None) is True


def test_should_remind_streak_false_when_active_today():
    today = datetime.now(timezone.utc).date()
    assert gamification.should_remind_streak(today) is False
