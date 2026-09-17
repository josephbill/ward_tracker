"""
SMS keyword flow (Section 3): deliberately narrow compared to the WhatsApp
bot — no menu navigation, since plain SMS has no state a keypad-only phone
can comfortably drive. A resident texts "<PROJECT_CODE> <1|2|3>" (1=confirmed
delivered, 2=not delivered, 3=partially delivered), "NEXT <PROJECT_CODE>
<1|2|3|4>" for the "what can I do next" escalation contacts (Section 9 gap-
fill item 6), or "HELP".

Reuses Reporter.preferred_language if the same phone number has already set
a language via WhatsApp — otherwise defaults to English, since SMS has no
language-selection step of its own for the pilot.
"""
from __future__ import annotations

import re

from ..config import Config
from ..models import Project, Reporter
from .escalation import render_escalation_response, situation_from_choice
from .report_service import UnknownProjectError, latest_active_report_id, submit_report
from .spam_defense import hash_phone
from .translation import t

_CLAIM_CHOICES = {"1": "confirmed_delivered", "2": "not_delivered", "3": "partially_delivered"}

_MESSAGE_RE = re.compile(r"^\s*([A-Za-z0-9\-]+)\s+([123])\s*$")
_NEXT_RE = re.compile(r"^\s*NEXT\s+([A-Za-z0-9\-]+)\s+([1234])\s*$", re.IGNORECASE)


def _lang_for_phone(raw_phone: str) -> str:
    reporter = Reporter.query.filter_by(phone_hash=hash_phone(raw_phone)).first()
    if reporter and reporter.preferred_language in Config.SUPPORTED_LANGUAGES:
        return reporter.preferred_language
    return Config.DEFAULT_LANGUAGE


def handle_sms(from_phone: str, body: str) -> str:
    body = (body or "").strip()
    lang = _lang_for_phone(from_phone)

    if body.upper() in {"HELP", "?"}:
        return t(lang, "sms_help")

    next_match = _NEXT_RE.match(body)
    if next_match:
        project_id_raw, choice = next_match.groups()
        project = Project.query.filter(Project.id.ilike(project_id_raw)).first()
        if project is None:
            return t(lang, "sms_unknown_project")
        situation = situation_from_choice(choice)
        return render_escalation_response(
            lang, situation,
            project_name=project.display_name(lang),
            ward=project.ward,
            project_id=project.id,
            report_id=latest_active_report_id(from_phone, project.id),
        )

    match = _MESSAGE_RE.match(body)
    if not match:
        return t(lang, "sms_help")

    project_id_raw, choice = match.groups()
    project = Project.query.filter(Project.id.ilike(project_id_raw)).first()
    if project is None:
        return t(lang, "sms_unknown_project")

    claim = _CLAIM_CHOICES[choice]
    try:
        result = submit_report(
            project_id=project.id, raw_phone=from_phone, claim=claim, channel="sms"
        )
    except UnknownProjectError:
        return t(lang, "sms_unknown_project")

    return t(
        lang,
        "sms_ack",
        project_name=result.project.display_name(lang),
        claim=claim,
        ledger_ref=result.report.ledger_ref,
    )
