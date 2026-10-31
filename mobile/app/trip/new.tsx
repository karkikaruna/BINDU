import { useMutation } from "@tanstack/react-query";
import { router } from "expo-router";
import { useState } from "react";
import { ActivityIndicator, Text, TextInput, View } from "react-native";
import { Button, Chip, ErrorBanner, inputClass, Screen, SectionTitle } from "@/components/common/ui";
import { ItineraryView } from "@/components/trip/ItineraryView";
import { useT } from "@/lib/i18n";
import { INTERESTS } from "@/constants/theme";
import { ApiError, generateTrip } from "@/services/api";
import { useProfile } from "@/stores/profile";
import { useTrips } from "@/stores/trips";
import type { TripRequest, TripResponse } from "@/types/features";

const PACES = ["relaxed", "balanced", "packed"] as const;
const BUDGETS = ["budget", "mid", "comfortable"] as const;

export default function NewTrip() {
  const t = useT();
  const profileInterests = useProfile((s) => s.interests);
  const saveTrip = useTrips((s) => s.save);
  const [destination, setDestination] = useState("Kathmandu Valley");
  const [days, setDays] = useState(3);
  const [pace, setPace] = useState<TripRequest["pace"]>("balanced");
  const [budget, setBudget] = useState<TripRequest["budget"]>("mid");
  const [interests, setInterests] = useState<string[]>(profileInterests);
  const [result, setResult] = useState<{ req: TripRequest; res: TripResponse } | null>(null);
  const [savedId, setSavedId] = useState<string | null>(null);

  const toggle = (i: string) => setInterests((cur) => (cur.includes(i) ? cur.filter((x) => x !== i) : cur.length >= 6 ? cur : [...cur, i]));
  const valid = destination.trim().length >= 2;

  const gen = useMutation({
    mutationFn: () => {
      const req: TripRequest = { destination: destination.trim(), days, interests, pace, budget };
      return generateTrip(req).then((res) => ({ req, res }));
    },
    onSuccess: (data) => { setResult(data); setSavedId(null); },
  });
  const errMsg = (e: unknown) => (e instanceof ApiError ? e.message : t("common.unexpected"));

  const save = () => {
    if (!result || savedId) return;
    const id = `${Date.now()}`;
    saveTrip({ id, request: result.req, itinerary: result.res.itinerary, isMock: result.res.is_mock, createdAt: new Date().toISOString() });
    setSavedId(id);
  };

  return (
    <Screen>
      <View className="mt-4 flex-row items-center justify-between">
        <Text className="text-3xl font-extrabold text-forest">{t("trip.title")}</Text>
        <Button label={t("common.close")} variant="ghost" onPress={() => router.back()} />
      </View>

      {!result ? (
        <>
          <SectionTitle title={t("trip.where")} />
          <TextInput testID="trip-destination" value={destination} onChangeText={setDestination} maxLength={80} placeholder="e.g. Kathmandu Valley, Bhaktapur" placeholderTextColor="#8A938C" accessibilityLabel="Destination" className={inputClass} />

          <SectionTitle title={t("trip.days")} />
          <View className="flex-row items-center">
            <Button testID="days-minus" label="−" variant="secondary" disabled={days <= 1} onPress={() => setDays((d) => Math.max(1, d - 1))} className="w-14" />
            <Text testID="days-value" className="mx-5 text-2xl font-bold text-charcoal">{days}</Text>
            <Button testID="days-plus" label="+" variant="secondary" disabled={days >= 7} onPress={() => setDays((d) => Math.min(7, d + 1))} className="w-14" />
          </View>

          <SectionTitle title={t("trip.pace")} />
          <View className="flex-row flex-wrap">{PACES.map((p) => <Chip key={p} label={t.opt(p)} selected={pace === p} onPress={() => setPace(p)} />)}</View>
          <SectionTitle title={t("trip.budget")} />
          <View className="flex-row flex-wrap">{BUDGETS.map((b) => <Chip key={b} label={t.opt(b)} selected={budget === b} onPress={() => setBudget(b)} />)}</View>
          <SectionTitle title={t("trip.interests")} hint={t("trip.upTo6")} />
          <View className="flex-row flex-wrap">{INTERESTS.map((i) => <Chip key={i} label={t.opt(i)} selected={interests.includes(i)} onPress={() => toggle(i)} />)}</View>

          {gen.isError ? <View className="mt-4"><ErrorBanner message={errMsg(gen.error)} onRetry={(gen.error as ApiError)?.retryable ? () => gen.mutate() : undefined} /></View> : null}
          {gen.isPending ? <View testID="planning" className="mt-6 items-center"><ActivityIndicator size="large" color="#174C3C" /><Text className="mt-2 text-sm text-muted">{t("trip.planning")}</Text></View> : null}
          <Button testID="generate-btn" label={t("trip.generate")} loading={gen.isPending} disabled={!valid} onPress={() => gen.mutate()} className="mt-5" />
        </>
      ) : (
        <View className="mt-4">
          <ItineraryView itinerary={result.res.itinerary} isMock={result.res.is_mock} disclaimer={result.res.disclaimer} />
          <Button testID="save-trip" label={savedId ? t("trip.saved") : t("trip.save")} variant="secondary" disabled={!!savedId} onPress={save} className="mt-4" />
          <Button label={t("trip.another")} variant="ghost" onPress={() => { setResult(null); gen.reset(); }} className="mt-1" />
        </View>
      )}
    </Screen>
  );
}
