import { router } from "expo-router";
import { Pressable, Text, View } from "react-native";
import { Badge, Button, Card, EmptyState, Screen, SectionTitle } from "@/components/common/ui";
import { useT } from "@/lib/i18n";
import { deleteRemote } from "@/lib/sync";
import { useDiscoveries } from "@/stores/discoveries";
import { useTrips } from "@/stores/trips";

export default function Journey() {
  const t = useT();
  const items = useDiscoveries((s) => s.items);
  const remove = useDiscoveries((s) => s.remove);
  const trips = useTrips((s) => s.items);

  return (
    <Screen>
      <Text className="mt-4 text-3xl font-extrabold text-forest">{t("journey.title")}</Text>
      <SectionTitle title={t("journey.trips")} />
      {trips.length === 0 ? (
        <EmptyState title={t("journey.noTrips")} body={t("journey.noTripsBody")} action={<Button testID="plan-first-trip" label={t("journey.planTrip")} onPress={() => router.push("/trip/new")} />} />
      ) : (
        <>
          {trips.map((trip) => (
            <Pressable key={trip.id} testID={`trip-${trip.id}`} accessibilityRole="button" onPress={() => router.push({ pathname: "/trip/[id]", params: { id: trip.id } })}>
              <Card className="mb-3">
                <Text className="text-base font-bold text-charcoal">{trip.itinerary.title}</Text>
                <Text className="mt-1 text-sm text-muted">{trip.request.days === 1 ? t("journey.day") : t("journey.days", { n: trip.request.days })} · {trip.request.destination}{trip.isMock ? ` · ${t("journey.demo")}` : ""}</Text>
              </Card>
            </Pressable>
          ))}
          <Button label={t("journey.planAnother")} variant="secondary" onPress={() => router.push("/trip/new")} />
        </>
      )}

      <SectionTitle title={t("journey.saved")} hint={t("journey.savedHint")} />
      {items.length === 0 ? (
        <EmptyState title={t("journey.nothingSaved")} body={t("journey.nothingSavedBody")} />
      ) : (
        items.map((d) => (
          <Card key={d.id} className="mb-3">
            <Text className="text-base font-bold text-charcoal">{d.title}</Text>
            <Text className="mt-1 text-sm text-charcoal">{d.summary}</Text>
            {d.phrase ? (
              <View className="mt-3 rounded-2xl bg-forest-50 p-3">
                <Text className="text-lg font-semibold text-forest">{d.phrase.nepali}</Text>
                <Text className="text-sm text-muted">{d.phrase.romanization} · {d.phrase.english}</Text>
              </View>
            ) : null}
            <View className="mt-3 flex-row items-center justify-between">
              <Badge label={new Date(d.createdAt).toLocaleDateString()} tone="forest" />
              <View className="flex-row">
                <Button testID={`card-${d.id}`} label={t("journey.card")} variant="ghost" onPress={() => router.push({ pathname: "/card/[id]", params: { id: d.id } })} className="min-h-[40px]" />
                <Button label={t("journey.remove")} variant="ghost" onPress={() => { remove(d.id); void deleteRemote("discoveries", d.id); }} className="min-h-[40px]" />
              </View>
            </View>
          </Card>
        ))
      )}
    </Screen>
  );
}
