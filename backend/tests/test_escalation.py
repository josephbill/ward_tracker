import pytest

from app.services.escalation import (
    ESCALATION_SITUATIONS,
    UnknownSituationError,
    escalation_contact,
    render_escalation_menu,
    render_escalation_response,
    situation_from_choice,
)


def test_situation_from_choice_maps_1_based_menu_replies():
    assert situation_from_choice("1") == "no_response"
    assert situation_from_choice("3") == "corruption"


def test_situation_from_choice_rejects_out_of_range_and_non_numeric():
    assert situation_from_choice("0") is None
    assert situation_from_choice("99") is None
    assert situation_from_choice("abc") is None


def test_every_situation_has_a_contact():
    for situation in ESCALATION_SITUATIONS:
        contact = escalation_contact(situation)
        assert contact["institution"]
        assert contact["detail"]


def test_unknown_situation_raises():
    with pytest.raises(UnknownSituationError):
        escalation_contact("not_a_real_situation")


def test_render_escalation_menu_lists_all_four_situations_in_order(app):
    menu = render_escalation_menu("en")
    assert "1." in menu and "2." in menu and "3." in menu and "4." in menu
    assert menu.index("1.") < menu.index("2.") < menu.index("3.") < menu.index("4.")


def test_render_escalation_response_prefills_project_and_report_ref(app):
    text = render_escalation_response(
        "en", "corruption", project_name="Manual opening and grading",
        ward="Kasikeu", project_id="KASIKEU-2022-23-001", report_id="abc123",
    )
    assert "EACC" in text
    assert "Manual opening and grading" in text
    assert "KASIKEU-2022-23-001" in text
    assert "abc123" in text


def test_render_escalation_response_handles_no_existing_report(app):
    text = render_escalation_response(
        "en", "no_response", project_name="Some Project",
        ward="Kasikeu", project_id="KASIKEU-2022-23-001", report_id=None,
    )
    # Doesn't crash, and doesn't claim a report reference that doesn't exist.
    assert "None" not in text


def test_render_escalation_response_is_translated_per_language(app):
    en = render_escalation_response(
        "en", "financial_accountability", project_name="P", ward="Kasikeu",
        project_id="X-1", report_id=None,
    )
    sw = render_escalation_response(
        "sw", "financial_accountability", project_name="P", ward="Kasikeu",
        project_id="X-1", report_id=None,
    )
    assert en != sw
    assert "Auditor-General" in en and "Auditor-General" in sw  # institution name unchanged across languages
