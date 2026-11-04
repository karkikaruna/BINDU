import { Link, Stack } from "expo-router";
import { Text, View } from "react-native";
import { useT } from "@/lib/i18n";

export default function NotFound() {
  const t = useT();
  return (
    <>
      <Stack.Screen options={{ headerShown: false }} />
      <View className="flex-1 items-center justify-center bg-cream px-6">
        <Text className="text-5xl">🧭</Text>
        <Text accessibilityRole="header" className="mt-3 text-center text-2xl font-extrabold text-forest">{t("notFound.title")}</Text>
        <Link href="/" className="mt-6 rounded-2xl bg-forest px-6 py-3 text-base font-semibold text-white">{t("notFound.home")}</Link>
      </View>
    </>
  );
}
