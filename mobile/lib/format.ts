import type { Itinerary } from "@/types/features";

const SLOT = { morning: "Morning", afternoon: "Afternoon", evening: "Evening" } as const;

/** Plain-text version of an itinerary for the system share sheet. */
export function tripAsText(it: Itinerary): string {
  const lines = [it.title, it.summary, ""];
  for (const d of it.days) {
    lines.push(`Day ${d.day_number}: ${d.title}`);
    for (const s of d.stops) lines.push(`  ${SLOT[s.slot]}: ${s.name} - ${s.description}`);
    lines.push("");
  }
  if (it.tips.length) lines.push("Tips:", ...it.tips.map((t) => `- ${t}`), "");
  lines.push("Planned with BINDU. Check hours, prices and transport locally.");
  return lines.join("\n");
}

/** "850 m" under a kilometre, otherwise "3.9 km". */
export function formatDistance(km: number | null | undefined): string {
  if (km == null) return "";
  return km < 1 ? `${Math.round(km * 1000)} m` : `${km.toFixed(1)} km`;
}

/** Cross-platform maps link (opens Google Maps in the browser or the maps app) for a coordinate. */
export const mapsUrl = (lat: number, lng: number): string => `https://www.google.com/maps/search/?api=1&query=${lat},${lng}`;
