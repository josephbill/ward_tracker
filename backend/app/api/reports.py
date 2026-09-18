import json

from flask import Blueprint, current_app, jsonify, request

from ..models import Project, Report, Reporter, StatusEvent
from ..services.ledger import get_ledger_client
from ..services.report_service import PhoneNotVerifiedError, UnknownProjectError, submit_report
from ..services.spam_defense import hash_phone
from ..services.translation import render_project_statement, t
from ..services.uploads import save_photo

reports_bp = Blueprint("reports", __name__)

VALID_CLAIMS = {"confirmed_delivered", "not_delivered", "partially_delivered"}
VALID_CHANNELS = {"app", "whatsapp", "sms", "bluetooth"}


def _save_photo(file_storage) -> str | None:
    return save_photo(file_storage, current_app.config_class.PHOTO_UPLOAD_DIR)


@reports_bp.post("/reports")
def create_report():
    config = current_app.config_class
    if request.content_type and "multipart/form-data" in request.content_type:
        form = request.form
        project_id = form.get("project_id")
        raw_phone = form.get("phone")
        claim = form.get("claim")
        channel = form.get("channel", "app")
        gps_lat = form.get("gps_lat", type=float)
        gps_lon = form.get("gps_lon", type=float)
        lang = form.get("lang", config.DEFAULT_LANGUAGE)
        remarks = form.get("remarks") or None
        photo_path = _save_photo(request.files.get("photo"))
    else:
        data = request.get_json(force=True) or {}
        project_id = data.get("project_id")
        raw_phone = data.get("phone")
        claim = data.get("claim")
        channel = data.get("channel", "app")
        gps_lat = data.get("gps_lat")
        gps_lon = data.get("gps_lon")
        lang = data.get("lang", config.DEFAULT_LANGUAGE)
        remarks = data.get("remarks") or None
        photo_path = None  # JSON callers send photos separately via multipart

    if not project_id or not raw_phone or claim not in VALID_CLAIMS:
        return jsonify({"error": "project_id, phone and a valid claim are required",
                         "valid_claims": sorted(VALID_CLAIMS)}), 400
    if channel not in VALID_CHANNELS:
        channel = "app"
    if lang not in config.SUPPORTED_LANGUAGES:
        lang = config.DEFAULT_LANGUAGE

    try:
        result = submit_report(
            project_id=project_id,
            raw_phone=raw_phone,
            claim=claim,
            channel=channel,
            photo_path=photo_path,
            gps_lat=gps_lat,
            gps_lon=gps_lon,
            remarks=remarks,
        )
    except UnknownProjectError:
        return jsonify({"error": "unknown_project"}), 404
    except PhoneNotVerifiedError:
        return jsonify({"error": "phone_not_verified"}), 403

    message = t(
        lang,
        result.user_message_key,
        project_name=result.project.display_name(lang),
        ledger_ref=result.report.ledger_ref,
    )

    return jsonify(
        {
            "message": message,
            "report": result.report.to_dict(),
            "reporter_id": result.reporter.id,
            "status_changed": result.status_changed,
            "previous_status": result.previous_status,
            "new_status": result.new_status,
        }
    ), 201


@reports_bp.get("/reports/mine")
def my_reports():
    """A resident's own report history (Section 3 nav: "view one's
    reports"). Gated behind an OTP-verified phone — same trust bar as
    submitting a report — since a phone number resolves to a specific
    person's history. Never exposes other reporters' data: only this exact
    phone's hash is looked up."""
    config = current_app.config_class
    raw_phone = request.args.get("phone", "")
    lang = request.args.get("lang", config.DEFAULT_LANGUAGE)
    if lang not in config.SUPPORTED_LANGUAGES:
        lang = config.DEFAULT_LANGUAGE
    if not raw_phone:
        return jsonify({"error": "phone is required"}), 400

    reporter = Reporter.query.filter_by(phone_hash=hash_phone(raw_phone)).first()
    if reporter is None or not reporter.phone_verified:
        return jsonify({"error": "phone_not_verified", "reports": []}), 403

    reports = (
        Report.query.filter_by(reporter_id=reporter.id, active=True)
        .order_by(Report.submitted_at.desc())
        .all()
    )
    out = []
    for r in reports:
        project = Project.query.get(r.project_id)
        out.append(
            {
                **r.to_dict(),
                "project_name": project.display_name(lang) if project else r.project_id,
                "ward": project.ward if project else None,
                "verification_status": project.verification_status if project else None,
                "statement": render_project_statement(project.to_dict(), lang) if project else None,
            }
        )

    return jsonify({"reports": out, "count": len(out)})


def _render_event_description(event: StatusEvent, payload: dict, lang: str) -> str:
    """The description stored on StatusEvent is a neutral, English audit-log
    line (fine for an internal record) — but anything shown to a resident
    needs to go through translation like everything else, so this rebuilds
    a display string from the event's own payload_json at read time rather
    than storing a second, pre-translated copy."""
    if event.event_type == "submission":
        return t(
            lang, "audit_submission_description",
            channel=t(lang, f"channel_label_{payload.get('channel')}"),
            claim=t(lang, f"claim_label_{payload.get('claim')}"),
        )
    if event.event_type == "status_change":
        return t(
            lang, "audit_status_change_description",
            previous_status=t(lang, f"verification_status_{payload.get('previous_status')}"),
            new_status=t(lang, f"verification_status_{payload.get('new_status')}"),
        )
    return event.description


@reports_bp.get("/projects/<project_id>/audit-trail")
def audit_trail(project_id: str):
    config = current_app.config_class
    lang = request.args.get("lang", config.DEFAULT_LANGUAGE)
    if lang not in config.SUPPORTED_LANGUAGES:
        lang = config.DEFAULT_LANGUAGE

    project = Project.query.get(project_id)
    if project is None:
        return jsonify({"error": "not_found"}), 404

    events = StatusEvent.query.filter_by(project_id=project_id).order_by(StatusEvent.created_at).all()
    ledger = get_ledger_client(config)

    trail = []
    for e in events:
        # Recompute the hash from the payload Flask actually stored and
        # confirm it matches what was anchored to the ledger — this is what
        # lets a journalist/auditor/skeptical resident independently confirm
        # the record hasn't been altered, per Section 5.
        verified = False
        payload = {}
        if e.ledger_ref:
            payload = json.loads(e.payload_json)
            verified = ledger.verify(payload, e.ledger_ref)
        translated_description = _render_event_description(e, payload, lang)

        # A "submission" event is permanent audit history even after the
        # report it created is later superseded by the same reporter's next
        # submission (never deleted — see docs/SPAM_DEFENSE.md). Without
        # this flag, a citizen editing their report 3 times just LOOKS like
        # 4 separate people reported, when only the last is actually active
        # and counted toward verification_counts — surfaced here so the
        # audit trail UI can show that distinction instead of implying
        # (incorrectly) that every submission independently counts.
        report_active = None
        if e.event_type == "submission" and e.related_report_id:
            related = Report.query.get(e.related_report_id)
            report_active = related.active if related is not None else None

        trail.append(
            {
                **e.to_dict(),
                "description": translated_description,
                "event_type_label": t(lang, f"event_type_{e.event_type}"),
                "ledger_verified": verified,
                "report_active": report_active,
            }
        )

    return jsonify({
        "project_id": project_id,
        "verification_status": project.verification_status,
        "verification_status_label": t(lang, f"verification_status_{project.verification_status}"),
        "events": trail,
    })
