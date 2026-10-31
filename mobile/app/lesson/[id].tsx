import { Ionicons } from "@expo/vector-icons";
import { setAudioModeAsync, useAudioPlayer, useAudioPlayerStatus } from "expo-audio";
import { router, useLocalSearchParams } from "expo-router";
import { useEffect, useMemo, useRef, useState } from "react";
import { Image, Pressable, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Button } from "@/components/common/ui";
import { findLesson } from "@/lib/curriculum";
import { checkMultipleChoice, checkWordBank, shuffled } from "@/lib/exercise";
import { hoursUntilNextHeart } from "@/lib/gamification";
import { useT } from "@/lib/i18n";
import { scoreLesson } from "@/lib/scoring";
import { useProgress } from "@/stores/progress";
import type { Exercise } from "@/types/lessons";

type Feedback = { correct: boolean; answer: string } | null;

export default function LessonPlayer() {
  const t = useT();
  const { id } = useLocalSearchParams<{ id: string }>();
  const lesson = findLesson(Number(id));
  const { hearts, heartsLastRefill, loseHeart, completeLesson } = useProgress();

  const [queue, setQueue] = useState<Exercise[]>(() => lesson?.exercises ?? []);
  const [pos, setPos] = useState(0);
  const [selected, setSelected] = useState<string | null>(null);
  const [placed, setPlaced] = useState<string[]>([]);
  const [feedback, setFeedback] = useState<Feedback>(null);
  const [result, setResult] = useState<{ stars: number; xp: number } | null>(null);
  const firstTry = useRef(new Set<number>());
  const missed = useRef(new Set<number>());

  const total = lesson?.exercises.length ?? 0;
  const current = queue[pos];

  // Pronunciation audio (hosted MP3 per exercise). Tap to play; never autoplays.
  const audioUrl = current?.audio_url ?? null;
  const player = useAudioPlayer(audioUrl);
  const audioStatus = useAudioPlayerStatus(player);
  const loadedRef = useRef(false);
  loadedRef.current = audioStatus.isLoaded;
  const [audioFailed, setAudioFailed] = useState(false);
  useEffect(() => { setAudioFailed(false); }, [audioUrl]);
  useEffect(() => { setAudioModeAsync({ playsInSilentMode: true }).catch(() => undefined); }, []);
  const playAudio = async () => {
    try {
      setAudioFailed(false);
      await player.seekTo(0);
      player.play();
      // expo-audio reports no load error, so treat "still not loaded after 4s" as unavailable (e.g. offline).
      setTimeout(() => { if (!loadedRef.current) setAudioFailed(true); }, 4000);
    } catch {
      setAudioFailed(true);
    }
  };
  const tiles = useMemo(() => (current ? shuffled(current.tokens, current.id) : []), [current]);

  if (!lesson) {
    return <SafeAreaView className="flex-1 items-center justify-center bg-cream"><Text>{t("lesson.notFound")}</Text><Button label={t("common.close")} onPress={() => router.back()} className="mt-4" /></SafeAreaView>;
  }

  if (hearts <= 0 && !feedback && !result) {
    return (
      <SafeAreaView className="flex-1 items-center justify-center bg-cream px-6">
        <Text className="text-5xl">💔</Text>
        <Text className="mt-3 text-2xl font-extrabold text-charcoal">{t("lesson.noHearts")}</Text>
        <Text className="mt-1 text-center text-muted">{t("lesson.noHeartsBody", { h: hoursUntilNextHeart(hearts, heartsLastRefill) })}</Text>
        <Button label={t("lesson.backToLessons")} onPress={() => router.back()} className="mt-6 self-stretch" />
      </SafeAreaView>
    );
  }

  if (result) {
    return (
      <SafeAreaView className="flex-1 items-center justify-center bg-cream px-6">
        <Text className="text-5xl">🎉</Text>
        <Text className="mt-3 text-2xl font-extrabold text-forest">{t("lesson.complete")}</Text>
        <Text className="mt-2 text-3xl">{"⭐".repeat(result.stars)}{"☆".repeat(3 - result.stars)}</Text>
        <Text className="mt-2 text-base text-charcoal">+{result.xp} XP</Text>
        <Button testID="finish-lesson" label={t("lesson.continue")} onPress={() => router.back()} className="mt-6 self-stretch" />
      </SafeAreaView>
    );
  }

  const answerOk = () => (current.type === "multiple_choice" ? selected != null : placed.length === current.tokens.length);

  const check = () => {
    const ok = current.type === "multiple_choice" ? checkMultipleChoice(selected ?? "", current.answer) : checkWordBank(placed, current.answer);
    if (ok) {
      if (!missed.current.has(current.id)) firstTry.current.add(current.id);
    } else {
      missed.current.add(current.id);
      loseHeart();
    }
    setFeedback({ correct: ok, answer: current.type === "multiple_choice" ? current.answer[0] : current.answer.join(" ") });
  };

  const advance = () => {
    const wasCorrect = feedback?.correct;
    setFeedback(null);
    setSelected(null);
    setPlaced([]);
    // Wrong answers are re-queued at the end, as in the original app.
    const nextQueue = wasCorrect ? queue : [...queue, current];
    if (pos + 1 >= nextQueue.length) {
      const score = scoreLesson(firstTry.current.size, total);
      completeLesson(lesson.id, score.stars, score.xp);
      setResult(score);
      return;
    }
    setQueue(nextQueue);
    setPos(pos + 1);
  };

  const progress = Math.min(1, pos / queue.length);

  return (
    <SafeAreaView className="flex-1 bg-cream">
      <View className="px-4 pt-2">
        <View className="flex-row items-center">
          <Pressable accessibilityRole="button" accessibilityLabel="Close lesson" onPress={() => router.back()} className="h-11 w-11 items-center justify-center rounded-xl bg-white"><Ionicons name="close" size={22} color="#B3261E" /></Pressable>
          <Text className="ml-3 flex-1 text-base font-bold text-charcoal" numberOfLines={1}>{lesson.name}</Text>
          <Text accessibilityLabel={`${hearts} hearts left`}>❤️ {hearts}</Text>
        </View>
        <View className="mt-3 h-2.5 overflow-hidden rounded-full bg-line"><View className="h-2.5 rounded-full bg-forest" style={{ width: `${progress * 100}%` }} /></View>
        <Text className="mt-4 text-sm text-muted">{t("lesson.question", { n: Math.min(pos + 1, queue.length), total: queue.length })}</Text>
        <View className="mt-2 flex-row items-center rounded-2xl bg-forest px-4 py-4">
          <Text className="flex-1 text-lg font-bold text-white">{current.prompt}</Text>
          {audioUrl ? (
            <Pressable testID="play-audio" accessibilityRole="button" accessibilityLabel="Play pronunciation" onPress={playAudio} className="ml-3 h-11 w-11 items-center justify-center rounded-full bg-white">
              <Image source={require("@/assets/brand/speaker_icon.png")} style={{ width: 24, height: 24 }} />
            </Pressable>
          ) : null}
        </View>
        {audioFailed ? <Text accessibilityRole="alert" className="mt-1 text-xs text-danger">Audio isn't available right now (it needs an internet connection).</Text> : null}
      </View>

      <View className="flex-1 px-4 pt-4">
        {current.type === "multiple_choice" ? (
          current.options.map((o) => {
            const chosen = selected === o;
            return (
              <Pressable key={o} disabled={!!feedback} onPress={() => setSelected(o)} accessibilityRole="radio" accessibilityState={{ selected: chosen }} className={`mb-3 min-h-[56px] items-center justify-center rounded-2xl border-2 px-4 ${chosen ? "border-forest bg-forest-50" : "border-line bg-white"}`}>
                <Text className="text-lg text-charcoal">{o}</Text>
              </Pressable>
            );
          })
        ) : (
          <View>
            <View className="min-h-[72px] flex-row flex-wrap rounded-2xl border border-dashed border-line bg-white p-2">
              {placed.map((t, i) => (
                <Pressable key={`${t}-${i}`} disabled={!!feedback} onPress={() => setPlaced(placed.filter((_, j) => j !== i))} className="m-1 rounded-xl bg-forest px-3 py-2"><Text className="text-base text-white">{t}</Text></Pressable>
              ))}
            </View>
            <View className="mt-4 flex-row flex-wrap">
              {tiles.map((t, i) => {
                const usedCount = placed.filter((p) => p === t).length;
                const seenBefore = tiles.slice(0, i).filter((x) => x === t).length;
                const used = seenBefore < usedCount;
                return (
                  <Pressable key={`${t}-${i}`} disabled={used || !!feedback} onPress={() => setPlaced([...placed, t])} className={`m-1 rounded-xl border px-3 py-2 ${used ? "border-line bg-line/50" : "border-line bg-white"}`}>
                    <Text className={`text-base ${used ? "text-transparent" : "text-charcoal"}`}>{t}</Text>
                  </Pressable>
                );
              })}
            </View>
          </View>
        )}
      </View>

      <View className={`px-4 pb-4 pt-3 ${feedback ? (feedback.correct ? "bg-forest-50" : "bg-danger/10") : ""}`}>
        {feedback ? (
          <Text accessibilityRole="alert" className={`mb-2 text-base font-bold ${feedback.correct ? "text-forest" : "text-danger"}`}>
            {feedback.correct ? t("lesson.correct") : t("lesson.wrong", { answer: feedback.answer })}
          </Text>
        ) : null}
        {feedback ? <Button testID="continue-btn" label={t("lesson.continue")} onPress={advance} /> : <Button testID="check-btn" label={t("lesson.check")} disabled={!answerOk()} onPress={check} />}
      </View>
    </SafeAreaView>
  );
}
