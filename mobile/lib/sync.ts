import { restDelete, restSelect, restUpsert } from "@/lib/supabase";
import { useDiscoveries, type SavedDiscovery } from "@/stores/discoveries";
import { useProfile } from "@/stores/profile";
import { useProgress } from "@/stores/progress";
import { useSession } from "@/stores/session";
import { useTrips, type SavedTrip } from "@/stores/trips";

export type ProgressData = { xp: number; streak: number; lastActive: string | null; completed: Record<number, number> };

/**
 * Merge two progress records without losing anything either side earned:
 * - lessons: highest stars per lesson; XP: the larger total (we cannot tell which XP overlaps, so we never add);
 * - streak: from whichever record was active more recently (ties keep the higher streak).
 */
export function mergeProgress(a: ProgressData, b: ProgressData): ProgressData {
  const completed: Record<number, number> = { ...a.completed };
  for (const [id, stars] of Object.entries(b.completed)) completed[Number(id)] = Math.max(completed[Number(id)] ?? 0, stars);
  const aLater = (a.lastActive ?? "") > (b.lastActive ?? "");
  const same = a.lastActive === b.lastActive;
  const pick = same ? (a.streak >= b.streak ? a : b) : aLater ? a : b;
  return { xp: Math.max(a.xp, b.xp), streak: pick.streak, lastActive: pick.lastActive, completed };
}

/** Union by id; the local copy wins when both sides have the id. Newest first. */
export function mergeById<T extends { id: string; createdAt: string }>(local: T[], remote: T[]): T[] {
  const byId = new Map<string, T>();
  for (const r of remote) byId.set(r.id, r);
  for (const l of local) byId.set(l.id, l);
  return [...byId.values()].sort((x, y) => y.createdAt.localeCompare(x.createdAt));
}

// ---- row mappers (local <-> database) ----
export const discoveryToRow = (d: SavedDiscovery, userId: string) => ({ id: d.id, user_id: userId, title: d.title, summary: d.summary, phrase: d.phrase ?? null, created_at: d.createdAt });
export const rowToDiscovery = (r: any): SavedDiscovery => ({ id: String(r.id), title: r.title, summary: r.summary ?? "", phrase: r.phrase ?? null, createdAt: new Date(r.created_at).toISOString() });
export const tripToRow = (t: SavedTrip, userId: string) => ({ id: t.id, user_id: userId, data: { request: t.request, itinerary: t.itinerary, isMock: t.isMock }, created_at: t.createdAt });
export const rowToTrip = (r: any): SavedTrip => ({ id: String(r.id), request: r.data.request, itinerary: r.data.itinerary, isMock: !!r.data.isMock, createdAt: new Date(r.created_at).toISOString() });

const progressToRow = (p: ProgressData & { hearts: number; heartsLastRefill: number }, userId: string) => ({
  user_id: userId, xp: p.xp, streak: p.streak, last_active: p.lastActive, hearts: p.hearts, hearts_last_refill: p.heartsLastRefill, completed: p.completed, updated_at: new Date().toISOString(),
});
const rowToProgress = (r: any): ProgressData => ({ xp: r.xp ?? 0, streak: r.streak ?? 0, lastActive: r.last_active ?? null, completed: Object.fromEntries(Object.entries(r.completed ?? {}).map(([k, v]) => [Number(k), Number(v)])) });

export type SyncResult = { ok: true; discoveries: number; trips: number } | { ok: false; reason: "signed-out" | "error"; message: string };

/** Two-way sync for the signed-in user. Safe to call repeatedly; never throws. */
export async function syncNow(): Promise<SyncResult> {
  const session = useSession.getState();
  const token = await session.getToken();
  const userId = useSession.getState().userId;
  if (!token || !userId) return { ok: false, reason: "signed-out", message: "Sign in to sync." };
  try {
    const [pRows, dRows, tRows, profRows] = await Promise.all([
      restSelect("progress", token, "select=*"), restSelect("discoveries", token, "select=*"),
      restSelect("trips", token, "select=*"), restSelect("profiles", token, "select=*"),
    ]);

    const prog = useProgress.getState();
    const mergedProgress = pRows?.[0] ? mergeProgress({ xp: prog.xp, streak: prog.streak, lastActive: prog.lastActive, completed: prog.completed }, rowToProgress(pRows[0]))
      : { xp: prog.xp, streak: prog.streak, lastActive: prog.lastActive, completed: prog.completed };
    useProgress.setState(mergedProgress);

    const discoveries = mergeById(useDiscoveries.getState().items, (dRows ?? []).map(rowToDiscovery));
    useDiscoveries.setState({ items: discoveries });
    const trips = mergeById(useTrips.getState().items, (tRows ?? []).map(rowToTrip));
    useTrips.setState({ items: trips });

    // Profile: the account's saved profile is restored on a fresh device; otherwise local settings are pushed up.
    const profile = useProfile.getState();
    if (profRows?.[0] && !profile.onboarded) {
      const r = profRows[0];
      useProfile.setState({ displayName: r.display_name, language: r.language, nepaliLevel: r.nepali_level, interests: r.interests ?? [], onboarded: true });
    }
    const p2 = useProfile.getState();
    const after = useProgress.getState();
    await Promise.all([
      restUpsert("progress", token, progressToRow({ ...mergedProgress, hearts: after.hearts, heartsLastRefill: after.heartsLastRefill }, userId), "user_id"),
      restUpsert("profiles", token, { user_id: userId, display_name: p2.displayName, language: p2.language, nepali_level: p2.nepaliLevel, interests: p2.interests, updated_at: new Date().toISOString() }, "user_id"),
      discoveries.length ? restUpsert("discoveries", token, discoveries.map((d) => discoveryToRow(d, userId)), "user_id,id") : Promise.resolve(null),
      trips.length ? restUpsert("trips", token, trips.map((t) => tripToRow(t, userId)), "user_id,id") : Promise.resolve(null),
    ]);
    return { ok: true, discoveries: discoveries.length, trips: trips.length };
  } catch {
    return { ok: false, reason: "error", message: "Couldn't sync right now. Your data is safe on this device; try again later." };
  }
}

/** Best-effort removal of a deleted item from the account so another device doesn't bring it back. */
export async function deleteRemote(table: "discoveries" | "trips", id: string): Promise<void> {
  const token = await useSession.getState().getToken();
  if (!token) return;
  try {
    await restDelete(table, token, `id=eq.${encodeURIComponent(id)}`);
  } catch {
    /* ignored: local delete already happened */
  }
}
