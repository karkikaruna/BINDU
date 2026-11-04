import { Linking, Pressable, Text, View } from "react-native";
import { Badge, Card } from "@/components/common/ui";
import type { AnalyzeResponse } from "@/types/explore";

const tone = { high: "forest", medium: "himalaya", low: "terracotta" } as const;

export function ResultView({ data }: { data: AnalyzeResponse }) {
  const a = data.analysis;
  return (
    <View testID="result-view">
      {data.is_mock ? (
        <View accessibilityRole="alert" className="mb-3 rounded-2xl border border-terracotta bg-terracotta-50 p-3">
          <Text className="font-bold text-terracotta-dark">Demo mode: not a real AI answer</Text>
          <Text className="text-sm text-charcoal">The server is using a placeholder provider ({data.model}). Nothing below was generated from your photo.</Text>
        </View>
      ) : null}

      <Card>
        <Text className="text-2xl font-extrabold text-forest">{a.title}</Text>
        {a.identified_place ? (
          <View className="mt-2 flex-row items-center">
            <Text className="mr-2 text-sm text-charcoal">Looks like: <Text className="font-semibold">{a.identified_place}</Text></Text>
            <Badge label={`${a.identification_confidence} confidence`} tone={tone[a.identification_confidence]} />
          </View>
        ) : (
          <Text className="mt-1 text-sm text-muted">Couldn't confidently identify the exact place.</Text>
        )}
      </Card>

      <Card className="mt-3">
        <Text className="text-base font-bold text-charcoal">What's visible</Text>
        {a.observations.map((o, i) => <Text key={i} className="mt-1.5 text-sm text-charcoal">• {o}</Text>)}
      </Card>

      <Card className="mt-3">
        <View className="flex-row items-center justify-between">
          <Text className="text-base font-bold text-charcoal">Cultural context</Text>
          <Badge label={`${a.cultural_context.confidence} confidence`} tone={tone[a.cultural_context.confidence]} />
        </View>
        <Text className="mt-2 text-sm leading-5 text-charcoal">{a.cultural_context.text}</Text>
        {a.cultural_context.needs_verification ? <Text className="mt-2 text-xs text-muted">Not verified against a trusted source. Treat as a starting point.</Text> : null}
        {data.sources.map((s) => (
          <Pressable key={s.name} disabled={!s.url} onPress={() => s.url && Linking.openURL(s.url)} accessibilityRole="link">
            <Text className="mt-2 text-xs text-himalaya underline">Source: {s.name}</Text>
          </Pressable>
        ))}
      </Card>

      {a.phrase ? (
        <Card className="mt-3 bg-forest-50">
          <Text className="text-xs font-semibold uppercase text-muted">Try saying</Text>
          <Text className="mt-1 text-2xl font-bold text-forest">{a.phrase.nepali}</Text>
          <Text className="text-base text-charcoal">{a.phrase.romanization}</Text>
          <Text className="text-sm text-muted">{a.phrase.english}</Text>
          {a.phrase.usage ? <Text className="mt-1 text-xs text-muted">{a.phrase.usage}</Text> : null}
        </Card>
      ) : null}

      {a.related_places.length > 0 || a.suggested_activities.length > 0 ? (
        <Card className="mt-3">
          {a.related_places.length > 0 ? <><Text className="text-base font-bold text-charcoal">Nearby or related</Text><Text className="mt-1 text-sm text-charcoal">{a.related_places.join(" · ")}</Text></> : null}
          {a.suggested_activities.length > 0 ? <><Text className="mt-3 text-base font-bold text-charcoal">Ideas</Text>{a.suggested_activities.map((s, i) => <Text key={i} className="mt-1 text-sm text-charcoal">• {s}</Text>)}</> : null}
        </Card>
      ) : null}

      <Text className="mt-3 text-xs text-muted">{data.disclaimer}</Text>
    </View>
  );
}
