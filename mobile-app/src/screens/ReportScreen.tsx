import React, { useEffect, useState } from "react";
import { View, Text, Pressable, StyleSheet, Image, Alert, ActivityIndicator, ScrollView, TextInput } from "react-native";
import * as Location from "expo-location";
import * as ImagePicker from "expo-image-picker";
import { useAppState } from "../state/AppContext";
import { t, Lang } from "../i18n/i18n";
import { Claim } from "../api/client";
import { enqueueReport } from "../offline/queue";
import { syncNow } from "../offline/syncManager";
import VoiceInputButton from "../components/VoiceInputButton";
import { trackEvent } from "../services/analytics";

const CLAIM_OPTIONS: { key: Claim; labelKey: string }[] = [
  { key: "confirmed_delivered", labelKey: "confirmDelivered" },
  { key: "not_delivered", labelKey: "notDelivered" },
  { key: "partially_delivered", labelKey: "partiallyDelivered" },
];

export default function ReportScreen({ route, navigation }: any) {
  const { projectId, projectName } = route.params;
  const { lang, phone, phoneVerified } = useAppState();
  const l = lang || "en";

  const [claim, setClaim] = useState<Claim | null>(null);
  const [remarks, setRemarks] = useState("");
  const [photoUri, setPhotoUri] = useState<string | null>(null);
  const [location, setLocation] = useState<{ lat: number; lon: number } | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!phoneVerified) {
      navigation.replace("PhoneVerify", { returnTo: "Report", returnParams: { projectId, projectName } });
    }
  }, [phoneVerified]);

  const pickPhoto = async (fromCamera: boolean) => {
    const permission = fromCamera
      ? await ImagePicker.requestCameraPermissionsAsync()
      : await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!permission.granted) {
      Alert.alert(t(l, "permissionNeededTitle"), t(l, "photoPermissionExplainer"));
      return;
    }
    const result = fromCamera
      ? await ImagePicker.launchCameraAsync({ quality: 0.5 })
      : await ImagePicker.launchImageLibraryAsync({ quality: 0.5 });
    if (!result.canceled && result.assets?.[0]) {
      setPhotoUri(result.assets[0].uri);
    }
  };

  const shareLocation = async () => {
    // Requested at point of use, not on app install (Section 3).
    const { status } = await Location.requestForegroundPermissionsAsync();
    if (status !== "granted") {
      Alert.alert(t(l, "permissionNeededTitle"), t(l, "locationPermissionExplainer"));
      return;
    }
    const pos = await Location.getCurrentPositionAsync({});
    setLocation({ lat: pos.coords.latitude, lon: pos.coords.longitude });
  };

  const appendTranscript = (text: string) => {
    setRemarks((prev) => (prev ? `${prev} ${text}` : text));
    trackEvent("voice_input_used", { screen: "Report" });
  };

  const submit = async () => {
    if (!claim || !phone) return;
    setSubmitting(true);
    try {
      await enqueueReport({
        project_id: projectId,
        phone,
        claim,
        channel: "app",
        gps_lat: location?.lat ?? null,
        gps_lon: location?.lon ?? null,
        lang: l,
        remarks: remarks.trim() || null,
        photoUri,
      });
      // Fire-and-forget: succeeds immediately if online, otherwise the
      // report stays queued and syncManager's NetInfo listener retries
      // automatically — the UI never blocks on network either way.
      syncNow();
      trackEvent("report_submitted", { project_id: projectId, claim, has_remarks: !!remarks.trim(), has_photo: !!photoUri });
      Alert.alert(t(l, "reportSubmitted"), "", [
        { text: "OK", onPress: () => navigation.popToTop() },
      ]);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={{ padding: 16 }}>
      <Text style={styles.title}>{projectName}</Text>
      <Text style={styles.question}>{t(l, "isThisProjectDelivered")}</Text>

      {CLAIM_OPTIONS.map((opt) => (
        <Pressable
          key={opt.key}
          style={[styles.claimButton, claim === opt.key && styles.claimButtonSelected]}
          onPress={() => setClaim(opt.key)}
        >
          <Text style={[styles.claimButtonText, claim === opt.key && styles.claimButtonTextSelected]}>
            {t(l, opt.labelKey)}
          </Text>
        </Pressable>
      ))}

      <Text style={styles.sectionLabel}>{t(l, "addRemarksOptional")}</Text>
      <TextInput
        style={styles.remarksInput}
        value={remarks}
        onChangeText={setRemarks}
        placeholder={t(l, "remarksPlaceholder")}
        multiline
        numberOfLines={3}
      />
      <VoiceInputButton lang={l as Lang} onTranscript={appendTranscript} />

      <Text style={styles.sectionLabel}>{t(l, "addPhotoOptional")}</Text>
      <View style={styles.row}>
        <Pressable style={styles.smallButton} onPress={() => pickPhoto(true)}>
          <Text style={styles.smallButtonText}>{t(l, "takePhoto")}</Text>
        </Pressable>
        <Pressable style={styles.smallButton} onPress={() => pickPhoto(false)}>
          <Text style={styles.smallButtonText}>{t(l, "choosePhoto")}</Text>
        </Pressable>
      </View>
      {photoUri && <Image source={{ uri: photoUri }} style={styles.photoPreview} />}

      <Text style={styles.sectionLabel}>{t(l, "shareLocationOptional")}</Text>
      <Text style={styles.explainer}>{t(l, "locationPermissionExplainer")}</Text>
      <Pressable style={styles.smallButton} onPress={shareLocation}>
        <Text style={styles.smallButtonText}>{location ? `${location.lat.toFixed(4)}, ${location.lon.toFixed(4)}` : t(l, "shareLocationOptional")}</Text>
      </Pressable>

      <Pressable
        style={[styles.submitButton, (!claim || submitting) && styles.submitButtonDisabled]}
        onPress={submit}
        disabled={!claim || submitting}
      >
        {submitting ? <ActivityIndicator color="#fff" /> : <Text style={styles.submitButtonText}>{t(l, "submitReport")}</Text>}
      </Pressable>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#fff" },
  title: { fontSize: 18, fontWeight: "700", marginBottom: 4 },
  question: { fontSize: 15, color: "#444", marginBottom: 14 },
  claimButton: { borderWidth: 1, borderColor: "#ccc", borderRadius: 10, padding: 14, marginBottom: 8 },
  claimButtonSelected: { borderColor: "#0b6e4f", backgroundColor: "#e6f4ef" },
  claimButtonText: { fontSize: 15, textAlign: "center" },
  claimButtonTextSelected: { color: "#0b6e4f", fontWeight: "700" },
  sectionLabel: { fontSize: 13, color: "#555", marginTop: 18, marginBottom: 6 },
  explainer: { fontSize: 12, color: "#888", marginBottom: 8 },
  row: { flexDirection: "row", gap: 8 },
  smallButton: { borderWidth: 1, borderColor: "#0b6e4f", borderRadius: 8, paddingVertical: 10, paddingHorizontal: 14 },
  smallButtonText: { color: "#0b6e4f", fontWeight: "600", fontSize: 13 },
  remarksInput: { borderWidth: 1, borderColor: "#ccc", borderRadius: 8, padding: 10, fontSize: 14, minHeight: 70, textAlignVertical: "top", marginBottom: 8 },
  photoPreview: { width: 100, height: 100, borderRadius: 8, marginTop: 10 },
  submitButton: { backgroundColor: "#0b6e4f", padding: 16, borderRadius: 10, marginTop: 28, marginBottom: 24 },
  submitButtonDisabled: { opacity: 0.5 },
  submitButtonText: { color: "#fff", textAlign: "center", fontWeight: "700", fontSize: 16 },
});
