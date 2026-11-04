import { Redirect } from "expo-router";
import { ActivityIndicator, View } from "react-native";
import { supabaseConfigured } from "@/lib/supabase";
import { useProfile } from "@/stores/profile";
import { useSession } from "@/stores/session";


export default function Index() {
  const hydrated = useProfile((s) => s.hydrated);
  const onboarded = useProfile((s) => s.onboarded);
  const restored = useSession((s) => s.restored);
  const userId = useSession((s) => s.userId);
  if (!hydrated || !restored) {
    return (
      <View className="flex-1 items-center justify-center bg-cream">
        <ActivityIndicator color="#174C3C" />
      </View>
    );
  }
  if (supabaseConfigured() && !userId) return <Redirect href="/welcome" />;
  return <Redirect href={onboarded ? "/(tabs)" : "/onboarding"} />;
}
