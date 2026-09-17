"""
"Clear Next Steps": when a project is Disputed (or a resident who has already
reported wants to take it further), point them at the ONE institution that
actually handles their specific situation instead of dumping all four
contacts on everyone. A resident picks a short situation (a menu, not free
text) and gets back the matching contact, pre-filled with the project
reference and their own report id if they have one.

Config/lookup table, not per-project text — the same four rows serve every
ward and every project, and every channel (app, WhatsApp, SMS) renders off
this one source so a change here never has to be made in three places.

Institution names/hotlines/URLs are real-world facts, not template prose —
they're kept as-is in every language (a hotline number doesn't translate);
only the situation label and the surrounding sentence go through the normal
locale/template system in locales/*.json, same as everything else a resident
reads.
"""
from __future__ import annotations

# Order matters: this is the order residents see the menu in, matching the
# gap-fill spec's table.
ESCALATION_SITUATIONS = [
    "no_response",                # first point of contact for any disputed project
    "financial_accountability",   # money allocated but work not done
    "corruption",                  # funds diverted, inflated costs, ghost contractor
    "maladministration",           # bureaucratic failure, no corruption implied
]

_CONTACTS: dict[str, dict[str, str]] = {
    "no_response": {
        "institution": "Ward Administrator / MCA's Office",
        "detail": "Visit or call your Ward Administrator or MCA's office for {ward} ward — "
                  "they are the first point of contact for any disputed project.",
    },
    "financial_accountability": {
        "institution": "Office of the Auditor-General and the Controller of Budget",
        "detail": "Office of the Auditor-General (oagkenya.go.ke) and the Controller of Budget "
                  "(cob.go.ke) — for money allocated but work not done.",
    },
    "corruption": {
        "institution": "Ethics and Anti-Corruption Commission (EACC)",
        "detail": "EACC via the Integrated Public Complaints Referral Mechanism (IPCRM), "
                  "hotline 0729 888 881/2/3, or the anonymous whistleblower channel "
                  "(reportcorruption.eacc.go.ke) if you want distance from what you report.",
    },
    "maladministration": {
        "institution": "Commission on Administrative Justice (the Ombudsman)",
        "detail": "Commission on Administrative Justice, the Ombudsman (ombudsman.go.ke, "
                  "0800 221 349 toll-free) — for a general service-delivery failure, no "
                  "corruption implied.",
    },
}


class UnknownSituationError(Exception):
    pass


def escalation_contact(situation: str) -> dict:
    if situation not in _CONTACTS:
        raise UnknownSituationError(situation)
    return _CONTACTS[situation]


def render_escalation_response(
    lang: str, situation: str, *, project_name: str, ward: str, project_id: str, report_id: str | None
) -> str:
    """The full pre-filled response text for one situation, in `lang`. Import
    is local to avoid a circular import (translation.py doesn't need to know
    about escalation.py, but this does need t())."""
    from .translation import t

    contact = escalation_contact(situation)
    return t(
        lang,
        "escalation_response",
        situation_label=t(lang, f"escalation_situation_{situation}"),
        institution=contact["institution"],
        detail=contact["detail"].format(ward=ward),
        project_name=project_name,
        project_id=project_id,
        report_id=report_id or t(lang, "escalation_no_report_yet"),
    )


def render_escalation_menu(lang: str) -> str:
    from .translation import t

    lines = [t(lang, "escalation_menu_header")]
    for i, situation in enumerate(ESCALATION_SITUATIONS, start=1):
        lines.append(f"{i}. {t(lang, f'escalation_situation_{situation}')}")
    return "\n".join(lines)


def situation_from_choice(choice: str) -> str | None:
    """Maps a 1-based numeric menu reply to a situation key, or None if the
    reply isn't a valid choice."""
    if not choice.isdigit():
        return None
    index = int(choice) - 1
    if 0 <= index < len(ESCALATION_SITUATIONS):
        return ESCALATION_SITUATIONS[index]
    return None
