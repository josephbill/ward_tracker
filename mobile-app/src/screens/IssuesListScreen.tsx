import React, { useEffect, useState } from "react";
import { View, Text, FlatList, Pressable, StyleSheet, ActivityIndicator } from "react-native";
import { useAppState } from "../state/AppContext";
import { t } from "../i18n/i18n";
import { fetchIssues, Issue } from "../api/client";

export default function IssuesListScreen({ navigation }: any) {
  const { lang, county, ward } = useAppState();
  const l = lang || "sw";
  const [issues, setIssues] = useState<Issue[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!ward || !county) return;
    fetchIssues(ward, county)
      .then((data) => setIssues(data.issues))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [ward, county]);

  return (
    <View style={styles.container}>
      <Pressable style={styles.reportButton} onPress={() => navigation.navigate("ReportIssue")}>
        <Text style={styles.reportButtonText}>{t(l, "reportAnIssue")}</Text>
      </Pressable>

      {loading ? (
        <ActivityIndicator style={{ marginTop: 24 }} />
      ) : issues.length === 0 ? (
        <Text style={styles.empty}>{t(l, "noIssuesYet")}</Text>
      ) : (
        <FlatList
          data={issues}
          keyExtractor={(i) => i.id}
          contentContainerStyle={{ paddingBottom: 24 }}
          renderItem={({ item }) => (
            <View style={styles.card}>
              <View style={styles.cardHeaderRow}>
                <Text style={styles.categoryTag}>{t(l, `issueCategory_${item.category}`)}</Text>
                <Text style={styles.statusTag}>{t(l, `issueStatus_${item.status}`)}</Text>
              </View>
              <Text style={styles.cardTitle}>{item.title}</Text>
              {item.description ? <Text style={styles.cardDesc}>{item.description}</Text> : null}
              <Text style={styles.cardMeta}>{new Date(item.submitted_at).toLocaleDateString()}</Text>
            </View>
          )}
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#fff", padding: 16 },
  reportButton: { backgroundColor: "#0b6e4f", padding: 14, borderRadius: 10, marginBottom: 16 },
  reportButtonText: { color: "#fff", textAlign: "center", fontWeight: "700" },
  empty: { textAlign: "center", marginTop: 40, color: "#777" },
  card: { borderWidth: 1, borderColor: "#eee", borderRadius: 10, padding: 14, marginBottom: 10, backgroundColor: "#fafafa" },
  cardHeaderRow: { flexDirection: "row", justifyContent: "space-between", marginBottom: 6 },
  categoryTag: { fontSize: 11, color: "#0b6e4f", fontWeight: "700", textTransform: "uppercase" },
  statusTag: { fontSize: 11, color: "#888", fontWeight: "600" },
  cardTitle: { fontSize: 15, fontWeight: "600" },
  cardDesc: { fontSize: 13, color: "#555", marginTop: 4 },
  cardMeta: { fontSize: 11, color: "#999", marginTop: 6 },
});
