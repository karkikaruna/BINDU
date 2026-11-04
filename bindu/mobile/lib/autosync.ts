import { syncNow } from "@/lib/sync";
import { useProfile } from "@/stores/profile";
import { useProgress } from "@/stores/progress";
import { useSession } from "@/stores/session";

const DEBOUNCE_MS = 2_000;

// Compared by value, because a sync writes merged data back into the stores and must not look like a new change.
const progressKey = () => { const p = useProgress.getState(); return JSON.stringify([p.xp, p.streak, p.lastActive, p.completed]); };
const profileKey = () => { const p = useProfile.getState(); return JSON.stringify([p.onboarded, p.displayName, p.language, p.nepaliLevel, p.interests]); };

/**
 * Saves a signed-in user's progress and profile to their account shortly after it changes (finishing a lesson, earning XP,
 * editing the profile), so nothing waits for the "Sync now" button. Returns a function that stops it.
 */
export function startAutoSync(): () => void {
  let timer: ReturnType<typeof setTimeout> | undefined;
  let last = progressKey() + profileKey();
  const check = () => {
    const now = progressKey() + profileKey();
    if (now === last) return;
    last = now;
    clearTimeout(timer);
    timer = setTimeout(() => {
      if (useSession.getState().userId) void syncNow().finally(() => { last = progressKey() + profileKey(); });
    }, DEBOUNCE_MS);
  };
  const offProgress = useProgress.subscribe(check);
  const offProfile = useProfile.subscribe(check);
  return () => { clearTimeout(timer); offProgress(); offProfile(); };
}
