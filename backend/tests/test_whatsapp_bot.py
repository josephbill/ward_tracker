from app.services.whatsapp_bot import IncomingMessage, handle_message


def _send(phone, text, **kwargs):
    return handle_message(IncomingMessage(from_phone=phone, text=text, **kwargs))


def test_full_conversation_browse_and_report(app, seeded_projects):
    phone = "+254799000001"

    replies = _send(phone, "1")  # select English
    assert "English" in replies[0]

    replies = _send(phone, "1")  # main menu -> browse
    assert "ward" in replies[0].lower()

    replies = _send(phone, "Kasikeu")
    assert "Kasikeu" in replies[0]
    assert "1." in replies[0]

    replies = _send(phone, "1")  # pick first project
    assert "Manual opening and grading" in replies[0] or "Rehabilitation" in replies[0]

    replies = _send(phone, "2")  # not delivered
    assert "photo" in replies[0].lower()

    replies = _send(phone, "SKIP")  # skip photo
    assert "location" in replies[0].lower()

    replies = _send(phone, "SKIP")  # skip location -> submits
    assert any("recorded" in r.lower() or "Ref" in r for r in replies)


def test_language_persists_across_messages(app, seeded_projects):
    phone = "+254799000002"
    _send(phone, "2")  # Kiswahili
    replies = _send(phone, "1")
    assert "kata" in replies[0].lower()


def test_invalid_menu_choice_reprompts(app, seeded_projects):
    phone = "+254799000003"
    _send(phone, "1")
    replies = _send(phone, "9")
    assert "didn't understand" in replies[0].lower() or "menu" in replies[0].lower()


def test_report_via_whatsapp_can_flip_project_to_disputed(app, seeded_projects):
    # Projects list in the ward-browse step is ordered by financial_year
    # desc, so KASIKEU-2024-25-041 (county: not_started) is choice "1" and
    # KASIKEU-2022-23-001 (county: delivered) is choice "2". A "not_delivered"
    # claim AGREES with not_started (see aggregation._AGREEMENT_MATRIX), so
    # to produce a genuine disagreement — and a Disputed outcome — reports
    # must target the "delivered" project, i.e. list choice "2".
    project_id = "KASIKEU-2022-23-001"
    coords = [(-1.0, 37.0), (-1.5, 37.5), (-1.9, 37.9)]

    from app.models import Project

    for i, (lat, lon) in enumerate(coords):
        phone = f"+25479910000{i}"
        _send(phone, "1")
        _send(phone, "2")
        _send(phone, "Kasikeu")
        _send(phone, "2")  # KASIKEU-2022-23-001 ("delivered")
        _send(phone, "2")  # not delivered
        _send(phone, "SKIP")
        _send(phone, "SKIP", latitude=lat, longitude=lon)

    project = Project.query.get(project_id)
    assert project.verification_status == "disputed"
