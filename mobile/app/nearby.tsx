import { useQuery } from "@tanstack/react-query";
import * as Location from "expo-location";
import { router, useLocalSearchParams } from "expo-router";
import { useState } from "react";
import { ActivityIndicator, Linking, Pressable, Text, TextInput, View } from "react-native";
import { Badge, Button, Card, Chip, EmptyState, ErrorBanner, inputClass, Screen, SectionTitle } from "@/components/common/ui";
import { formatDistance, mapsUrl } from "@/lib/format";
import { useT } from "@/lib/i18n";
import { ApiError, getNearby, getPlaceCategories, searchPlaces } from "@/services/api";

type Origin = { lat: number; lng: number } | null;

export default function Nearby() {
  const t = useT();
  const { q: initialQ } = useLocalSearchParams<{ q?: string }>();
  const [origin, setOrigin] = useState<Origin>(null);
  const [query, setQuery] = useState(initialQ ?? "");
  const [submitted, setSubmitted] = useState(initialQ ?? "");
  const [category, setCategory] = useState<string | undefined>(undefined);
  const [locating, setLocating] = useState(false);
  const [note, setNote] = useState<string | null>(null);

  const cats = useQuery({ queryKey: ["place-categories"], queryFn: getPlaceCategories });
  const mode = origin ? "nearby" : submitted ? "search" : "idle";
  const places = useQuery({
    queryKey: ["places", mode, origin?.lat, origin?.lng, submitted, category],
    enabled: mode !== "idle",
    queryFn: () => (origin ? getNearby(origin.lat, origin.lng, category) : searchPlaces(submitted, category)),
  });

  const locate = async () => {
    setNote(null);
    setLocating(true);
    try {
      const perm = await Location.requestForegroundPermissionsAsync();
      if (!perm.granted) {
        setNote("Location access was denied. You can enable it in Settings, or search by destination below.");
        return;
      }
      const pos = await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.Balanced });
      setOrigin({ lat: pos.coords.latitude, lng: pos.coords.longitude });
      setSubmitted("");
    } catch {
      setNote("Couldn't get your location. Check that location services are on, or search by destination below.");
    } finally {
      setLocating(false);
    }
  };

  const err = places.error;
  const list = places.data?.places ?? [];

  return (
    <Screen>
      <View className="mt-4 flex-row items-center justify-between">
        <Text className="text-3xl font-extrabold text-forest">{t("nearby.title")}</Text>
        <Button label={t("common.close")} variant="ghost" onPress={() => router.back()} />
      </View>
      <Text className="mt-1 text-sm text-muted">{t("nearby.subtitle")}</Text>

      <Button testID="use-location" label={origin ? t("nearby.locationFound") : t("nearby.useLocation")} loading={locating} onPress={locate} className="mt-4" />
      {note ? <Text accessibilityRole="alert" className="mt-2 text-sm text-danger">{note}</Text> : null}

      <SectionTitle title={t("nearby.orSearch")} />
      <TextInput testID="place-search" value={query} onChangeText={setQuery} onSubmitEditing={() => { setOrigin(null); setSubmitted(query.trim()); }} returnKeyType="search" placeholder="e.g. Bhaktapur, temple, curd" placeholderTextColor="#8A938C" accessibilityLabel="Search places" className={inputClass} />
      <Button testID="place-search-btn" label={t("nearby.search")} variant="secondary" disabled={query.trim().length < 2} onPress={() => { setOrigin(null); setSubmitted(query.trim()); }} className="mt-3" />

      {cats.data && cats.data.length > 0 ? (
        <View className="mt-4 flex-row flex-wrap">
          <Chip label={t("nearby.all")} selected={!category} onPress={() => setCategory(undefined)} />
          {cats.data.map((c) => <Chip key={c} label={t.opt(c)} selected={category === c} onPress={() => setCategory(category === c ? undefined : c)} />)}
        </View>
      ) : null}

      {mode === "idle" ? <View className="mt-4"><EmptyState title={t("nearby.where")} body={t("nearby.whereBody")} /></View> : null}
      {places.isPending && mode !== "idle" ? <View className="mt-6 items-center"><ActivityIndicator size="large" color="#174C3C" /></View> : null}
      {places.isError ? <View className="mt-4"><ErrorBanner message={err instanceof ApiError ? err.message : t("common.unexpected")} onRetry={() => places.refetch()} /></View> : null}
      {places.isSuccess && list.length === 0 ? <View className="mt-4"><EmptyState title="Nothing found" body={origin ? "No curated places within 50 km of you. The list currently covers the Kathmandu Valley." : "Try a different name or clear the category filter."} /></View> : null}

      {list.map((p) => (
        <Card key={p.id} className="mt-3">
          <View className="flex-row items-center justify-between">
            <Badge label={t.opt(p.category)} tone="himalaya" />
            {p.distance_km != null ? <Text testID={`distance-${p.id}`} className="text-sm font-semibold text-forest">{formatDistance(p.distance_km)}</Text> : null}
          </View>
          <Text className="mt-2 text-base font-bold text-charcoal">{p.name}</Text>
          <Text className="text-xs text-muted">{p.area}</Text>
          <Text className="mt-1 text-sm text-charcoal">{p.blurb}</Text>
          <View className="mt-3 flex-row items-center justify-between">
            <Pressable accessibilityRole="link" onPress={() => Linking.openURL(mapsUrl(p.latitude, p.longitude))}><Text className="text-sm font-semibold text-himalaya underline">{t("nearby.openMaps")}</Text></Pressable>
            {p.source_url ? <Pressable accessibilityRole="link" onPress={() => Linking.openURL(p.source_url!)}><Text className="text-xs text-himalaya underline">Source</Text></Pressable> : null}
          </View>
        </Card>
      ))}
      {places.data ? <Text className="mt-4 text-xs text-muted">{places.data.note}</Text> : null}
    </Screen>
  );
}
