import { router, useLocalSearchParams } from "expo-router";
import { Share, Text, View } from "react-native";
import { Button, Screen } from "@/components/common/ui";
import { ItineraryView } from "@/components/trip/ItineraryView";
import { tripAsText } from "@/lib/format";
import { useT } from "@/lib/i18n";
import { deleteRemote } from "@/lib/sync";
import { useTrips } from "@/stores/trips";

export default function TripDetail() {
  const t = useT();
  const { id } = useLocalSearchParams<{ id: string }>();
  const trip = useTrips((s) => s.items.find((t) => t.id === id));
  const remove = useTrips((s) => s.remove);

  if (!trip) {
    return (
      <Screen>
        <Text className="mt-6 text-center text-charcoal">This trip is no longer saved.</Text>
        <Button label={t("common.close")} onPress={() => router.back()} className="mt-4" />
      </Screen>
    );
  }
  return (
    <Screen>
      <View className="mt-4 flex-row items-center justify-between">
        <Text className="text-3xl font-extrabold text-forest">{t("trip.yourTrip")}</Text>
        <Button label={t("common.close")} variant="ghost" onPress={() => router.back()} />
      </View>
      <View className="mt-3"><ItineraryView itinerary={trip.itinerary} isMock={trip.isMock} /></View>
      <Button testID="share-trip" label={t("trip.share")} variant="secondary" onPress={() => Share.share({ message: tripAsText(trip.itinerary) })} className="mt-4" />
      <Button testID="delete-trip" label={t("trip.delete")} variant="ghost" onPress={() => { remove(trip.id); void deleteRemote("trips", trip.id); router.back(); }} className="mt-1" />
    </Screen>
  );
}
