jest.mock("@/lib/storage", () => ({ safeStorage: { getItem: async () => null, setItem: async () => undefined, removeItem: async () => undefined } }));
process.env.EXPO_PUBLIC_SUPABASE_URL = "https://proj.supabase.co";
process.env.EXPO_PUBLIC_SUPABASE_ANON_KEY = "anon-key";

// Required (not imported) so the env vars above are set before lib/supabase reads them at module load.
/* eslint-disable @typescript-eslint/no-require-imports */
const { AuthError, requestPasswordReset, restSelect, restUpsert, signIn, signUp } = require("@/lib/supabase") as typeof import("@/lib/supabase");
const { syncNow } = require("@/lib/sync") as typeof import("@/lib/sync");
const { setAccessToken } = require("@/services/api") as typeof import("@/services/api");
const { useDiscoveries } = require("@/stores/discoveries") as typeof import("@/stores/discoveries");
const { useProgress } = require("@/stores/progress") as typeof import("@/stores/progress");
const { useSession } = require("@/stores/session") as typeof import("@/stores/session");
const { useTrips } = require("@/stores/trips") as typeof import("@/stores/trips");

type Call = { url: string; init: RequestInit };
let calls: Call[];
let routes: Record<string, (init: RequestInit) => { status: number; body: unknown }>;
beforeEach(() => {
  calls = [];
  routes = {};
  setAccessToken(null);
  useSession.setState({ refreshToken: null, userId: null, email: null, accessToken: null, expiresAt: 0 });
  useDiscoveries.setState({ items: [] });
  useTrips.setState({ items: [] });
  useProgress.getState().reset();
  (globalThis as any).fetch = jest.fn(async (url: string, init: RequestInit) => {
    calls.push({ url, init });
    const key = Object.keys(routes).find((k) => url.includes(k));
    const r = key ? routes[key](init) : { status: 404, body: {} };
    return { ok: r.status < 400, status: r.status, json: async () => r.body, text: async () => (r.body == null ? "" : JSON.stringify(r.body)) } as Response;
  });
});

const tokenBody = { access_token: "acc", refresh_token: "ref", expires_in: 3600, user: { id: "u1", email: "a@b.co" } };

describe("supabase auth client", () => {
  it("signs in with the password grant and the anon key", async () => {
    routes["token?grant_type=password"] = () => ({ status: 200, body: tokenBody });
    const t = await signIn("a@b.co", "password1");
    expect(t).toMatchObject({ accessToken: "acc", refreshToken: "ref", userId: "u1", email: "a@b.co" });
    expect((calls[0].init.headers as any).apikey).toBe("anon-key");
  });
  it("maps wrong credentials to a friendly message", async () => {
    routes["token?grant_type=password"] = () => ({ status: 400, body: { msg: "Invalid login credentials" } });
    await expect(signIn("a@b.co", "bad")).rejects.toMatchObject({ message: "Wrong email or password.", status: 400 });
  });
  it("sign-up distinguishes immediate session from email confirmation", async () => {
    routes["signup"] = () => ({ status: 200, body: { id: "u1", email: "a@b.co" } });
    expect(await signUp("a@b.co", "password1")).toEqual({ needsConfirmation: true });
    routes["signup"] = () => ({ status: 200, body: tokenBody });
    expect(await signUp("a@b.co", "password1")).toHaveProperty("tokens");
  });
  it("password reset posts only the email to /recover and never needs a session", async () => {
    routes["recover"] = () => ({ status: 200, body: {} });
    await requestPasswordReset("a@b.co");
    expect(calls[0].url).toMatch(/\/auth\/v1\/recover$/);
    expect(JSON.parse(calls[0].init.body as string)).toEqual({ email: "a@b.co" });
    expect((calls[0].init.headers as any).Authorization).toBe("Bearer anon-key");
  });
  it("password reset failure is an AuthError", async () => {
    routes["recover"] = () => ({ status: 429, body: { msg: "For security purposes, you can only request this once every 60 seconds" } });
    await expect(requestPasswordReset("a@b.co")).rejects.toBeInstanceOf(AuthError);
  });
  it("network failure is an AuthError, not a crash", async () => {
    (globalThis as any).fetch = jest.fn(async () => { throw new TypeError("offline"); });
    await expect(signIn("a@b.co", "password1")).rejects.toBeInstanceOf(AuthError);
  });
});

describe("session store", () => {
  it("sign-in stores identity, sets the API token, and sign-out clears everything", async () => {
    routes["token?grant_type=password"] = () => ({ status: 200, body: tokenBody });
    routes["logout"] = () => ({ status: 204, body: null });
    await useSession.getState().signIn("a@b.co", "password1");
    expect(useSession.getState()).toMatchObject({ userId: "u1", refreshToken: "ref" });
    await useSession.getState().signOut();
    expect(useSession.getState()).toMatchObject({ userId: null, refreshToken: null, accessToken: null });
  });
  it("restore keeps the session on a network error but drops it when the refresh token is rejected", async () => {
    useSession.setState({ refreshToken: "old", userId: "u1", email: "a@b.co" });
    (globalThis as any).fetch = jest.fn(async () => { throw new TypeError("offline"); });
    await useSession.getState().restore();
    expect(useSession.getState().refreshToken).toBe("old");
    routes["token?grant_type=refresh_token"] = () => ({ status: 400, body: { msg: "Invalid Refresh Token" } });
    (globalThis as any).fetch = jest.fn(async (url: string, init: RequestInit) => { const r = routes["token?grant_type=refresh_token"](init); return { ok: false, status: r.status, json: async () => r.body, text: async () => "" } as Response; });
    await useSession.getState().restore();
    expect(useSession.getState().refreshToken).toBeNull();
  });
  it("getToken returns null when signed out and refreshes an expiring token", async () => {
    expect(await useSession.getState().getToken()).toBeNull();
    useSession.setState({ refreshToken: "ref", userId: "u1", accessToken: "stale", expiresAt: Math.floor(Date.now() / 1000) + 10 });
    routes["token?grant_type=refresh_token"] = () => ({ status: 200, body: { ...tokenBody, access_token: "fresh" } });
    expect(await useSession.getState().getToken()).toBe("fresh");
  });
});

describe("postgrest helpers", () => {
  it("upsert sets merge-duplicates and on_conflict", async () => {
    routes["/rest/v1/trips"] = () => ({ status: 201, body: null });
    await restUpsert("trips", "tok", [{ id: "1" }], "user_id,id");
    expect(calls[0].url).toBe("https://proj.supabase.co/rest/v1/trips?on_conflict=user_id,id");
    expect((calls[0].init.headers as any).Prefer).toContain("merge-duplicates");
    expect((calls[0].init.headers as any).Authorization).toBe("Bearer tok");
  });
  it("surfaces HTTP failures", async () => {
    routes["/rest/v1/trips"] = () => ({ status: 403, body: {} });
    await expect(restSelect("trips", "tok")).rejects.toMatchObject({ name: "RestError", status: 403 });
  });
});

describe("syncNow", () => {
  const signedIn = () => useSession.setState({ refreshToken: "ref", userId: "u1", email: "a@b.co", accessToken: "acc", expiresAt: Math.floor(Date.now() / 1000) + 3000 });

  it("does nothing when signed out", async () => {
    expect(await syncNow()).toMatchObject({ ok: false, reason: "signed-out" });
    expect(calls).toHaveLength(0);
  });

  it("merges remote data into local stores and pushes the merged result", async () => {
    signedIn();
    useProgress.setState({ xp: 50, completed: { 1: 2 }, streak: 1, lastActive: "2026-10-26" });
    useDiscoveries.setState({ items: [{ id: "local", title: "L", summary: "", phrase: null, createdAt: "2026-10-27T00:00:00.000Z" }] });
    routes["/rest/v1/progress"] = (init) => (init.method === "GET" ? { status: 200, body: [{ user_id: "u1", xp: 80, streak: 4, last_active: "2026-10-27", completed: { "1": 3, "2": 1 } }] } : { status: 201, body: null });
    routes["/rest/v1/discoveries"] = (init) => (init.method === "GET" ? { status: 200, body: [{ id: "remote", user_id: "u1", title: "R", summary: "s", phrase: null, created_at: "2026-10-25T00:00:00Z" }] } : { status: 201, body: null });
    routes["/rest/v1/trips"] = (init) => (init.method === "GET" ? { status: 200, body: [] } : { status: 201, body: null });
    routes["/rest/v1/profiles"] = (init) => (init.method === "GET" ? { status: 200, body: [] } : { status: 201, body: null });

    const r = await syncNow();
    expect(r).toEqual({ ok: true, discoveries: 2, trips: 0 });
    expect(useProgress.getState()).toMatchObject({ xp: 80, streak: 4, completed: { 1: 3, 2: 1 } });
    expect(useDiscoveries.getState().items.map((d) => d.id)).toEqual(["local", "remote"]);
    const pushed = calls.filter((c) => c.init.method === "POST");
    expect(pushed.map((c) => c.url.match(/v1\/(\w+)/)![1]).sort()).toEqual(["discoveries", "profiles", "progress"]); // no empty trips upsert
    const discBody = JSON.parse(pushed.find((c) => c.url.includes("discoveries"))!.init.body as string);
    expect(discBody.every((row: any) => row.user_id === "u1")).toBe(true);
  });

  it("reports a safe message and leaves local data untouched when the server fails", async () => {
    signedIn();
    useProgress.setState({ xp: 50 });
    routes["/rest/v1/"] = () => ({ status: 500, body: {} });
    const r = await syncNow();
    expect(r).toMatchObject({ ok: false, reason: "error" });
    expect(useProgress.getState().xp).toBe(50);
  });
});
