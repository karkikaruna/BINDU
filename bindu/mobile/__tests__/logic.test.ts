import { checkMultipleChoice, checkWordBank, shuffled } from "@/lib/exercise";
import { HEART_REFILL_PERIOD_HOURS, hoursUntilNextHeart, levelForXp, MAX_HEARTS, refillHeartsIfDue, updateStreak } from "@/lib/gamification";
import { allLessons, isUnlocked, nextLesson, units } from "@/lib/curriculum";
import { scoreLesson } from "@/lib/scoring";

const H = 3_600_000;

describe("exercise validation (ported from exercise_validator.py)", () => {
  it("multiple choice is trimmed and case-insensitive", () => {
    expect(checkMultipleChoice("  Namaste ", ["namaste"])).toBe(true);
    expect(checkMultipleChoice("x", ["namaste"])).toBe(false);
    expect(checkMultipleChoice("x", [])).toBe(false);
  });
  it("word bank needs same length and order", () => {
    expect(checkWordBank(["a", "b"], ["a", "b"])).toBe(true);
    expect(checkWordBank(["b", "a"], ["a", "b"])).toBe(false);
    expect(checkWordBank(["a"], ["a", "b"])).toBe(false);
  });
  it("shuffle keeps all tokens and is deterministic", () => {
    const t = ["a", "b", "c", "d", "e"];
    expect([...shuffled(t, 7)].sort()).toEqual(t);
    expect(shuffled(t, 7)).toEqual(shuffled(t, 7));
  });
});

describe("gamification (ported from gamification.py)", () => {
  it("levels every 100 XP", () => {
    expect([0, 99, 100, 250].map(levelForXp)).toEqual([1, 1, 2, 3]);
  });
  it("refills one heart per period and keeps partial progress", () => {
    const t0 = 1_000_000_000_000;
    expect(refillHeartsIfDue(2, t0, t0 + 3 * H)).toEqual([2, t0]);
    expect(refillHeartsIfDue(2, t0, t0 + 9 * H)).toEqual([4, t0 + 2 * HEART_REFILL_PERIOD_HOURS * H]);
    expect(refillHeartsIfDue(4, t0, t0 + 100 * H)[0]).toBe(MAX_HEARTS);
    expect(refillHeartsIfDue(MAX_HEARTS, t0, t0 + H)[0]).toBe(MAX_HEARTS);
  });
  it("reports hours until next heart", () => {
    const t0 = 1_000_000_000_000;
    expect(hoursUntilNextHeart(3, t0, t0 + 1 * H)).toBe(3);
    expect(hoursUntilNextHeart(MAX_HEARTS, t0, t0 + 1 * H)).toBe(0);
  });
  it("streak rules", () => {
    expect(updateStreak(null, "2026-10-27", 0)).toBe(1);
    expect(updateStreak("2026-10-27", "2026-10-27", 4)).toBe(4);
    expect(updateStreak("2026-10-26", "2026-10-27", 4)).toBe(5);
    expect(updateStreak("2026-10-20", "2026-10-27", 4)).toBe(1);
    expect(updateStreak("2026-02-28", "2026-03-01", 2)).toBe(3); // month boundary
  });
});

describe("scoring (original rule: stars=round(3*first/total), 10/5 XP)", () => {
  it("perfect run", () => expect(scoreLesson(7, 7)).toEqual({ stars: 3, xp: 70 }));
  it("mixed run", () => expect(scoreLesson(4, 7)).toEqual({ stars: 2, xp: 55 }));
  it("never shows zero stars on a completed lesson", () => expect(scoreLesson(0, 7)).toEqual({ stars: 1, xp: 35 }));
  it("empty lesson", () => expect(scoreLesson(0, 0)).toEqual({ stars: 0, xp: 0 }));
});

describe("curriculum reused from the original app", () => {
  it("has 3 units / 9 lessons / 63 exercises, all answerable", () => {
    expect(units).toHaveLength(3);
    expect(allLessons).toHaveLength(9);
    const ex = allLessons.flatMap((l) => l.exercises);
    expect(ex).toHaveLength(63);
    for (const e of ex) {
      expect(e.answer.length).toBeGreaterThan(0);
      if (e.type === "multiple_choice") expect(e.options).toContain(e.answer[0]);
      else expect([...e.tokens].sort()).toEqual([...e.answer].sort());
    }
  });
  it("unlocks lessons strictly in order", () => {
    expect(isUnlocked(1, {})).toBe(true);
    expect(isUnlocked(2, {})).toBe(false);
    expect(isUnlocked(2, { 1: 3 })).toBe(true);
    expect(isUnlocked(3, { 1: 3 })).toBe(false);
    expect(nextLesson({ 1: 2, 2: 1 })?.id).toBe(3);
    expect(nextLesson(Object.fromEntries(allLessons.map((l) => [l.id, 3])))).toBeUndefined();
  });
});
