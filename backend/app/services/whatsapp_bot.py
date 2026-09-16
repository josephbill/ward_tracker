"""
WhatsApp conversation state machine (Section 3 & 4). Detects/remembers the
resident's preferred language per phone number, lets them browse ward
projects, and submit a confirm/dispute report with optional photo + GPS —
all of it going through the same submit_report() the REST API and SMS bot
use, so the audit trail and aggregation behave identically no matter which
channel a report came in on.

Session state is kept in memory per phone number, which is fine for a demo
process; a production deployment would move `_sessions` to Redis or a DB
table so state survives a restart / scales across workers.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..config import Config
from ..models import Project
from .report_service import UnknownProjectError, submit_report
from .translation import format_ksh, supported_languages, t

_LANG_CHOICES = {"1": "en", "2": "sw", "3": "kam"}
_CLAIM_CHOICES = {"1": "confirmed_delivered", "2": "not_delivered", "3": "partially_delivered"}
_PAGE_SIZE = 8  # keeps one WhatsApp message readable on a phone screen


@dataclass
class Session:
    phone: str
    lang: str | None = None
    state: str = "language_select"
    ward: str | None = None
    project_ids: list[str] = field(default_factory=list)
    page: int = 0
    project_id: str | None = None
    claim: str | None = None
    photo_path: str | None = None


_sessions: dict[str, Session] = {}


def _get_session(phone: str, known_lang: str | None = None) -> Session:
    session = _sessions.get(phone)
    if session is None:
        session = Session(phone=phone, lang=known_lang, state="language_select" if not known_lang else "main_menu")
        _sessions[phone] = session
    return session


def reset_sessions() -> None:
    """Test helper."""
    _sessions.clear()


@dataclass
class IncomingMessage:
    from_phone: str
    text: str = ""
    media_path: str | None = None
    latitude: float | None = None
    longitude: float | None = None


def handle_message(msg: IncomingMessage) -> list[str]:
    session = _get_session(msg.from_phone)
    text = (msg.text or "").strip()

    if session.state == "language_select":
        return _handle_language_select(session, text)
    if session.state == "main_menu":
        return _handle_main_menu(session, text)
    if session.state == "browse_ask_ward":
        return _handle_ask_ward(session, text)
    if session.state == "browse_list":
        return _handle_browse_list(session, text)
    if session.state == "project_detail":
        return _handle_project_detail(session, text)
    if session.state == "report_ask_action":
        return _handle_report_action(session, text)
    if session.state == "report_ask_photo":
        return _handle_report_photo(session, text, msg.media_path)
    if session.state == "report_ask_location":
        return _handle_report_location(session, text, msg.latitude, msg.longitude)

    session.state = "language_select"
    return _handle_language_select(session, text)


def _handle_language_select(session: Session, text: str) -> list[str]:
    lang = _LANG_CHOICES.get(text)
    if lang is None:
        return [t("en", "select_language_prompt")]
    session.lang = lang
    session.state = "main_menu"
    return [t(lang, "language_set_confirmation"), t(lang, "main_menu")]


def _handle_main_menu(session: Session, text: str) -> list[str]:
    lang = session.lang
    if text == "1":
        session.state = "browse_ask_ward"
        return [t(lang, "ask_ward")]
    if text == "2":
        session.state = "browse_ask_ward"
        return [t(lang, "ask_ward")]
    if text == "3":
        session.state = "language_select"
        return [t("en", "select_language_prompt")]
    return [t(lang, "invalid_choice"), t(lang, "main_menu")]


def _handle_ask_ward(session: Session, text: str) -> list[str]:
    lang = session.lang
    ward = text.strip()
    projects = Project.query.filter(Project.ward.ilike(ward)).order_by(Project.financial_year.desc()).all()
    if not projects:
        return [t(lang, "no_projects_found"), t(lang, "ask_ward")]

    session.ward = ward
    session.project_ids = [p.id for p in projects]
    session.page = 0
    session.state = "browse_list"
    return [_render_page(session)]


def _render_page(session: Session) -> str:
    lang = session.lang
    projects = Project.query.filter(Project.id.in_(session.project_ids)).all()
    by_id = {p.id: p for p in projects}
    ordered = [by_id[pid] for pid in session.project_ids]

    start = session.page * _PAGE_SIZE
    page_items = ordered[start:start + _PAGE_SIZE]
    has_more = start + _PAGE_SIZE < len(ordered)

    lines = [t(lang, "project_list_header", ward=session.ward)]
    for i, p in enumerate(page_items, start=start + 1):
        lines.append(
            t(lang, "project_list_item", index=i, project_name=p.display_name(lang),
              financial_year=p.financial_year, amount=format_ksh(p.allocated_amount_ksh))
        )
    if has_more:
        lines.append(f"({len(ordered) - start - len(page_items)} more - reply MORE to see them)")
    lines.append(t(lang, "ask_project_choice"))
    return "\n".join(lines)


def _handle_browse_list(session: Session, text: str) -> list[str]:
    lang = session.lang
    if text.strip().upper() == "MORE":
        session.page += 1
        return [_render_page(session)]

    if not text.isdigit() or not (1 <= int(text) <= len(session.project_ids)):
        return [t(lang, "invalid_choice")]

    project_id = session.project_ids[int(text) - 1]
    session.project_id = project_id
    session.state = "project_detail"

    from .translation import render_project_statement

    project = Project.query.get(project_id)
    statement = render_project_statement(project.to_dict(), lang)
    return [statement, t(lang, "ask_report_action")]


def _handle_project_detail(session: Session, text: str) -> list[str]:
    return _handle_report_action(session, text)


def _handle_report_action(session: Session, text: str) -> list[str]:
    lang = session.lang
    if text == "4":
        session.state = "main_menu"
        return [t(lang, "main_menu")]
    claim = _CLAIM_CHOICES.get(text)
    if claim is None:
        return [t(lang, "ask_report_action")]
    session.claim = claim
    session.state = "report_ask_photo"
    return [t(lang, "ask_photo_optional")]


def _handle_report_photo(session: Session, text: str, media_path: str | None) -> list[str]:
    lang = session.lang
    if media_path:
        session.photo_path = media_path
    elif text.strip().upper() != "SKIP":
        return [t(lang, "ask_photo_optional")]
    session.state = "report_ask_location"
    return [t(lang, "ask_location_optional")]


def _handle_report_location(session: Session, text: str, lat: float | None, lon: float | None) -> list[str]:
    lang = session.lang
    if text.strip().upper() != "SKIP" and lat is None:
        return [t(lang, "ask_location_optional")]

    try:
        result = submit_report(
            project_id=session.project_id,
            raw_phone=session.phone,
            claim=session.claim,
            channel="whatsapp",
            photo_path=session.photo_path,
            gps_lat=lat,
            gps_lon=lon,
        )
    except UnknownProjectError:
        session.state = "main_menu"
        return [t(lang, "invalid_choice"), t(lang, "main_menu")]

    messages = [
        t(lang, result.user_message_key, project_name=result.project.display_name(lang), ledger_ref=result.report.ledger_ref)
    ]
    if result.status_changed and result.new_status == "disputed":
        messages.append(
            t(lang, "status_changed_disputed_notice", project_name=result.project.display_name(lang),
              threshold=Config.DISPUTE_THRESHOLD_COUNT)
        )

    session.state = "main_menu"
    session.claim = None
    session.photo_path = None
    messages.append(t(lang, "main_menu"))
    return messages
