from app.db import db
from app.models import Project, StatusEvent


def test_display_name_uses_translation_when_present(app):
    project = Project(
        id="TEST-001", ward="Kasikeu", county="Makueni", subward="Kasikeu", sector="Water",
        project_name="Test Project", project_name_sw="Mradi wa Majaribio", project_name_kam=None,
        description="", financial_year="2024/25", allocated_amount_ksh=1000,
        county_claimed_status="delivered", county_remarks="", source_document="test", source_page=1,
    )
    assert project.display_name("en") == "Test Project"
    assert project.display_name("sw") == "Mradi wa Majaribio"
    # No Kikamba translation set for this project -> falls back to English,
    # never raises and never shows a blank title.
    assert project.display_name("kam") == "Test Project"


def test_to_dict_includes_raw_translation_columns(app):
    project = Project(
        id="TEST-002", ward="Kasikeu", county="Makueni", subward="Kasikeu", sector="Water",
        project_name="Another Project", project_name_sw="Mradi Mwingine",
        description="", financial_year="2024/25", allocated_amount_ksh=1000,
        county_claimed_status="delivered", county_remarks="", source_document="test", source_page=1,
    )
    d = project.to_dict()
    assert d["project_name_sw"] == "Mradi Mwingine"
    assert d["project_name_kam"] is None


def _make_project(app, **overrides):
    defaults = dict(
        id="TEST-003", ward="Kasikeu", county="Makueni", subward="Kasikeu", sector="Water",
        project_name="Traceability Project", description="", financial_year="2024/25",
        allocated_amount_ksh=1000, county_claimed_status="delivered", county_remarks="",
        source_document="Kasikeu Ward Development Profile, 2025", source_page=11,
    )
    defaults.update(overrides)
    project = Project(**defaults)
    db.session.add(project)
    db.session.commit()
    return project


def test_to_dict_includes_source_reference(app):
    project = _make_project(
        app, id="TEST-004",
        source_reference="Kasikeu Ward Development Profile, 2025, Section 3, Kasikeu Ward, p.11",
    )
    assert project.to_dict()["source_reference"] == (
        "Kasikeu Ward Development Profile, 2025, Section 3, Kasikeu Ward, p.11"
    )


def test_last_updated_at_falls_back_to_created_at_with_no_events(app):
    project = _make_project(app, id="TEST-005")
    assert project.last_updated_at() == project.created_at
    assert project.to_dict()["last_updated_at"] is not None


def test_last_updated_at_reflects_most_recent_event(app):
    project = _make_project(app, id="TEST-006")
    older = StatusEvent(
        project_id=project.id, event_type="submission", description="first report",
        payload_json="{}", payload_hash="a" * 64,
    )
    db.session.add(older)
    db.session.commit()

    newer = StatusEvent(
        project_id=project.id, event_type="status_change", description="status changed",
        payload_json="{}", payload_hash="b" * 64,
    )
    db.session.add(newer)
    db.session.commit()

    assert project.last_updated_at() == newer.created_at
    assert project.last_updated_at() != older.created_at
