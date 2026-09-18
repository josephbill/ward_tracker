import React, { useEffect, useState } from "react";
import { View, Text, Pressable, StyleSheet, Image, ActivityIndicator, ScrollView, TextInput } from "react-native";
import * as Location from "expo-location";
import * as ImagePicker from "expo-image-picker";
import { useAppState } from "../state/AppContext";
import { t, Lang, translateApiError } from "../i18n/i18n";
import { IssueCategory, submitIssue } from "../api/client";
import VoiceInputButton from "../components/VoiceInputButton";
import { trackEvent } from "../services/analytics";
import { showAlert } from "../services/alert";

const CATEGORIES: IssueCategory[] = ["roads", "water", "health", "education", "electricity", "security", "sanitation", "other"];

/**
 * "Areas needing improvement or critical infrastructure" (Section 9 item
 * 3) — unlike ReportScreen, this ISN'T confirming/disputing an existing
 * budgeted project's status; it's a resident surfacing something new
 * (a pothole, a broken borehole) that may have no project record at all.
 *
 * Known limitation: unlike project reports, issue submissions are NOT
 * offline-queued yet — they require a live connection at submit time. The
 * offline queue (src/offline/queue.ts) is scoped to project reports for
 * now; extending it to a second payload shape is straightforward future
 * work, called out here rather than silently shipped as if it were covered.
 */
export default function ReportIssueScreen({ navigation }: any) {
  const { lang, county, ward, phone, phoneVerified } = useAppState();
  const l = lang || "sw";

  const [category, setCategory] = useState<IssueCategory | null>(null);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [photoUri, setPhotoUri] = useState<string | null>(null);
  const [location, setLocation] = useState<{ lat: number; lon: number } | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!phoneVerified) {
      navigation.replace("PhoneVerify", { returnTo: "ReportIssue", returnParams: {} });
    }
  }, [phoneVerified]);

  const pickPhoto = async (fromCamera: boolean) => {
    const permission = fromCamera
      ? await ImagePicker.requestCameraPermissionsAsync()
      : await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!permission.granted) {
      showAlert(t(l, "permissionNeededTitle"), t(l, "photoPermissionExplainer"));
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
    const { status } = await Location.requestForegroundPermissionsAsync();
    if (status !== "granted") {
      showAlert(t(l, "permissionNeededTitle"), t(l, "locationPermissionExplainer"));
      return;
    }
    const pos = await Location.getCurrentPositionAsync({});
    setLocation({ lat: pos.coords.latitude, lon: pos.coords.longitude });
  };

  const submit = async () => {
    if (!category || !title.trim() || !phone || !county || !ward) return;
    setSubmitting(true);
    try {
      await submitIssue({
        phone, county, ward, category, title: title.trim(),
        description: description.trim() || null,
        gps_lat: location?.lat ?? null, gps_lon: location?.lon ?? null,
        photoUri,
      });
      trackEvent("issue_submitted", { category, ward, has_photo: !!photoUri });
      // See ReportScreen.tsx's submit() for why this doesn't go through
      // Alert.alert's onPress: that callback never fires on the web build,
      // which left the resident stuck here after a successful submit.
      navigation.navigate("WardProjects", { flashMessageKey: "issueSubmitted" });
    } catch (err: any) {
      showAlert(t(l, "genericErrorTitle"), translateApiError(l, err.message));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={{ padding: 16 }}>
      <Text style={styles.title}>{t(l, "reportAnIssue")}</Text>
      <Text style={styles.explainer}>{t(l, "reportIssueExplainer")}</Text>

      <Text style={styles.sectionLabel}>{t(l, "issueCategoryLabel")}</Text>
      <View style={styles.categoryGrid}>
        {CATEGORIES.map((cat) => (
          <Pressable
            key={cat}
            style={[styles.categoryChip, category === cat && styles.categoryChipSelected]}
            onPress={() => setCategory(cat)}
            accessibilityRole="radio"
            accessibilityState={{ selected: category === cat }}
            accessibilityLabel={t(l, `issueCategory_${cat}`)}
          >
            <Text style={[styles.categoryChipText, category === cat && styles.categoryChipTextSelected]}>
              {t(l, `issueCategory_${cat}`)}
            </Text>
          </Pressable>
        ))}
      </View>

      <Text style={styles.sectionLabel}>{t(l, "issueTitleLabel")}</Text>
      <TextInput style={styles.input} value={title} onChangeText={setTitle} placeholder={t(l, "issueTitlePlaceholder")} />

      <Text style={styles.sectionLabel}>{t(l, "issueDescriptionLabel")}</Text>
      <TextInput
        style={styles.remarksInput}
        value={description}
        onChangeText={setDescription}
        placeholder={t(l, "issueDescriptionPlaceholder")}
        multiline
        numberOfLines={3}
      />
      <VoiceInputButton
        lang={l as Lang}
        onTranscript={(text) => setDescription((prev) => (prev ? `${prev} ${text}` : text))}
      />

      <Text style={styles.sectionLabel}>{t(l, "addPhotoOptional")}</Text>
      <View style={styles.row}>
        <Pressable style={styles.smallButton} onPress={() => pickPhoto(true)} accessibilityRole="button" accessibilityLabel={t(l, "takePhoto")}>
          <Text style={styles.smallButtonText}>{t(l, "takePhoto")}</Text>
        </Pressable>
        <Pressable style={styles.smallButton} onPress={() => pickPhoto(false)} accessibilityRole="button" accessibilityLabel={t(l, "choosePhoto")}>
          <Text style={styles.smallButtonText}>{t(l, "choosePhoto")}</Text>
        </Pressable>
      </View>
      {photoUri && <Image source={{ uri: photoUri }} style={styles.photoPreview} accessibilityLabel={t(l, "addPhotoOptional")} />}

      <Text style={styles.sectionLabel}>{t(l, "shareLocationOptional")}</Text>
      <Pressable style={styles.smallButton} onPress={shareLocation} accessibilityRole="button" accessibilityLabel={t(l, "shareLocationOptional")}>
        <Text style={styles.smallButtonText}>{location ? `${location.lat.toFixed(4)}, ${location.lon.toFixed(4)}` : t(l, "shareLocationOptional")}</Text>
      </Pressable>

      <Pressable
        style={[styles.submitButton, (!category || !title.trim() || submitting) && styles.submitButtonDisabled]}
        onPress={submit}
        disabled={!category || !title.trim() || submitting}
        accessibilityRole="button"
        accessibilityLabel={t(l, "submitIssue")}
        accessibilityState={{ disabled: !category || !title.trim() || submitting }}
      >
        {submitting ? <ActivityIndicator color="#fff" /> : <Text style={styles.submitButtonText}>{t(l, "submitIssue")}</Text>}
      </Pressable>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#fff" },
  title: { fontSize: 18, fontWeight: "700", marginBottom: 4 },
  explainer: { fontSize: 13, color: "#666", marginBottom: 14 },
  sectionLabel: { fontSize: 13, color: "#555", marginTop: 18, marginBottom: 6 },
  categoryGrid: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  categoryChip: { borderWidth: 1, borderColor: "#ccc", borderRadius: 20, paddingVertical: 8, paddingHorizontal: 14, minHeight: 44, justifyContent: "center" },
  categoryChipSelected: { borderColor: "#0b6e4f", backgroundColor: "#e6f4ef" },
  categoryChipText: { fontSize: 13 },
  categoryChipTextSelected: { color: "#0b6e4f", fontWeight: "700" },
  input: { borderWidth: 1, borderColor: "#ccc", borderRadius: 8, padding: 10, fontSize: 14 },
  remarksInput: { borderWidth: 1, borderColor: "#ccc", borderRadius: 8, padding: 10, fontSize: 14, minHeight: 70, textAlignVertical: "top", marginBottom: 8 },
  row: { flexDirection: "row", gap: 8 },
  smallButton: { borderWidth: 1, borderColor: "#0b6e4f", borderRadius: 8, paddingVertical: 10, paddingHorizontal: 14, minHeight: 44, justifyContent: "center" },
  smallButtonText: { color: "#0b6e4f", fontWeight: "600", fontSize: 13 },
  photoPreview: { width: 100, height: 100, borderRadius: 8, marginTop: 10 },
  submitButton: { backgroundColor: "#0b6e4f", padding: 16, borderRadius: 10, marginTop: 28, marginBottom: 24 },
  submitButtonDisabled: { opacity: 0.5 },
  submitButtonText: { color: "#fff", textAlign: "center", fontWeight: "700", fontSize: 16 },
});
