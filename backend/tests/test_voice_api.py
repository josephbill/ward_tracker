import io


def test_transcribe_requires_audio_file(client, app):
    resp = client.post("/api/voice/transcribe", data={"lang": "en"})
    assert resp.status_code == 400


def test_transcribe_with_dummy_backend_returns_empty_transcript_not_fabricated(client, app):
    """DummySttClient must never invent words — an empty transcript is
    honest; a fake one would be actively misleading in a citizen report."""
    data = {
        "audio": (io.BytesIO(b"fake-audio-bytes"), "clip.m4a"),
        "lang": "en",
    }
    resp = client.post("/api/voice/transcribe", data=data, content_type="multipart/form-data")
    assert resp.status_code == 200
    assert resp.get_json()["transcript"] == ""
