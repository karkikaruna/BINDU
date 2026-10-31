import { Ionicons } from "@expo/vector-icons";
import { Pressable, Text, View } from "react-native";

type Props = { title: string; subtitle: string; icon: React.ComponentProps<typeof Ionicons>["name"]; onPress?: () => void; soon?: boolean; tint?: string };

/** Quick-action tile. Features not built yet are shown disabled with an honest "Soon" label. */
export function ActionTile({ title, subtitle, icon, onPress, soon, tint = "#174C3C" }: Props) {
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={soon ? `${title} (coming soon)` : title}
      accessibilityState={{ disabled: !!soon }}
      disabled={soon}
      onPress={onPress}
      className={`w-[48.5%] rounded-3xl border border-line bg-white p-4 mb-3 ${soon ? "opacity-60" : "active:bg-cream"}`}
    >
      <View className="h-11 w-11 items-center justify-center rounded-2xl" style={{ backgroundColor: tint + "1A" }}>
        <Ionicons name={icon} size={24} color={tint} />
      </View>
      <Text className="mt-3 text-base font-bold text-charcoal">{title}</Text>
      <Text className="text-xs text-muted mt-0.5">{soon ? "Coming soon" : subtitle}</Text>
    </Pressable>
  );
}
