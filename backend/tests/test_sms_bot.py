from app.services.sms_bot import handle_sms


def test_help_keyword(app, seeded_projects):
    reply = handle_sms("+254788000001", "HELP")
    assert "MAKUENI" in reply.upper() or "reply" in reply.lower()


def test_valid_project_code_and_choice_submits_report(app, seeded_projects):
    reply = handle_sms("+254788000002", "KASIKEU-2022-23-001 2")
    assert "Ref" in reply or "recorded" in reply.lower()

    from app.models import Report

    reports = Report.query.filter_by(project_id="KASIKEU-2022-23-001").all()
    assert len(reports) == 1
    assert reports[0].claim == "not_delivered"
    assert reports[0].channel == "sms"


def test_unknown_project_code(app, seeded_projects):
    reply = handle_sms("+254788000003", "NOT-A-PROJECT 1")
    assert "don't recognise" in reply.lower() or "recognise" in reply.lower()


def test_malformed_message_returns_help(app, seeded_projects):
    reply = handle_sms("+254788000004", "gibberish")
    assert "reply" in reply.lower() or "MAKUENI" in reply.upper()


def test_case_insensitive_project_code(app, seeded_projects):
    reply = handle_sms("+254788000005", "kasikeu-2022-23-001 1")
    assert "Ref" in reply or "recorded" in reply.lower()
