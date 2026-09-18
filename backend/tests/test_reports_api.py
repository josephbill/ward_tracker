from app.config import Config


def test_cors_enabled_for_cross_origin_web_clients(client, seeded_projects):
    """The Expo web preview runs on its own dev-server origin and calls this
    API cross-origin — without CORS enabled every fetch() silently fails and
    the app looks permanently offline (a real bug caught while smoke-testing
    the web build)."""
    resp = client.get("/api/projects", headers={"Origin": "http://localhost:19100"})
    assert resp.headers.get("Access-Control-Allow-Origin") == "http://localhost:19100"


def test_list_projects_returns_translated_statements(client, seeded_projects):
    resp = client.get("/api/projects?ward=Kasikeu&lang=en")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["count"] == 2
    assert all("statement" in p for p in data["projects"])
    assert any("Ksh 1,000,000" in p["statement"] for p in data["projects"])


def test_list_projects_includes_purported_completion_rate(client, seeded_projects):
    # seeded_projects: 1 "delivered" + 1 "not_started" out of 2 total
    resp = client.get("/api/projects?ward=Kasikeu&lang=en")
    data = resp.get_json()
    assert data["delivered_count"] == 1
    assert data["purported_completion_rate"] == 0.5


def test_verification_info_exposes_thresholds(client, seeded_projects):
    """The Help screen (gap-fill Section 3) reads these rather than
    hardcoding the numbers, so it stays correct if a deployment tunes them
    via env vars."""
    resp = client.get("/api/verification-info")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["confirmation_threshold"] == 2
    assert body["dispute_threshold"] == 3
    assert body["independence_radius_m"] == 500


def test_project_responses_include_verification_counts(client, seeded_projects):
    resp = client.get("/api/projects/KASIKEU-2022-23-001")
    body = resp.get_json()
    assert body["verification_counts"] == {
        "agree_count": 0, "agree_needed": 2,
        "disagree_count": 0, "disagree_needed": 3,
        "total_active_reports": 0,
    }

    list_resp = client.get("/api/projects?ward=Kasikeu")
    assert all("verification_counts" in p for p in list_resp.get_json()["projects"])


def test_verification_counts_reflect_submitted_reports(client, seeded_projects, verify_phone):
    project_id = "KASIKEU-2022-23-001"
    verify_phone("+254700300001")
    client.post("/api/reports", json={
        "project_id": project_id, "phone": "+254700300001", "claim": "not_delivered",
        "channel": "app", "gps_lat": -1.0, "gps_lon": 37.0,
    })
    body = client.get(f"/api/projects/{project_id}").get_json()
    assert body["verification_counts"]["disagree_count"] == 1
    assert body["verification_counts"]["total_active_reports"] == 1


def test_list_counties_and_wards(client, seeded_projects):
    counties = client.get("/api/counties").get_json()
    assert counties["counties"] == ["Makueni"]

    wards = client.get("/api/wards?county=Makueni").get_json()
    assert wards["wards"] == ["Kasikeu"]


def test_get_single_project_in_kikamba(client, seeded_projects):
    resp = client.get("/api/projects/KASIKEU-2022-23-001?lang=kam")
    assert resp.status_code == 200
    assert resp.get_json()["statement"] != ""


def test_unknown_project_404s(client, seeded_projects):
    resp = client.get("/api/projects/DOES-NOT-EXIST")
    assert resp.status_code == 404


def test_submit_report_rejects_invalid_claim(client, seeded_projects):
    resp = client.post("/api/reports", json={
        "project_id": "KASIKEU-2022-23-001", "phone": "+254700000010", "claim": "bogus", "channel": "app",
    })
    assert resp.status_code == 400


def test_submit_report_stores_optional_remarks(client, seeded_projects, verify_phone):
    """Remarks (typed or voice-transcribed — Section 9 item 1) are optional
    free text stored alongside the structured claim, never required."""
    verify_phone("+254700000011")
    resp = client.post("/api/reports", json={
        "project_id": "KASIKEU-2022-23-001", "phone": "+254700000011", "claim": "not_delivered",
        "channel": "app", "remarks": "The borehole here has been dry since March.",
    })
    assert resp.status_code == 201
    assert resp.get_json()["report"]["remarks"] == "The borehole here has been dry since March."

    # Omitting remarks entirely must still work.
    resp2 = client.post("/api/reports", json={
        "project_id": "KASIKEU-2024-25-041", "phone": "+254700000011", "claim": "not_delivered", "channel": "app",
    })
    assert resp2.status_code == 201
    assert resp2.get_json()["report"]["remarks"] is None


def test_full_dispute_flow_end_to_end(client, seeded_projects, verify_phone):
    """The Section 10 'done' demo moment: 3 independent conflicting reports
    push a project into Disputed status, visible in the audit trail."""
    project_id = "KASIKEU-2022-23-001"  # county says "delivered"
    phones_and_coords = [
        ("+254700100001", -1.00, 37.00),
        ("+254700100002", -1.50, 37.50),
        ("+254700100003", -1.90, 37.90),
    ]

    last_resp = None
    for phone, lat, lon in phones_and_coords:
        verify_phone(phone)
        last_resp = client.post("/api/reports", json={
            "project_id": project_id, "phone": phone, "claim": "not_delivered",
            "channel": "app", "gps_lat": lat, "gps_lon": lon,
        })
        assert last_resp.status_code == 201

    body = last_resp.get_json()
    assert body["status_changed"] is True
    assert body["new_status"] == "disputed"
    assert body["report"]["ledger_ref"] is not None

    trail_resp = client.get(f"/api/projects/{project_id}/audit-trail")
    trail = trail_resp.get_json()
    assert trail["verification_status"] == "disputed"
    event_types = [e["event_type"] for e in trail["events"]]
    assert event_types.count("submission") == 3
    assert "status_change" in event_types
    assert all(e["ledger_verified"] for e in trail["events"])


def test_audit_trail_descriptions_are_translated(client, seeded_projects, verify_phone):
    """Audit trail event descriptions must go through translation like every
    other resident-facing string — previously they were hardcoded English
    regardless of `lang` (a real bug caught while auditing the app for
    incomplete translation coverage)."""
    project_id = "KASIKEU-2022-23-001"
    verify_phone("+254700100050")
    client.post("/api/reports", json={"project_id": project_id, "phone": "+254700100050",
                                       "claim": "not_delivered", "channel": "app"})

    en = client.get(f"/api/projects/{project_id}/audit-trail?lang=en").get_json()
    sw = client.get(f"/api/projects/{project_id}/audit-trail?lang=sw").get_json()

    assert "not delivered" in en["events"][0]["description"]
    assert "haijakamilika" in sw["events"][0]["description"]
    assert en["events"][0]["description"] != sw["events"][0]["description"]
    assert en["events"][0]["event_type_label"] == "Submission"
    assert sw["events"][0]["event_type_label"] == "Uwasilishaji"


def test_audit_trail_flags_superseded_submissions(client, seeded_projects, verify_phone):
    """The screenshot-driven bug report: a resident editing their report
    several times produces several "SUBMISSION" audit events that all LOOK
    identical/independent, which reads as "the same person reported
    multiple times and it all counts" even though only the last is active.
    report_active must distinguish them so the UI can show that."""
    project_id = "KASIKEU-2022-23-001"
    verify_phone("+254700100099")
    for claim in ["not_delivered", "confirmed_delivered", "partially_delivered"]:
        client.post("/api/reports", json={"project_id": project_id, "phone": "+254700100099",
                                           "claim": claim, "channel": "app"})

    trail = client.get(f"/api/projects/{project_id}/audit-trail").get_json()
    submissions = [e for e in trail["events"] if e["event_type"] == "submission"]
    assert len(submissions) == 3
    assert [s["report_active"] for s in submissions] == [False, False, True]

    # And the aggregate figure agrees: only 1 active report, not 3.
    detail = client.get(f"/api/projects/{project_id}").get_json()
    assert detail["verification_counts"]["total_active_reports"] == 1


def test_project_detail_shows_active_reports_only(client, seeded_projects, verify_phone):
    project_id = "KASIKEU-2022-23-001"
    verify_phone("+254700100010")
    client.post("/api/reports", json={"project_id": project_id, "phone": "+254700100010",
                                       "claim": "not_delivered", "channel": "app"})
    client.post("/api/reports", json={"project_id": project_id, "phone": "+254700100010",
                                       "claim": "confirmed_delivered", "channel": "app"})  # edits, supersedes

    detail = client.get(f"/api/projects/{project_id}").get_json()
    assert len(detail["reports"]) == 1
    assert detail["reports"][0]["claim"] == "confirmed_delivered"


def test_my_reports_requires_verified_phone(client, seeded_projects):
    resp = client.get("/api/reports/mine?phone=+254700555000")
    assert resp.status_code == 403


def test_my_reports_returns_own_history_only(client, seeded_projects):
    phone_a = "+254700555001"
    phone_b = "+254700555002"

    client.post("/api/auth/request-otp", json={"phone": phone_a})
    client.post("/api/auth/verify-otp", json={"phone": phone_a, "code": phone_a[-6:]})
    client.post("/api/auth/request-otp", json={"phone": phone_b})
    client.post("/api/auth/verify-otp", json={"phone": phone_b, "code": phone_b[-6:]})

    client.post("/api/reports", json={"project_id": "KASIKEU-2022-23-001", "phone": phone_a,
                                       "claim": "not_delivered", "channel": "app"})
    client.post("/api/reports", json={"project_id": "KASIKEU-2024-25-041", "phone": phone_b,
                                       "claim": "confirmed_delivered", "channel": "app"})

    # NOTE: phone numbers contain "+", which a naive f-string query URL would
    # send unencoded — and "+" in a query string decodes as a space, silently
    # corrupting the phone and breaking the hash lookup. Always pass through
    # a proper query-string encoder (query_string= here; encodeURIComponent
    # in the mobile client).
    resp = client.get("/api/reports/mine", query_string={"phone": phone_a})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["count"] == 1
    assert body["reports"][0]["project_name"] is not None
    assert body["reports"][0]["claim"] == "not_delivered"


def test_otp_accepts_last_six_digits_of_phone_as_demo_fallback(client, seeded_projects):
    """Demo convenience: verify_otp also accepts the phone's own last 6
    digits, so a live demo doesn't need to tail logs for the real code."""
    phone = "+254799887766"
    client.post("/api/auth/request-otp", json={"phone": phone})

    resp = client.post("/api/auth/verify-otp", json={"phone": phone, "code": "887766"})
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "verified"


def test_otp_flow_verifies_phone(client, seeded_projects):
    phone = "+254711222333"
    resp = client.post("/api/auth/request-otp", json={"phone": phone})
    assert resp.status_code == 200

    from app.services import otp
    from app.services.spam_defense import normalize_phone
    code = otp._store[normalize_phone(phone)][0]

    bad = client.post("/api/auth/verify-otp", json={"phone": phone, "code": "000000"})
    if code == "000000":
        pass  # astronomically unlikely, skip
    else:
        assert bad.status_code == 400

    good = client.post("/api/auth/verify-otp", json={"phone": phone, "code": code})
    assert good.status_code == 200
    assert good.get_json()["status"] == "verified"
