import { Platform } from "react-native";
import { z } from "zod";
import { analyzeResponseSchema, askResponseSchema, type AnalyzeResponse, type AskResponse } from "@/types/explore";
import {
  assistantResponseSchema, cardResponseSchema, categoriesSchema, evaluateResponseSchema, nearbyResponseSchema, practiceResponseSchema, tripResponseSchema,
  type AssistantResponse, type CardRequest, type CardResponse, type ChatMessage, type EvaluateResponse, type NearbyResponse, type PracticeResponse, type TripRequest, type TripResponse,
} from "@/types/features";

/**
 * Base URL of the BINDU API. On a physical phone `localhost` is the phone itself, so set EXPO_PUBLIC_API_URL
 * to your computer's LAN address (e.g. http://192.168.1.20:8000/api/v1). The Android emulator reaches the host at 10.0.2.2.
 */
export const API_URL = (process.env.EXPO_PUBLIC_API_URL ?? (Platform.OS === "android" ? "http://10.0.2.2:8000/api/v1" : "http://localhost:8000/api/v1")).replace(/\/$/, "");
console.log("API_URL =", API_URL);
const TIMEOUT_MS = 75_000;

export class ApiError extends Error {
  constructor(message: string, public status: number | null, public retryable: boolean) {
    super(message);
    this.name = "ApiError";
  }
}

// Set by the auth session (see stores/session.ts). With no token, requests are made as a guest.
let accessToken: string | null = null;
export const setAccessToken = (t: string | null) => { accessToken = t; };

async function request<T>(path: string, init: RequestInit, schema: z.ZodType<T>): Promise<T> {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), TIMEOUT_MS);
  try {
    const headers: Record<string, string> = { Accept: "application/json", ...(init.headers as Record<string, string> | undefined) };
    if (accessToken) headers.Authorization = `Bearer ${accessToken}`;
    let res: Response;
    try {
      res = await fetch(`${API_URL}${path}`, { ...init, headers, signal: ctrl.signal });
    } catch (e) {
      if ((e as Error).name === "AbortError") throw new ApiError("The request timed out. Check your connection and try again.", null, true);
      throw new ApiError("Can't reach the BINDU server. Check your connection and that the backend is running.", null, true);
    }
    const body = await res.json().catch(() => null);
    if (!res.ok) {
      const msg = body?.error?.message ?? `Request failed (${res.status}).`;
      throw new ApiError(msg, res.status, res.status === 429 || res.status >= 500);
    }
    const parsed = schema.safeParse(body);
    if (!parsed.success) throw new ApiError("The server sent an unexpected response.", res.status, true);
    return parsed.data;
  } finally {
    clearTimeout(timer);
  }
}

export type PickedImage = { uri: string; mimeType: string; fileName: string };

async function toFormPart(img: PickedImage): Promise<Blob | { uri: string; name: string; type: string }> {
  if (Platform.OS === "web") {
    const blob = await (await fetch(img.uri)).blob();
    return new File([blob], img.fileName, { type: img.mimeType || blob.type });
  }
  return { uri: img.uri, name: img.fileName, type: img.mimeType };
}

export async function analyzeImage(img: PickedImage, question: string, placeHint: string): Promise<AnalyzeResponse> {
  const form = new FormData();
  form.append("image", (await toFormPart(img)) as never);
  if (question.trim()) form.append("question", question.trim());
  if (placeHint.trim()) form.append("place_hint", placeHint.trim());
  return request("/explore/analyze", { method: "POST", body: form }, analyzeResponseSchema);
}

export async function askFollowUp(question: string, contextTitle: string, contextSummary: string): Promise<AskResponse> {
  return request(
    "/explore/ask",
    { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ question, context_title: contextTitle, context_summary: contextSummary }) },
    askResponseSchema,
  );
}


const postJson = <T,>(path: string, body: unknown, schema: z.ZodType<T>) =>
  request(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }, schema);

export const generateTrip = (req: TripRequest): Promise<TripResponse> => postJson("/trips/generate", req, tripResponseSchema);

export const getNearby = (lat: number, lng: number, category?: string, radiusKm = 50): Promise<NearbyResponse> => {
  const q = new URLSearchParams({ lat: String(lat), lng: String(lng), radius_km: String(radiusKm) });
  if (category) q.set("category", category);
  return request(`/places/nearby?${q}`, { method: "GET" }, nearbyResponseSchema);
};

export const searchPlaces = (query: string, category?: string): Promise<NearbyResponse> => {
  const q = new URLSearchParams({ q: query });
  if (category) q.set("category", category);
  return request(`/places/search?${q}`, { method: "GET" }, nearbyResponseSchema);
};

export const getPlaceCategories = (): Promise<string[]> => request("/places/categories", { method: "GET" }, categoriesSchema);

export const generatePractice = (topic: string, level: string, count: number): Promise<PracticeResponse> =>
  postJson("/practice/generate", { topic, level, count }, practiceResponseSchema);

export const evaluatePractice = (promptEn: string, expectedNepali: string, userAnswer: string): Promise<EvaluateResponse> =>
  postJson("/practice/evaluate", { prompt_en: promptEn, expected_nepali: expectedNepali, user_answer: userAnswer }, evaluateResponseSchema);

export const askAssistant = (messages: ChatMessage[]): Promise<AssistantResponse> =>
  postJson("/assistant/chat", { messages: messages.slice(-12) }, assistantResponseSchema);

export const deleteAccount = (): Promise<{ deleted: boolean }> =>
  request("/account", { method: "DELETE" }, z.object({ deleted: z.boolean() }));

export const generateCard = (req: CardRequest): Promise<CardResponse> => postJson("/cards/generate", req, cardResponseSchema);
