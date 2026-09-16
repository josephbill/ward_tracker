"""
Central config. Every threshold the spam-defense and dispute-aggregation
logic relies on lives here as a named constant (never hardcoded inline) so
it can be tuned without touching logic code.
"""
import os
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent


class Config:
    BACKEND_ROOT = BACKEND_ROOT
    REPO_ROOT = REPO_ROOT

    # --- Storage ---
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{BACKEND_ROOT / 'instance' / 'app.db'}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SEED_DATA_PATH = REPO_ROOT / "data" / "ward_projects.json"
    PHOTO_UPLOAD_DIR = BACKEND_ROOT / "instance" / "uploads"

    # --- Languages ---
    SUPPORTED_LANGUAGES = ["en", "sw", "kam"]
    DEFAULT_LANGUAGE = "en"

    # --- Dispute aggregation (Section 5) ---
    # Status flips to "Disputed" once this many INDEPENDENT reports disagree
    # with the county-claimed status.
    DISPUTE_THRESHOLD_COUNT = int(os.environ.get("DISPUTE_THRESHOLD_COUNT", 3))
    # "Independent" = different reporters whose GPS points are further apart
    # than this radius. This is a documented proxy for "not the same
    # household" since we have no household-level data to check against.
    DISPUTE_INDEPENDENCE_RADIUS_M = float(os.environ.get("DISPUTE_INDEPENDENCE_RADIUS_M", 500))
    # Reports agreeing with the official status also need this many
    # independent corroborations before a project is marked "Confirmed".
    CONFIRMATION_THRESHOLD_COUNT = int(os.environ.get("CONFIRMATION_THRESHOLD_COUNT", 2))

    # --- Spam / abuse defense (Section 6) ---
    # One *active* report per (phone, project); an edit within this window
    # updates the existing report instead of creating spam.
    REPORT_EDIT_WINDOW_HOURS = int(os.environ.get("REPORT_EDIT_WINDOW_HOURS", 24))
    # Burst detection: more than this many reports from one phone within the
    # window below gets auto-flagged and excluded from aggregation pending review.
    BURST_MAX_REPORTS = int(os.environ.get("BURST_MAX_REPORTS", 5))
    BURST_WINDOW_MINUTES = int(os.environ.get("BURST_WINDOW_MINUTES", 10))
    # A brand-new number (no report history) reporting on more than this many
    # distinct wards gets flagged for review rather than auto-trusted.
    NEW_NUMBER_MULTI_WARD_THRESHOLD = int(os.environ.get("NEW_NUMBER_MULTI_WARD_THRESHOLD", 3))
    PHONE_HASH_SALT = os.environ.get("PHONE_HASH_SALT", "dev-only-salt-change-in-prod")

    # --- Ledger (Hedera) ---
    # "stub" (default, no network calls, deterministic local hash-anchoring)
    # or "hedera_sidecar" (calls the Node.js sidecar in ledger-sidecar/,
    # requires real testnet credentials there).
    LEDGER_BACKEND = os.environ.get("LEDGER_BACKEND", "stub")
    LEDGER_SIDECAR_URL = os.environ.get("LEDGER_SIDECAR_URL", "http://localhost:4001")

    # --- WhatsApp / SMS channel clients ---
    # "dummy" (default, logs instead of sending — fully testable with no
    # credentials) or "twilio" / "africas_talking" once real creds are set.
    WHATSAPP_BACKEND = os.environ.get("WHATSAPP_BACKEND", "dummy")
    SMS_BACKEND = os.environ.get("SMS_BACKEND", "dummy")
    TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "")
    TWILIO_WHATSAPP_FROM = os.environ.get("TWILIO_WHATSAPP_FROM", "")
    AFRICASTALKING_USERNAME = os.environ.get("AFRICASTALKING_USERNAME", "sandbox")
    AFRICASTALKING_API_KEY = os.environ.get("AFRICASTALKING_API_KEY", "")
    AFRICASTALKING_SHORTCODE = os.environ.get("AFRICASTALKING_SHORTCODE", "")

    # --- Speech-to-text (voice-to-text reporting) ---
    # "dummy" (default, returns an empty transcript — no credentials needed)
    # or "openai_whisper" once OPENAI_API_KEY is set. Only used for the
    # native audio-upload path; the web build transcribes client-side via
    # the browser's Web Speech API and never calls this.
    STT_BACKEND = os.environ.get("STT_BACKEND", "dummy")
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
    VOICE_UPLOAD_DIR = BACKEND_ROOT / "instance" / "voice_uploads"
