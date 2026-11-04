import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";
import { safeStorage } from "@/lib/storage";

export type SavedDiscovery = {
  id: string;
  title: string;
  summary: string;
  phrase?: { nepali: string; romanization: string; english: string } | null;
  createdAt: string;
};

type State = {
  items: SavedDiscovery[];
  save: (d: SavedDiscovery) => boolean;
  remove: (id: string) => void;
};

/** Local-first discovery history (guest mode). Cloud sync via Supabase arrives with auth. */
export const useDiscoveries = create<State>()(
  persist(
    (set, get) => ({
      items: [],
      save: (d) => {
        if (get().items.some((x) => x.id === d.id)) return false; // no duplicate saves
        set({ items: [d, ...get().items] });
        return true;
      },
      remove: (id) => set({ items: get().items.filter((x) => x.id !== id) }),
    }),
    { name: "bindu-discoveries", storage: createJSONStorage(() => safeStorage) },
  ),
);
