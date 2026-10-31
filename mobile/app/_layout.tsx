import "../global.css";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Stack, type ErrorBoundaryProps } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { useEffect } from "react";
import { Pressable, Text, View } from "react-native";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { useT } from "@/lib/i18n";
import { syncNow } from "@/lib/sync";
import { useSession } from "@/stores/session";

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, staleTime: 60_000 }, mutations: { retry: 0 } },
});

/** Shown instead of a blank screen when a screen throws while rendering. Saved data lives in storage, so it is unaffected. */
export function ErrorBoundary({ retry }: ErrorBoundaryProps) {
  const t = useT();
  return (
    <View accessibilityRole="alert" className="flex-1 items-center justify-center bg-cream px-6">
      <Text className="text-5xl">🙏</Text>
      <Text className="mt-3 text-center text-2xl font-extrabold text-forest">{t("crash.title")}</Text>
      <Text className="mt-2 text-center text-base text-muted">{t("crash.body")}</Text>
      <Pressable accessibilityRole="button" onPress={retry} className="mt-6 rounded-2xl bg-forest px-6 py-3">
        <Text className="text-base font-semibold text-white">{t("crash.retry")}</Text>
      </Pressable>
    </View>
  );
}

export default function RootLayout() {
  const restore = useSession((s) => s.restore);
  const userId = useSession((s) => s.userId);
  // Restore a saved sign-in once, then sync whenever an account becomes active (sign-in, app start).
  useEffect(() => { void restore(); }, [restore]);
  useEffect(() => { if (userId) void syncNow(); }, [userId]);

  return (
    <SafeAreaProvider>
      <QueryClientProvider client={queryClient}>
        <StatusBar style="dark" />
        <Stack screenOptions={{ headerShown: false, contentStyle: { backgroundColor: "#F7F3E8" } }}>
          <Stack.Screen name="index" />
          <Stack.Screen name="onboarding" />
          <Stack.Screen name="(tabs)" />
          <Stack.Screen name="profile" options={{ presentation: "modal" }} />
          <Stack.Screen name="auth" options={{ presentation: "modal" }} />
          <Stack.Screen name="trip/new" />
          <Stack.Screen name="trip/[id]" />
          <Stack.Screen name="nearby" />
          <Stack.Screen name="practice" />
          <Stack.Screen name="assistant" />
          <Stack.Screen name="card/[id]" options={{ presentation: "modal" }} />
          <Stack.Screen name="lesson/[id]" options={{ gestureEnabled: false }} />
        </Stack>
      </QueryClientProvider>
    </SafeAreaProvider>
  );
}
