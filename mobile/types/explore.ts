import { z } from "zod";

const confidence = z.enum(["high", "medium", "low"]);

export const phraseSchema = z.object({
  nepali: z.string(), romanization: z.string(), english: z.string(), usage: z.string().default(""),
});

export const analyzeResponseSchema = z.object({
  analysis: z.object({
    title: z.string(),
    observations: z.array(z.string()),
    identified_place: z.string().nullable().optional(),
    identification_confidence: confidence,
    cultural_context: z.object({ text: z.string(), confidence, needs_verification: z.boolean() }),
    related_places: z.array(z.string()).default([]),
    suggested_activities: z.array(z.string()).default([]),
    phrase: phraseSchema.nullable().optional(),
  }),
  sources: z.array(z.object({ name: z.string(), url: z.string().nullable().optional() })).default([]),
  provider: z.string(),
  model: z.string(),
  is_mock: z.boolean(),
  disclaimer: z.string(),
});
export type AnalyzeResponse = z.infer<typeof analyzeResponseSchema>;

export const askResponseSchema = z.object({
  result: z.object({ answer: z.string(), confidence, needs_verification: z.boolean() }),
  provider: z.string(), model: z.string(), is_mock: z.boolean(),
});
export type AskResponse = z.infer<typeof askResponseSchema>;
