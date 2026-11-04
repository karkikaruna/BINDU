import { analyzeImage, ApiError, askAssistant, deleteAccount, generateCard, setAccessToken } from "@/services/api";

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

it("rejects a malformed server response instead of crashing the UI", async () => {
  respond(200, { result: { answer: 42 } });
  await expect(askAssistant([{ role: "user", content: "hi" }])).rejects.toMatchObject({ name: "ApiError", retryable: true });
});

it("maps server errors to safe messages and retryability", async () => {
  respond(429, { error: { code: 429, message: "Too many AI requests." } });
  await expect(askAssistant([{ role: "user", content: "hi" }])).rejects.toMatchObject({ message: "Too many AI requests.", status: 429, retryable: true });
  respond(422, { error: { code: 422, message: "Invalid request: messages." } });
  await expect(askAssistant([{ role: "user", content: "hi" }])).rejects.toMatchObject({ status: 422, retryable: false });
});

it("network failure becomes a friendly retryable error", async () => {
  (globalThis as any).fetch = jest.fn(async () => { throw new TypeError("Network request failed"); });
  const e = await askAssistant([{ role: "user", content: "hi" }]).catch((x) => x);
  expect(e).toBeInstanceOf(ApiError);
  expect(e.retryable).toBe(true);
  expect(e.message).toMatch(/Can't reach the BINDU server/);
});

it("sends the bearer token once signed in", async () => {
  respond(200, { result: { answer: "a", confidence: "low", needs_verification: true }, ...prov });
  setAccessToken("tok123");
  await askAssistant([{ role: "user", content: "hi" }]);
  expect((calls[0].init.headers as Record<string, string>).Authorization).toBe("Bearer tok123");
});

it("assistant and card endpoints", async () => {
  respond(200, { result: { answer: "a", confidence: "low", needs_verification: true }, ...prov });
  expect((await askAssistant(Array.from({ length: 20 }, (_, i) => ({ role: "user" as const, content: String(i) })))).result.followups).toEqual([]);
  expect(JSON.parse(calls[0].init.body as string).messages).toHaveLength(12); // only the latest 12 are sent
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

it("analyzeImage with base64 sends plain JSON to /explore/analyze-json (no multipart)", async () => {
  const ok = {
    analysis: { title: "T", observations: ["o"], identification_confidence: "low", cultural_context: { text: "c", confidence: "low", needs_verification: true } },
    provider: "meta", model: "muse-spark-1.3", is_mock: false, disclaimer: "d",
  };
  respond(200, ok);
  const out = await analyzeImage({ uri: "file:///x.jpg", mimeType: "image/jpeg", fileName: "x.jpg", base64: "QUJDRA==" }, " Who? ", "");
  expect(out.analysis.title).toBe("T");
  expect(calls[0].url).toMatch(/\/explore\/analyze-json$/);
  expect(typeof calls[0].init.body).toBe("string");
  expect((calls[0].init.headers as Record<string, string>)["Content-Type"]).toBe("application/json");
  expect(JSON.parse(calls[0].init.body as string)).toEqual({ image_base64: "QUJDRA==", question: "Who?", place_hint: null });
});
