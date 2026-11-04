import { Ionicons } from "@expo/vector-icons";
import { router } from "expo-router";
import { Pressable, Text, View } from "react-native";
import { ActionTile } from "@/components/common/ActionTile";
import { Card, Screen, SectionTitle } from "@/components/common/ui";
import { nextLesson, unitOfLesson } from "@/lib/curriculum";
import { levelForXp } from "@/lib/gamification";
import { useT } from "@/lib/i18n";
import { useProgress } from "@/stores/progress";
import { useDiscoveries } from "@/stores/discoveries";

export default function Home() {
  const t = useT();
  const { xp, streak, completed } = useProgress();
  const saved = useDiscoveries((s) => s.items);
  const next = nextLesson(completed);

  return (
    <Screen padded={false}>
      <View className="flex-row items-center justify-between border-b border-line bg-white px-4 py-3">
        <View className="flex-row items-center">
          <View accessible accessibilityLabel={t("home.streak", { n: streak })} className="mr-5 flex-row items-center">
            <Text className="text-xl">🔥</Text>
            <Text className="ml-1.5 text-lg font-extrabold text-terracotta">{streak}</Text>
          </View>
          <View accessible accessibilityLabel={t("home.xpLevel", { xp, level: levelForXp(xp) })} className="flex-row items-center">
            <Text className="text-xl">⭐</Text>
            <Text className="ml-1.5 text-lg font-extrabold text-marigold">{xp}</Text>
          </View>
        </View>
        <Pressable testID="open-profile" accessibilityRole="button" accessibilityLabel={t("home.profile")} onPress={() => router.push("/profile")} className="h-10 w-10 items-center justify-center rounded-full border border-line bg-cream">
          <Ionicons name="person-outline" size={20} color="#174C3C" />
        </Pressable>
      </View>

      <View className="px-4">
        <SectionTitle title={t("home.whatToDo")} />
        <View className="flex-row flex-wrap justify-between">
          <ActionTile title={t("home.learn")} subtitle={t("home.learnSub")} icon="chatbubbles-outline" onPress={() => router.push("/(tabs)/learn")} />
          <ActionTile title={t("home.explore")} subtitle={t("home.exploreSub")} icon="camera-outline" tint="#C76B45" onPress={() => router.push("/(tabs)/explore")} />
          <ActionTile wide title={t("home.ask")} subtitle={t("home.askSub")} icon="help-circle-outline" tint="#387A9B" onPress={() => router.push("/assistant")} />
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