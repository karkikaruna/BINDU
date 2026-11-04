// Port of bindu/domain/exercise_validator.py (case-insensitive, trimmed comparison).
const norm = (s: string) => s.trim().toLowerCase();

export function checkMultipleChoice(selected: string, answer: string[]): boolean {
  return answer.length > 0 && norm(selected) === norm(answer[0]);
}

export function checkWordBank(ordered: string[], answer: string[]): boolean {
  return ordered.length === answer.length && ordered.every((t, i) => norm(t) === norm(answer[i]));
}

/** Deterministic shuffle (seeded) so tile order is stable across re-renders. */
export function shuffled<T>(items: T[], seed: number): T[] {
  const out = [...items];
  let s = seed || 1;
  for (let i = out.length - 1; i > 0; i--) {
    s = (s * 1664525 + 1013904223) % 4294967296;
    const j = s % (i + 1);
    [out[i], out[j]] = [out[j], out[i]];
  }
  return out;
}
