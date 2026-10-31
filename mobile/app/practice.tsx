import { useMutation } from "@tanstack/react-query";
import { router } from "expo-router";
import { useState } from "react";
import { ActivityIndicator, Text, TextInput, View } from "react-native";
import { Badge, Button, Card, Chip, ErrorBanner, inputClass, Screen, SectionTitle } from "@/components/common/ui";
import { useT } from "@/lib/i18n";
import { ApiError, evaluatePractice, generatePractice } from "@/services/api";
import { useProfile } from "@/stores/profile";
import { useProgress } from "@/stores/progress";
import type { EvaluateResponse, PracticeItem } from "@/types/features";

const TOPICS = ["Greetings", "Ordering food", "Shopping & bargaining", "Asking directions", "At a temple", "Emergencies"];
const XP_PER_CORRECT = 5;

export default function Practice() {
  const t = useT();
  const level = useProfile((s) => s.nepaliLevel);
  const addXp = useProgress((s) => s.addXp);
  const [topic, setTopic] = useState(TOPICS[0]);
  const [items, setItems] = useState<PracticeItem[] | null>(null);
  const [mock, setMock] = useState(false);
  const [idx, setIdx] = useState(0);
  const [answer, setAnswer] = useState("");
  const [verdict, setVerdict] = useState<EvaluateResponse | null>(null);
  const [correct, setCorrect] = useState(0);
  const [done, setDone] = useState(false);

  const gen = useMutation({
    mutationFn: () => generatePractice(topic, level, 3),
    onSuccess: (d) => { setItems(d.result.items); setMock(d.is_mock); setIdx(0); setAnswer(""); setVerdict(null); setCorrect(0); setDone(false); },
  });
  const check = useMutation({
    mutationFn: () => evaluatePractice(items![idx].prompt_en, items![idx].expected_nepali, answer.trim()),
    onSuccess: (d) => { setVerdict(d); if (d.result.correct) setCorrect((c) => c + 1); },
  });
  const errMsg = (e: unknown) => (e instanceof ApiError ? e.message : t("common.unexpected"));

  const next = () => {
    if (!items) return;
    if (idx + 1 >= items.length) {
      // Practice earns a little XP (not streak/lessons) so it counts without competing with the lesson path.
      addXp(correct * XP_PER_CORRECT);
      setDone(true);
      return;
    }
    setIdx(idx + 1); setAnswer(""); setVerdict(null); check.reset();
  };
  const restart = () => { setItems(null); setDone(false); gen.reset(); check.reset(); };

  return (
    <Screen>
      <View className="mt-4 flex-row items-center justify-between">
        <Text className="text-3xl font-extrabold text-forest">{t("practice.title")}</Text>
        <Button label={t("common.close")} variant="ghost" onPress={() => router.back()} />
      </View>
      <Text className="mt-1 text-sm text-muted">{t("practice.subtitle")}</Text>

      {!items ? (
        <>
          <SectionTitle title={t("practice.pickTopic")} hint={`${t("profile.nepaliLevel")}: ${t.opt(level)}`} />
          <View className="flex-row flex-wrap">{TOPICS.map((tp) => <Chip key={tp} label={t.opt(tp)} selected={topic === tp} onPress={() => setTopic(tp)} />)}</View>
          {gen.isError ? <View className="mt-4"><ErrorBanner message={errMsg(gen.error)} onRetry={(gen.error as ApiError)?.retryable ? () => gen.mutate() : undefined} /></View> : null}
          {gen.isPending ? <View className="mt-6 items-center"><ActivityIndicator size="large" color="#174C3C" /></View> : null}
          <Button testID="start-practice" label={t("practice.start")} loading={gen.isPending} onPress={() => gen.mutate()} className="mt-5" />
        </>
      ) : done ? (
        <Card className="mt-5 items-center">
          <Text className="text-5xl">🙏</Text>
          <Text className="mt-2 text-2xl font-extrabold text-forest">Practice complete</Text>
          <Text testID="practice-score" className="mt-1 text-base text-charcoal">{correct} of {items.length} correct{correct > 0 ? ` · +${correct * XP_PER_CORRECT} XP` : ""}</Text>
          <Button label={t("practice.again")} onPress={restart} className="mt-5 self-stretch" />
        </Card>
      ) : (
        <View className="mt-4">
          {mock ? <View accessibilityRole="alert" className="mb-3 rounded-2xl border border-terracotta bg-terracotta-50 p-3"><Text className="text-sm text-charcoal">Demo mode: placeholder phrases and marking, not a real tutor.</Text></View> : null}
          <Badge label={`Question ${idx + 1} of ${items.length}`} tone="forest" />
          <View className="mt-2 rounded-2xl bg-forest px-4 py-4"><Text className="text-lg font-bold text-white">{items[idx].prompt_en}</Text></View>
          {items[idx].hint ? <Text className="mt-2 text-xs text-muted">Hint: {items[idx].hint}</Text> : null}
          <TextInput testID="practice-input" value={answer} onChangeText={setAnswer} editable={!verdict} maxLength={200} placeholder="Your answer in Nepali" placeholderTextColor="#8A938C" accessibilityLabel="Your answer" autoCapitalize="none" className={`mt-4 ${inputClass}`} />
          {check.isError ? <View className="mt-3"><ErrorBanner message={errMsg(check.error)} /></View> : null}
          {verdict ? (
            <Card className={`mt-4 ${verdict.result.correct ? "bg-forest-50" : ""}`}>
              <Text accessibilityRole="alert" className={`text-base font-bold ${verdict.result.correct ? "text-forest" : "text-danger"}`}>{verdict.result.correct ? "Correct!" : "Not quite"} · {verdict.result.score}/100</Text>
              <Text className="mt-1 text-sm text-charcoal">{verdict.result.feedback}</Text>
              {!verdict.result.correct ? <Text className="mt-2 text-sm text-charcoal">Answer: <Text className="font-bold">{verdict.result.corrected || items[idx].expected_nepali}</Text> ({items[idx].romanization})</Text> : null}
              {verdict.is_mock ? <Text className="mt-1 text-xs text-muted">Marked by the demo provider.</Text> : null}
            </Card>
          ) : null}
          {verdict ? <Button testID="practice-next" label={idx + 1 >= items.length ? t("practice.finish") : t("practice.next")} onPress={next} className="mt-4" /> : <Button testID="practice-check" label={t("practice.check")} loading={check.isPending} disabled={answer.trim().length === 0} onPress={() => check.mutate()} className="mt-4" />}
        </View>
      )}
    </Screen>
  );
}
