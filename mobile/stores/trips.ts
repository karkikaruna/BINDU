import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";
import { safeStorage } from "@/lib/storage";
import type { Itinerary, TripRequest } from "@/types/features";

export type SavedTrip = { id: string; request: TripRequest; itinerary: Itinerary; isMock: boolean; createdAt: string };

type State = {
  items: SavedTrip[];
  save: (t: SavedTrip) => boolean;
  remove: (id: string) => void;
};

/** Saved itineraries (local-first; synced to the account when signed in). */
export const useTrips = create<State>()(
  persist(
    (set, get) => ({
      items: [],
      save: (t) => {
        if (get().items.some((x) => x.id === t.id)) return false;
        set({ items: [t, ...get().items] });
        return true;
      },
      remove: (id) => set({ items: get().items.filter((x) => x.id !== id) }),
    }),
    { name: "bindu-trips", storage: createJSONStorage(() => safeStorage) },
  ),
);
