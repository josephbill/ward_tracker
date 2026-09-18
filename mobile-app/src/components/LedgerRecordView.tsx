import React, { useState } from "react";
import { View, Text, Pressable, StyleSheet, ActivityIndicator, Linking } from "react-native";
import { Lang, t } from "../i18n/i18n";
import {
  MirrorMessage,
  fetchMirrorMessage,
  formatConsensusTimestamp,
  hashscanTopicUrl,
  isRealHederaRef,
} from "../services/hedera";

/**
 * "View reported data from both a DB and a ledger perspective" (gap-fill
 * Section 2). The caller (AuditTrailScreen) already shows the DB side —
 * what Flask/SQLite has stored, translated, read instantly. This is the
 * OTHER side: a live, on-demand fetch straight from Hedera's public mirror
 * node, fetched from the device itself rather than proxied through our own
 * backend — so what it shows is independent proof, not just "the backend
 * says the backend is telling the truth."
 */
export default function LedgerRecordView({
  lang, ledgerRef, dbPayloadHash,
}: {
  lang: Lang;
  ledgerRef: string | null;
  dbPayloadHash: string;
}) {
  const [expanded, setExpanded] = useState(false);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<MirrorMessage | null>(null);
  const [error, setError] = useState<string | null>(null);

  const onRealLedger = isRealHederaRef(ledgerRef);

  const load = async () => {
    if (!ledgerRef) return;
    setLoading(true);
    setError(null);
    try {
      const msg = await fetchMirrorMessage(ledgerRef);
      setMessage(msg);
    } catch (err: any) {
      setError(err.message || "error");
    } finally {
      setLoading(false);
    }
  };

  const toggle = () => {
    const next = !expanded;
    setExpanded(next);
    if (next && !message && !loading) load();
  };

  if (!ledgerRef) return null;

  if (!onRealLedger) {
    return (
      <Text style={styles.stubNote}>{t(lang, "ledgerStubNote")}</Text>
    );
  }

  const hashscanUrl = hashscanTopicUrl(ledgerRef);
  const hashesMatch = message?.payloadHash === dbPayloadHash;

  return (
    <View>
      <Pressable
        onPress={toggle}
        style={styles.toggle}
        accessibilityRole="button"
        accessibilityLabel={t(lang, "viewOnHedera")}
      >
        <Text style={styles.toggleText}>{expanded ? t(lang, "hideHederaRecord") : t(lang, "viewOnHedera")}</Text>
      </Pressable>

      {expanded && (
        <View style={styles.card}>
          {loading && <ActivityIndicator size="small" color="#0b6e4f" />}
          {error && <Text style={styles.errorText}>{t(lang, "hederaLookupError")}</Text>}
          {message && (
            <>
              <Row label={t(lang, "hederaTopicLabel")} value={message.topicId} />
              <Row label={t(lang, "hederaSequenceLabel")} value={String(message.sequenceNumber)} />
              <Row label={t(lang, "hederaConsensusTimeLabel")} value={formatConsensusTimestamp(message.consensusTimestamp)} />
              <Row label={t(lang, "hederaPayloadHashLabel")} value={message.payloadHash ?? "—"} mono />
              <Text style={[styles.matchText, hashesMatch ? styles.matchOk : styles.matchFail]}>
                {hashesMatch ? t(lang, "hederaHashMatches") : t(lang, "hederaHashMismatch")}
              </Text>
              {hashscanUrl && (
                <Pressable onPress={() => Linking.openURL(hashscanUrl)} accessibilityRole="link">
                  <Text style={styles.link}>{t(lang, "openInHashscan")} ↗</Text>
                </Pressable>
              )}
            </>
          )}
        </View>
      )}
    </View>
  );
}

function Row({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <View style={styles.row}>
      <Text style={styles.rowLabel}>{label}</Text>
      <Text style={[styles.rowValue, mono && styles.mono]} numberOfLines={2}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  stubNote: { fontSize: 11, color: "#999", fontStyle: "italic", marginTop: 4 },
  toggle: { marginTop: 6, alignSelf: "flex-start" },
  toggleText: { fontSize: 12, color: "#0b6e4f", fontWeight: "600", textDecorationLine: "underline" },
  card: { backgroundColor: "#f6faf8", borderRadius: 8, borderWidth: 1, borderColor: "#dbe9e3", padding: 10, marginTop: 6 },
  row: { flexDirection: "row", justifyContent: "space-between", marginBottom: 4, gap: 8 },
  rowLabel: { fontSize: 11, color: "#667", flexShrink: 0 },
  rowValue: { fontSize: 11, color: "#222", flexShrink: 1, textAlign: "right" },
  mono: { fontFamily: "monospace" as any },
  errorText: { fontSize: 12, color: "#b3261e" },
  matchText: { fontSize: 12, fontWeight: "700", marginTop: 4 },
  matchOk: { color: "#0b6e4f" },
  matchFail: { color: "#b3261e" },
  link: { fontSize: 12, color: "#0b6e4f", marginTop: 6, textDecorationLine: "underline" },
});
