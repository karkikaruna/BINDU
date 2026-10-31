import { cardAsText, localCard } from "@/lib/card";
import { formatDistance, mapsUrl, tripAsText } from "@/lib/format";
import { discoveryToRow, mergeById, mergeProgress, rowToDiscovery, rowToTrip, tripToRow } from "@/lib/sync";
import type { SavedDiscovery } from "@/stores/discoveries";
import type { SavedTrip } from "@/stores/trips";

describe("mergeProgress", () => {
  const base = { xp: 0, streak: 0, lastActive: null as string | null, completed: {} as Record<number, number> };
  it("keeps the best stars per lesson and never adds XP", () => {
    const m = mergeProgress({ ...base, xp: 120, completed: { 1: 3, 2: 1 } }, { ...base, xp: 150, completed: { 2: 3, 3: 2 } });
    expect(m.completed).toEqual({ 1: 3, 2: 3, 3: 2 });
    expect(m.xp).toBe(150);
  });
  it("takes the streak from the more recently active side", () => {
    expect(mergeProgress({ ...base, streak: 9, lastActive: "2026-10-20" }, { ...base, streak: 2, lastActive: "2026-10-27" })).toMatchObject({ streak: 2, lastActive: "2026-10-27" });
    expect(mergeProgress({ ...base, streak: 2, lastActive: "2026-10-27" }, { ...base, streak: 9, lastActive: "2026-10-20" })).toMatchObject({ streak: 2, lastActive: "2026-10-27" });
  });
  it("on the same day keeps the higher streak; null dates lose", () => {
    expect(mergeProgress({ ...base, streak: 3, lastActive: "2026-10-27" }, { ...base, streak: 5, lastActive: "2026-10-27" }).streak).toBe(5);
    expect(mergeProgress({ ...base, streak: 0, lastActive: null }, { ...base, streak: 4, lastActive: "2026-10-01" }).streak).toBe(4);
  });
  it("is symmetric for xp and lessons", () => {
    const a = { ...base, xp: 10, completed: { 1: 2 } }, b = { ...base, xp: 40, completed: { 1: 3, 4: 1 } };
    expect(mergeProgress(a, b).completed).toEqual(mergeProgress(b, a).completed);
    expect(mergeProgress(a, b).xp).toBe(mergeProgress(b, a).xp);
  });
});

describe("mergeById", () => {
  const item = (id: string, createdAt: string, title = id) => ({ id, createdAt, title });
  it("unions, prefers local on conflict, sorts newest first", () => {
    const out = mergeById([item("a", "2026-10-02", "local-a"), item("b", "2026-10-01")], [item("a", "2026-10-02", "remote-a"), item("c", "2026-10-03")]);
    expect(out.map((x) => x.id)).toEqual(["c", "a", "b"]);
    expect(out.find((x) => x.id === "a")!.title).toBe("local-a");
  });
  it("handles empty sides", () => {
    expect(mergeById([], [])).toEqual([]);
    expect(mergeById([item("a", "2026-10-01")], [])).toHaveLength(1);
  });
});

describe("row mappers round-trip", () => {
  const d: SavedDiscovery = { id: "1", title: "Window", summary: "Carved", phrase: { nepali: "यो के हो?", romanization: "Yo ke ho?", english: "What is this?" }, createdAt: "2026-10-27T10:00:00.000Z" };
  it("discoveries", () => {
    const row = discoveryToRow(d, "u1");
    expect(row.user_id).toBe("u1");
    expect(rowToDiscovery({ ...row, created_at: "2026-10-27T10:00:00+00:00" })).toEqual(d);
  });
  it("trips keep the full itinerary", () => {
    const t: SavedTrip = {
      id: "9", isMock: true, createdAt: "2026-10-27T10:00:00.000Z",
      request: { destination: "Patan", days: 1, interests: [], pace: "balanced", budget: "mid" },
      itinerary: { title: "T", summary: "S", tips: ["x"], days: [{ day_number: 1, title: "D", stops: [{ name: "N", slot: "morning", description: "d", category: "", tip: "" }] }] },
    };
    expect(rowToTrip({ ...tripToRow(t, "u1"), created_at: "2026-10-27T10:00:00Z" })).toEqual(t);
  });
});

describe("format helpers", () => {
  it("formats distances", () => {
    expect(formatDistance(0.85)).toBe("850 m");
    expect(formatDistance(3.94)).toBe("3.9 km");
    expect(formatDistance(null)).toBe("");
  });
  it("builds a plain maps url", () => expect(mapsUrl(27.6727, 85.3253)).toBe("https://www.google.com/maps/search/?api=1&query=27.6727,85.3253"));
  it("renders an itinerary as shareable text", () => {
    const txt = tripAsText({ title: "3 days", summary: "Nice", tips: ["Dress modestly"], days: [{ day_number: 1, title: "Patan", stops: [{ name: "Durbar Square", slot: "morning", description: "Walk", category: "", tip: "" }] }] });
    expect(txt).toContain("Day 1: Patan");
    expect(txt).toContain("Morning: Durbar Square - Walk");
    expect(txt).toContain("- Dress modestly");
    expect(txt).toContain("Check hours, prices and transport locally");
  });
});

describe("postcard", () => {
  const d: SavedDiscovery = { id: "1", title: "A".repeat(120), summary: "First sentence here. Second sentence follows and goes on for a while. " + "x ".repeat(200), phrase: null, createdAt: "" };
  it("caps headline and caption lengths and cuts at a sentence", () => {
    const c = localCard(d);
    expect(c.headline.length).toBeLessThanOrEqual(80);
    expect(c.caption.length).toBeLessThanOrEqual(251);
    expect(c.caption.startsWith("First sentence here.")).toBe(true);
    expect(c.nepali).toBe("");
  });
  it("falls back when there is no summary and includes the phrase when present", () => {
    expect(localCard({ ...d, summary: "" }).caption).toBe("A moment from Nepal.");
    const c = localCard({ ...d, summary: "Short.", phrase: { nepali: "नमस्ते", romanization: "Namaste", english: "Hello" } });
    expect(cardAsText(c)).toContain("नमस्ते");
    expect(cardAsText(c)).toContain("Namaste · Hello");
  });
});
