import { useMutation } from "@tanstack/react-query";
import { router, useLocalSearchParams } from "expo-router";
import { useState } from "react";
import { Image, Share, Text, View } from "react-native";
import { Button, Chip, ErrorBanner, Screen } from "@/components/common/ui";
import { cardAsText, localCard, THEME_COLORS, type CardData } from "@/lib/card";
import { ApiError, generateCard } from "@/services/api";
import { useDiscoveries } from "@/stores/discoveries";

export default function CardScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const discovery = useDiscoveries((s) => s.items.find((d) => d.id === id));
  const [card, setCard] = useState<CardData | null>(null);
  const [aiMock, setAiMock] = useState(false);

  const improve = useMutation({
    mutationFn: () => generateCard({ kind: "discovery", title: discovery!.title, body: discovery!.summary, nepali: discovery!.phrase?.nepali, english: discovery!.phrase?.english }),
    onSuccess: (d) => { setCard(d.card); setAiMock(d.is_mock); },
  });

  if (!discovery) {
    return (
      <Screen>
        <Text className="mt-6 text-center text-charcoal">That discovery is no longer saved.</Text>
        <Button label="Back" onPress={() => router.back()} className="mt-4" />
      </Screen>
    );
  }
  const shown = card ?? localCard(discovery);
  const bg = THEME_COLORS[shown.theme];

  return (
    <Screen>
      <View className="mt-4 flex-row items-center justify-between">
        <Text className="text-3xl font-extrabold text-forest">Share card</Text>
        <Button label="Close" variant="ghost" onPress={() => router.back()} />
      </View>

      <View testID="postcard" className="mt-4 rounded-[32px] p-6" style={{ backgroundColor: bg }}>
        <View className="flex-row items-center">
          <Image source={require("@/assets/brand/bindu_logo_icon.png")} style={{ width: 36, height: 36 }} accessibilityLabel="BINDU logo" />
          <Text className="ml-2 text-sm font-bold tracking-widest text-white/90">BINDU · NEPAL</Text>
        </View>
        <Text className="mt-6 text-3xl font-extrabold text-white">{shown.headline}</Text>
        <Text className="mt-3 text-base leading-6 text-white/90">{shown.caption}</Text>
        {shown.nepali ? (
          <View className="mt-5 rounded-2xl bg-white/15 p-4">
            <Text className="text-2xl font-bold text-white">{shown.nepali}</Text>
            {shown.romanization ? <Text className="text-base text-white/90">{shown.romanization}</Text> : null}
            {shown.english ? <Text className="text-sm text-white/80">{shown.english}</Text> : null}
          </View>
        ) : null}
      </View>
      {aiMock ? <Text className="mt-2 text-xs text-muted">Demo mode: this caption came from the placeholder provider.</Text> : null}

      <Text className="mt-4 text-sm font-semibold text-charcoal">Colour</Text>
      <View className="mt-2 flex-row flex-wrap">
        {(Object.keys(THEME_COLORS) as (keyof typeof THEME_COLORS)[]).map((t) => <Chip key={t} label={t[0].toUpperCase() + t.slice(1)} selected={shown.theme === t} onPress={() => setCard({ ...shown, theme: t })} />)}
      </View>

      {improve.isError ? <View className="mt-3"><ErrorBanner message={improve.error instanceof ApiError ? improve.error.message : "Something unexpected happened."} /></View> : null}
      <Button testID="share-card" label="Share" onPress={() => Share.share({ message: cardAsText(shown) })} className="mt-4" />
      <Button testID="improve-card" label="Rewrite caption with AI" variant="secondary" loading={improve.isPending} onPress={() => improve.mutate()} className="mt-3" />
    </Screen>
  );
}
