/**
 * Minimal Supabase client over fetch (Auth + PostgREST), so no extra SDK is needed.
 * Only the public anon key is used here. Row-level security (supabase/migrations/0001_init.sql) restricts every
 * table to the signed-in user's own rows.
 */
const URL_BASE = (process.env.EXPO_PUBLIC_SUPABASE_URL ?? "").replace(/\/$/, "");
const ANON_KEY = process.env.EXPO_PUBLIC_SUPABASE_ANON_KEY ?? "";

export const supabaseConfigured = (): boolean => URL_BASE.length > 0 && ANON_KEY.length > 0;

export class AuthError extends Error {
  constructor(message: string, public status: number | null = null) {
    super(message);
    this.name = "AuthError";
  }
}

export type Tokens = { accessToken: string; refreshToken: string; expiresAt: number; userId: string; email: string };
export type SignUpResult = { tokens: Tokens } | { needsConfirmation: true };

const headers = (token?: string): Record<string, string> => ({
  apikey: ANON_KEY,
  "Content-Type": "application/json",
  Authorization: `Bearer ${token ?? ANON_KEY}`,
});

function toTokens(body: any): Tokens {
  const now = Math.floor(Date.now() / 1000);
  return {
    accessToken: body.access_token,
    refreshToken: body.refresh_token,
    expiresAt: typeof body.expires_at === "number" ? body.expires_at : now + (body.expires_in ?? 3600),
    userId: body.user?.id ?? "",
    email: body.user?.email ?? "",
  };
}

async function authCall(path: string, payload: unknown): Promise<any> {
  if (!supabaseConfigured()) throw new AuthError("Sign-in isn't set up on this build. You can keep using BINDU as a guest.");
  let res: Response;
  try {
    res = await fetch(`${URL_BASE}/auth/v1/${path}`, { method: "POST", headers: headers(), body: JSON.stringify(payload) });
  } catch {
    throw new AuthError("Can't reach the sign-in service. Check your connection.");
  }
  const body = await res.json().catch(() => null);
  if (!res.ok) {
    const raw: string = body?.msg ?? body?.error_description ?? body?.message ?? "";
    const friendly = /invalid login/i.test(raw) ? "Wrong email or password." : /already registered|already been registered/i.test(raw) ? "That email already has an account. Try signing in." : /password/i.test(raw) ? raw : raw || "Sign-in failed. Please try again.";
    throw new AuthError(friendly, res.status);
  }
  return body;
}

export async function signUp(email: string, password: string): Promise<SignUpResult> {
  const body = await authCall("signup", { email, password });
  return body?.access_token ? { tokens: toTokens(body) } : { needsConfirmation: true };
}

export async function signIn(email: string, password: string): Promise<Tokens> {
  return toTokens(await authCall("token?grant_type=password", { email, password }));
}

/** Sends a password-reset email. Supabase answers 200 whether or not the address has an account (no account enumeration). */
export async function requestPasswordReset(email: string): Promise<void> {
  await authCall("recover", { email });
}

export async function refreshSession(refreshToken: string): Promise<Tokens> {
  return toTokens(await authCall("token?grant_type=refresh_token", { refresh_token: refreshToken }));
}

export async function signOutRemote(accessToken: string): Promise<void> {
  try {
    await fetch(`${URL_BASE}/auth/v1/logout`, { method: "POST", headers: headers(accessToken) });
  } catch {
    /* local sign-out proceeds regardless */
  }
}

// ---- PostgREST ----
export class RestError extends Error {
  constructor(message: string, public status: number) {
    super(message);
    this.name = "RestError";
  }
}

async function rest(method: string, path: string, token: string, body?: unknown, extra: Record<string, string> = {}): Promise<any> {
  const res = await fetch(`${URL_BASE}/rest/v1/${path}`, { method, headers: { ...headers(token), ...extra }, body: body === undefined ? undefined : JSON.stringify(body) });
  if (!res.ok) throw new RestError(`Sync request failed (${res.status}).`, res.status);
  const text = await res.text();
  return text ? JSON.parse(text) : null;
}

export const restSelect = (table: string, token: string, query = "select=*") => rest("GET", `${table}?${query}`, token);
export const restUpsert = (table: string, token: string, rows: unknown[] | object, onConflict: string) =>
  rest("POST", `${table}?on_conflict=${onConflict}`, token, rows, { Prefer: "resolution=merge-duplicates,return=minimal" });
export const restDelete = (table: string, token: string, filter: string) => rest("DELETE", `${table}?${filter}`, token, undefined, { Prefer: "return=minimal" });
