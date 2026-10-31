import { Redirect } from "expo-router";
import { ActivityIndicator, View } from "react-native";
import { useProfile } from "@/stores/profile";

/** Entry gate: wait for persisted profile to load, then route to onboarding or the tabs. */
export default function Index() {
  const hydrated = useProfile((s) => s.hydrated);
  const onboarded = useProfile((s) => s.onboarded);
  if (!hydrated) {
    return (
      <View className="flex-1 items-center justify-center bg-cream">
        <ActivityIndicator color="#174C3C" />
      </View>
    );
  }
  return <Redirect href={onboarded ? "/(tabs)" : "/onboarding"} />;
}
