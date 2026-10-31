import { useMutation } from "@tanstack/react-query";
import * as ImagePicker from "expo-image-picker";
import { useState } from "react";
import { ActivityIndicator, Image, Text, TextInput, View } from "react-native";
import { Button, Card, ErrorBanner, Screen, SectionTitle } from "@/components/common/ui";
import { useT } from "@/lib/i18n";
import { ResultView } from "@/components/explore/ResultView";
import { analyzeImage, ApiError, askFollowUp, type PickedImage } from "@/services/api";
import { useDiscoveries } from "@/stores/discoveries";
import type { AnalyzeResponse } from "@/types/explore";

type QA = { q: string; a: string; mock: boolean; verify: boolean };

const toPicked = (a: ImagePicker.ImagePickerAsset): PickedImage => ({
  uri: a.uri,
  mimeType: a.mimeType ?? "image/jpeg",
  fileName: a.fileName ?? "photo.jpg",
});

export default function Explore() {
  const t = useT();
  const [image, setImage] = useState<PickedImage | null>(null);
  const [question, setQuestion] = useState("");
  const [hint, setHint] = useState("");
  const [permissionNote, setPermissionNote] = useState<string | null>(null);
  const [result, setResult] = useState<AnalyzeResponse | null>(null);
  const [savedId, setSavedId] = useState<string | null>(null);
  const [followUp, setFollowUp] = useState("");
  const [thread, setThread] = useState<QA[]>([]);
  const saveDiscovery = useDiscoveries((s) => s.save);

  const analyze = useMutation({
    mutationFn: () => analyzeImage(image!, question, hint),
    onSuccess: (data) => { setResult(data); setThread([]); setSavedId(null); },
  });
  const ask = useMutation({
    mutationFn: (q: string) => askFollowUp(q, result!.analysis.title, result!.analysis.cultural_context.text),
    onSuccess: (data, q) => { setThread((t) => [...t, { q, a: data.result.answer, mock: data.is_mock, verify: data.result.needs_verification }]); setFollowUp(""); },
  });

  const pick = async (source: "camera" | "gallery") => {
    setPermissionNote(null);
    const perm = source === "camera" ? await ImagePicker.requestCameraPermissionsAsync() : await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!perm.granted) {
      setPermissionNote(source === "camera" ? "Camera access was denied. You can enable it in Settings, or choose a photo from your gallery instead." : "Photo access was denied. You can enable it in Settings, or take a photo with the camera instead.");
      return;
    }
    const opts: ImagePicker.ImagePickerOptions = { mediaTypes: ["images"], quality: 0.8, allowsEditing: false };
    const res = source === "camera" ? await ImagePicker.launchCameraAsync(opts) : await ImagePicker.launchImageLibraryAsync(opts);
    if (!res.canceled && res.assets[0]) {
      setImage(toPicked(res.assets[0]));
      setResult(null);
      analyze.reset();
    }
  };

  const reset = () => { setImage(null); setResult(null); setThread([]); setQuestion(""); setHint(""); analyze.reset(); ask.reset(); };

  const save = () => {
    if (!result || savedId) return;
    const id = `${Date.now()}`;
    const a = result.analysis;
    saveDiscovery({ id, title: a.title, summary: a.cultural_context.text, phrase: a.phrase ? { nepali: a.phrase.nepali, romanization: a.phrase.romanization, english: a.phrase.english } : null, createdAt: new Date().toISOString() });
    setSavedId(id);
  };

  const errMsg = (e: unknown) => (e instanceof ApiError ? e.message : t("common.unexpected"));

  return (
    <Screen>
      <Text className="mt-4 text-3xl font-extrabold text-forest">{t("explore.title")}</Text>
      <Text className="mt-1 text-sm text-muted">{t("explore.subtitle")}</Text>

      {!image ? (
        <View className="mt-5">
          <Button testID="take-photo" label={t("explore.takePhoto")} onPress={() => pick("camera")} />
          <Button testID="pick-photo" label={t("explore.gallery")} variant="secondary" onPress={() => pick("gallery")} className="mt-3" />
          {permissionNote ? <Text accessibilityRole="alert" className="mt-3 text-sm text-danger">{permissionNote}</Text> : null}
          <Card className="mt-5"><Text className="text-sm text-muted">Your photo is sent to the BINDU server and an AI provider to generate the answer. It isn't stored by BINDU. Location data embedded in the photo is removed before it leaves the server.</Text></Card>
        </View>
      ) : (
        <View className="mt-4">
          <Image source={{ uri: image.uri }} accessibilityLabel="Selected photo preview" style={{ width: "100%", height: 260, borderRadius: 24 }} resizeMode="cover" />
          {!result ? (
            <>
              <SectionTitle title="Anything specific?" hint="Optional. Naming the place helps BINDU use trusted notes." />
              <TextInput value={hint} onChangeText={setHint} maxLength={120} placeholder="Place, e.g. Patan Durbar Square" placeholderTextColor="#8A938C" accessibilityLabel="Place name" className="min-h-[52px] rounded-2xl border border-line bg-white px-4 text-base text-charcoal" />
              <TextInput value={question} onChangeText={setQuestion} maxLength={500} placeholder="Your question (optional)" placeholderTextColor="#8A938C" accessibilityLabel="Your question" multiline className="mt-3 min-h-[52px] rounded-2xl border border-line bg-white px-4 py-3 text-base text-charcoal" />
              {analyze.isError ? <View className="mt-4"><ErrorBanner message={errMsg(analyze.error)} onRetry={(analyze.error as ApiError)?.retryable ? () => analyze.mutate() : undefined} /></View> : null}
              {analyze.isPending ? (
                <View testID="analyzing" className="mt-6 items-center"><ActivityIndicator size="large" color="#174C3C" /><Text className="mt-2 text-sm text-muted">{t("explore.looking")}</Text></View>
              ) : null}
              <Button testID="analyze-btn" label={t("explore.analyze")} loading={analyze.isPending} onPress={() => analyze.mutate()} className="mt-5" />
              <Button label={t("explore.differentPhoto")} variant="ghost" disabled={analyze.isPending} onPress={reset} className="mt-1" />
            </>
          ) : (
            <View className="mt-4">
              <ResultView data={result} />

              {thread.map((t, i) => (
                <Card key={i} className="mt-3">
                  <Text className="text-sm font-semibold text-forest">You: {t.q}</Text>
                  <Text className="mt-1 text-sm text-charcoal">{t.mock ? "(demo) " : ""}{t.a}</Text>
                  {t.verify ? <Text className="mt-1 text-xs text-muted">Not verified. Check with a trusted source.</Text> : null}
                </Card>
              ))}
              <SectionTitle title={t("explore.followUp")} />
              <TextInput value={followUp} onChangeText={setFollowUp} maxLength={500} placeholder="e.g. Who made these carvings?" placeholderTextColor="#8A938C" accessibilityLabel="Follow-up question" className="min-h-[52px] rounded-2xl border border-line bg-white px-4 text-base text-charcoal" />
              {ask.isError ? <View className="mt-3"><ErrorBanner message={errMsg(ask.error)} /></View> : null}
              <Button testID="ask-btn" label={t("explore.ask")} loading={ask.isPending} disabled={followUp.trim().length < 2} onPress={() => ask.mutate(followUp.trim())} className="mt-3" />

              <Button testID="save-btn" label={savedId ? t("explore.saved") : t("explore.save")} variant="secondary" disabled={!!savedId} onPress={save} className="mt-3" />
              <Button label={t("explore.newPhoto")} variant="ghost" onPress={reset} className="mt-1" />
            </View>
          )}
        </View>
      )}
    </Screen>
  );
}
