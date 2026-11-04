jest.mock("@/lib/storage", () => ({ safeStorage: { getItem: async () => null, setItem: async () => undefined, removeItem: async () => undefined } }));
process.env.EXPO_PUBLIC_SUPABASE_URL = "https://proj.supabase.co";
process.env.EXPO_PUBLIC_SUPABASE_ANON_KEY = "anon-key";

// Required (not imported) so the env vars above are set before lib/supabase reads them at module load.
/* eslint-disable @typescript-eslint/no-require-imports */
const { AuthError, requestPasswordReset, restSelect, restUpsert, signIn, signUp } = require("@/lib/supabase") as typeof import("@/lib/supabase");
const { syncNow, signOutAndClear } = require("@/lib/sync") as typeof import("@/lib/sync");
const { startAutoSync } = require("@/lib/autosync") as typeof import("@/lib/autosync");
const { useProfile } = require("@/stores/profile") as typeof import("@/stores/profile");
const { setAccessToken } = require("@/services/api") as typeof import("@/services/api");
const { useDiscoveries } = require("@/stores/discoveries") as typeof import("@/stores/discoveries");
const { useProgress } = require("@/stores/progress") as typeof import("@/stores/progress");
const { useSession } = require("@/stores/session") as typeof import("@/stores/session");

type Call = { url: string; init: RequestInit };
let calls: Call[];
let routes: Record<string, (init: RequestInit) => { status: number; body: unknown }>;
beforeEach(() => {
  calls = [];
  routes = {};
  setAccessToken(null);
  useSession.setState({ refreshToken: null, userId: null, email: null, accessToken: null, expiresAt: 0 });
  useDiscoveries.setState({ items: [] });
  useProgress.getState().reset();
  useProfile.getState().reset();
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
    routes["/rest/v1/discoveries"] = () => ({ status: 201, body: null });
    await restUpsert("discoveries", "tok", [{ id: "1" }], "user_id,id");
    expect(calls[0].url).toBe("https://proj.supabase.co/rest/v1/discoveries?on_conflict=user_id,id");
    expect((calls[0].init.headers as any).Prefer).toContain("merge-duplicates");
    expect((calls[0].init.headers as any).Authorization).toBe("Bearer tok");
  });
  it("surfaces HTTP failures", async () => {
    routes["/rest/v1/discoveries"] = () => ({ status: 403, body: {} });
    await expect(restSelect("discoveries", "tok")).rejects.toMatchObject({ name: "RestError", status: 403 });
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
    routes["/rest/v1/profiles"] = (init) => (init.method === "GET" ? { status: 200, body: [] } : { status: 201, body: null });

    const r = await syncNow();
    expect(r).toEqual({ ok: true, discoveries: 2 });
    expect(useProgress.getState()).toMatchObject({ xp: 80, streak: 4, completed: { 1: 3, 2: 1 } });
    expect(useDiscoveries.getState().items.map((d) => d.id)).toEqual(["local", "remote"]);
    const pushed = calls.filter((c) => c.init.method === "POST");
    expect(pushed.map((c) => c.url.match(/v1\/(\w+)/)![1]).sort()).toEqual(["discoveries", "profiles", "progress"]);
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


describe("registration identity", () => {
  it("sign-up sends the name as user metadata so the database trigger can create the profile", async () => {
    routes["signup"] = () => ({ status: 200, body: tokenBody });
    await signUp("a@b.co", "password1", "  Asha Gurung ");
    expect(JSON.parse(calls[0].init.body as string)).toEqual({ email: "a@b.co", password: "password1", data: { display_name: "Asha Gurung" } });
  });
  it("sign-up without a name sends no metadata", async () => {
    routes["signup"] = () => ({ status: 200, body: tokenBody });
    await signUp("a@b.co", "password1");
    expect(JSON.parse(calls[0].init.body as string)).toEqual({ email: "a@b.co", password: "password1" });
  });
});

describe("account profile sync", () => {
  const signedIn = () => useSession.setState({ refreshToken: "ref", userId: "u1", email: "a@b.co", accessToken: "acc", expiresAt: Math.floor(Date.now() / 1000) + 3000 });
  const serve = (profile: object | null) => {
    routes["/rest/v1/progress"] = (init) => (init.method === "GET" ? { status: 200, body: [] } : { status: 201, body: null });
    routes["/rest/v1/discoveries"] = (init) => (init.method === "GET" ? { status: 200, body: [] } : { status: 201, body: null });
    routes["/rest/v1/profiles"] = (init) => (init.method === "GET" ? { status: 200, body: profile ? [profile] : [] } : { status: 201, body: null });
  };
  const pushedProfile = () => JSON.parse(calls.find((c) => c.url.includes("/rest/v1/profiles") && c.init.method === "POST")!.init.body as string);

  it("a returning user on a fresh phone gets their saved profile back and skips onboarding", async () => {
    signedIn();
    serve({ user_id: "u1", display_name: "Asha", language: "नेपाली", nepali_level: "Intermediate", interests: ["Food"], onboarded: true });
    await syncNow();
    expect(useProfile.getState()).toMatchObject({ onboarded: true, displayName: "Asha", language: "नेपाली", nepaliLevel: "Intermediate", interests: ["Food"] });
  });

  it("a brand-new account (profile row exists but onboarding not done) still sees onboarding, with the sign-up name filled in", async () => {
    signedIn();
    serve({ user_id: "u1", display_name: "Asha", language: "English", nepali_level: "Beginner", interests: [], onboarded: false });
    await syncNow();
    expect(useProfile.getState()).toMatchObject({ onboarded: false, displayName: "Asha" });
  });

  it("pushes identity (name, email) and onboarding state to the account", async () => {
    signedIn();
    serve(null);
    useProfile.setState({ onboarded: true, displayName: "Asha", language: "English", nepaliLevel: "Beginner", interests: [] });
    await syncNow();
    expect(pushedProfile()).toMatchObject({ user_id: "u1", display_name: "Asha", email: "a@b.co", onboarded: true });
  });
});

describe("signing out on a shared phone", () => {
  const signedIn = () => useSession.setState({ refreshToken: "ref", userId: "u1", email: "a@b.co", accessToken: "acc", expiresAt: Math.floor(Date.now() / 1000) + 3000 });
  const okRoutes = () => {
    for (const t of ["progress", "discoveries", "profiles"]) routes[`/rest/v1/${t}`] = (init) => (init.method === "GET" ? { status: 200, body: [] } : { status: 201, body: null });
    routes["logout"] = () => ({ status: 204, body: null });
  };

  it("saves progress first, then signs out and wipes the local copy so the next person starts clean", async () => {
    signedIn();
    okRoutes();
    useProgress.setState({ xp: 120, completed: { 1: 3 } });
    useProfile.setState({ onboarded: true, displayName: "Asha" });
    useDiscoveries.setState({ items: [{ id: "d", title: "T", summary: "", phrase: null, createdAt: "2026-10-27T00:00:00.000Z" }] });
    expect(await signOutAndClear()).toEqual({ ok: true });
    const progressPush = calls.find((c) => c.url.includes("/rest/v1/progress") && c.init.method === "POST")!;
    expect(JSON.parse(progressPush.init.body as string)).toMatchObject({ user_id: "u1", xp: 120, completed: { "1": 3 } });
    expect(calls.findIndex((c) => c.url.includes("logout"))).toBeGreaterThan(calls.indexOf(progressPush));
    expect(useSession.getState()).toMatchObject({ userId: null, refreshToken: null });
    expect(useProgress.getState()).toMatchObject({ xp: 0, completed: {} });
    expect(useProfile.getState()).toMatchObject({ onboarded: false, displayName: "" });
    expect(useDiscoveries.getState().items).toEqual([]);
  });

  it("if progress can't be saved (offline) it neither signs out nor wipes anything", async () => {
    signedIn();
    routes["/rest/v1/"] = () => ({ status: 500, body: {} });
    useProgress.setState({ xp: 120 });
    const r = await signOutAndClear();
    expect(r.ok).toBe(false);
    expect(useSession.getState().userId).toBe("u1");
    expect(useProgress.getState().xp).toBe(120);
  });
});

describe("auto-save", () => {
  beforeEach(() => jest.useFakeTimers());
  afterEach(() => jest.useRealTimers());
  const signedIn = () => useSession.setState({ refreshToken: "ref", userId: "u1", email: "a@b.co", accessToken: "acc", expiresAt: Math.floor(Date.now() / 1000) + 3000 });
  const progressPosts = () => calls.filter((c) => c.url.includes("/rest/v1/progress") && c.init.method === "POST").length;
  const okRoutes = () => { for (const t of ["progress", "discoveries", "profiles"]) routes[`/rest/v1/${t}`] = (init) => (init.method === "GET" ? { status: 200, body: [] } : { status: 201, body: null }); };

  it("saves to the account shortly after a lesson is completed, once for a burst of changes", async () => {
    signedIn();
    okRoutes();
    const stop = startAutoSync();
    useProgress.getState().completeLesson(1, 3, 20);
    useProgress.getState().addXp(5);
    expect(progressPosts()).toBe(0);
    await jest.advanceTimersByTimeAsync(2100);
    expect(progressPosts()).toBe(1);
    await jest.advanceTimersByTimeAsync(10_000); // the sync's own write-back must not trigger another round
    expect(progressPosts()).toBe(1);
    stop();
  });

  it("does nothing for a guest and stops when asked", async () => {
    okRoutes();
    const stop = startAutoSync();
    useProgress.getState().addXp(5);
    await jest.advanceTimersByTimeAsync(2100);
    expect(calls).toHaveLength(0);
    signedIn();
    stop();
    useProgress.getState().addXp(5);
    await jest.advanceTimersByTimeAsync(2100);
    expect(calls).toHaveLength(0);
  });
});
