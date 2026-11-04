import { router } from "expo-router";
import { useEffect } from "react";
import { Pressable, Text, View } from "react-native";
import { Card, Screen } from "@/components/common/ui";
import { isUnlocked, units, nextLesson } from "@/lib/curriculum";
import { levelForXp, hoursUntilNextHeart, MAX_HEARTS } from "@/lib/gamification";
import { useT } from "@/lib/i18n";
import { useProfile } from "@/stores/profile";
import { useProgress } from "@/stores/progress";

// Zig-zag offsets (in px from centre) for the winding path, as in the original lesson map.
const OFFSETS = [0, -56, -84, -56, 0, 56, 84, 56];

export default function Learn() {
  const t = useT();
  const level = useProfile((s) => s.nepaliLevel);
  const { hearts, heartsLastRefill, xp, completed, refreshHearts } = useProgress();
  useEffect(() => refreshHearts(), [refreshHearts]);
  const next = nextLesson(completed);
  const total = units.reduce((n, u) => n + u.lessons.length, 0);
  const done = Object.keys(completed).length;

  return (
    <Screen>
      <View className="mt-4 flex-row items-center justify-between">
        <View>
          <Text className="text-3xl font-extrabold text-forest">{t("learn.title")}</Text>
          <Text className="text-sm text-muted">{t.opt(level)} · {t("home.xpLevel", { xp, level: levelForXp(xp) })}</Text>
        </View>
        <Text accessibilityLabel={`${hearts} of ${MAX_HEARTS} hearts`} className="text-lg">{"❤️".repeat(hearts)}{"🤍".repeat(MAX_HEARTS - hearts)}</Text>
      </View>
      {hearts < MAX_HEARTS ? <Text className="text-xs text-muted mt-1">{t("learn.nextHeart", { h: hoursUntilNextHeart(hearts, heartsLastRefill) })}</Text> : null}

      <Card className="mt-4">
        <Text className="text-sm font-semibold text-charcoal">{t("learn.cleared", { done, total })}</Text>
        <View className="mt-2 h-2.5 overflow-hidden rounded-full bg-cream"><View className="h-2.5 rounded-full bg-terracotta" style={{ width: `${(done / total) * 100}%` }} /></View>
      </Card>

      {units.map((unit) => (
        <View key={unit.id}>
          <View className="mt-6 rounded-2xl px-4 py-3.5" style={{ backgroundColor: "#C76B45" }}>
            <Text className="text-lg font-bold text-white">{t("learn.unit", { n: unit.order_index, name: unit.name })}</Text>
            <Text className="text-xs text-white/80">{t("learn.unitProgress", { done: unit.lessons.filter((l) => completed[l.id] != null).length, total: unit.lessons.length })}</Text>
          </View>
          {unit.lessons.map((lesson, i) => {
            const stars = completed[lesson.id];
            const isDone = stars != null;
            const open = isUnlocked(lesson.id, completed);
            const current = next?.id === lesson.id;
            const bg = isDone ? "bg-marigold" : current ? "bg-[#FFD23F]" : "bg-[#D9D9D9]";
            return (
              <View key={lesson.id} className="items-center py-3" style={{ transform: [{ translateX: OFFSETS[i % OFFSETS.length] }] }}>
                <Pressable
                  testID={`lesson-node-${lesson.id}`}
                  accessibilityRole="button"
                  accessibilityLabel={`${lesson.name}${isDone ? `, ${stars} ★` : open ? "" : `, ${t("learn.locked")}`}`}
                  accessibilityState={{ disabled: !open }}
                  disabled={!open}
                  onPress={() => router.push({ pathname: "/lesson/[id]", params: { id: String(lesson.id) } })}
                  className={`h-20 w-20 items-center justify-center rounded-full ${bg}`}
                  style={{ shadowColor: "#000", shadowOpacity: open ? 0.15 : 0, shadowOffset: { width: 0, height: 4 }, elevation: open ? 4 : 0 }}
                >
                  <Text className="text-3xl">{open ? "🌼" : "🔒"}</Text>
                </Pressable>
                <Text className="mt-1 text-xs text-muted text-center max-w-[140px]">{isDone ? "⭐".repeat(stars) : lesson.name}</Text>
                {isDone ? <Text className="text-[11px] text-muted">{lesson.name} · {t("learn.review")}</Text> : null}
              </View>
            );
          })}
        </View>
      ))}
    </Screen>
  );
}
