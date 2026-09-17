import React, { useState } from "react";
import { View, Text, Pressable, StyleSheet } from "react-native";
import { Lang, t } from "../i18n/i18n";
import { ESCALATION_SITUATIONS, EscalationSituation, renderEscalationResponse } from "../services/escalation";
import { trackEvent } from "../services/analytics";

/**
 * "Clear Next Steps" (gap-fill Section 6): shown on a Disputed project's
 * detail screen. A resident picks the situation that matches what they're
 * reporting (a short menu, not free text) and gets back the ONE institution
 * that handles it — pre-filled with the project reference and their own
 * report id if they have one — instead of four contacts dumped on everyone.
 * Same config table WhatsApp/SMS render from (services/escalation.ts).
 */
export default function EscalationPanel({
  lang, projectName, projectId, reportId,
}: {
  lang: Lang;
  projectName: string;
  projectId: string;
  reportId: string | null;
}) {
  const [selected, setSelected] = useState<EscalationSituation | null>(null);

  return (
    <View style={styles.card} accessibilityLabel={t(lang, "whatYouCanDo")}>
      <Text style={styles.title}>{t(lang, "whatYouCanDoNotice")}</Text>

      {selected ? (
        <>
          <Text style={styles.situationLabel}>{t(lang, `escalationSituation_${selected}`)}</Text>
          <Text style={styles.response}>
            {renderEscalationResponse(lang, selected, { projectName, projectId, reportId })}
          </Text>
          <Pressable
            style={styles.backButton}
            onPress={() => setSelected(null)}
            accessibilityRole="button"
            accessibilityLabel={t(lang, "escalationBack")}
            hitSlop={8}
          >
            <Text style={styles.backButtonText}>{t(lang, "escalationBack")}</Text>
          </Pressable>
        </>
      ) : (
        <>
          <Text style={styles.prompt}>{t(lang, "escalationMenuPrompt")}</Text>
          {ESCALATION_SITUATIONS.map((situation) => (
            <Pressable
              key={situation}
              style={styles.situationButton}
              onPress={() => {
                setSelected(situation);
                trackEvent("escalation_situation_selected", { situation, project_id: projectId });
              }}
              accessibilityRole="button"
              accessibilityLabel={t(lang, `escalationSituation_${situation}`)}
            >
              <Text style={styles.situationButtonText}>{t(lang, `escalationSituation_${situation}`)}</Text>
            </Pressable>
          ))}
        </>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  card: { backgroundColor: "#fdecea", borderRadius: 12, padding: 14, marginBottom: 20 },
  title: { fontSize: 14, fontWeight: "700", color: "#8a2a20", marginBottom: 10 },
  prompt: { fontSize: 13, color: "#6b3229", marginBottom: 10 },
  situationButton: {
    backgroundColor: "#fff", borderRadius: 8, borderWidth: 1, borderColor: "#e3b3ac",
    paddingVertical: 12, paddingHorizontal: 12, marginBottom: 8, minHeight: 44, justifyContent: "center",
  },
  situationButtonText: { fontSize: 13, color: "#5a2019" },
  situationLabel: { fontSize: 13, fontWeight: "700", color: "#8a2a20", marginBottom: 6 },
  response: { fontSize: 13, color: "#5a2019", lineHeight: 19, marginBottom: 10 },
  backButton: { paddingVertical: 10, minHeight: 44, justifyContent: "center" },
  backButtonText: { fontSize: 13, color: "#8a2a20", fontWeight: "600", textDecorationLine: "underline" },
});
