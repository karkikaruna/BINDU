import { z } from "zod";

const confidence = z.enum(["high", "medium", "low"]);
const provenance = { provider: z.string(), model: z.string(), is_mock: z.boolean() };

// ---- assistant ----
export const assistantResponseSchema = z.object({
  result: z.object({ answer: z.string(), confidence, needs_verification: z.boolean(), followups: z.array(z.string()).default([]) }),
  ...provenance,
});
export type AssistantResponse = z.infer<typeof assistantResponseSchema>;
export type ChatMessage = { role: "user" | "assistant"; content: string };

// ---- cards ----
export const cardResponseSchema = z.object({
  card: z.object({
    headline: z.string(), caption: z.string(), nepali: z.string().default(""), romanization: z.string().default(""),
    english: z.string().default(""), theme: z.enum(["forest", "terracotta", "himalaya", "marigold"]),
  }),
  ...provenance,
});
export type CardResponse = z.infer<typeof cardResponseSchema>;
export type CardRequest = { kind: "discovery" | "phrase" | "place"; title: string; body?: string; nepali?: string; english?: string };
