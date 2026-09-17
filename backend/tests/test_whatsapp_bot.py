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


def test_voice_note_media_is_transcribed_into_remarks_not_treated_as_photo(app, seeded_projects, monkeypatch):
    """Accessibility (gap-fill Section 2): a voice note is an alternative to
    typing/photo, not a new field — it becomes the same free-text remarks a
    typed message would, via the same STT client the app's voice button
    uses. DummySttClient returns "" (honest placeholder, no credentials), so
    patch it here to prove the transcript actually reaches the submitted
    report rather than asserting on empty-string plumbing alone."""
    from app.services import whatsapp_bot

    monkeypatch.setattr(
        whatsapp_bot, "get_stt_client",
        lambda config: type("FakeStt", (), {"transcribe": staticmethod(lambda path, lang: "Borehole is dry")})(),
    )

    phone = "+254799000010"
    _send(phone, "1")  # English
    _send(phone, "1")  # browse
    _send(phone, "Kasikeu")
    _send(phone, "1")  # pick first project
    _send(phone, "2")  # not delivered
    replies = _send(phone, "", media_path="https://example.com/voice.ogg", media_content_type="audio/ogg")
    assert "location" in replies[0].lower()

    _send(phone, "SKIP")  # skip location -> submits

    from app.models import Report, Reporter
    from app.services.spam_defense import hash_phone

    reporter = Reporter.query.filter_by(phone_hash=hash_phone(phone)).first()
    report = Report.query.filter_by(reporter_id=reporter.id).order_by(Report.submitted_at.desc()).first()
    assert report.remarks == "Borehole is dry"
    assert report.photo_path is None


def test_image_media_is_still_stored_as_photo(app, seeded_projects):
    phone = "+254799000011"
    _send(phone, "1")
    _send(phone, "1")
    _send(phone, "Kasikeu")
    _send(phone, "1")
    _send(phone, "2")
    replies = _send(phone, "", media_path="https://example.com/photo.jpg", media_content_type="image/jpeg")
    assert "location" in replies[0].lower()
    _send(phone, "SKIP")

    from app.models import Report, Reporter
    from app.services.spam_defense import hash_phone

    reporter = Reporter.query.filter_by(phone_hash=hash_phone(phone)).first()
    report = Report.query.filter_by(reporter_id=reporter.id).order_by(Report.submitted_at.desc()).first()
    assert report.photo_path == "https://example.com/photo.jpg"
    assert report.remarks is None


def test_escalation_menu_reachable_from_project_detail_and_prefills_report_ref(app, seeded_projects):
    phone = "+254799000012"
    _send(phone, "1")
    _send(phone, "1")
    _send(phone, "Kasikeu")
    _send(phone, "1")  # project detail

    replies = _send(phone, "E")
    assert "1." in replies[0] and "EACC" not in replies[0]  # menu, not yet a specific contact

    replies = _send(phone, "3")  # corruption
    assert "EACC" in replies[0]
    assert "none yet" in replies[0].lower()  # no prior report from this phone on this project


def test_disputed_status_change_offers_escalation_menu_immediately(app, seeded_projects):
    project_id = "KASIKEU-2022-23-001"
    coords = [(-1.0, 37.0), (-1.5, 37.5), (-1.9, 37.9)]

    last_replies = []
    for i, (lat, lon) in enumerate(coords):
        phone = f"+25479920000{i}"
        _send(phone, "1")
        _send(phone, "1")
        _send(phone, "Kasikeu")
        _send(phone, "2")  # KASIKEU-2022-23-001 ("delivered")
        _send(phone, "2")  # not delivered
        _send(phone, "SKIP")
        last_replies = _send(phone, "SKIP", latitude=lat, longitude=lon)

    assert any("disputed" in r.lower() for r in last_replies)
    assert any("1." in r and "4." in r for r in last_replies)  # escalation menu shown, not just main menu


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
