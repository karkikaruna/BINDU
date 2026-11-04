import { Ionicons } from "@expo/vector-icons";
import { Redirect, Tabs } from "expo-router";
import { colors } from "@/constants/theme";
import { useT, type I18nKey } from "@/lib/i18n";
import { supabaseConfigured } from "@/lib/supabase";
import { useSession } from "@/stores/session";

type IconName = React.ComponentProps<typeof Ionicons>["name"];
const tab = (title: string, icon: IconName, iconActive: IconName) => ({
  title,
  tabBarIcon: ({ focused, color, size }: { focused: boolean; color: unknown; size: number }) => (
    <Ionicons name={focused ? iconActive : icon} color={color as string} size={size} />
  ),
});

export default function TabsLayout() {
  const t = useT();
  const title = (k: I18nKey) => t(k);
  const restored = useSession((s) => s.restored);
  const userId = useSession((s) => s.userId);
  // Signed out (or the saved sign-in was rejected): back to the welcome screen rather than showing someone's lessons.
  if (restored && supabaseConfigured() && !userId) return <Redirect href="/welcome" />;
  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: colors.forest,
        tabBarInactiveTintColor: colors.muted,
        tabBarStyle: { backgroundColor: colors.white, borderTopColor: colors.line, height: 72, paddingBottom: 12, paddingTop: 8 },
        tabBarLabelStyle: { fontSize: 12, fontWeight: "600" },
      }}
    >
      <Tabs.Screen name="index" options={tab(title("tabs.home"), "home-outline", "home")} />
      <Tabs.Screen name="explore" options={tab(title("tabs.explore"), "compass-outline", "compass")} />
      <Tabs.Screen name="journey" options={tab(title("tabs.journey"), "map-outline", "map")} />
      <Tabs.Screen name="learn" options={tab(title("tabs.learn"), "book-outline", "book")} />
    </Tabs>
  );
}
