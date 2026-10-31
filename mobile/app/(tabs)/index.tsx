import { Ionicons } from "@expo/vector-icons";
import { router } from "expo-router";
import { Pressable, Text, View } from "react-native";
import { ActionTile } from "@/components/common/ActionTile";
import { Badge, Card, Screen, SectionTitle } from "@/components/common/ui";
import { CURATED_PLACES } from "@/constants/places";
import { nextLesson, unitOfLesson } from "@/lib/curriculum";
import { levelForXp } from "@/lib/gamification";
import { useT } from "@/lib/i18n";
import { useProfile } from "@/stores/profile";
import { useProgress } from "@/stores/progress";
import { useDiscoveries } from "@/stores/discoveries";

export default function Home() {
  const t = useT();
  const name = useProfile((s) => s.displayName);
  const { xp, streak, completed } = useProgress();
  const saved = useDiscoveries((s) => s.items);
  const next = nextLesson(completed);

  return (
    <Screen padded={false}>
      <View className="bg-forest px-4 pb-6 pt-4 rounded-b-[32px]">
        <View className="flex-row items-center justify-between">
          <View className="flex-1 pr-3">
            <Text className="text-sm text-white/70">नमस्ते 🙏</Text>
            <Text className="text-2xl font-extrabold text-white" numberOfLines={1}>
              {name ? t("home.welcome", { name }) : t("home.welcomeGuest")}
            </Text>
          </View>
          <Pressable testID="open-profile" accessibilityRole="button" accessibilityLabel={t("home.profile")} onPress={() => router.push("/profile")} className="h-11 w-11 items-center justify-center rounded-full bg-white/15">
            <Ionicons name="person-outline" size={22} color="#fff" />
          </Pressable>
        </View>
        <View className="mt-4 flex-row">
          <Text className="text-white/90 mr-4">🔥 {t("home.streak", { n: streak })}</Text>
          <Text className="text-white/90">⭐ {t("home.xpLevel", { xp, level: levelForXp(xp) })}</Text>
        </View>
      </View>

      <View className="px-4">
        <SectionTitle title={t("home.whatToDo")} />
        <View className="flex-row flex-wrap justify-between">
          <ActionTile title={t("home.plan")} subtitle={t("home.planSub")} icon="calendar-outline" tint="#387A9B" onPress={() => router.push("/trip/new")} />
          <ActionTile title={t("home.explore")} subtitle={t("home.exploreSub")} icon="camera-outline" tint="#C76B45" onPress={() => router.push("/(tabs)/explore")} />
          <ActionTile title={t("home.learn")} subtitle={t("home.learnSub")} icon="chatbubbles-outline" onPress={() => router.push("/(tabs)/learn")} />
          <ActionTile title={t("home.nearby")} subtitle={t("home.nearbySub")} icon="location-outline" tint="#387A9B" onPress={() => router.push("/nearby")} />
          <ActionTile title={t("home.tutor")} subtitle={t("home.tutorSub")} icon="mic-outline" tint="#E8A33D" onPress={() => router.push("/practice")} />
          <ActionTile title={t("home.ask")} subtitle={t("home.askSub")} icon="help-circle-outline" tint="#174C3C" onPress={() => router.push("/assistant")} />
        </View>

        <SectionTitle title={t("home.continue")} />
        {next ? (
          <Pressable testID="continue-lesson" accessibilityRole="button" onPress={() => router.push({ pathname: "/lesson/[id]", params: { id: String(next.id) } })}>
            <Card className="flex-row items-center">
              <View className="mr-3 h-12 w-12 items-center justify-center rounded-full bg-marigold"><Text className="text-xl">🌼</Text></View>
              <View className="flex-1">
                <Text className="text-xs font-semibold uppercase text-muted">{unitOfLesson(next.id)?.name}</Text>
                <Text className="text-base font-bold text-charcoal">{next.name}</Text>
              </View>
              <Ionicons name="chevron-forward" size={20} color="#5C665F" />
            </Card>
          </Pressable>
        ) : (
          <Card><Text className="text-charcoal">{t("home.allDone")}</Text></Card>
        )}

        <SectionTitle title={t("home.heritage")} hint={t("home.heritageHint")} />
        {CURATED_PLACES.map((p) => (
          <Pressable key={p.id} testID={`heritage-${p.id}`} accessibilityRole="button" accessibilityLabel={p.name} onPress={() => router.push({ pathname: "/nearby", params: { q: p.name } })}>
            <Card className="mb-3">
              <Badge label={t.opt(p.category)} tone="himalaya" />
              <Text className="mt-2 text-base font-bold text-charcoal">{p.name}</Text>
              <Text className="text-xs text-muted">{p.area}</Text>
              <Text className="mt-1 text-sm text-charcoal">{p.blurb}</Text>
            </Card>
          </Pressable>
        ))}

        {saved.length > 0 ? (
          <>
            <SectionTitle title={t("home.recent")} />
            {saved.slice(0, 2).map((d) => (
              <Card key={d.id} className="mb-3"><Text className="font-bold text-charcoal">{d.title}</Text><Text className="mt-1 text-sm text-muted" numberOfLines={2}>{d.summary}</Text></Card>
            ))}
          </>
        ) : null}
      </View>
    </Screen>
  );
}
