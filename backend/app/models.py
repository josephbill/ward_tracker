"""
SQLAlchemy models.

Design notes (Section 5 & 6 of the spec):
  - Reporter.phone_hash is the identity anchor, never the raw phone number.
    Reporter.id (a UUID) is what gets shown anywhere reports are attributed.
  - Report rows are never deleted. An edited report is superseded (marked
    inactive) rather than overwritten in place, and a burst-flagged report is
    marked excluded_from_aggregation rather than removed — the full history
    stays visible in the audit trail.
  - StatusEvent is the append-only audit log; every row also carries the
    ledger_ref returned by the Hedera (or stub) ledger client so the trail
    is independently verifiable.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import object_session

from .db import db


def _uuid() -> str:
    return uuid.uuid4().hex


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Project(db.Model):
    __tablename__ = "projects"

    id = db.Column(db.String(40), primary_key=True)  # e.g. KASIKEU-2022-23-001
    ward = db.Column(db.String(80), nullable=False, index=True)
    county = db.Column(db.String(80), nullable=False)
    subward = db.Column(db.String(80), nullable=False)
    sector = db.Column(db.String(120), nullable=False)
    project_name = db.Column(db.String(255), nullable=False)
    # Translated titles (Section 4: template+variable translation covers UI
    # chrome and the statement grammar, but the project *name* itself is
    # free text lifted from the source PDF — it needs its own translation,
    # not just substitution. Populated from data/project_name_translations.json
    # at seed time; nullable so an untranslated project still renders (falls
    # back to English — see services/translation.resolve_project_name).
    project_name_sw = db.Column(db.String(255), nullable=True)
    project_name_kam = db.Column(db.String(255), nullable=True)
    description = db.Column(db.Text, nullable=False, default="")
    financial_year = db.Column(db.String(10), nullable=False)
    allocated_amount_ksh = db.Column(db.Integer, nullable=False, default=0)

    # What the county's own document claims: delivered | ongoing | not_started | planned
    county_claimed_status = db.Column(db.String(20), nullable=False)
    county_remarks = db.Column(db.Text, nullable=False, default="")
    source_document = db.Column(db.String(255), nullable=False)
    source_page = db.Column(db.Integer, nullable=False)
    # A specific citation within source_document (e.g. which table/section a
    # row came from) — source_document+source_page already narrow it to a
    # page, this narrows it to the exact list a resident could go look up
    # themselves. Nullable/defaulted so existing rows and the test fixtures
    # that predate this field still load fine; populated by pdf_ingest.py.
    source_reference = db.Column(db.String(255), nullable=False, default="")

    # Citizen-facing aggregate status: reported | confirmed | partially_delivered
    # | not_delivered | disputed. Starts at "reported" (Section 5) and is
    # recomputed by services.aggregation whenever a report is submitted.
    verification_status = db.Column(db.String(20), nullable=False, default="reported")

    created_at = db.Column(db.DateTime, default=_now)

    reports = db.relationship("Report", backref="project", lazy="dynamic")
    events = db.relationship("StatusEvent", backref="project", lazy="dynamic")

    def display_name(self, lang: str) -> str:
        """The project name in `lang`, falling back to the English source
        text when no translation exists for it (e.g. a gap in Kikamba's
        best-effort coverage) — used everywhere a project name is shown to
        a resident, across every channel (REST API, WhatsApp, SMS)."""
        if lang == "sw" and self.project_name_sw:
            return self.project_name_sw
        if lang == "kam" and self.project_name_kam:
            return self.project_name_kam
        return self.project_name

    def last_updated_at(self):
        """Timestamp of the most recent audit-trail event for this project
        (a new report counts as an update even if it didn't flip the status —
        a resident asking "when was this last touched?" means either), falling
        back to when the record was first ingested if it has no events yet.
        A transient/detached instance (not yet added to a session, or built
        directly like Project(...) in tests) has no queryable `events`
        relationship — fall back the same way rather than erroring, since
        to_dict() is expected to work on those too."""
        if object_session(self) is None:
            return self.created_at
        latest = self.events.order_by(StatusEvent.created_at.desc()).first()
        return latest.created_at if latest is not None else self.created_at

    def to_dict(self) -> dict:
        last_updated = self.last_updated_at()
        return {
            "id": self.id,
            "ward": self.ward,
            "county": self.county,
            "subward": self.subward,
            "sector": self.sector,
            "project_name": self.project_name,
            "project_name_sw": self.project_name_sw,
            "project_name_kam": self.project_name_kam,
            "description": self.description,
            "financial_year": self.financial_year,
            "allocated_amount_ksh": self.allocated_amount_ksh,
            "county_claimed_status": self.county_claimed_status,
            "county_remarks": self.county_remarks,
            "source_document": self.source_document,
            "source_page": self.source_page,
            "source_reference": self.source_reference,
            "verification_status": self.verification_status,
            "last_updated_at": last_updated.isoformat() if last_updated else None,
        }


class Reporter(db.Model):
    __tablename__ = "reporters"

    id = db.Column(db.String(32), primary_key=True, default=_uuid)  # anonymized public id
    phone_hash = db.Column(db.String(64), unique=True, nullable=False, index=True)
    # Internal-only weighting signal from past corroborated reports. Never
    # serialized to any public-facing API response.
    reputation_score = db.Column(db.Float, nullable=False, default=1.0)
    phone_verified = db.Column(db.Boolean, nullable=False, default=False)
    flagged_for_review = db.Column(db.Boolean, nullable=False, default=False)
    preferred_language = db.Column(db.String(8), nullable=True)
    first_seen_at = db.Column(db.DateTime, default=_now)

    reports = db.relationship("Report", backref="reporter", lazy="dynamic")

    def to_public_dict(self) -> dict:
        """Never includes phone_hash or reputation_score — those are internal only."""
        return {"id": self.id}


class Report(db.Model):
    __tablename__ = "reports"

    id = db.Column(db.String(32), primary_key=True, default=_uuid)
    project_id = db.Column(db.String(40), db.ForeignKey("projects.id"), nullable=False, index=True)
    reporter_id = db.Column(db.String(32), db.ForeignKey("reporters.id"), nullable=False, index=True)

    channel = db.Column(db.String(20), nullable=False)  # app | whatsapp | sms | bluetooth
    claim = db.Column(db.String(20), nullable=False)  # confirmed_delivered | not_delivered | partially_delivered
    photo_path = db.Column(db.String(255), nullable=True)
    gps_lat = db.Column(db.Float, nullable=True)
    gps_lon = db.Column(db.Float, nullable=True)
    # Free-text context a resident typed or dictated (see services/stt.py for
    # the voice-to-text path). Optional — the claim buttons alone are enough
    # to submit a report; this is extra color, not required structured data.
    remarks = db.Column(db.Text, nullable=True)

    submitted_at = db.Column(db.DateTime, default=_now)
    edited_at = db.Column(db.DateTime, nullable=True)

    # Never deleted. `active=False` means superseded by a later edit from the
    # same reporter; `excluded_from_aggregation=True` means it was caught by
    # burst/anomaly detection and is held out of the aggregate count pending
    # review, but stays visible in the audit trail either way.
    active = db.Column(db.Boolean, nullable=False, default=True)
    excluded_from_aggregation = db.Column(db.Boolean, nullable=False, default=False)
    exclusion_reason = db.Column(db.String(255), nullable=True)

    ledger_ref = db.Column(db.String(120), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "reporter_id": self.reporter_id,  # anonymized id only
            "channel": self.channel,
            "claim": self.claim,
            "remarks": self.remarks,
            "has_photo": bool(self.photo_path),
            "gps_lat": self.gps_lat,
            "gps_lon": self.gps_lon,
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
            "edited_at": self.edited_at.isoformat() if self.edited_at else None,
            "active": self.active,
            "excluded_from_aggregation": self.excluded_from_aggregation,
            "ledger_ref": self.ledger_ref,
        }


class StatusEvent(db.Model):
    """Append-only audit trail. One row per submission / status change /
    dispute resolution. Anchored to the ledger via ledger_ref."""

    __tablename__ = "status_events"

    id = db.Column(db.String(32), primary_key=True, default=_uuid)
    project_id = db.Column(db.String(40), db.ForeignKey("projects.id"), nullable=False, index=True)
    related_report_id = db.Column(db.String(32), db.ForeignKey("reports.id"), nullable=True)
    actor_reporter_id = db.Column(db.String(32), nullable=True)  # anonymized id, may be null for system events

    event_type = db.Column(db.String(30), nullable=False)  # submission | status_change | dispute_resolution
    description = db.Column(db.Text, nullable=False)
    # The exact payload that was hashed and anchored to the ledger, kept here
    # in full (per Section 5: Flask keeps the real data, the ledger only
    # gets a hash/reference) so anyone can independently recompute the hash
    # and confirm it matches what's on-chain — see GET /projects/<id>/audit-trail.
    payload_json = db.Column(db.Text, nullable=False)
    payload_hash = db.Column(db.String(64), nullable=False)
    ledger_ref = db.Column(db.String(120), nullable=True)

    created_at = db.Column(db.DateTime, default=_now)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "related_report_id": self.related_report_id,
            "actor_reporter_id": self.actor_reporter_id,
            "event_type": self.event_type,
            "description": self.description,
            "payload_hash": self.payload_hash,
            "ledger_ref": self.ledger_ref,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


ISSUE_CATEGORIES = ["roads", "water", "health", "education", "electricity", "security", "sanitation", "other"]
ISSUE_STATUSES = ["open", "acknowledged", "resolved"]


class IssueReport(db.Model):
    """A citizen-initiated report of something needing attention that ISN'T
    tied to an existing budgeted project — a pothole, a broken borehole, an
    unsafe stretch of road — the "areas needing improvement or critical
    infrastructure" feature. Deliberately a separate table from Report:
    Report always verifies/disputes an existing Project's official claim,
    whereas an IssueReport has no official county claim to compare against
    — it's residents surfacing something new, not confirming something
    published. Anchored to the same ledger for the same tamper-evident
    trail, but doesn't feed the Project dispute-aggregation logic."""

    __tablename__ = "issue_reports"

    id = db.Column(db.String(32), primary_key=True, default=_uuid)
    reporter_id = db.Column(db.String(32), db.ForeignKey("reporters.id"), nullable=False, index=True)

    county = db.Column(db.String(80), nullable=False, index=True)
    ward = db.Column(db.String(80), nullable=False, index=True)
    category = db.Column(db.String(20), nullable=False)  # one of ISSUE_CATEGORIES
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)

    channel = db.Column(db.String(20), nullable=False, default="app")
    photo_path = db.Column(db.String(255), nullable=True)
    gps_lat = db.Column(db.Float, nullable=True)
    gps_lon = db.Column(db.Float, nullable=True)

    status = db.Column(db.String(20), nullable=False, default="open")  # one of ISSUE_STATUSES
    active = db.Column(db.Boolean, nullable=False, default=True)  # never deleted, same convention as Report

    ledger_ref = db.Column(db.String(120), nullable=True)
    submitted_at = db.Column(db.DateTime, default=_now)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "reporter_id": self.reporter_id,
            "county": self.county,
            "ward": self.ward,
            "category": self.category,
            "title": self.title,
            "description": self.description,
            "channel": self.channel,
            "has_photo": bool(self.photo_path),
            "gps_lat": self.gps_lat,
            "gps_lon": self.gps_lon,
            "status": self.status,
            "ledger_ref": self.ledger_ref,
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
        }
