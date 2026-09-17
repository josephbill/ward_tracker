import uuid

from flask import Blueprint, current_app, jsonify, request
from werkzeug.utils import secure_filename

from ..services.stt import get_stt_client

voice_bp = Blueprint("voice", __name__)


@voice_bp.post("/voice/transcribe")
def transcribe():
    """Native voice-to-text path (Section 9, item 1): the app records a
    short audio clip locally and uploads it here for transcription. See
    services/stt.py — returns an empty transcript by default (no STT
    credentials configured), never a fabricated one."""
    config = current_app.config_class
    audio = request.files.get("audio")
    lang = request.form.get("lang", config.DEFAULT_LANGUAGE)
    if audio is None or audio.filename == "":
        return jsonify({"error": "audio file is required"}), 400

    config.VOICE_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    ext = audio.filename.rsplit(".", 1)[-1].lower() if "." in audio.filename else "m4a"
    dest = config.VOICE_UPLOAD_DIR / secure_filename(f"{uuid.uuid4().hex}.{ext}")
    audio.save(dest)

    client = get_stt_client(config)
    transcript = client.transcribe(str(dest), lang)

    return jsonify({"transcript": transcript})
