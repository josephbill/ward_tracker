import React, { useState } from "react";
import { View, Text, Pressable, StyleSheet, Modal } from "react-native";
import { useAppState } from "../state/AppContext";
import { t } from "../i18n/i18n";

interface Destination {
  labelKey: string;
  route: string;
  icon: string;
}

const DESTINATIONS: Destination[] = [
  { labelKey: "navWardProjects", route: "WardProjects", icon: "🏠" },
  { labelKey: "myReports", route: "MyReports", icon: "📝" },
  { labelKey: "localIssues", route: "IssuesList", icon: "⚠️" },
  { labelKey: "reportAnIssue", route: "ReportIssue", icon: "➕" },
  { labelKey: "changeWard", route: "WardSelect", icon: "🏘️" },
  { labelKey: "changeCounty", route: "CountySelect", icon: "📍" },
  { labelKey: "changeLanguage", route: "LanguageSelect", icon: "🌍" },
];

/**
 * Global navigation entry point, rendered in every screen's header (see
 * App.tsx's Stack.Navigator screenOptions). Without this, a resident who
 * navigated into e.g. "My Reports" had no way to reach "Local Issues" or
 * change their ward short of backing out to the ward-projects screen first
 * — and the language/county/ward selection screens had no header at all,
 * so there was no way back out of them once entered outside the initial
 * setup flow. This menu fixes both: it's reachable from anywhere, and it
 * gives every screen a real header (with React Navigation's automatic back
 * button) instead of a hidden one.
 */
export default function MenuButton({ navigation }: { navigation: any }) {
  const { lang } = useAppState();
  const l = lang || "sw";
  const [open, setOpen] = useState(false);

  const go = (route: string) => {
    setOpen(false);
    navigation.navigate(route);
  };

  return (
    <>
      <Pressable
        style={styles.trigger}
        onPress={() => setOpen(true)}
        hitSlop={10}
        accessibilityRole="button"
        accessibilityLabel={t(l, "navigationMenu")}
      >
        <Text style={styles.triggerText}>☰</Text>
      </Pressable>

      <Modal visible={open} transparent animationType="fade" onRequestClose={() => setOpen(false)}>
        <Pressable style={styles.backdrop} onPress={() => setOpen(false)}>
          <Pressable style={styles.sheet} onPress={(e) => e.stopPropagation()}>
            <Text style={styles.sheetTitle}>{t(l, "navigationMenu")}</Text>
            {DESTINATIONS.map((d) => (
              <Pressable
                key={d.route}
                style={styles.item}
                onPress={() => go(d.route)}
                accessibilityRole="button"
                accessibilityLabel={t(l, d.labelKey)}
              >
                <Text style={styles.itemIcon}>{d.icon}</Text>
                <Text style={styles.itemLabel}>{t(l, d.labelKey)}</Text>
              </Pressable>
            ))}
            <Pressable style={styles.closeButton} onPress={() => setOpen(false)} accessibilityRole="button" accessibilityLabel={t(l, "cancel")}>
              <Text style={styles.closeButtonText}>{t(l, "cancel")}</Text>
            </Pressable>
          </Pressable>
        </Pressable>
      </Modal>
    </>
  );
}

const styles = StyleSheet.create({
  trigger: { paddingHorizontal: 12, paddingVertical: 6 },
  triggerText: { fontSize: 22, color: "#0b6e4f" },
  backdrop: { flex: 1, backgroundColor: "rgba(0,0,0,0.35)", justifyContent: "flex-end" },
  sheet: {
    backgroundColor: "#fff", borderTopLeftRadius: 20, borderTopRightRadius: 20,
    paddingTop: 12, paddingBottom: 28, paddingHorizontal: 20,
  },
  sheetTitle: { fontSize: 13, fontWeight: "700", color: "#5b6b66", textTransform: "uppercase", marginBottom: 8, marginTop: 8 },
  item: { flexDirection: "row", alignItems: "center", paddingVertical: 14, borderBottomWidth: 1, borderBottomColor: "#f0f0f0" },
  itemIcon: { fontSize: 20, marginRight: 14, width: 26, textAlign: "center" },
  itemLabel: { fontSize: 16, fontWeight: "600", color: "#14231e" },
  closeButton: { marginTop: 16, paddingVertical: 12, alignItems: "center" },
  closeButtonText: { fontSize: 15, color: "#888", fontWeight: "600" },
});
