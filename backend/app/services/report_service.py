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

from ..config import Config
from ..db import db
from ..models import Project, Report, Reporter, StatusEvent
from .aggregation import recompute_verification_status
from .ledger import get_ledger_client
from .ledger.base import compute_payload_hash
from .spam_defense import check_report_gate, hash_phone, update_reputation

_STATUS_TO_CLAIM = {
    "confirmed": "confirmed_delivered",
    "partially_delivered": "partially_delivered",
    "not_delivered": "not_delivered",
}


class UnknownProjectError(Exception):
    pass


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
    gate = check_report_gate(reporter, project_id)

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

    ledger = get_ledger_client(Config)
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
