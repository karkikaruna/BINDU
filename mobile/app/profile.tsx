import { router } from "expo-router";
import { useState } from "react";
import { Alert, Platform, Text, TextInput, View } from "react-native";
import { Button, Card, Chip, inputClass, Screen, SectionTitle } from "@/components/common/ui";
import { INTERESTS, LANGUAGES, LEVELS } from "@/constants/theme";
import { levelForXp } from "@/lib/gamification";
import { useT } from "@/lib/i18n";
import { syncNow } from "@/lib/sync";
import { deleteAccount } from "@/services/api";
import { useSession } from "@/stores/session";
import { useDiscoveries } from "@/stores/discoveries";
import { useProfile } from "@/stores/profile";
import { useProgress } from "@/stores/progress";

/** Cross-platform confirm: Alert buttons don't render on web, so fall back to window.confirm there. */
function confirmAsync(title: string, body: string, confirmLabel: string, cancelLabel: string): Promise<boolean> {
  if (Platform.OS === "web") return Promise.resolve(typeof window !== "undefined" && window.confirm(`${title}\n\n${body}`));
  return new Promise((resolve) =>
    Alert.alert(title, body, [
      { text: cancelLabel, style: "cancel", onPress: () => resolve(false) },
      { text: confirmLabel, style: "destructive", onPress: () => resolve(true) },
    ], { cancelable: true, onDismiss: () => resolve(false) }),
  );
}

export default function Profile() {
  const t = useT();
  const p = useProfile();
  const prog = useProgress();
  const saved = useDiscoveries((s) => s.items.length);
  const { email, userId, signOut } = useSession();
  const [syncMsg, setSyncMsg] = useState<string | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [deleteMsg, setDeleteMsg] = useState<string | null>(null);

  const sync = async () => {
    setSyncing(true);
    const r = await syncNow();
    setSyncMsg(r.ok ? t("profile.synced", { d: r.discoveries, t: r.trips }) : r.message);
    setSyncing(false);
  };

  const toggleInterest = (i: string) => p.update({ interests: p.interests.includes(i) ? p.interests.filter((x) => x !== i) : [...p.interests, i] });

  const resetAll = () => {
    p.reset();
    prog.reset();
    router.replace("/onboarding");
  };

  const removeAccount = async () => {
    setDeleteMsg(null);
    const ok = await confirmAsync(t("profile.deleteTitle"), t("profile.deleteBody"), t("profile.deleteConfirm"), t("common.cancel"));
    if (!ok) return;
    setDeleting(true);
    try {
      // Ask the server first: only sign out locally once the account is really gone.
      await deleteAccount();
      await signOut();
      setSyncMsg(null);
      setDeleteMsg(t("profile.deleted"));
    } catch {
      setDeleteMsg(t("profile.deleteFailed"));
    } finally {
      setDeleting(false);
    }
  };

  return (
    <Screen>
      <View className="mt-4 flex-row items-center justify-between">
        <Text className="text-3xl font-extrabold text-forest">{t("profile.title")}</Text>
        <Button label={t("common.close")} variant="ghost" onPress={() => router.back()} />
      </View>
      <Card className="mt-2">
        <Text className="text-xl font-bold text-charcoal">{p.displayName || t("profile.guest")}</Text>
        <Text className="text-sm text-muted">{userId ? t("profile.signedInAs", { email: email ?? "" }) : t("profile.guestNote")}</Text>
        <View className="mt-3 flex-row justify-between">
          <Stat label={t("profile.level")} value={String(levelForXp(prog.xp))} />
          <Stat label="XP" value={String(prog.xp)} />
          <Stat label={t("profile.streak")} value={String(prog.streak)} />
          <Stat label={t("profile.lessons")} value={String(Object.keys(prog.completed).length)} />
          <Stat label={t("profile.savedStat")} value={String(saved)} />
        </View>
      </Card>

      <SectionTitle title={t("profile.about")} />
      <TextInput testID="profile-name" value={p.displayName} onChangeText={(v) => p.update({ displayName: v })} maxLength={40} placeholder={t("profile.name")} placeholderTextColor="#8A938C" accessibilityLabel={t("profile.name")} className={inputClass} />
      <Text className="mt-4 mb-2 text-sm font-semibold text-charcoal">{t("profile.interests")}</Text>
      <View className="flex-row flex-wrap">{INTERESTS.map((i) => <Chip key={i} label={t.opt(i)} selected={p.interests.includes(i)} onPress={() => toggleInterest(i)} />)}</View>

      <SectionTitle title={t("profile.account")} />
      {userId ? (
        <View>
          <Button testID="sync-btn" label={t("profile.syncNow")} loading={syncing} onPress={sync} />
          {syncMsg ? <Text accessibilityRole="alert" className="mt-2 text-sm text-muted">{syncMsg}</Text> : null}
          <Button label={t("profile.signOut")} variant="secondary" onPress={async () => { await signOut(); setSyncMsg(null); }} className="mt-3" />
          <Button testID="delete-account" label={t("profile.deleteAccount")} variant="ghost" loading={deleting} onPress={removeAccount} className="mt-1" />
        </View>
      ) : (
        <Button testID="open-auth" label={t("profile.signIn")} variant="secondary" onPress={() => router.push("/auth")} />
      )}
      {deleteMsg ? <Text accessibilityRole="alert" className="mt-2 text-sm text-muted">{deleteMsg}</Text> : null}

      <SectionTitle title={t("profile.ifaceLang")} />
      <View className="flex-row flex-wrap">{LANGUAGES.map((l) => <Chip key={l} label={l} selected={p.language === l} onPress={() => p.update({ language: l })} />)}</View>
      <SectionTitle title={t("profile.nepaliLevel")} />
      <View className="flex-row flex-wrap">{LEVELS.map((l) => <Chip key={l} label={t.opt(l)} selected={p.nepaliLevel === l} onPress={() => p.update({ nepaliLevel: l })} />)}</View>
      <SectionTitle title={t("profile.privacy")} />
      <Text className="text-sm text-muted">{t("profile.privacyBody")}</Text>
      <Button label={t("profile.reset")} variant="secondary" onPress={resetAll} className="mt-6" />
    </Screen>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <View className="items-center">
      <Text className="text-lg font-bold text-forest">{value}</Text>
      <Text className="text-xs text-muted">{label}</Text>
    </View>
  );
}
