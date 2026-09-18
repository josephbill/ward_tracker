from app.services.email_client import DummyEmailClient, get_email_client


def test_dummy_email_client_never_raises_and_records_sends():
    dummy = DummyEmailClient()
    dummy.send(to="josephbill00@gmail.com", subject="Test", html="<p>hi</p>")
    assert dummy.sent == [("josephbill00@gmail.com", "Test", "<p>hi</p>")]


def test_submitting_a_report_sends_a_county_notification_email(client, seeded_projects, app, verify_phone):
    # Must fetch the client via the app's OWN configured class (TestConfig),
    # not the plain Config import — get_email_client() caches a single
    # module-level client, so grabbing it via the wrong config class here
    # would prime that cache with whatever backend Config.EMAIL_BACKEND
    # happens to resolve to (e.g. a real SendByteEmailClient, if a real
    # backend/.env is present) instead of the dummy TestConfig expects.
    dummy = get_email_client(app.config_class)
    verify_phone("+254700555999")

    resp = client.post("/api/reports", json={
        "project_id": "KASIKEU-2022-23-001", "phone": "+254700555999",
        "claim": "not_delivered", "channel": "app", "remarks": "Nothing built here yet.",
    })
    assert resp.status_code == 201

    assert len(dummy.sent) == 1
    to, subject, html = dummy.sent[0]
    assert to == "josephbill00@gmail.com"
    assert "KASIKEU-2022-23-001" in subject
    assert "Nothing built here yet." in html


def test_email_failure_never_breaks_report_submission(client, seeded_projects, app, monkeypatch, verify_phone):
    """The core guarantee: a broken email integration must never roll back
    or fail a report submission that has already succeeded."""
    import app.services.notifications as notifications_module

    def boom(*args, **kwargs):
        raise RuntimeError("SendByte is down")

    monkeypatch.setattr(notifications_module, "get_email_client", boom)
    verify_phone("+254700556000")

    resp = client.post("/api/reports", json={
        "project_id": "KASIKEU-2022-23-001", "phone": "+254700556000",
        "claim": "not_delivered", "channel": "app",
    })
    assert resp.status_code == 201
    assert resp.get_json()["report"]["claim"] == "not_delivered"


def test_submitting_an_issue_sends_a_county_notification_email(client, app):
    dummy = get_email_client(app.config_class)

    phone = "+254700556001"
    client.post("/api/auth/request-otp", json={"phone": phone})
    client.post("/api/auth/verify-otp", json={"phone": phone, "code": phone[-6:]})

    resp = client.post("/api/issues", json={
        "phone": phone, "county": "Makueni", "ward": "Kasikeu",
        "category": "roads", "title": "Pothole near the market",
    })
    assert resp.status_code == 201

    assert len(dummy.sent) == 1
    to, subject, html = dummy.sent[0]
    assert to == "josephbill00@gmail.com"
    assert "Pothole near the market" in subject
