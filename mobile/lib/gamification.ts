// TypeScript port of bindu/domain/gamification.py from the original Streamlit app.
export const MAX_HEARTS = 5;
export const HEART_REFILL_PERIOD_HOURS = 4;
export const XP_PER_LEVEL = 100;
const HOUR_MS = 3_600_000;

export const levelForXp = (xp: number): number => Math.floor(xp / XP_PER_LEVEL) + 1;

/** Returns [hearts, newRefillInstantMs]; the instant only advances by whole periods consumed. */
export function refillHeartsIfDue(
  hearts: number,
  lastRefillMs: number,
  nowMs: number = Date.now(),
): [number, number] {
  if (hearts >= MAX_HEARTS) return [MAX_HEARTS, nowMs];
  const periods = Math.floor((nowMs - lastRefillMs) / HOUR_MS / HEART_REFILL_PERIOD_HOURS);
  if (periods <= 0) return [hearts, lastRefillMs];
  return [
    Math.min(hearts + periods, MAX_HEARTS),
    lastRefillMs + periods * HEART_REFILL_PERIOD_HOURS * HOUR_MS,
  ];
}

export function hoursUntilNextHeart(hearts: number, lastRefillMs: number, nowMs: number = Date.now()): number {
  if (hearts >= MAX_HEARTS) return 0;
  const elapsed = Math.floor((nowMs - lastRefillMs) / HOUR_MS);
  const remainder = elapsed % HEART_REFILL_PERIOD_HOURS;
  return Math.max(0, Math.min(HEART_REFILL_PERIOD_HOURS, HEART_REFILL_PERIOD_HOURS - remainder));
}

const dayNumber = (iso: string) => Math.floor(Date.parse(iso + "T00:00:00Z") / 86_400_000);

/** Dates are UTC 'YYYY-MM-DD'. Same day keeps the streak (min 1); next day increments; else resets to 1. */
export function updateStreak(lastActive: string | null, today: string, current: number): number {
  if (!lastActive) return 1;
  const gap = dayNumber(today) - dayNumber(lastActive);
  if (gap === 0) return Math.max(current, 1);
  if (gap === 1) return current + 1;
  return 1;
}

export const utcToday = (nowMs: number = Date.now()): string => new Date(nowMs).toISOString().slice(0, 10);
