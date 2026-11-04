import { router } from "expo-router";
import { Image, Text, View } from "react-native";
import { Button, Screen } from "@/components/common/ui";
import { useT } from "@/lib/i18n";

/** First screen for someone who isn't signed in: choose between signing in and creating an account. */
export default function Welcome() {
  const t = useT();
  return (
    <Screen>
      <View className="items-center pt-16">
        <Image source={require("@/assets/brand/bindu_logo_icon.png")} style={{ width: 104, height: 104 }} accessibilityLabel="BINDU logo" />
        <Text className="mt-4 text-5xl font-extrabold tracking-widest text-forest">BINDU</Text>
        <Text className="mt-2 text-center text-base text-muted">{t("onboarding.tagline")}</Text>
        <Text className="mt-8 text-center text-base text-charcoal">{t("welcome.blurb")}</Text>
      </View>
      <Button testID="welcome-signin" label={t("auth.signIn")} onPress={() => router.push({ pathname: "/auth", params: { mode: "signin" } })} className="mt-8" />
      <Button testID="welcome-register" label={t("auth.create")} variant="secondary" onPress={() => router.push({ pathname: "/auth", params: { mode: "signup" } })} className="mt-3" />
    </Screen>
  );
}
