import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";
import { safeStorage } from "@/lib/storage";
import { MAX_HEARTS, refillHeartsIfDue, updateStreak, utcToday } from "@/lib/gamification";

type ProgressState = {
  hearts: number;
  heartsLastRefill: number;
  xp: number;
  streak: number;
  lastActive: string | null;
  /** lessonId -> stars (1-3) */
  completed: Record<number, number>;
  refreshHearts: () => void;
  loseHeart: () => void;
  completeLesson: (lessonId: number, stars: number, xpGained: number) => void;
  /** XP from activities outside the lesson path (e.g. AI tutor practice). Does not touch streak or lessons. */
  addXp: (amount: number) => void;
  reset: () => void;
};

const initial = { hearts: MAX_HEARTS, heartsLastRefill: Date.now(), xp: 0, streak: 0, lastActive: null as string | null, completed: {} as Record<number, number> };

export const useProgress = create<ProgressState>()(
  persist(
    (set, get) => ({
      ...initial,
      refreshHearts: () => {
        const { hearts, heartsLastRefill } = get();
        const [h, t] = refillHeartsIfDue(hearts, heartsLastRefill);
        if (h !== hearts || t !== heartsLastRefill) set({ hearts: h, heartsLastRefill: t });
      },
      loseHeart: () => {
        const { hearts } = get();
        if (hearts <= 0) return;
        // Starting to lose hearts from full restarts the refill clock.
        set({ hearts: hearts - 1, heartsLastRefill: hearts === MAX_HEARTS ? Date.now() : get().heartsLastRefill });
      },
      completeLesson: (lessonId, stars, xpGained) => {
        const s = get();
        const today = utcToday();
        set({
          completed: { ...s.completed, [lessonId]: Math.max(s.completed[lessonId] ?? 0, stars) },
          xp: s.xp + xpGained,
          streak: updateStreak(s.lastActive, today, s.streak),
          lastActive: today,
        });
      },
      addXp: (amount) => { if (amount > 0) set({ xp: get().xp + Math.floor(amount) }); },
      reset: () => set({ ...initial, heartsLastRefill: Date.now() }),
    }),
    {
      name: "bindu-progress",
      storage: createJSONStorage(() => safeStorage),
      partialize: ({ hearts, heartsLastRefill, xp, streak, lastActive, completed }) => ({ hearts, heartsLastRefill, xp, streak, lastActive, completed }),
    },
  ),
);
