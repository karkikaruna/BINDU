import { ReactNode } from "react";
import { ActivityIndicator, Pressable, ScrollView, Text, View, type ViewStyle } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useT } from "@/lib/i18n";

export function Screen({ children, scroll = true, padded = true }: { children: ReactNode; scroll?: boolean; padded?: boolean }) {
  const pad = padded ? "px-4" : "";
  return (
    <SafeAreaView edges={["top"]} className="flex-1 bg-cream">
      {scroll ? (
        <ScrollView className="flex-1" contentContainerClassName={`${pad} pb-8`} keyboardShouldPersistTaps="handled">
          {children}
        </ScrollView>
      ) : (
        <View className={`flex-1 ${pad}`}>{children}</View>
      )}
    </SafeAreaView>
  );
}

export function Card({ children, className = "", style }: { children: ReactNode; className?: string; style?: ViewStyle }) {
  return (
    <View style={style} className={`rounded-3xl bg-white border border-line p-4 ${className}`}>
      {children}
    </View>
  );
}

type BtnProps = { label: string; onPress?: () => void; disabled?: boolean; loading?: boolean; variant?: "primary" | "secondary" | "ghost"; className?: string; testID?: string };
export function Button({ label, onPress, disabled, loading, variant = "primary", className = "", testID }: BtnProps) {
  const base = "min-h-[52px] items-center justify-center rounded-2xl px-5 flex-row";
  const styles = {
    primary: disabled ? "bg-forest/40" : "bg-forest active:bg-forest-700",
    secondary: "bg-white border border-line active:bg-cream",
    ghost: "active:bg-forest-50",
  }[variant];
  const text = variant === "primary" ? "text-white" : "text-forest";
  return (
    <Pressable testID={testID} accessibilityRole="button" accessibilityLabel={label} accessibilityState={{ disabled: !!(disabled || loading) }} disabled={disabled || loading} onPress={onPress} className={`${base} ${styles} ${className}`}>
      {loading ? <ActivityIndicator color={variant === "primary" ? "#fff" : "#174C3C"} /> : <Text className={`text-base font-semibold ${text}`}>{label}</Text>}
    </Pressable>
  );
}

export function Chip({ label, selected, onPress }: { label: string; selected?: boolean; onPress?: () => void }) {
  return (
    <Pressable onPress={onPress} accessibilityRole="button" accessibilityState={{ selected: !!selected }} className={`rounded-full border px-4 py-2 mr-2 mb-2 ${selected ? "bg-forest border-forest" : "bg-white border-line"}`}>
      <Text className={`text-sm font-medium ${selected ? "text-white" : "text-charcoal"}`}>{label}</Text>
    </Pressable>
  );
}

export function SectionTitle({ title, hint }: { title: string; hint?: string }) {
  return (
    <View className="mt-6 mb-3">
      <Text className="text-xl font-bold text-charcoal">{title}</Text>
      {hint ? <Text className="text-sm text-muted mt-0.5">{hint}</Text> : null}
    </View>
  );
}

export function Badge({ label, tone = "terracotta" }: { label: string; tone?: "terracotta" | "himalaya" | "forest" }) {
  const t = { terracotta: "bg-terracotta-50 text-terracotta-dark", himalaya: "bg-himalaya-50 text-himalaya", forest: "bg-forest-50 text-forest" }[tone];
  const [bg, fg] = t.split(" ");
  return (
    <View className={`self-start rounded-full px-2.5 py-1 ${bg}`}>
      <Text className={`text-xs font-semibold ${fg}`}>{label}</Text>
    </View>
  );
}

export function EmptyState({ title, body, action }: { title: string; body: string; action?: ReactNode }) {
  return (
    <Card className="items-center py-8">
      <Text className="text-lg font-bold text-charcoal text-center">{title}</Text>
      <Text className="text-sm text-muted text-center mt-1 mb-4">{body}</Text>
      {action}
    </Card>
  );
}

export function ErrorBanner({ message, onRetry }: { message: string; onRetry?: () => void }) {
  const t = useT();
  return (
    <View accessibilityRole="alert" className="rounded-2xl border border-danger/30 bg-danger/5 p-4">
      <Text className="text-danger font-semibold">{t("common.error")}</Text>
      <Text className="text-charcoal mt-1">{message}</Text>
      {onRetry ? (
        <Pressable onPress={onRetry} accessibilityRole="button" className="mt-3 self-start rounded-xl bg-danger px-4 py-2">
          <Text className="text-white font-semibold">{t("common.tryAgain")}</Text>
        </Pressable>
      ) : null}
    </View>
  );
}

export const inputClass = "min-h-[52px] rounded-2xl border border-line bg-white px-4 text-base text-charcoal";
