import type { SavedDiscovery } from "@/stores/discoveries";
import type { CardResponse } from "@/types/features";

export type CardData = CardResponse["card"];

const firstSentences = (text: string, max: number): string => {
  const clean = text.replace(/\s+/g, " ").trim();
  if (clean.length <= max) return clean;
  const cut = clean.slice(0, max);
  const stop = Math.max(cut.lastIndexOf(". "), cut.lastIndexOf("! "), cut.lastIndexOf("? "));
  return stop > max * 0.4 ? cut.slice(0, stop + 1) : cut.replace(/\s+\S*$/, "") + "…";
};

/** A card built entirely on the device, so sharing works offline. AI can rewrite the caption later. */
export function localCard(d: SavedDiscovery): CardData {
  return {
    headline: d.title.length > 80 ? d.title.slice(0, 77) + "…" : d.title,
    caption: firstSentences(d.summary, 250) || "A moment from Nepal.",
    nepali: d.phrase?.nepali ?? "",
    romanization: d.phrase?.romanization ?? "",
    english: d.phrase?.english ?? "",
    theme: "forest",
  };
}

export function cardAsText(c: CardData): string {
  const lines = [c.headline, c.caption];
  if (c.nepali) lines.push("", c.nepali, [c.romanization, c.english].filter(Boolean).join(" · "));
  lines.push("", "Shared from BINDU: Explore Nepal. Understand its culture. Learn its language.");
  return lines.join("\n");
}

export const THEME_COLORS = { forest: "#174C3C", terracotta: "#C76B45", himalaya: "#387A9B", marigold: "#E8A33D" } as const;
