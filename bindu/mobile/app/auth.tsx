import { router, useLocalSearchParams } from "expo-router";
import { useState } from "react";
import { Text, TextInput, View } from "react-native";
import { Button, Card, ErrorBanner, inputClass, Screen } from "@/components/common/ui";
import { useT } from "@/lib/i18n";
import { AuthError, requestPasswordReset, supabaseConfigured } from "@/lib/supabase";
import { syncNow } from "@/lib/sync";
import { useProfile } from "@/stores/profile";
import { useSession } from "@/stores/session";

export const isValidEmail = (e: string) => /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(e.trim());

export default function Auth() {
  const t = useT();
  const { signIn, signUp } = useSession();
  const params = useLocalSearchParams<{ mode?: string }>();
  const [mode, setMode] = useState<"signin" | "signup">(params.mode === "signup" ? "signup" : "signin");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const configured = supabaseConfigured();

  const submit = async () => {
    setError(null);
    setNotice(null);
    if (mode === "signup" && !name.trim()) return setError(t("auth.nameRequired"));
    if (!isValidEmail(email)) return setError(t("auth.invalidEmail"));
    if (password.length < 8) return setError(t("auth.shortPassword"));
    if (mode === "signup" && password !== confirm) return setError(t("auth.mismatch"));
    setBusy(true);
    try {
      if (mode === "signup") {
        const r = await signUp(email, password, name.trim());
        if ("needsConfirmation" in r) {
          setNotice(t("auth.confirmNotice"));
          setMode("signin");
          return;
        }
        useProfile.getState().update({ displayName: name.trim().slice(0, 40) }); // onboarding starts with the name they just gave
      } else {
        await signIn(email, password);
      }
      await syncNow();
      // Back to the entry gate, which sends a brand-new account to onboarding and a returning one to their lessons.
      if (router.canDismiss()) router.dismissAll();
      router.replace("/");
    } catch (e) {
      setError(e instanceof AuthError ? e.message : t("common.unexpected"));
    } finally {
      setBusy(false);
    }
  };

  const forgot = async () => {
    setError(null);
    setNotice(null);
    if (!isValidEmail(email)) return setError(t("auth.resetNeedsEmail"));
    setBusy(true);
    try {
      await requestPasswordReset(email.trim());
      setNotice(t("auth.resetSent")); // same message whether or not the address has an account
    } catch (e) {
      setError(e instanceof AuthError ? e.message : t("common.unexpected"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Screen>
      <View className="mt-4 flex-row items-center justify-between">
        <Text className="text-3xl font-extrabold text-forest">{mode === "signin" ? t("auth.signIn") : t("auth.create")}</Text>
        <Button label={t("common.close")} variant="ghost" onPress={() => router.back()} />
      </View>
      <Text className="mt-1 text-sm text-muted">{t("auth.blurb")}</Text>

      {!configured ? (
        <Card className="mt-4"><Text className="text-sm text-charcoal">{t("auth.notConfigured")}</Text></Card>
      ) : null}

      <View className="mt-5">
        {mode === "signup" ? <TextInput testID="auth-name" value={name} onChangeText={setName} placeholder={t("auth.name")} placeholderTextColor="#8A938C" maxLength={40} autoComplete="name" textContentType="name" accessibilityLabel={t("auth.name")} className={`mb-3 ${inputClass}`} /> : null}
        <TextInput testID="auth-email" value={email} onChangeText={setEmail} placeholder={t("auth.email")} placeholderTextColor="#8A938C" autoCapitalize="none" autoComplete="email" keyboardType="email-address" textContentType="emailAddress" accessibilityLabel={t("auth.email")} className={inputClass} />
        <TextInput testID="auth-password" value={password} onChangeText={setPassword} placeholder={t("auth.password")} placeholderTextColor="#8A938C" secureTextEntry autoCapitalize="none" autoComplete={mode === "signin" ? "current-password" : "new-password"} textContentType={mode === "signin" ? "password" : "newPassword"} accessibilityLabel={t("auth.password")} onSubmitEditing={mode === "signin" ? submit : undefined} className={`mt-3 ${inputClass}`} />
        {mode === "signup" ? <TextInput testID="auth-confirm" value={confirm} onChangeText={setConfirm} placeholder={t("auth.confirm")} placeholderTextColor="#8A938C" secureTextEntry autoCapitalize="none" autoComplete="new-password" textContentType="newPassword" accessibilityLabel={t("auth.confirm")} onSubmitEditing={submit} className={`mt-3 ${inputClass}`} /> : null}
      </View>
      {error ? <View className="mt-4"><ErrorBanner message={error} /></View> : null}
      {notice ? <Text accessibilityRole="alert" className="mt-4 text-sm text-forest">{notice}</Text> : null}
      <Button testID="auth-submit" label={mode === "signin" ? t("auth.signIn") : t("auth.create")} loading={busy} disabled={!configured} onPress={submit} className="mt-5" />
      {mode === "signin" ? <Button testID="auth-forgot" label={t("auth.forgot")} variant="ghost" disabled={busy || !configured} onPress={forgot} className="mt-1" /> : null}
      <Button label={mode === "signin" ? t("auth.newHere") : t("auth.haveAccount")} variant="ghost" disabled={busy} onPress={() => { setMode(mode === "signin" ? "signup" : "signin"); setError(null); setNotice(null); }} className="mt-1" />
    </Screen>
  );
}
