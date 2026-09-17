import React, { useEffect, useState } from "react";
import { View, Text, Pressable, StyleSheet, ScrollView, ActivityIndicator } from "react-native";
import { useAppState } from "../state/AppContext";
import { t } from "../i18n/i18n";
import { fetchProject, fetchMyReports, Project } from "../api/client";
import ListenButton from "../components/ListenButton";
import { trackEvent } from "../services/analytics";
import EscalationPanel from "../components/EscalationPanel";

export default function ProjectDetailScreen({ route, navigation }: any) {
  const { projectId } = route.params;
  const { lang, phone, phoneVerified } = useAppState();
  const [project, setProject] = useState<(Project & { reports: any[] }) | null>(null);
  const [loading, setLoading] = useState(true);
  const [myReportId, setMyReportId] = useState<string | null>(null);

  useEffect(() => {
    fetchProject(projectId, lang || "sw")
      .then((p) => {
        setProject(p);
        trackEvent("project_viewed", { project_id: projectId, ward: p.ward });
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [projectId, lang]);

  useEffect(() => {
    // Pre-fills "your report ref" in the escalation panel (Section 6) when
    // the resident already has one for this project — best-effort, never
    // blocks rendering the rest of the screen if it fails or is skipped.
    if (!phoneVerified || !phone) return;
    fetchMyReports(phone, lang || "sw")
      .then((res) => {
        const mine = res.reports.find((r) => r.project_id === projectId && r.active);
        if (mine) setMyReportId(mine.id);
      })
      .catch(() => {});
  }, [projectId, phone, phoneVerified, lang]);

  const l = lang || "sw";

  if (loading) return <ActivityIndicator style={{ marginTop: 40 }} />;
  if (!project) return <Text style={styles.empty}>{t(l, "projectLoadError")}</Text>;

  return (
    <ScrollView style={styles.container} contentContainerStyle={{ padding: 16 }}>
      <Text style={styles.title}>{project.project_name}</Text>
      <Text style={styles.statement}>{project.statement}</Text>

      <ListenButton text={project.statement} lang={l as any} />

      <View style={styles.statusRow}>
        <StatusPill label={t(l, "countyStatusLabel")} value={t(l, `countyStatus_${project.county_claimed_status}`)} />
        <StatusPill
          label={t(l, "citizenStatusLabel")}
          value={t(l, `verificationStatus_${project.verification_status}`)}
          emphasis={project.verification_status === "disputed"}
        />
      </View>

      {project.verification_status === "disputed" && (
        <EscalationPanel
          lang={l as any}
          projectName={project.project_name}
          projectId={project.id}
          reportId={myReportId}
        />
      )}

      <Pressable
        style={styles.primaryButton}
        onPress={() => navigation.navigate("Report", { projectId: project.id, projectName: project.project_name })}
        accessibilityRole="button"
        accessibilityLabel={t(l, "reportOnThisProject")}
      >
        <Text style={styles.primaryButtonText}>{t(l, "reportOnThisProject")}</Text>
      </Pressable>

      <Pressable
        style={styles.secondaryButton}
        onPress={() => navigation.navigate("AuditTrail", { projectId: project.id })}
        accessibilityRole="button"
        accessibilityLabel={t(l, "viewAuditTrail")}
      >
        <Text style={styles.secondaryButtonText}>{t(l, "viewAuditTrail")}</Text>
      </Pressable>

      <Text style={styles.whatsappHint}>{t(l, "whatsappHint", { projectId: project.id })}</Text>

      <Text style={styles.sourceNote}>
        {t(l, "lastUpdatedLabel")}: {project.last_updated_at ? new Date(project.last_updated_at).toLocaleDateString() : "—"}
      </Text>
      <Text style={styles.sourceNote}>
        {t(l, "sourceReferenceLabel")}: {project.source_reference || `${project.source_document}, ${t(l, "pageAbbrev")} ${project.source_page}`}
      </Text>
    </ScrollView>
  );
}

function StatusPill({ label, value, emphasis }: { label: string; value: string; emphasis?: boolean }) {
  return (
    <View style={[styles.pill, emphasis && styles.pillEmphasis]}>
      <Text style={styles.pillLabel}>{label}</Text>
      <Text style={[styles.pillValue, emphasis && styles.pillValueEmphasis]}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#fff" },
  title: { fontSize: 20, fontWeight: "700", marginBottom: 10 },
  statement: { fontSize: 15, lineHeight: 22, color: "#333", marginBottom: 16 },
  statusRow: { flexDirection: "row", gap: 10, marginBottom: 20 },
  pill: { flex: 1, backgroundColor: "#f3f3f3", borderRadius: 10, padding: 10 },
  pillEmphasis: { backgroundColor: "#fdecea" },
  pillLabel: { fontSize: 11, color: "#777" },
  pillValue: { fontSize: 13, fontWeight: "600", marginTop: 2 },
  pillValueEmphasis: { color: "#b3261e" },
  primaryButton: { backgroundColor: "#0b6e4f", padding: 14, borderRadius: 10, marginBottom: 10 },
  primaryButtonText: { color: "#fff", textAlign: "center", fontWeight: "600", fontSize: 16 },
  secondaryButton: { borderWidth: 1, borderColor: "#0b6e4f", padding: 14, borderRadius: 10, marginBottom: 16 },
  secondaryButtonText: { color: "#0b6e4f", textAlign: "center", fontWeight: "600" },
  whatsappHint: { fontSize: 12, color: "#555", marginBottom: 16 },
  sourceNote: { fontSize: 11, color: "#999" },
  empty: { textAlign: "center", marginTop: 40, color: "#777", padding: 16 },
});
