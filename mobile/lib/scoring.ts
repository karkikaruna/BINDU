/** Scoring carried over from the original app: stars = round(3 * firstTry / total); XP 10 per first-try, 5 per retried. */
export function scoreLesson(firstTryCount: number, total: number): { stars: number; xp: number } {
  if (total <= 0) return { stars: 0, xp: 0 };
  // A completed lesson always shows at least one star so it reads as "done" in the path.
  const stars = Math.max(1, Math.round((3 * firstTryCount) / total));
  const xp = 10 * firstTryCount + 5 * (total - firstTryCount);
  return { stars, xp };
}
