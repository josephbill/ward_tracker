from app.db import db
from app.models import Project, Report, Reporter
from app.services.aggregation import recompute_verification_status


def _add_reporter(i: int) -> Reporter:
    reporter = Reporter(phone_hash=f"hash-{i}")
    db.session.add(reporter)
    db.session.flush()
    return reporter


def _add_report(project_id, reporter, claim, lat=None, lon=None, excluded=False):
    report = Report(
        project_id=project_id, reporter_id=reporter.id, channel="app", claim=claim,
        gps_lat=lat, gps_lon=lon, excluded_from_aggregation=excluded,
    )
    db.session.add(report)
    db.session.flush()
    return report


def test_status_stays_reported_below_threshold(app, db, seeded_projects):
    project = Project.query.get("KASIKEU-2022-23-001")  # county says delivered
    for i in range(2):  # DISPUTE_THRESHOLD_COUNT default is 3
        r = _add_reporter(i)
        _add_report(project.id, r, "not_delivered", lat=-1.9 + i, lon=37.5 + i)
    db.session.commit()

    assert recompute_verification_status(project) == "reported"


def test_status_flips_to_disputed_at_threshold_with_independent_reporters(app, db, seeded_projects):
    project = Project.query.get("KASIKEU-2022-23-001")  # county says delivered
    for i in range(3):
        r = _add_reporter(i)
        _add_report(project.id, r, "not_delivered", lat=-1.0 + i * 5, lon=37.0 + i * 5)  # far apart
    db.session.commit()

    assert recompute_verification_status(project) == "disputed"


def test_reports_clustered_within_radius_do_not_count_as_independent(app, db, seeded_projects):
    project = Project.query.get("KASIKEU-2022-23-001")
    # 3 reports all within DISPUTE_INDEPENDENCE_RADIUS_M of each other (~10m apart)
    # should collapse into ONE independent cluster, not enough to dispute.
    base_lat, base_lon = -1.9000, 37.5000
    for i in range(3):
        r = _add_reporter(i)
        _add_report(project.id, r, "not_delivered", lat=base_lat + i * 0.00005, lon=base_lon)
    db.session.commit()

    assert recompute_verification_status(project) == "reported"


def test_reports_with_no_gps_are_always_treated_as_independent(app, db, seeded_projects):
    project = Project.query.get("KASIKEU-2022-23-001")
    for i in range(3):
        r = _add_reporter(i)
        _add_report(project.id, r, "not_delivered", lat=None, lon=None)
    db.session.commit()

    assert recompute_verification_status(project) == "disputed"


def test_agreeing_reports_confirm_the_county_status(app, db, seeded_projects):
    project = Project.query.get("KASIKEU-2022-23-001")  # county says delivered
    for i in range(2):  # CONFIRMATION_THRESHOLD_COUNT default is 2
        r = _add_reporter(i)
        _add_report(project.id, r, "confirmed_delivered", lat=-1.0 + i * 5, lon=37.0 + i * 5)
    db.session.commit()

    assert recompute_verification_status(project) == "confirmed"


def test_excluded_reports_do_not_count_toward_any_threshold(app, db, seeded_projects):
    project = Project.query.get("KASIKEU-2022-23-001")
    for i in range(3):
        r = _add_reporter(i)
        _add_report(project.id, r, "not_delivered", lat=-1.0 + i * 5, lon=37.0 + i * 5, excluded=True)
    db.session.commit()

    assert recompute_verification_status(project) == "reported"


def test_low_reputation_reporters_cannot_alone_trip_the_dispute_threshold(app, db, seeded_projects):
    """Section 6: reputation affects internal aggregation weighting. Three
    independent reports normally trip DISPUTE_THRESHOLD_COUNT (3), but if
    all three reporters have been down-weighted to 0.5 reputation, their
    combined weight (1.5) falls short and the project should NOT dispute."""
    project = Project.query.get("KASIKEU-2022-23-001")  # county says delivered
    for i in range(3):
        r = _add_reporter(i)
        r.reputation_score = 0.5
        _add_report(project.id, r, "not_delivered", lat=-1.0 + i * 5, lon=37.0 + i * 5)
    db.session.commit()

    assert recompute_verification_status(project) == "reported"


def test_not_started_project_agrees_with_not_delivered_claim(app, db, seeded_projects):
    project = Project.query.get("KASIKEU-2024-25-041")  # county says not_started
    for i in range(2):
        r = _add_reporter(i)
        _add_report(project.id, r, "not_delivered", lat=-1.0 + i * 5, lon=37.0 + i * 5)
    db.session.commit()

    assert recompute_verification_status(project) == "not_delivered"
