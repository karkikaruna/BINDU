import { z } from "zod";

const confidence = z.enum(["high", "medium", "low"]);
const provenance = { provider: z.string(), model: z.string(), is_mock: z.boolean() };

// ---- trips ----
export const stopSchema = z.object({
  name: z.string(), slot: z.enum(["morning", "afternoon", "evening"]), description: z.string(),
  category: z.string().default(""), tip: z.string().default(""),
});
export const itinerarySchema = z.object({
  title: z.string(), summary: z.string(),
  days: z.array(z.object({ day_number: z.number(), title: z.string(), stops: z.array(stopSchema) })),
  tips: z.array(z.string()).default([]),
});
export const tripResponseSchema = z.object({ itinerary: itinerarySchema, ...provenance, disclaimer: z.string() });
export type Itinerary = z.infer<typeof itinerarySchema>;
export type TripResponse = z.infer<typeof tripResponseSchema>;
export type TripRequest = { destination: string; days: number; interests: string[]; pace: "relaxed" | "balanced" | "packed"; budget: "budget" | "mid" | "comfortable" };

// ---- places ----
export const placeSchema = z.object({
  id: z.string(), name: z.string(), category: z.string(), area: z.string(), latitude: z.number(), longitude: z.number(),
  blurb: z.string(), distance_km: z.number().nullable().optional(), source_name: z.string().nullable().optional(), source_url: z.string().nullable().optional(),
});
export const nearbyResponseSchema = z.object({ places: z.array(placeSchema), provider: z.string(), note: z.string() });
export type Place = z.infer<typeof placeSchema>;
export type NearbyResponse = z.infer<typeof nearbyResponseSchema>;
export const categoriesSchema = z.array(z.string());

// ---- practice ----
export const practiceItemSchema = z.object({ prompt_en: z.string(), expected_nepali: z.string(), romanization: z.string(), hint: z.string().default("") });
export const practiceResponseSchema = z.object({ result: z.object({ items: z.array(practiceItemSchema) }), ...provenance });
export const evaluateResponseSchema = z.object({
  result: z.object({ correct: z.boolean(), score: z.number(), feedback: z.string(), corrected: z.string().default("") }),
  method: z.enum(["exact", "ai"]), ...provenance,
});
export type PracticeItem = z.infer<typeof practiceItemSchema>;
export type PracticeResponse = z.infer<typeof practiceResponseSchema>;
export type EvaluateResponse = z.infer<typeof evaluateResponseSchema>;

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
