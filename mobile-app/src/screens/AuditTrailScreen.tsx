import React, { useEffect, useState } from "react";
import { View, Text, FlatList, StyleSheet, ActivityIndicator } from "react-native";
import { useAppState } from "../state/AppContext";
import { t } from "../i18n/i18n";
import { fetchAuditTrail } from "../api/client";

export default function AuditTrailScreen({ route }: any) {
  const { projectId } = route.params;
  const { lang } = useAppState();
  const l = lang || "sw";
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchAuditTrail(projectId, l)
      .then(setData)
      .finally(() => setLoading(false));
  }, [projectId, l]);

  if (loading) return <ActivityIndicator style={{ marginTop: 40 }} />;
  if (!data) return <Text style={styles.empty}>{t(l, "auditTrailLoadError")}</Text>;

  return (
    <View style={styles.container}>
      <Text style={styles.status}>{t(l, "currentStatusLabel")}: {data.verification_status_label}</Text>
      <FlatList
        data={data.events}
        keyExtractor={(e: any) => e.id}
        renderItem={({ item }) => (
          <View style={styles.eventRow}>
            <Text style={styles.eventType}>{item.event_type_label}</Text>
            <Text style={styles.eventDesc}>{item.description}</Text>
            <Text style={styles.eventMeta}>
              {new Date(item.created_at).toLocaleString()} · {t(l, "ledgerRefLabel")} {item.ledger_ref} ·{" "}
              {item.ledger_verified ? t(l, "ledgerVerified") : t(l, "ledgerNotYetVerified")}
            </Text>
          </View>
        )}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#fff", padding: 16 },
  status: { fontSize: 15, fontWeight: "700", marginBottom: 14 },
  eventRow: { borderLeftWidth: 3, borderLeftColor: "#0b6e4f", paddingLeft: 10, marginBottom: 14 },
  eventType: { fontSize: 12, color: "#0b6e4f", fontWeight: "700", textTransform: "uppercase" },
  eventDesc: { fontSize: 14, marginTop: 2 },
  eventMeta: { fontSize: 11, color: "#888", marginTop: 4 },
  empty: { textAlign: "center", marginTop: 40, color: "#777", padding: 16 },
});
