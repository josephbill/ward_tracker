from app.models import Project


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
