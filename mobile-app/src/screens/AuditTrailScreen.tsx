import React, { useEffect, useState } from "react";
import { View, Text, FlatList, StyleSheet, ActivityIndicator } from "react-native";
import { useAppState } from "../state/AppContext";
import { t } from "../i18n/i18n";
import { fetchAuditTrail } from "../api/client";
import LedgerRecordView from "../components/LedgerRecordView";

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
      <Text style={styles.explainer}>{t(l, "auditTrailExplainer")}</Text>
      <FlatList
        data={data.events}
        keyExtractor={(e: any) => e.id}
        renderItem={({ item }) => {
          // report_active is only meaningful on "submission" events — null
          // for status_change/dispute_resolution events, which have no
          // single report behind them.
          const superseded = item.report_active === false;
          return (
            <View style={[styles.eventRow, superseded && styles.eventRowSuperseded]}>
              <View style={styles.eventTypeRow}>
                <Text style={[styles.eventType, superseded && styles.eventTypeSuperseded]}>{item.event_type_label}</Text>
                {superseded && <Text style={styles.supersededBadge}>{t(l, "supersededBadge")}</Text>}
              </View>
              <Text style={[styles.eventDesc, superseded && styles.eventDescSuperseded]}>{item.description}</Text>
              {superseded && <Text style={styles.supersededNote}>{t(l, "supersededNote")}</Text>}
              <Text style={styles.eventMeta}>
                {new Date(item.created_at).toLocaleString()} · {t(l, "ledgerRefLabel")} {item.ledger_ref} ·{" "}
                {item.ledger_verified ? t(l, "ledgerVerified") : t(l, "ledgerNotYetVerified")}
              </Text>
              <LedgerRecordView lang={l as any} ledgerRef={item.ledger_ref} dbPayloadHash={item.payload_hash} />
            </View>
          );
        }}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#fff", padding: 16 },
  status: { fontSize: 15, fontWeight: "700", marginBottom: 4 },
  explainer: { fontSize: 12, color: "#777", marginBottom: 14, lineHeight: 17 },
  eventRow: { borderLeftWidth: 3, borderLeftColor: "#0b6e4f", paddingLeft: 10, marginBottom: 14 },
  eventRowSuperseded: { borderLeftColor: "#ccc" },
  eventTypeRow: { flexDirection: "row", alignItems: "center", gap: 8 },
  eventType: { fontSize: 12, color: "#0b6e4f", fontWeight: "700", textTransform: "uppercase" },
  eventTypeSuperseded: { color: "#999" },
  supersededBadge: {
    fontSize: 10, color: "#888", backgroundColor: "#f0f0f0", borderRadius: 4,
    paddingHorizontal: 6, paddingVertical: 1, textTransform: "uppercase", fontWeight: "700",
  },
  eventDesc: { fontSize: 14, marginTop: 2 },
  eventDescSuperseded: { color: "#999", textDecorationLine: "line-through" },
  supersededNote: { fontSize: 11, color: "#888", fontStyle: "italic", marginTop: 2 },
  eventMeta: { fontSize: 11, color: "#888", marginTop: 4 },
  empty: { textAlign: "center", marginTop: 40, color: "#777", padding: 16 },
});
