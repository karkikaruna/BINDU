import { Ionicons } from "@expo/vector-icons";
import { router, useLocalSearchParams } from "expo-router";
import { useEffect, useMemo, useRef, useState } from "react";
import { Image, Pressable, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Button } from "@/components/common/ui";
import { findLesson } from "@/lib/curriculum";
import { checkMultipleChoice, checkWordBank, shuffled } from "@/lib/exercise";
import { useT } from "@/lib/i18n";
import { scoreLesson } from "@/lib/scoring";
import { speakNepali, stopSpeech } from "@/lib/speech";
import { useProgress } from "@/stores/progress";
import type { Exercise } from "@/types/lessons";

type Feedback = { correct: boolean; answer: string } | null;

/** Plates of dal bhat per lesson attempt. Lives belong to the lesson, not the account, and refill on every try. */
const MAX_LIVES = 5;

export default function LessonPlayer() {
  const t = useT();
  const { id } = useLocalSearchParams<{ id: string }>();
  const lesson = findLesson(Number(id));
  const { completeLesson } = useProgress();

  const [queue, setQueue] = useState<Exercise[]>(() => lesson?.exercises ?? []);
  const [pos, setPos] = useState(0);
  const [selected, setSelected] = useState<string | null>(null);
  const [placed, setPlaced] = useState<string[]>([]);
  const [feedback, setFeedback] = useState<Feedback>(null);
  const [result, setResult] = useState<{ stars: number; xp: number; corrected: number } | null>(null);
  const [lives, setLives] = useState(MAX_LIVES);
  // "main" is the normal run. Once it ends, every exercise answered wrongly comes back in "review" so it can be corrected (for less XP). Wrong answers cost a plate in both phases.
  const [phase, setPhase] = useState<"main" | "review">("main");
  const missed = useRef(new Set<number>());

  const total = lesson?.exercises.length ?? 0;
  const current = queue[pos];

  const restart = () => {
    stopSpeech();
    missed.current = new Set();
    setQueue(lesson?.exercises ?? []);
    setPos(0);
    setPhase("main");
    setLives(MAX_LIVES);
    setSelected(null);
    setPlaced([]);
    setFeedback(null);
    setResult(null);
  };

  const [audioFailed, setAudioFailed] = useState(false);
  const hear = async (text: string) => {
    setAudioFailed(false);
    if ((await speakNepali(text)) === "unavailable") setAudioFailed(true);
  };
  const readQuestion = () => { if (current?.prompt_ne) void hear(current.prompt_ne); };
  useEffect(() => {
    setAudioFailed(false);
    if (!current || lives <= 0) return;
    const id = setTimeout(() => { if (current.prompt_ne) void hear(current.prompt_ne); }, 350); // a beat after the screen settles
    return () => clearTimeout(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [current?.id, pos]);
  useEffect(() => { if (result || lives <= 0) stopSpeech(); }, [result, lives]);
  useEffect(() => () => stopSpeech(), []);
  const tiles = useMemo(() => (current ? shuffled(current.tokens, current.id) : []), [current]);

  if (!lesson) {
    return <SafeAreaView className="flex-1 items-center justify-center bg-cream"><Text>{t("lesson.notFound")}</Text><Button label={t("common.close")} onPress={() => router.back()} className="mt-4" /></SafeAreaView>;
  }

  if (lives <= 0 && !feedback && !result) {
    return (
      <SafeAreaView className="flex-1 items-center justify-center bg-cream px-6">
        <Text className="text-5xl">🍽️</Text>
        <Text className="mt-3 text-2xl font-extrabold text-charcoal">{t("lesson.noLives")}</Text>
        <Text className="mt-1 text-center text-muted">{t("lesson.noLivesBody")}</Text>
        <Button testID="retry-lesson" label={t("lesson.tryAgain")} onPress={restart} className="mt-6 self-stretch" />
        <Button label={t("lesson.backToLessons")} variant="secondary" onPress={() => router.back()} className="mt-3 self-stretch" />
      </SafeAreaView>
    );
  }

  if (result) {
    return (
      <SafeAreaView className="flex-1 items-center justify-center bg-cream px-6">
        <Text className="text-5xl">🌼</Text>
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
    if (!ok) {
     
      missed.current.add(current.id);
      setLives((n) => Math.max(0, n - 1));
    }
    setFeedback({ correct: ok, answer: current.type === "multiple_choice" ? current.answer[0] : current.answer.join(" ") });
  };

  const advance = () => {
    const wasCorrect = feedback?.correct;
    setFeedback(null);
    setSelected(null);
    setPlaced([]);
   
    if (lives <= 0) return;
    // In the review, a wrong answer goes to the back of the line until it is corrected. It costs a plate too, so the run can still end here.
    const nextQueue = phase === "review" && !wasCorrect ? [...queue, current] : queue;
    if (pos + 1 < nextQueue.length) {
      setQueue(nextQueue);
      setPos(pos + 1);
      return;
    }
    // Main run finished with mistakes: go back over them.
    if (phase === "main" && missed.current.size > 0) {
      setQueue((lesson.exercises).filter((e) => missed.current.has(e.id)));
      setPos(0);
      setPhase("review");
      return;
    }
    const score = scoreLesson(total - missed.current.size, total);
    completeLesson(lesson.id, score.stars, score.xp);
    setResult({ ...score, corrected: missed.current.size });
  };

  const progress = Math.min(1, pos / queue.length);

  return (
    <SafeAreaView className="flex-1 bg-cream">
      <View className="px-4 pt-2">
        <View className="flex-row items-center">
          <Pressable accessibilityRole="button" accessibilityLabel="Close lesson" onPress={() => router.back()} className="h-11 w-11 items-center justify-center rounded-xl bg-white"><Ionicons name="close" size={22} color="#B3261E" /></Pressable>
          <Text className="ml-3 flex-1 text-base font-bold text-charcoal" numberOfLines={1}>{lesson.name}</Text>
          <Text accessibilityLabel={t("lesson.livesLeft", { n: lives, max: MAX_LIVES })} className="text-base">{"🍛".repeat(lives)}{"🍽️".repeat(MAX_LIVES - lives)}</Text>
        </View>
        <View className="mt-3 h-2.5 overflow-hidden rounded-full bg-line"><View className="h-2.5 rounded-full bg-forest" style={{ width: `${progress * 100}%` }} /></View>
        <Text className="mt-4 text-sm text-muted">{t(phase === "review" ? "lesson.reviewTitle" : "lesson.question", { n: Math.min(pos + 1, queue.length), total: queue.length })}</Text>
        <View className="mt-2 flex-row items-center rounded-2xl bg-forest px-4 py-4">
          <Text className="flex-1 text-lg font-bold text-white">{current.prompt}</Text>
          <Pressable testID="play-question" accessibilityRole="button" accessibilityLabel={t("lesson.hearQuestion")} onPress={readQuestion} className="ml-3 h-11 w-11 items-center justify-center rounded-full bg-white">
            <Image source={require("@/assets/brand/speaker_icon.png")} style={{ width: 30, height: 30 }} />
          </Pressable>
        </View>
        {audioFailed ? <Text accessibilityRole="alert" className="mt-1 text-xs text-danger">{t("lesson.audioUnavailable")}</Text> : null}
      </View>

      <View className="flex-1 px-4 pt-4">
        {current.type === "multiple_choice" ? (
          current.options.map((o, i) => {
            const chosen = selected === o;
            return (
              <View key={o} className="mb-3 flex-row items-stretch">
                <Pressable testID={`option-${i}`} disabled={!!feedback} onPress={() => { setSelected(o); void hear(o); }} accessibilityRole="radio" accessibilityState={{ selected: chosen }} className={`min-h-[56px] flex-1 items-center justify-center rounded-2xl border-2 px-4 ${chosen ? "border-forest bg-forest-50" : "border-line bg-white"}`}>
                  <Text className="text-lg text-charcoal">{o}</Text>
                </Pressable>
              </View>
            );
          })
        ) : (
          <View>
            <View className="flex-row items-stretch">
              <View className="min-h-[72px] flex-1 flex-row flex-wrap rounded-2xl border border-dashed border-line bg-white p-2">
                {placed.map((w, i) => (
                  <Pressable key={`${w}-${i}`} disabled={!!feedback} onPress={() => setPlaced(placed.filter((_, j) => j !== i))} className="m-1 rounded-xl bg-forest px-3 py-2"><Text className="text-base text-white">{w}</Text></Pressable>
                ))}
              </View>
            </View>
            <Text className="mt-2 text-xs text-muted">{t("lesson.tapToHear")}</Text>
            <View className="mt-4 flex-row flex-wrap">
              {tiles.map((w, i) => {
                const usedCount = placed.filter((p) => p === w).length;
                const seenBefore = tiles.slice(0, i).filter((x) => x === w).length;
                const used = seenBefore < usedCount;
                return (
                  <Pressable key={`${w}-${i}`} disabled={used || !!feedback} onPress={() => { setPlaced([...placed, w]); void hear(w); }} accessibilityHint={t("lesson.tapToHear")} className={`m-1 rounded-xl border px-3 py-2 ${used ? "border-line bg-line/50" : "border-line bg-white"}`}>
                    <Text className={`text-base ${used ? "text-transparent" : "text-charcoal"}`}>{w}</Text>
                  </Pressable>
                );
              })}
            </View>
          </View>
        )}
      </View>

      <View className={`px-4 pb-4 pt-3 ${feedback ? (feedback.correct ? "bg-forest-50" : "bg-danger/10") : ""}`}>
        {feedback ? (
          <View className="mb-2 flex-row items-center">
            <Text accessibilityRole="alert" className={`flex-1 text-base font-bold ${feedback.correct ? "text-forest" : "text-danger"}`}>
              {feedback.correct ? t("lesson.correct") : t("lesson.wrong", { answer: feedback.answer })}
            </Text>
          </View>
        ) : null}
        {feedback ? <Button testID="continue-btn" label={t("lesson.continue")} onPress={advance} /> : <Button testID="check-btn" label={t("lesson.check")} disabled={!answerOk()} onPress={check} />}
      </View>
    </SafeAreaView>
  );
}