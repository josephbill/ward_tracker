/**
 * "Clear Next Steps" (gap-fill Section 6) — mirrors backend/app/services/
 * escalation.py's lookup table exactly, so the app renders the same four
 * situations and the same institution contacts as WhatsApp/SMS from one
 * canonical config, just implemented client-side here (no extra endpoint
 * needed — this data never changes per-project or per-ward). If the backend
 * table changes, this one needs the matching edit.
 */
import { Lang, t } from "../i18n/i18n";

export type EscalationSituation = "no_response" | "financial_accountability" | "corruption" | "maladministration";

export const ESCALATION_SITUATIONS: EscalationSituation[] = [
  "no_response",
  "financial_accountability",
  "corruption",
  "maladministration",
];

const CONTACTS: Record<EscalationSituation, { institution: string; detail: string }> = {
  no_response: {
    institution: "Ward Administrator / MCA's Office",
    detail: "Visit or call your Ward Administrator or MCA's office — they are the first point of contact for any disputed project.",
  },
  financial_accountability: {
    institution: "Office of the Auditor-General and the Controller of Budget",
    detail: "Office of the Auditor-General (oagkenya.go.ke) and the Controller of Budget (cob.go.ke) — for money allocated but work not done.",
  },
  corruption: {
    institution: "Ethics and Anti-Corruption Commission (EACC)",
    detail: "EACC via the Integrated Public Complaints Referral Mechanism (IPCRM), hotline 0729 888 881/2/3, or the anonymous whistleblower channel (reportcorruption.eacc.go.ke) if you want distance from what you report.",
  },
  maladministration: {
    institution: "Commission on Administrative Justice (the Ombudsman)",
    detail: "Commission on Administrative Justice, the Ombudsman (ombudsman.go.ke, 0800 221 349 toll-free) — for a general service-delivery failure, no corruption implied.",
  },
};

export function escalationContact(situation: EscalationSituation) {
  return CONTACTS[situation];
}

export function renderEscalationResponse(
  lang: Lang,
  situation: EscalationSituation,
  opts: { projectName: string; projectId: string; reportId: string | null }
): string {
  const contact = escalationContact(situation);
  return t(lang, "escalationResponse", {
    institution: contact.institution,
    detail: contact.detail,
    projectName: opts.projectName,
    projectId: opts.projectId,
    reportId: opts.reportId || t(lang, "escalationNoReportYet"),
  });
}
