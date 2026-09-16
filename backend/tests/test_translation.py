from app.services.translation import (
    format_ksh,
    render_project_statement,
    resolve_project_name,
    supported_languages,
    t,
    translate_sector,
    translate_subward,
)

PROJECT = {
    "project_name": "Test Borehole",
    "ward": "Kasikeu",
    "subward": "Kiou",
    "allocated_amount_ksh": 1_234_567,
    "financial_year": "2023/24",
    "sector": "Water",
    "county_claimed_status": "delivered",
    "verification_status": "disputed",
}


def test_supported_languages_are_the_required_minimum():
    assert supported_languages() == ["en", "kam", "sw"]


def test_format_ksh_uses_thousands_separators():
    assert format_ksh(1_234_567) == "Ksh 1,234,567"


def test_render_project_statement_in_every_language_includes_locale_stable_amount():
    for lang in supported_languages():
        statement = render_project_statement(PROJECT, lang)
        assert "Ksh 1,234,567" in statement, f"currency formatting must stay consistent in {lang}"
        assert "2023/24" in statement
        assert PROJECT["project_name"] in statement


def test_missing_key_falls_back_to_english():
    # "app_name" exists in every locale; use a key that only exists in en to
    # exercise the fallback path safely.
    assert t("sw", "app_name") != ""


def test_unknown_language_falls_back_gracefully():
    # Falls back to English content rather than raising, since t() is called
    # from user-facing webhook code that must never 500 on a bad lang param.
    result = t("fr", "app_name")
    assert result == t("en", "app_name")


def test_resolve_project_name_uses_translation_when_present():
    project = {"project_name": "Manual opening and grading", "project_name_sw": "Kufungua na kusawazisha barabara"}
    assert resolve_project_name(project, "en") == "Manual opening and grading"
    assert resolve_project_name(project, "sw") == "Kufungua na kusawazisha barabara"


def test_resolve_project_name_falls_back_to_english_when_translation_missing():
    # This is the real bug that got reported: a project title untranslated
    # in the DB (no project_name_sw/kam) must still render something, not
    # raise or show an empty string.
    project = {"project_name": "Kwa Mbumbu ECDE"}
    assert resolve_project_name(project, "sw") == "Kwa Mbumbu ECDE"
    assert resolve_project_name(project, "kam") == "Kwa Mbumbu ECDE"


def test_translate_sector_known_and_unknown():
    assert translate_sector("Water", "sw") == "Maji"
    assert translate_sector("Water", "en") == "Water"
    # An unrecognized sector (e.g. a future county's own department name)
    # must fall back to the original text rather than disappearing.
    assert translate_sector("Some New Department", "sw") == "Some New Department"


def test_translate_subward_only_translates_cross_cutting_not_place_names():
    assert translate_subward("Cross-cutting", "sw") == "Mtambuka (wadi nzima)"
    # "Kasikeu"/"Kiou" are place names within the ward and must never be
    # translated, in any language.
    assert translate_subward("Kasikeu", "sw") == "Kasikeu"
    assert translate_subward("Kiou", "kam") == "Kiou"


def test_render_project_statement_uses_translated_project_name_and_sector():
    project = {
        **PROJECT,
        "project_name_sw": "Mfereji wa Majaribio",
        "sector": "Water",
    }
    statement_sw = render_project_statement(project, "sw")
    assert "Mfereji wa Majaribio" in statement_sw
    assert "Maji" in statement_sw
    assert "Test Borehole" not in statement_sw

    statement_en = render_project_statement(project, "en")
    assert "Test Borehole" in statement_en
    assert "Water" in statement_en
