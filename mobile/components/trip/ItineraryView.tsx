import { Text, View } from "react-native";
import { Badge, Card } from "@/components/common/ui";
import type { Itinerary } from "@/types/features";

const SLOT_LABEL = { morning: "Morning", afternoon: "Afternoon", evening: "Evening" } as const;

export function ItineraryView({ itinerary, isMock, disclaimer }: { itinerary: Itinerary; isMock: boolean; disclaimer?: string }) {
  return (
    <View testID="itinerary-view">
      {isMock ? (
        <View accessibilityRole="alert" className="mb-3 rounded-2xl border border-terracotta bg-terracotta-50 p-3">
          <Text className="font-bold text-terracotta-dark">Demo mode: not a real AI plan</Text>
          <Text className="text-sm text-charcoal">The server is using a placeholder provider. These stops are samples, not recommendations.</Text>
        </View>
      ) : null}
      <Card>
        <Text className="text-2xl font-extrabold text-forest">{itinerary.title}</Text>
        <Text className="mt-1 text-sm text-charcoal">{itinerary.summary}</Text>
      </Card>
      {itinerary.days.map((day) => (
        <Card key={day.day_number} className="mt-3">
          <Badge label={`Day ${day.day_number}`} tone="himalaya" />
          <Text className="mt-2 text-lg font-bold text-charcoal">{day.title}</Text>
          {day.stops.map((s, i) => (
            <View key={i} className="mt-3 border-l-2 border-line pl-3">
              <Text className="text-xs font-semibold uppercase text-muted">{SLOT_LABEL[s.slot]}{s.category ? ` · ${s.category}` : ""}</Text>
              <Text className="text-base font-bold text-charcoal">{s.name}</Text>
              <Text className="text-sm text-charcoal">{s.description}</Text>
              {s.tip ? <Text className="mt-1 text-xs text-muted">Tip: {s.tip}</Text> : null}
            </View>
          ))}
        </Card>
      ))}
      {itinerary.tips.length > 0 ? (
        <Card className="mt-3">
          <Text className="text-base font-bold text-charcoal">Good to know</Text>
          {itinerary.tips.map((t, i) => <Text key={i} className="mt-1.5 text-sm text-charcoal">• {t}</Text>)}
        </Card>
      ) : null}
      <Text className="mt-3 text-xs text-muted">{disclaimer ?? "AI-generated plan. Opening hours, prices and transport are not included; check them locally before you go."}</Text>
    </View>
  );
}
