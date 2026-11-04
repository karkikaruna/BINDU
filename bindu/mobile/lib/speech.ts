import { createAudioPlayer, setAudioModeAsync, type AudioPlayer } from "expo-audio";
import * as Speech from "expo-speech";
import { NEPALI_AUDIO } from "./audioMap";
import { API_URL } from "@/services/api";

/**
 * Text-to-speech for the lesson player. Everything is spoken in Nepali: questions, options, word tiles and answers.
 *  1. Pre-made Swar clips (`lib/audioMap.ts`, made by scripts/generate_nepali_audio.py) hosted in the public Supabase `audio` bucket,
 *     under ne/. They are NOT bundled in the app, so the app stays small: one consistent voice, fetched on demand.
 *  2. For text with no clip (or if the bucket can't be reached): the backend's Swar voice (`GET /tts`, cached on the server).
 *  3. If the server can't be reached either: the device's Nepali (or Hindi, which reads Devanagari) voice.
 * Only one thing speaks at a time: starting anything stops whatever was playing, and `stopSpeech()` silences everything.
 */

export type SpeakResult = "ok" | "unavailable" | "superseded";

const SERVER_TIMEOUT_MS = 8_000;
const SERVER_BACKOFF_MS = 60_000;

const SUPABASE_URL = (process.env.EXPO_PUBLIC_SUPABASE_URL ?? "").replace(/\/$/, "");
const AUDIO_BUCKET = process.env.EXPO_PUBLIC_AUDIO_BUCKET ?? "audio";
const CLIP_BASE = SUPABASE_URL ? `${SUPABASE_URL}/storage/v1/object/public/${AUDIO_BUCKET}/ne` : "";

/** Public URL of the hosted clip for this exact text, or null if there is none (or Supabase isn't configured on this build). */
export const clipUrl = (text: string): string | null => {
  const file = NEPALI_AUDIO[text];
  return file && CLIP_BASE ? `${CLIP_BASE}/${encodeURIComponent(file)}` : null;
};

let player: AudioPlayer | null = null;
let generation = 0; // bumped by every request, so a slow answer that arrives late never talks over a newer one
const downUntil = { clips: 0, server: 0 }; // per source: skip one that just failed with a 5xx / network error for a minute
let deviceVoiceLang: string | null | undefined; // undefined = not looked up yet

export const ttsUrl = (text: string): string => `${API_URL}/tts?text=${encodeURIComponent(text)}`;

function releasePlayer() {
  const p = player;
  player = null;
  if (!p) return;
  try { p.pause(); } catch { /* already released */ }
  try { p.remove(); } catch { /* already released */ }
}

export function stopSpeech(): void {
  generation++;
  releasePlayer();
  Speech.stop().catch(() => undefined);
}

let audioModeSet = false;
function ensureAudioMode() {
  if (audioModeSet) return;
  audioModeSet = true;
  setAudioModeAsync({ playsInSilentMode: true }).catch(() => undefined);
}

type Source = keyof typeof downUntil;

/**
 * Play audio from a URL (a hosted clip or the server's TTS). The request first checks the URL is really audio, and doubles as a
 * warm-up: when the player then asks for the same URL it is served from the cache. "failed" lets the caller try the next source.
 */
async function playUrl(url: string, source: Source, mine: number): Promise<"played" | "failed" | "superseded"> {
  if (Date.now() < downUntil[source]) return "failed";
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), SERVER_TIMEOUT_MS);
  try {
    const res = await fetch(url, { signal: ctrl.signal });
    try { await res.body?.cancel?.(); } catch { /* body not streamable here; nothing to free */ }
    if (mine !== generation) return "superseded";
    if (!res.ok || !(res.headers?.get?.("content-type") ?? "audio/wav").startsWith("audio")) {
      // 4xx (a missing clip, a rate limit, bad text) is not an outage; 5xx/network means this source is down, so skip it for a while.
      if (res.status >= 500) downUntil[source] = Date.now() + SERVER_BACKOFF_MS;
      return "failed";
    }
    ensureAudioMode();
    releasePlayer();
    const p = createAudioPlayer({ uri: url });
    player = p;
    p.addListener("playbackStatusUpdate", (s) => { if (s.didJustFinish && player === p) releasePlayer(); });
    p.play();
    return "played";
  } catch {
    if (mine !== generation) return "superseded";
    downUntil[source] = Date.now() + SERVER_BACKOFF_MS;
    return "failed";
  } finally {
    clearTimeout(timer);
  }
}

const normLang = (l: string) => l.toLowerCase().replace("_", "-");

/** Nepali if the device has it, else Hindi (same script, widely installed), else nothing. Only a non-empty answer is remembered. */
async function findDeviceVoiceLang(): Promise<string | null> {
  if (deviceVoiceLang !== undefined) return deviceVoiceLang;
  try {
    const voices = await Speech.getAvailableVoicesAsync();
    if (!voices.length) return null; // the web lists voices lazily; try again next time
    const has = (prefix: string) => voices.some((v) => normLang(v.language).startsWith(prefix));
    deviceVoiceLang = has("ne") ? "ne-NP" : has("hi") ? "hi-IN" : null;
  } catch {
    deviceVoiceLang = null;
  }
  return deviceVoiceLang;
}

/** Read Nepali text aloud (hosted clip, else server, else device voice). Resolves when playback has been started, not when it finishes. */
export async function speakNepali(text: string): Promise<SpeakResult> {
  const spoken = text.replace(/\s+/g, " ").trim();
  if (!spoken) return "unavailable";
  stopSpeech();
  const mine = generation;

  const clip = clipUrl(spoken);
  if (clip) {
    const hosted = await playUrl(clip, "clips", mine);
    if (hosted === "played") return "ok";
    if (hosted === "superseded") return "superseded";
  }

  const server = await playUrl(ttsUrl(spoken), "server", mine);
  if (server === "played") return "ok";
  if (server === "superseded") return "superseded";

  const lang = await findDeviceVoiceLang();
  if (mine !== generation) return "superseded";
  if (!lang) return "unavailable";
  ensureAudioMode();
  try {
    Speech.speak(spoken, { language: lang, rate: 0.85 });
    return "ok";
  } catch {
    return "unavailable";
  }
}

/** Test hook: forget cached server/voice state. */
export function __resetSpeechForTests(): void {
  generation = 0;
  downUntil.clips = 0;
  downUntil.server = 0;
  deviceVoiceLang = undefined;
  audioModeSet = false;
  player = null;
}
