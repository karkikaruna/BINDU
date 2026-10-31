import { analyzeImage, ApiError, askAssistant, deleteAccount, evaluatePractice, generateCard, generatePractice, generateTrip, getNearby, searchPlaces, setAccessToken } from "@/services/api";

type Call = { url: string; init: RequestInit };
const calls: Call[] = [];
const respond = (status: number, body: unknown) => {
  (globalThis as any).fetch = jest.fn(async (url: string, init: RequestInit) => {
    calls.push({ url, init });
    return { ok: status < 400, status, json: async () => body, text: async () => JSON.stringify(body) } as Response;
  });
};
beforeEach(() => { calls.length = 0; setAccessToken(null); });

const prov = { provider: "mock", model: "m", is_mock: true };

it("generateTrip posts the request and validates the response shape", async () => {
  respond(200, { itinerary: { title: "T", summary: "S", days: [{ day_number: 1, title: "D", stops: [{ name: "N", slot: "morning", description: "d" }] }], tips: [] }, ...prov, disclaimer: "x" });
  const r = await generateTrip({ destination: "Patan", days: 1, interests: [], pace: "balanced", budget: "mid" });
  expect(r.itinerary.days[0].stops[0].category).toBe("");
  expect(calls[0].url).toMatch(/\/trips\/generate$/);
  expect(JSON.parse(calls[0].init.body as string)).toMatchObject({ destination: "Patan", days: 1 });
});

it("rejects a malformed server response instead of crashing the UI", async () => {
  respond(200, { itinerary: { title: "T" } });
  await expect(generateTrip({ destination: "Patan", days: 1, interests: [], pace: "balanced", budget: "mid" })).rejects.toMatchObject({ name: "ApiError", retryable: true });
});

it("maps server errors to safe messages and retryability", async () => {
  respond(429, { error: { code: 429, message: "Too many AI requests." } });
  await expect(askAssistant([{ role: "user", content: "hi" }])).rejects.toMatchObject({ message: "Too many AI requests.", status: 429, retryable: true });
  respond(422, { error: { code: 422, message: "Invalid request: days." } });
  await expect(generateTrip({ destination: "P", days: 0, interests: [], pace: "balanced", budget: "mid" })).rejects.toMatchObject({ status: 422, retryable: false });
});

it("network failure becomes a friendly retryable error", async () => {
  (globalThis as any).fetch = jest.fn(async () => { throw new TypeError("Network request failed"); });
  const e = await askAssistant([{ role: "user", content: "hi" }]).catch((x) => x);
  expect(e).toBeInstanceOf(ApiError);
  expect(e.retryable).toBe(true);
  expect(e.message).toMatch(/Can't reach the BINDU server/);
});

it("sends the bearer token once signed in", async () => {
  respond(200, { places: [], provider: "curated", note: "n" });
  setAccessToken("tok123");
  await getNearby(27.7, 85.3);
  expect((calls[0].init.headers as Record<string, string>).Authorization).toBe("Bearer tok123");
});

it("builds nearby and search queries", async () => {
  respond(200, { places: [], provider: "curated", note: "n" });
  await getNearby(27.7, 85.3, "Local food", 20);
  expect(calls[0].url).toMatch(/\/places\/nearby\?lat=27\.7&lng=85\.3&radius_km=20&category=Local\+food$/);
  await searchPlaces("bhaktapur");
  expect(calls[1].url).toMatch(/\/places\/search\?q=bhaktapur$/);
});

it("practice, assistant and card endpoints", async () => {
  respond(200, { result: { items: [{ prompt_en: "Hi", expected_nepali: "नमस्ते", romanization: "Namaste" }] }, ...prov });
  expect((await generatePractice("Greetings", "Beginner", 3)).result.items[0].hint).toBe("");
  respond(200, { result: { correct: true, score: 100, feedback: "ok" }, method: "exact", ...prov });
  expect((await evaluatePractice("Hi", "नमस्ते", "नमस्ते")).method).toBe("exact");
  expect(JSON.parse(calls[1].init.body as string)).toEqual({ prompt_en: "Hi", expected_nepali: "नमस्ते", user_answer: "नमस्ते" });
  respond(200, { result: { answer: "a", confidence: "low", needs_verification: true }, ...prov });
  expect((await askAssistant(Array.from({ length: 20 }, (_, i) => ({ role: "user" as const, content: String(i) })))).result.followups).toEqual([]);
  expect(JSON.parse(calls[2].init.body as string).messages).toHaveLength(12); // only the latest 12 are sent
  respond(200, { card: { headline: "H", caption: "C", theme: "forest" }, ...prov });
  expect((await generateCard({ kind: "phrase", title: "H" })).card.nepali).toBe("");
});

it("analyzeImage is unchanged: multipart with optional fields", async () => {
  respond(200, { nope: true });
  await expect(analyzeImage({ uri: "file:///x.jpg", mimeType: "image/jpeg", fileName: "x.jpg" }, "", "")).rejects.toBeInstanceOf(ApiError);
});

it("deleteAccount sends DELETE /account with the bearer token and validates the reply", async () => {
  setAccessToken("tok");
  respond(200, { deleted: true });
  expect(await deleteAccount()).toEqual({ deleted: true });
  expect(calls[0].url).toMatch(/\/account$/);
  expect(calls[0].init.method).toBe("DELETE");
  expect((calls[0].init.headers as any).Authorization).toBe("Bearer tok");
});

it("deleteAccount surfaces a server refusal as an ApiError (so the app does not sign out)", async () => {
  respond(502, { error: { code: 502, message: "The account could not be deleted. Please try again." } });
  await expect(deleteAccount()).rejects.toMatchObject({ name: "ApiError", status: 502, retryable: true });
});
