def _verify_phone(client, phone):
    client.post("/api/auth/request-otp", json={"phone": phone})
    client.post("/api/auth/verify-otp", json={"phone": phone, "code": phone[-6:]})


def test_issue_submission_requires_verified_phone(client, app):
    resp = client.post("/api/issues", json={
        "phone": "+254700900001", "county": "Makueni", "ward": "Kasikeu",
        "category": "roads", "title": "Pothole on Kasikeu-Kwale road",
    })
    assert resp.status_code == 403


def test_issue_submission_rejects_invalid_category(client, app):
    phone = "+254700900002"
    _verify_phone(client, phone)
    resp = client.post("/api/issues", json={
        "phone": phone, "county": "Makueni", "ward": "Kasikeu",
        "category": "bogus", "title": "Something",
    })
    assert resp.status_code == 400
    assert "valid_categories" in resp.get_json()


def test_issue_submission_and_listing(client, app):
    phone = "+254700900003"
    _verify_phone(client, phone)
    resp = client.post("/api/issues", json={
        "phone": phone, "county": "Makueni", "ward": "Kasikeu", "category": "water",
        "title": "Broken borehole at Kwa Mbita", "description": "No water for two weeks.",
    })
    assert resp.status_code == 201
    body = resp.get_json()["issue"]
    assert body["status"] == "open"
    assert body["ledger_ref"] is not None
    assert body["category"] == "water"

    listing = client.get("/api/issues?ward=Kasikeu&county=Makueni").get_json()
    assert listing["count"] == 1
    assert listing["issues"][0]["title"] == "Broken borehole at Kwa Mbita"


def test_issue_submission_is_rate_limited(client, app):
    from app.config import Config

    phone = "+254700900004"
    _verify_phone(client, phone)
    for i in range(Config.BURST_MAX_REPORTS):
        resp = client.post("/api/issues", json={
            "phone": phone, "county": "Makueni", "ward": "Kasikeu",
            "category": "other", "title": f"Issue {i}",
        })
        assert resp.status_code == 201

    resp = client.post("/api/issues", json={
        "phone": phone, "county": "Makueni", "ward": "Kasikeu",
        "category": "other", "title": "One too many",
    })
    assert resp.status_code == 429


def test_list_categories(client, app):
    resp = client.get("/api/issues/categories")
    data = resp.get_json()
    assert "roads" in data["categories"]
    assert "water" in data["categories"]
