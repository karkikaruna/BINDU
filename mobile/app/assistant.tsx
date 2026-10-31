import { router } from "expo-router";
import { useRef, useState } from "react";
import { ActivityIndicator, KeyboardAvoidingView, Platform, Pressable, ScrollView, Text, TextInput, View, type ScrollViewInstance } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Button, ErrorBanner, inputClass } from "@/components/common/ui";
import { useT } from "@/lib/i18n";
import { ApiError, askAssistant } from "@/services/api";
import type { ChatMessage } from "@/types/features";

type Turn = ChatMessage & { verify?: boolean; mock?: boolean };
const STARTERS = ["What should I wear at a temple?", "What is dal bhat?", "How do I say thank you in Nepali?", "Best way to behave at Pashupatinath?"];

export default function Assistant() {
  const t = useT();
  const [turns, setTurns] = useState<Turn[]>([]);
  const [text, setText] = useState("");
  const [followups, setFollowups] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<{ message: string; retry?: () => void } | null>(null);
  const scroller = useRef<ScrollViewInstance>(null);

  const send = async (q: string, base: Turn[] = turns) => {
    const question = q.trim();
    if (!question || busy) return;
    const history: Turn[] = [...base, { role: "user", content: question }];
    setTurns(history);
    setText("");
    setFollowups([]);
    setError(null);
    setBusy(true);
    try {
      const res = await askAssistant(history.map(({ role, content }) => ({ role, content })));
      setTurns([...history, { role: "assistant", content: res.result.answer, verify: res.result.needs_verification, mock: res.is_mock }]);
      setFollowups(res.result.followups);
    } catch (e) {
      const api = e instanceof ApiError ? e : null;
      setError({ message: api?.message ?? t("common.unexpected"), retry: api?.retryable ? () => send(question, base) : undefined });
      setTurns(base); // roll back the unanswered question so a retry doesn't duplicate it
      setText(question);
    } finally {
      setBusy(false);
      setTimeout(() => scroller.current?.scrollToEnd({ animated: true }), 50);
    }
  };

  return (
    <SafeAreaView className="flex-1 bg-cream">
      <KeyboardAvoidingView className="flex-1" behavior={Platform.OS === "ios" ? "padding" : undefined}>
        <View className="flex-row items-center justify-between px-4 pt-4">
          <Text className="text-3xl font-extrabold text-forest">{t("assistant.title")}</Text>
          <Button label={t("common.close")} variant="ghost" onPress={() => router.back()} />
        </View>
        <ScrollView ref={scroller} className="flex-1 px-4" contentContainerClassName="pb-4" keyboardShouldPersistTaps="handled">
          {turns.length === 0 ? (
            <View className="mt-4">
              <Text className="text-sm text-muted">{t("assistant.intro")}</Text>
              <View className="mt-4 flex-row flex-wrap">
                {STARTERS.map((s) => (
                  <Pressable key={s} accessibilityRole="button" onPress={() => send(s)} className="mb-2 mr-2 rounded-full border border-line bg-white px-4 py-2"><Text className="text-sm text-charcoal">{s}</Text></Pressable>
                ))}
              </View>
            </View>
          ) : null}
          {turns.map((t, i) => (
            <View key={i} className={`mt-3 max-w-[88%] rounded-3xl px-4 py-3 ${t.role === "user" ? "self-end bg-forest" : "self-start border border-line bg-white"}`}>
              <Text className={`text-sm leading-5 ${t.role === "user" ? "text-white" : "text-charcoal"}`}>{t.mock ? "(demo) " : ""}{t.content}</Text>
              {t.role === "assistant" && t.verify ? <Text className="mt-1 text-xs text-muted">Not verified. Check with a trusted source.</Text> : null}
            </View>
          ))}
          {busy ? <View testID="assistant-typing" className="mt-3 self-start"><ActivityIndicator color="#174C3C" /></View> : null}
          {error ? <View className="mt-3"><ErrorBanner message={error.message} onRetry={error.retry} /></View> : null}
          {followups.length > 0 && !busy ? (
            <View className="mt-3 flex-row flex-wrap">
              {followups.map((f) => <Pressable key={f} accessibilityRole="button" onPress={() => send(f)} className="mb-2 mr-2 rounded-full border border-himalaya bg-himalaya-50 px-3 py-1.5"><Text className="text-xs text-himalaya">{f}</Text></Pressable>)}
            </View>
          ) : null}
        </ScrollView>
        <View className="flex-row items-end border-t border-line bg-white px-3 py-2">
          <TextInput testID="assistant-input" value={text} onChangeText={setText} maxLength={1000} multiline placeholder={t("assistant.placeholder")} placeholderTextColor="#8A938C" accessibilityLabel="Your question" onSubmitEditing={() => send(text)} className={`mr-2 max-h-28 flex-1 ${inputClass}`} />
          <Button testID="assistant-send" label={t("assistant.send")} loading={busy} disabled={text.trim().length === 0} onPress={() => send(text)} />
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}
