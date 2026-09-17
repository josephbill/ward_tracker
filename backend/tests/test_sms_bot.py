from app.services.sms_bot import handle_sms


def test_help_keyword(app, seeded_projects):
    """No phone history yet -> falls back to Config.DEFAULT_LANGUAGE, which
    is Kiswahili by default (see config.py) — this reply is expected in
    Kiswahili, not English."""
    reply = handle_sms("+254788000001", "HELP")
    assert "MFUATILIAJI" in reply.upper() or "jibu" in reply.lower()


def test_valid_project_code_and_choice_submits_report(app, seeded_projects):
    reply = handle_sms("+254788000002", "KASIKEU-2022-23-001 2")
    assert "Rejea" in reply or "imesajiliwa" in reply.lower()

    from app.models import Report

    reports = Report.query.filter_by(project_id="KASIKEU-2022-23-001").all()
    assert len(reports) == 1
    assert reports[0].claim == "not_delivered"
    assert reports[0].channel == "sms"


def test_unknown_project_code(app, seeded_projects):
    reply = handle_sms("+254788000003", "NOT-A-PROJECT 1")
    assert "hatutambui" in reply.lower()


def test_malformed_message_returns_help(app, seeded_projects):
    reply = handle_sms("+254788000004", "gibberish")
    assert "jibu" in reply.lower() or "MFUATILIAJI" in reply.upper()


def test_case_insensitive_project_code(app, seeded_projects):
    reply = handle_sms("+254788000005", "kasikeu-2022-23-001 1")
    assert "Rejea" in reply or "imesajiliwa" in reply.lower()


def test_default_language_is_kiswahili_for_a_number_with_no_history(app, seeded_projects):
    """The gap-fill request: Kiswahili is the primary default language,
    English remains a fully supported translation. A phone with no prior
    WhatsApp-set preference gets Kiswahili, not English, on first contact."""
    reply = handle_sms("+254788000099", "HELP")
    assert reply == handle_sms("+254788000098", "HELP")  # deterministic, not random
    assert "Reply" not in reply  # not the English copy


def test_next_command_returns_escalation_contact(app, seeded_projects):
    reply = handle_sms("+254788000006", "NEXT KASIKEU-2022-23-001 3")
    assert "EACC" in reply
    assert "KASIKEU-2022-23-001" in reply


def test_next_command_case_insensitive_keyword(app, seeded_projects):
    reply = handle_sms("+254788000007", "next KASIKEU-2022-23-001 1")
    assert "MCA" in reply or "Ward Administrator" in reply


def test_next_command_unknown_project(app, seeded_projects):
    reply = handle_sms("+254788000008", "NEXT NOT-A-PROJECT 1")
    assert "hatutambui" in reply.lower()


def test_next_command_prefills_existing_report_reference(app, seeded_projects):
    phone = "+254788000009"
    handle_sms(phone, "KASIKEU-2022-23-001 2")  # submit a report first
    reply = handle_sms(phone, "NEXT KASIKEU-2022-23-001 2")
    assert "none yet" not in reply.lower()  # a report ref should now be pre-filled
