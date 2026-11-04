const mockPlayer = () => ({ play: jest.fn(), pause: jest.fn(), remove: jest.fn(), addListener: jest.fn() });
const players: (ReturnType<typeof mockPlayer> & { source?: unknown })[] = [];
jest.mock("expo-audio", () => ({
  setAudioModeAsync: jest.fn(async () => undefined),
  createAudioPlayer: jest.fn((source: unknown) => { const p = Object.assign(mockPlayer(), { source }); players.push(p); return p; }),
}));
jest.mock("expo-speech", () => ({
  speak: jest.fn(),
  stop: jest.fn(async () => undefined),
  getAvailableVoicesAsync: jest.fn(async () => []),
}));
process.env.EXPO_PUBLIC_API_URL = "http://api.test/api/v1";

/* eslint-disable @typescript-eslint/no-require-imports */
const Speech = require("expo-speech") as jest.Mocked<typeof import("expo-speech")>;
const audio = require("expo-audio") as { createAudioPlayer: jest.Mock };
const { speakNepali, stopSpeech, ttsUrl, __resetSpeechForTests } = require("@/lib/speech") as typeof import("@/lib/speech");

type FakeRes = { ok: boolean; status: number; headers: { get: (k: string) => string | null }; body?: { cancel: () => Promise<void> } };
const wav = (): FakeRes => ({ ok: true, status: 200, headers: { get: () => "audio/wav" }, body: { cancel: async () => undefined } });
const fail = (status: number): FakeRes => ({ ok: false, status, headers: { get: () => "application/json" } });
const setFetch = (impl: (url: string) => Promise<FakeRes>) => { (globalThis as any).fetch = jest.fn((url: string) => impl(url)); };
const voices = (...langs: string[]) => Speech.getAvailableVoicesAsync.mockResolvedValue(langs.map((language) => ({ identifier: language, name: language, quality: "Default", language })) as never);

beforeEach(() => {
  jest.clearAllMocks();
  players.length = 0;
  __resetSpeechForTests();
  Speech.getAvailableVoicesAsync.mockResolvedValue([]);
});

describe("Nepali answers", () => {
  it("streams the server voice, asking for exactly this text", async () => {
    setFetch(async () => wav());
    expect(await speakNepali("  नमस्ते  ")).toBe("ok");
    expect((globalThis as any).fetch.mock.calls[0][0]).toBe(ttsUrl("नमस्ते"));
    expect(ttsUrl("नमस्ते")).toBe(`http://api.test/api/v1/tts?text=${encodeURIComponent("नमस्ते")}`);
    expect(audio.createAudioPlayer).toHaveBeenCalledWith({ uri: ttsUrl("नमस्ते") });
    expect(players[0].play).toHaveBeenCalled();
    expect(Speech.speak).not.toHaveBeenCalled();
  });

  it("falls back to the device Nepali voice when the server is down, and stops asking the server for a while", async () => {
    voices("en-US", "ne-NP");
    setFetch(async () => { throw new TypeError("offline"); });
    expect(await speakNepali("धन्यवाद")).toBe("ok");
    expect(Speech.speak).toHaveBeenCalledWith("धन्यवाद", expect.objectContaining({ language: "ne-NP" }));
    await speakNepali("कृपया");
    expect((globalThis as any).fetch).toHaveBeenCalledTimes(1); // second tap skipped the dead server
    expect(Speech.speak).toHaveBeenCalledTimes(2);
  });

  it("uses a Hindi voice (same script) when the device has no Nepali one", async () => {
    voices("en-US", "hi_IN");
    setFetch(async () => fail(503));
    await speakNepali("तीन");
    expect(Speech.speak).toHaveBeenCalledWith("तीन", expect.objectContaining({ language: "hi-IN" }));
  });

  it("reports unavailable instead of garbling Devanagari with an English voice", async () => {
    voices("en-US", "fr-FR");
    setFetch(async () => fail(503));
    expect(await speakNepali("तीन")).toBe("unavailable");
    expect(Speech.speak).not.toHaveBeenCalled();
  });

  it("a rate-limit answer falls back for this tap but does not mark the server as down", async () => {
    voices("ne-NP");
    setFetch(async () => fail(429));
    await speakNepali("एक");
    await speakNepali("दुई");
    expect((globalThis as any).fetch).toHaveBeenCalledTimes(2);
  });

  it("every option uses the same engine, so the right answer can't be told apart by its voice", async () => {
    setFetch(async () => wav());
    for (const o of ["नमस्ते", "धन्यवाद", "माफ गर्नुहोस्", "अलविदा"]) await speakNepali(o);
    expect(audio.createAudioPlayer).toHaveBeenCalledTimes(4);
    expect(Speech.speak).not.toHaveBeenCalled();
  });

  it("a slow answer never talks over a newer request", async () => {
    let release!: (r: FakeRes) => void;
    setFetch((url) => (url.includes(encodeURIComponent("पहिलो")) ? new Promise<FakeRes>((res) => { release = res; }) : Promise.resolve(wav())));
    const first = speakNepali("पहिलो");
    const second = speakNepali("दोस्रो");
    expect(await second).toBe("ok");
    release(wav());
    expect(await first).toBe("superseded");
    expect(audio.createAudioPlayer).toHaveBeenCalledTimes(1);
    expect(players[0].source).toEqual({ uri: ttsUrl("दोस्रो") });
  });

  it("stopSpeech silences the player and cancels a request still in flight", async () => {
    let release!: (r: FakeRes) => void;
    setFetch(() => new Promise<FakeRes>((res) => { release = res; }));
    const pending = speakNepali("एक");
    stopSpeech();
    release(wav());
    expect(await pending).toBe("superseded");
    expect(audio.createAudioPlayer).not.toHaveBeenCalled();

    setFetch(async () => wav());
    await speakNepali("दुई");
    stopSpeech();
    expect(players[0].pause).toHaveBeenCalled();
    expect(players[0].remove).toHaveBeenCalled();
  });
});
