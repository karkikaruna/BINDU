import { Platform } from "react-native";
import * as SecureStore from "expo-secure-store";
import type { StateStorage } from "zustand/middleware";

/**
 * Key/value storage that never throws: SecureStore on devices, localStorage on web.
 * Storage can be unavailable (private mode, blocked site data) so every call is guarded.
 */
export const safeStorage: StateStorage = {
  getItem: async (name) => {
    try {
      if (Platform.OS === "web") return globalThis.localStorage?.getItem(name) ?? null;
      return await SecureStore.getItemAsync(name);
    } catch {
      return null;
    }
  },
  setItem: async (name, value) => {
    try {
      if (Platform.OS === "web") globalThis.localStorage?.setItem(name, value);
      else await SecureStore.setItemAsync(name, value);
    } catch {
      /* persistence is best-effort */
    }
  },
  removeItem: async (name) => {
    try {
      if (Platform.OS === "web") globalThis.localStorage?.removeItem(name);
      else await SecureStore.deleteItemAsync(name);
    } catch {
      /* ignore */
    }
  },
};
