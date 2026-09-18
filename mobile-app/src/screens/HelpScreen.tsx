import React, { useEffect, useState } from "react";
import { View, Text, StyleSheet, ScrollView, ActivityIndicator } from "react-native";
import { useAppState } from "../state/AppContext";
import { t } from "../i18n/i18n";
import { fetchVerificationInfo, VerificationInfo } from "../api/client";

/**
 * Answers the question residents actually asked (gap-fill Section 3): "I
 * reported a project and it still says not verified — what does that mean,
 * and what does it actually take?" Thresholds are fetched rather than
 * hardcoded so this stays accurate if a deployment tunes
 * CONFIRMATION_THRESHOLD_COUNT / DISPUTE_THRESHOLD_COUNT / the independence
 * radius via env vars — see backend/app/config.py.
 */
export default function HelpScreen() {
  const { lang } = useAppState();
  const l = lang || "sw";
  const [info, setInfo] = useState<VerificationInfo | null>(null);

  useEffect(() => {
    fetchVerificationInfo().then(setInfo).catch(() => {});
  }, []);

  if (!info) return <ActivityIndicator style={{ marginTop: 40 }} />;

  const vars = {
    agreeNeeded: info.confirmation_threshold,
    disagreeNeeded: info.dispute_threshold,
    radiusM: info.independence_radius_m,
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={{ padding: 16 }}>
      <Text style={styles.title}>{t(l, "helpTitle")}</Text>
      <Text style={styles.intro}>{t(l, "helpIntro")}</Text>

      <Section title={t(l, "helpStatus_reportedTitle")} body={t(l, "helpStatus_reportedBody")} />
      <Section title={t(l, "helpStatus_confirmedTitle")} body={t(l, "helpStatus_confirmedBody", vars)} />
      <Section title={t(l, "helpStatus_disputedTitle")} body={t(l, "helpStatus_disputedBody", vars)} accent="#b3261e" />
      <Section title={t(l, "helpIndependenceTitle")} body={t(l, "helpIndependenceBody", vars)} />
      <Section title={t(l, "helpCountsTitle")} body={t(l, "helpCountsBody")} />
    </ScrollView>
  );
}

function Section({ title, body, accent }: { title: string; body: string; accent?: string }) {
  return (
    <View style={styles.section}>
      <Text style={[styles.sectionTitle, accent ? { color: accent } : null]}>{title}</Text>
      <Text style={styles.sectionBody}>{body}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#fff" },
  title: { fontSize: 20, fontWeight: "700", marginBottom: 10 },
  intro: { fontSize: 14, color: "#555", lineHeight: 20, marginBottom: 20 },
  section: { marginBottom: 18, borderLeftWidth: 3, borderLeftColor: "#0b6e4f", paddingLeft: 12 },
  sectionTitle: { fontSize: 14, fontWeight: "700", color: "#0b6e4f", marginBottom: 4 },
  sectionBody: { fontSize: 13, color: "#444", lineHeight: 19 },
});
