import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";
import { safeStorage } from "@/lib/storage";
import { refreshSession, signIn as sbSignIn, signOutRemote, signUp as sbSignUp, type SignUpResult, type Tokens } from "@/lib/supabase";
import { setAccessToken } from "@/services/api";

type SessionState = {
  /** Only the refresh token and identity are persisted (small, and the access token is short-lived). */
  refreshToken: string | null;
  userId: string | null;
  email: string | null;
  accessToken: string | null;
  expiresAt: number;
  restored: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signUp: (email: string, password: string) => Promise<SignUpResult>;
  signOut: () => Promise<void>;
  /** Restore a saved session on app start. Never throws: a failure just means the user is a guest. */
  restore: () => Promise<void>;
  /** Returns a valid access token (refreshing if it is about to expire) or null when signed out. */
  getToken: () => Promise<string | null>;
};

const apply = (t: Tokens) => {
  setAccessToken(t.accessToken);
  return { accessToken: t.accessToken, refreshToken: t.refreshToken, expiresAt: t.expiresAt, userId: t.userId, email: t.email };
};

export const useSession = create<SessionState>()(
  persist(
    (set, get) => ({
      refreshToken: null, userId: null, email: null, accessToken: null, expiresAt: 0, restored: false,
      signIn: async (email, password) => {
        set(apply(await sbSignIn(email.trim(), password)));
      },
      signUp: async (email, password) => {
        const r = await sbSignUp(email.trim(), password);
        if ("tokens" in r) set(apply(r.tokens));
        return r;
      },
      signOut: async () => {
        const { accessToken } = get();
        if (accessToken) await signOutRemote(accessToken);
        setAccessToken(null);
        set({ accessToken: null, refreshToken: null, userId: null, email: null, expiresAt: 0 });
      },
      restore: async () => {
        const { refreshToken } = get();
        try {
          if (refreshToken) set(apply(await refreshSession(refreshToken)));
        } catch (e) {
          // A rejected refresh token (401/400) means the session is gone; a network error keeps it for next time.
          const status = (e as { status?: number | null }).status;
          if (status === 400 || status === 401) set({ refreshToken: null, userId: null, email: null, accessToken: null });
        } finally {
          set({ restored: true });
        }
      },
      getToken: async () => {
        const { accessToken, refreshToken, expiresAt } = get();
        if (!refreshToken) return null;
        if (accessToken && expiresAt - Math.floor(Date.now() / 1000) > 60) return accessToken;
        try {
          set(apply(await refreshSession(refreshToken)));
          return get().accessToken;
        } catch {
          return null;
        }
      },
    }),
    {
      name: "bindu-session",
      storage: createJSONStorage(() => safeStorage),
      partialize: ({ refreshToken, userId, email }) => ({ refreshToken, userId, email }),
      onRehydrateStorage: () => () => { /* restore() is called from the root layout */ },
    },
  ),
);
