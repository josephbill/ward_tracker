import React, { useCallback, useEffect, useState } from "react";
import { View, Text, FlatList, Pressable, StyleSheet, ActivityIndicator } from "react-native";
import NetInfo from "@react-native-community/netinfo";
import { useAppState } from "../state/AppContext";
import { t } from "../i18n/i18n";
import { fetchProjects, Project } from "../api/client";
import { cacheProjects, getCachedProjects, pendingCount } from "../offline/queue";
import { onSyncComplete, syncNow } from "../offline/syncManager";

export default function WardProjectsScreen({ navigation, route }: any) {
  const { lang, county, ward, setPhoneVerified } = useAppState();
  const l = lang || "sw";
  const [projects, setProjects] = useState<Project[]>([]);
  const [deliveredCount, setDeliveredCount] = useState(0);
  const [completionRate, setCompletionRate] = useState(0);
  const [loading, setLoading] = useState(false);
  const [offline, setOffline] = useState(false);
  const [cachedAt, setCachedAt] = useState<string | null>(null);
  const [pending, setPending] = useState(0);
  const [flashMessage, setFlashMessage] = useState<string | null>(null);
  const [needsReverify, setNeedsReverify] = useState(false);

  // Report/issue submission lands here via navigate(..., { flashMessageKey })
  // rather than an Alert.alert dialog — see ReportScreen/ReportIssueScreen's
  // submit(): Alert.alert's onPress callback never fires on the web build,
  // which previously left the resident stuck on the submission screen with
  // no confirmation and no way back. This banner is the redirect target's
  // confirmation instead, and works identically on every platform.
  useEffect(() => {
    const key = route?.params?.flashMessageKey;
    if (!key) return;
    setFlashMessage(key);
    navigation.setParams({ flashMessageKey: undefined });
    const timer = setTimeout(() => setFlashMessage(null), 5000);
    return () => clearTimeout(timer);
  }, [route?.params?.flashMessageKey]);

  const load = useCallback(async () => {
    if (!ward || !county) return;
    setLoading(true);
    try {
      const state = await NetInfo.fetch();
      if (state.isConnected) {
        const data = await fetchProjects(ward, l, county);
        setProjects(data.projects);
        setDeliveredCount(data.delivered_count);
        setCompletionRate(data.purported_completion_rate);
        setOffline(false);
        setCachedAt(null);
        await cacheProjects(county, ward, l, data.projects);
      } else {
        throw new Error("offline");
      }
    } catch {
      const cached = await getCachedProjects(county, ward, l);
      if (cached) {
        setProjects(cached.projects);
        setCachedAt(cached.cachedAt);
        const delivered = cached.projects.filter((p: Project) => p.county_claimed_status === "delivered").length;
        setDeliveredCount(delivered);
        setCompletionRate(cached.projects.length ? delivered / cached.projects.length : 0);
      }
      setOffline(true);
    } finally {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ward, county, l]);

  useEffect(() => {
    load();
    pendingCount().then(setPending);
    const unsub = onSyncComplete((result) => {
      pendingCount().then(setPending);
      if (result.needsReverify) {
        // A queued report's phone looked verified on this device but the
        // backend disagreed (403) — most likely because too much time has
        // passed, or the backend's own state changed since. Clear the
        // stale local flag through the real setter (keeps in-memory state
        // and AsyncStorage in sync) so the next report attempt correctly
        // re-prompts OTP instead of repeating the same silent failure.
        setPhoneVerified(false);
        setNeedsReverify(true);
      }
      load();
    });
    const netUnsub = NetInfo.addEventListener((state) => {
      if (state.isConnected) syncNow();
    });
    return () => {
      unsub();
      netUnsub();
    };
  }, [load]);

  return (
    <View style={styles.container}>
      <View style={styles.menuRow}>
        <Pressable style={styles.menuButton} onPress={() => navigation.navigate("MyReports")} accessibilityRole="button" accessibilityLabel={t(l, "myReports")}>
          <Text style={styles.menuButtonText}>{t(l, "myReports")}</Text>
        </Pressable>
        <Pressable style={styles.menuButton} onPress={() => navigation.navigate("IssuesList")} accessibilityRole="button" accessibilityLabel={t(l, "localIssues")}>
          <Text style={styles.menuButtonText}>{t(l, "localIssues")}</Text>
        </Pressable>
        <Pressable style={styles.menuButton} onPress={() => navigation.navigate("WardSelect")} accessibilityRole="button" accessibilityLabel={t(l, "changeWard")}>
          <Text style={styles.menuButtonText}>{t(l, "changeWard")}</Text>
        </Pressable>
        <Pressable style={styles.menuButton} onPress={() => navigation.navigate("LanguageSelect")} accessibilityRole="button" accessibilityLabel={t(l, "changeLanguage")}>
          <Text style={styles.menuButtonText}>{t(l, "changeLanguage")}</Text>
        </Pressable>
      </View>

      <Text style={styles.wardHeading}>{ward}{county ? `, ${county}` : ""}</Text>

      {flashMessage && (
        <Pressable
          style={styles.successBanner}
          onPress={() => setFlashMessage(null)}
          accessibilityRole="button"
          accessibilityLabel={t(l, flashMessage)}
        >
          <Text style={styles.successBannerText}>{t(l, flashMessage)}</Text>
        </Pressable>
      )}

      {needsReverify && (
        <Pressable
          style={styles.reverifyBanner}
          onPress={() => setNeedsReverify(false)}
          accessibilityRole="button"
          accessibilityLabel={t(l, "needsReverifyNotice")}
        >
          <Text style={styles.reverifyBannerText}>{t(l, "needsReverifyNotice")}</Text>
        </Pressable>
      )}

      {offline && (
        <View style={styles.offlineBanner}>
          <Text style={styles.offlineBannerText}>
            {t(l, "offlineBanner")}
            {cachedAt ? ` (cached ${new Date(cachedAt).toLocaleString()})` : ""}
          </Text>
        </View>
      )}
      {pending > 0 && (
        <View style={styles.pendingBanner}>
          <Text style={styles.pendingBannerText}>{t(l, "reportsWaitingToSync", { count: pending })}</Text>
        </View>
      )}

      {projects.length > 0 && (
        <View style={styles.progressCard}>
          <Text style={styles.progressLabel}>
            {t(l, "completionRateLabel", { percent: Math.round(completionRate * 100), delivered: deliveredCount, total: projects.length })}
          </Text>
          <View style={styles.progressTrack}>
            <View style={[styles.progressFill, { width: `${Math.round(completionRate * 100)}%` }]} />
          </View>
          <Text style={styles.progressCaveat}>{t(l, "completionRateCaveat")}</Text>
        </View>
      )}

      {loading ? (
        <ActivityIndicator style={{ marginTop: 24 }} />
      ) : projects.length === 0 ? (
        <Text style={styles.empty}>{t(l, "noProjectsFound")}</Text>
      ) : (
        <FlatList
          data={projects}
          keyExtractor={(p) => p.id}
          contentContainerStyle={{ paddingBottom: 24 }}
          renderItem={({ item }) => (
            <Pressable
              style={styles.card}
              onPress={() => navigation.navigate("ProjectDetail", { projectId: item.id })}
              accessibilityRole="button"
              accessibilityLabel={`${item.project_name}, ${t(l, `verificationStatus_${item.verification_status}`)}`}
            >
              <Text style={styles.cardTitle}>{item.project_name}</Text>
              <Text style={styles.cardMeta}>{item.financial_year} · Ksh {item.allocated_amount_ksh.toLocaleString()}</Text>
              <Text style={styles.cardStatus}>{t(l, `verificationStatus_${item.verification_status}`)}</Text>
              {!!item.verification_counts?.total_active_reports && (
                <Text style={styles.cardReportCount}>
                  {t(l, "totalReportsLabel", { count: item.verification_counts.total_active_reports })}
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
  menuRow: { flexDirection: "row", gap: 8, marginBottom: 12, flexWrap: "wrap" },
  menuButton: { borderWidth: 1, borderColor: "#0b6e4f", borderRadius: 8, paddingVertical: 6, paddingHorizontal: 10, minHeight: 44, justifyContent: "center" },
  menuButtonText: { color: "#0b6e4f", fontSize: 12, fontWeight: "600" },
  wardHeading: { fontSize: 20, fontWeight: "700", marginBottom: 10 },
  successBanner: { backgroundColor: "#e6f4ef", padding: 12, borderRadius: 8, marginBottom: 8, borderWidth: 1, borderColor: "#0b6e4f" },
  successBannerText: { color: "#0b6e4f", fontSize: 13, fontWeight: "600" },
  reverifyBanner: { backgroundColor: "#fdecea", padding: 12, borderRadius: 8, marginBottom: 8, borderWidth: 1, borderColor: "#b3261e" },
  reverifyBannerText: { color: "#8a2a20", fontSize: 13, fontWeight: "600" },
  offlineBanner: { backgroundColor: "#fff3cd", padding: 10, borderRadius: 8, marginBottom: 8 },
  offlineBannerText: { color: "#664d03", fontSize: 13 },
  pendingBanner: { backgroundColor: "#e7f1ff", padding: 10, borderRadius: 8, marginBottom: 8 },
  pendingBannerText: { color: "#0b4a8f", fontSize: 13 },
  progressCard: { backgroundColor: "#f3f3f3", borderRadius: 10, padding: 12, marginBottom: 14 },
  progressLabel: { fontSize: 13, fontWeight: "600", marginBottom: 8 },
  progressTrack: { height: 8, backgroundColor: "#ddd", borderRadius: 4, overflow: "hidden" },
  progressFill: { height: 8, backgroundColor: "#0b6e4f" },
  progressCaveat: { fontSize: 11, color: "#888", marginTop: 6 },
  empty: { textAlign: "center", marginTop: 40, color: "#777" },
  card: { borderWidth: 1, borderColor: "#eee", borderRadius: 10, padding: 14, marginBottom: 10, backgroundColor: "#fafafa" },
  cardTitle: { fontSize: 15, fontWeight: "600" },
  cardMeta: { fontSize: 12, color: "#666", marginTop: 4 },
  cardStatus: { fontSize: 12, color: "#0b6e4f", marginTop: 4 },
  cardReportCount: { fontSize: 11, color: "#888", marginTop: 2 },
});
