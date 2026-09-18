"""
The one place that actually writes a Report — every channel (REST API,
WhatsApp bot, SMS bot, Bluetooth-hub sync) calls through here, so the
spam-defense gate, ledger anchoring, audit trail, and status aggregation
only exist once and stay consistent across channels (Section 3: "one
backend").
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone

from flask import current_app

from ..db import db
from ..models import Project, Report, Reporter, StatusEvent
from .aggregation import recompute_verification_status
from .ledger import get_ledger_client
from .ledger.base import compute_payload_hash
from .notifications import notify_county_of_report
from .privacy import round_gps
from .spam_defense import check_report_gate, hash_phone, update_reputation

_STATUS_TO_CLAIM = {
    "confirmed": "confirmed_delivered",
    "partially_delivered": "partially_delivered",
    "not_delivered": "not_delivered",
}


class UnknownProjectError(Exception):
    pass


class PhoneNotVerifiedError(Exception):
    pass


# Channels where the report was composed on a device the app itself already
# gated behind OTP verification (see mobile-app/src/screens/ReportScreen.tsx
# — it redirects to PhoneVerify before rendering the submit button; a
# Bluetooth-relayed report is queued from that exact same screen, just
# forwarded over BLE instead of the internet — see
# scripts/simulate_bluetooth_relay.py's docstring). WhatsApp/SMS are
# deliberately excluded: sending a message FROM a number is itself proof of
# controlling that SIM, so there's no separate OTP step in those flows by
# design (see whatsapp_bot.py / sms_bot.py).
_CHANNELS_REQUIRING_OTP = {"app", "bluetooth"}


@dataclass
class SubmitReportResult:
    report: Report
    reporter: Reporter
    project: Project
    status_changed: bool
    previous_status: str
    new_status: str
    user_message_key: str


def get_or_create_reporter(raw_phone: str) -> Reporter:
    phone_hash = hash_phone(raw_phone)
    reporter = Reporter.query.filter_by(phone_hash=phone_hash).first()
    if reporter is None:
        reporter = Reporter(phone_hash=phone_hash)
        db.session.add(reporter)
        db.session.flush()
    return reporter


def latest_active_report_id(raw_phone: str, project_id: str) -> str | None:
    """A resident's own most recent active report on one project, if any —
    used to pre-fill "your report ref" in the escalation ("what you can do
    next") flow so they're not starting from scratch re-explaining what they
    saw. Looks up by phone_hash only; never creates a Reporter row just for
    this lookup, since someone merely browsing/escalating shouldn't gain a
    Reporter record."""
    phone_hash = hash_phone(raw_phone)
    reporter = Reporter.query.filter_by(phone_hash=phone_hash).first()
    if reporter is None:
        return None
    report = (
        Report.query.filter_by(reporter_id=reporter.id, project_id=project_id, active=True)
        .order_by(Report.submitted_at.desc())
        .first()
    )
    return report.id if report else None


def submit_report(
    *,
    project_id: str,
    raw_phone: str,
    claim: str,
    channel: str,
    photo_path: str | None = None,
    gps_lat: float | None = None,
    gps_lon: float | None = None,
    remarks: str | None = None,
) -> SubmitReportResult:
    project = Project.query.get(project_id)
    if project is None:
        raise UnknownProjectError(project_id)

    reporter = get_or_create_reporter(raw_phone)
    if channel in _CHANNELS_REQUIRING_OTP and not reporter.phone_verified:
        raise PhoneNotVerifiedError()

    gate = check_report_gate(reporter, project_id)
    gps_lat, gps_lon = round_gps(gps_lat, gps_lon)

    if gate.supersede_report_id:
        old = Report.query.get(gate.supersede_report_id)
        old.active = False
        old.edited_at = datetime.now(timezone.utc)

    report = Report(
        project_id=project_id,
        reporter_id=reporter.id,
        channel=channel,
        claim=claim,
        photo_path=photo_path,
        gps_lat=gps_lat,
        gps_lon=gps_lon,
        remarks=remarks,
        excluded_from_aggregation=gate.exclude_from_aggregation,
        exclusion_reason=gate.exclusion_reason,
    )
    db.session.add(report)
    db.session.flush()

    ledger = get_ledger_client(current_app.config_class)
    submission_payload = {
        "report_id": report.id,
        "project_id": project_id,
        "reporter_id": reporter.id,
        "claim": claim,
        "channel": channel,
        "remarks": remarks,
        "submitted_at": report.submitted_at.isoformat(),
    }
    receipt = ledger.submit_event("submission", submission_payload)
    report.ledger_ref = receipt.ledger_ref

    db.session.add(
        StatusEvent(
            project_id=project_id,
            related_report_id=report.id,
            actor_reporter_id=reporter.id,
            event_type="submission",
            description=f"Report submitted via {channel}: {claim}",
            payload_json=json.dumps(submission_payload, sort_keys=True),
            payload_hash=receipt.payload_hash,
            ledger_ref=receipt.ledger_ref,
        )
    )

    previous_status = project.verification_status
    new_status = recompute_verification_status(project)
    status_changed = new_status != previous_status

    if status_changed:
        _apply_reputation_updates(project, new_status)
        change_payload = {
            "project_id": project_id,
            "previous_status": previous_status,
            "new_status": new_status,
            "changed_at": datetime.now(timezone.utc).isoformat(),
        }
        change_receipt = ledger.submit_event("status_change", change_payload)
        db.session.add(
            StatusEvent(
                project_id=project_id,
                related_report_id=report.id,
                actor_reporter_id=None,
                event_type="status_change",
                description=f"Status changed from {previous_status} to {new_status}",
                payload_json=json.dumps(change_payload, sort_keys=True),
                payload_hash=change_receipt.payload_hash,
                ledger_ref=change_receipt.ledger_ref,
            )
        )

    db.session.commit()

    # Best-effort county email notification — added after the fact,
    # deliberately last and deliberately unable to affect anything above:
    # the report is already durably saved by the time this runs, and
    # notify_county_of_report() swallows its own exceptions.
    notify_county_of_report(report, project, reporter)

    return SubmitReportResult(
        report=report,
        reporter=reporter,
        project=project,
        status_changed=status_changed,
        previous_status=previous_status,
        new_status=new_status,
        user_message_key=gate.user_message_key,
    )


def _apply_reputation_updates(project: Project, new_status: str) -> None:
    target_claim = _STATUS_TO_CLAIM.get(new_status)
    if target_claim is None:  # "disputed" has no single correct claim yet
        return
    active_reports = Report.query.filter_by(
        project_id=project.id, active=True, excluded_from_aggregation=False
    ).all()
    for r in active_reports:
        reporter = Reporter.query.get(r.reporter_id)
        update_reputation(reporter, corroborated=(r.claim == target_claim))
