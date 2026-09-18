import React, { useState } from "react";
import { View, Text, TextInput, Pressable, StyleSheet } from "react-native";
import { useAppState } from "../state/AppContext";
import { t, translateApiError } from "../i18n/i18n";
import { requestOtp, verifyOtp } from "../api/client";
import { showAlert } from "../services/alert";

/**
 * Section 6: "app should require phone verification via OTP, not just
 * device install." Requested only the first time a resident tries to
 * submit a report (point-of-use, same principle as the location permission
 * prompt) — not during onboarding/install.
 */
export default function PhoneVerifyScreen({ navigation, route }: any) {
  const { lang, setPhone, setPhoneVerified } = useAppState();
  const [phone, setPhoneInput] = useState("");
  const [code, setCode] = useState("");
  const [codeSent, setCodeSent] = useState(false);
  const [busy, setBusy] = useState(false);
  const l = lang || "sw";

  const onRequestCode = async () => {
    if (!phone.trim()) return;
    setBusy(true);
    try {
      await requestOtp(phone.trim());
      setCodeSent(true);
    } catch (err: any) {
      showAlert(t(l, "genericErrorTitle"), translateApiError(l, err.message));
    } finally {
      setBusy(false);
    }
  };

  const onVerify = async () => {
    setBusy(true);
    try {
      await verifyOtp(phone.trim(), code.trim());
      setPhone(phone.trim());
      setPhoneVerified(true);
      const returnTo = route.params?.returnTo ?? "Report";
      const returnParams = route.params?.returnParams ?? route.params;
      navigation.replace(returnTo, returnParams);
    } catch (err: any) {
      showAlert(t(l, "genericErrorTitle"), t(l, "otpMismatchError"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.trustNote}>{t(l, "phoneTrustNote")}</Text>
      <Text style={styles.label}>{t(l, "phoneNumber")}</Text>
      <TextInput
        style={styles.input}
        value={phone}
        onChangeText={setPhoneInput}
        placeholder="+254700000000"
        keyboardType="phone-pad"
        editable={!codeSent}
      />

      {!codeSent ? (
        <Pressable style={styles.button} onPress={onRequestCode} disabled={busy}>
          <Text style={styles.buttonText}>{t(l, "requestCode")}</Text>
        </Pressable>
      ) : (
        <>
          <Text style={styles.label}>{t(l, "enterOtp")}</Text>
          <TextInput style={styles.input} value={code} onChangeText={setCode} keyboardType="number-pad" maxLength={6} />
          <Pressable style={styles.button} onPress={onVerify} disabled={busy}>
            <Text style={styles.buttonText}>{t(l, "verify")}</Text>
          </Pressable>
        </>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 24, backgroundColor: "#fff", justifyContent: "center" },
  trustNote: { fontSize: 12, color: "#888", marginBottom: 12, lineHeight: 18 },
  label: { fontSize: 14, color: "#555", marginBottom: 6, marginTop: 12 },
  input: { borderWidth: 1, borderColor: "#ccc", borderRadius: 8, padding: 12, fontSize: 16 },
  button: { backgroundColor: "#0b6e4f", padding: 14, borderRadius: 10, marginTop: 20 },
  buttonText: { color: "#fff", textAlign: "center", fontWeight: "600", fontSize: 16 },
});
