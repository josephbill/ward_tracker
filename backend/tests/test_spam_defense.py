from datetime import datetime, timedelta, timezone

from app.config import Config
from app.db import db
from app.models import Project, Report, Reporter
from app.services.report_service import submit_report


def test_hash_phone_is_deterministic_and_never_reversible_in_storage():
    from app.services.spam_defense import hash_phone

    h1 = hash_phone("+254700111111")
    h2 = hash_phone("+254700111111")
    assert h1 == h2
    assert "+254700111111" not in h1


def test_second_submission_from_same_phone_supersedes_not_duplicates(app, db, seeded_projects):
    project_id = "KASIKEU-2022-23-001"
    r1 = submit_report(project_id=project_id, raw_phone="+254700000001", claim="not_delivered", channel="app")
    r2 = submit_report(project_id=project_id, raw_phone="+254700000001", claim="confirmed_delivered", channel="app")

    assert r1.reporter.id == r2.reporter.id
    active_reports = Report.query.filter_by(project_id=project_id, active=True).all()
    assert len(active_reports) == 1
    assert active_reports[0].claim == "confirmed_delivered"

    superseded = Report.query.filter_by(project_id=project_id, active=False).all()
    assert len(superseded) == 1, "the original report must be marked superseded, never deleted"


def test_burst_of_reports_gets_excluded_from_aggregation_not_rejected(app, db, seeded_projects):
    reporter = Reporter(phone_hash="burst-hash")
    db.session.add(reporter)
    db.session.flush()

    # Create BURST_MAX_REPORTS reports across different projects (so none
    # supersede each other) to trip the burst window.
    for i in range(Config.BURST_MAX_REPORTS):
        project = Project(
            id=f"BURST-TEST-{i}", ward="Kasikeu", county="Makueni", subward="Kasikeu",
            sector="Test", project_name=f"Burst test project {i}", description="",
            financial_year="2024/25", allocated_amount_ksh=1000, county_claimed_status="delivered",
            county_remarks="", source_document="test", source_page=1,
        )
        db.session.add(project)
        db.session.add(Report(project_id=project.id, reporter_id=reporter.id, claim="not_delivered", channel="app"))
    db.session.commit()

    project = Project(
        id="BURST-TEST-LAST", ward="Kasikeu", county="Makueni", subward="Kasikeu",
        sector="Test", project_name="One more", description="", financial_year="2024/25",
        allocated_amount_ksh=1000, county_claimed_status="delivered", county_remarks="",
        source_document="test", source_page=1,
    )
    db.session.add(project)
    db.session.commit()

    from app.services.spam_defense import check_report_gate

    gate = check_report_gate(reporter, project.id)
    assert gate.exclude_from_aggregation is True
    assert "burst" in gate.exclusion_reason


def test_report_is_never_deleted_only_marked(app, db, seeded_projects):
    project_id = "KASIKEU-2022-23-001"
    submit_report(project_id=project_id, raw_phone="+254700000002", claim="not_delivered", channel="app")
    submit_report(project_id=project_id, raw_phone="+254700000002", claim="partially_delivered", channel="app")

    all_reports = Report.query.filter_by(project_id=project_id).all()
    assert len(all_reports) == 2
    assert sum(1 for r in all_reports if not r.active) == 1


def test_reporter_public_dict_never_exposes_phone_hash_or_reputation(app, db, seeded_projects):
    result = submit_report(project_id="KASIKEU-2022-23-001", raw_phone="+254700000003",
                            claim="not_delivered", channel="app")
    public = result.reporter.to_public_dict()
    assert public == {"id": result.reporter.id}
    assert "phone_hash" not in public
    assert "reputation_score" not in public
