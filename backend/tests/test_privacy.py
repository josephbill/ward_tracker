import pytest

from app.services.privacy import GPS_PRECISION_DECIMALS, round_gps


def test_round_gps_caps_precision():
    lat, lon = round_gps(-1.234567891, 37.987654321)
    assert lat == round(-1.234567891, GPS_PRECISION_DECIMALS)
    assert lon == round(37.987654321, GPS_PRECISION_DECIMALS)
    # 3 decimal places ~111m — coarser than an exact GPS fix, but still well
    # inside the 500m dispute-independence radius so aggregation still works.
    assert len(str(lat).split(".")[-1]) <= GPS_PRECISION_DECIMALS


def test_round_gps_passes_through_none():
    assert round_gps(None, None) == (None, None)
    assert round_gps(-1.5, None) == (-1.5, None)


def test_submit_report_stores_rounded_gps(client, seeded_projects, verify_phone):
    verify_phone("+254700200001")
    resp = client.post("/api/reports", json={
        "project_id": "KASIKEU-2022-23-001", "phone": "+254700200001", "claim": "not_delivered",
        "channel": "app", "gps_lat": -1.234567891, "gps_lon": 37.987654321,
    })
    assert resp.status_code == 201
    report = resp.get_json()["report"]
    assert report["gps_lat"] == round(-1.234567891, GPS_PRECISION_DECIMALS)
    assert report["gps_lon"] == round(37.987654321, GPS_PRECISION_DECIMALS)


def test_submit_issue_stores_rounded_gps(client, seeded_projects):
    phone = "+254700200002"
    client.post("/api/auth/request-otp", json={"phone": phone})
    client.post("/api/auth/verify-otp", json={"phone": phone, "code": phone[-6:]})

    resp = client.post("/api/issues", json={
        "phone": phone, "county": "Makueni", "ward": "Kasikeu", "category": "roads",
        "title": "Pothole near market", "gps_lat": -1.234567891, "gps_lon": 37.987654321,
    })
    assert resp.status_code == 201
    issue = resp.get_json()["issue"]
    assert issue["gps_lat"] == round(-1.234567891, GPS_PRECISION_DECIMALS)
    assert issue["gps_lon"] == round(37.987654321, GPS_PRECISION_DECIMALS)


def test_save_photo_strips_exif_gps_data(app, tmp_path):
    pytest.importorskip("PIL")
    from io import BytesIO

    from PIL import Image
    from werkzeug.datastructures import FileStorage

    from app.services.uploads import save_photo

    # Build a tiny JPEG carrying an EXIF tag, the way a phone camera would
    # (tag 271 = "Make", a plain ASCII field — an actual GPS IFD pointer tag
    # trips an unrelated Pillow bug when synthesized outside a real photo,
    # so a simple string tag is enough to prove metadata survives save and
    # is then gone after save_photo() re-encodes the file).
    img = Image.new("RGB", (4, 4), color="red")
    exif = img.getexif()
    exif[271] = "TestPhoneCameraCo"
    buf = BytesIO()
    img.save(buf, format="JPEG", exif=exif)
    buf.seek(0)

    upload_dir = tmp_path / "uploads"
    file_storage = FileStorage(stream=buf, filename="photo.jpg", content_type="image/jpeg")
    saved_path = save_photo(file_storage, upload_dir)

    with Image.open(saved_path) as saved:
        assert len(saved.getexif()) == 0
