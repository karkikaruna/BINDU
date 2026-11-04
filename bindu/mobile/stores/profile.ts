import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";
import { safeStorage } from "@/lib/storage";

type ProfileState = {
  hydrated: boolean;
  onboarded: boolean;
  displayName: string;
  language: "English" | "नेपाली";
  nepaliLevel: "Beginner" | "Intermediate" | "Advanced";
  interests: string[];
  completeOnboarding: (p: { displayName: string; language: ProfileState["language"]; nepaliLevel: ProfileState["nepaliLevel"]; interests: string[] }) => void;
  update: (p: Partial<Pick<ProfileState, "displayName" | "language" | "nepaliLevel" | "interests">>) => void;
  reset: () => void;
};

export const useProfile = create<ProfileState>()(
  persist(
    (set) => ({
      hydrated: false,
      onboarded: false,
      displayName: "",
      language: "English",
      nepaliLevel: "Beginner",
      interests: [],
      completeOnboarding: (p) => set({ ...p, onboarded: true }),
      update: (p) => set(p),
      reset: () => set({ onboarded: false, displayName: "", language: "English", nepaliLevel: "Beginner", interests: [] }),
    }),
    {
      name: "bindu-profile",
      storage: createJSONStorage(() => safeStorage),
      partialize: ({ onboarded, displayName, language, nepaliLevel, interests }) => ({ onboarded, displayName, language, nepaliLevel, interests }),
      onRehydrateStorage: () => () => useProfile.setState({ hydrated: true }),
    },
  ),
);
