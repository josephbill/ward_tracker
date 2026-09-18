import React, { useEffect, useMemo, useState } from "react";
import { View, Text, FlatList, Pressable, StyleSheet, ActivityIndicator } from "react-native";
import { useAppState } from "../state/AppContext";
import { t } from "../i18n/i18n";
import { fetchMyReports, MyReport } from "../api/client";
import ListSearchInput from "../components/ListSearchInput";

export default function MyReportsScreen({ navigation }: any) {
  const { lang, phone, phoneVerified } = useAppState();
  const l = lang || "sw";
  const [reports, setReports] = useState<MyReport[]>([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState("");

  useEffect(() => {
    if (!phone || !phoneVerified) {
      setLoading(false);
      return;
    }
    fetchMyReports(phone, l)
      .then((data) => setReports(data.reports))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [phone, phoneVerified, l]);

  const filteredReports = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return reports;
    return reports.filter(
      (r) =>
        r.project_name.toLowerCase().includes(q) ||
        (r.ward ?? "").toLowerCase().includes(q) ||
        t(l, `claim_${r.claim}`).toLowerCase().includes(q)
    );
  }, [reports, query, l]);

  if (!phone || !phoneVerified) {
    return (
      <View style={styles.container}>
        <Text style={styles.explainer}>{t(l, "myReportsNeedsVerification")}</Text>
        <Pressable
          style={styles.verifyButton}
          onPress={() => navigation.navigate("PhoneVerify", { returnTo: "MyReports" })}
        >
          <Text style={styles.verifyButtonText}>{t(l, "verify")}</Text>
        </Pressable>
      </View>
    );
  }

  if (loading) return <ActivityIndicator style={{ marginTop: 40 }} />;

  return (
    <View style={styles.container}>
      {reports.length > 0 && (
        <ListSearchInput value={query} onChangeText={setQuery} placeholder={t(l, "searchPlaceholder")} />
      )}

      {reports.length === 0 ? (
        <Text style={styles.explainer}>{t(l, "noReportsYet")}</Text>
      ) : filteredReports.length === 0 ? (
        <Text style={styles.explainer}>{t(l, "noSearchResults")}</Text>
      ) : (
        <FlatList
          data={filteredReports}
          keyExtractor={(r) => r.id}
          renderItem={({ item }) => (
            <Pressable
              style={styles.card}
              onPress={() => navigation.navigate("ProjectDetail", { projectId: item.project_id })}
            >
              <Text style={styles.cardTitle}>{item.project_name}</Text>
              <Text style={styles.cardMeta}>{item.ward} · {new Date(item.submitted_at).toLocaleDateString()}</Text>
              <Text style={styles.cardClaim}>{t(l, `claim_${item.claim}`)}</Text>
              {item.verification_status && (
                <Text style={styles.cardStatus}>
                  {t(l, "wardStatusNow")}: {t(l, `verificationStatus_${item.verification_status}`)}
                </Text>
              )}
            </Pressable>
          )}
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#fff", padding: 16 },
  explainer: { textAlign: "center", marginTop: 40, color: "#666", paddingHorizontal: 16, lineHeight: 20 },
  verifyButton: { backgroundColor: "#0b6e4f", padding: 14, borderRadius: 10, marginTop: 20, marginHorizontal: 16 },
  verifyButtonText: { color: "#fff", textAlign: "center", fontWeight: "600" },
  card: { borderWidth: 1, borderColor: "#eee", borderRadius: 10, padding: 14, marginBottom: 10, backgroundColor: "#fafafa" },
  cardTitle: { fontSize: 15, fontWeight: "600" },
  cardMeta: { fontSize: 12, color: "#666", marginTop: 4 },
  cardClaim: { fontSize: 13, color: "#0b6e4f", fontWeight: "600", marginTop: 6 },
  cardStatus: { fontSize: 12, color: "#888", marginTop: 4 },
});
