import { useState } from "react";
import { Image, Text, TextInput, View } from "react-native";
import { router } from "expo-router";
import { Button, Chip, Screen, SectionTitle } from "@/components/common/ui";
import { INTERESTS, LANGUAGES, LEVELS } from "@/constants/theme";
import { makeTranslator } from "@/lib/i18n";
import { useProfile } from "@/stores/profile";

export default function Onboarding() {
  const complete = useProfile((s) => s.completeOnboarding);
  const [name, setName] = useState("");
  const [language, setLanguage] = useState<(typeof LANGUAGES)[number]>("English");
  const [level, setLevel] = useState<(typeof LEVELS)[number]>("Beginner");
  const [interests, setInterests] = useState<string[]>([]);
  // The screen switches language as soon as the person picks one, before onboarding is saved.
  const t = makeTranslator(language);

  const toggle = (i: string) => setInterests((cur) => (cur.includes(i) ? cur.filter((x) => x !== i) : [...cur, i]));

  const start = () => {
    complete({ displayName: name.trim(), language, nepaliLevel: level, interests });
    router.replace("/(tabs)");
  };

  return (
    <Screen>
      <View className="items-center pt-6">
        <Image source={require("@/assets/brand/bindu_logo_icon.png")} style={{ width: 84, height: 84 }} accessibilityLabel="BINDU logo" />
        <Text className="mt-3 text-4xl font-extrabold tracking-widest text-forest">BINDU</Text>
        <Text className="mt-2 text-center text-base text-muted">{t("onboarding.tagline")}</Text>
      </View>

      <SectionTitle title={t("profile.ifaceLang")} />
      <View className="flex-row flex-wrap">
        {LANGUAGES.map((l) => <Chip key={l} label={l} selected={language === l} onPress={() => setLanguage(l)} />)}
      </View>

      <SectionTitle title={t("onboarding.callYou")} hint={t("onboarding.optional")} />
      <TextInput
        value={name}
        onChangeText={setName}
        placeholder={t("onboarding.yourName")}
        placeholderTextColor="#8A938C"
        maxLength={40}
        accessibilityLabel={t("onboarding.yourName")}
        className="min-h-[52px] rounded-2xl border border-line bg-white px-4 text-base text-charcoal"
      />

      <SectionTitle title={t("onboarding.level")} />
      <View className="flex-row flex-wrap">
        {LEVELS.map((l) => <Chip key={l} label={t.opt(l)} selected={level === l} onPress={() => setLevel(l)} />)}
      </View>

      <SectionTitle title={t("onboarding.interestsQ")} hint={t("onboarding.pickAny")} />
      <View className="flex-row flex-wrap">
        {INTERESTS.map((i) => <Chip key={i} label={t.opt(i)} selected={interests.includes(i)} onPress={() => toggle(i)} />)}
      </View>

      <Text className="mt-4 text-xs text-muted">{t("onboarding.locationNote")}</Text>
      <Button testID="start-btn" label={t("onboarding.start")} onPress={start} className="mt-5" />
    </Screen>
  );
}
