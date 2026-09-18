"""
Central config. Every threshold the spam-defense and dispute-aggregation
logic relies on lives here as a named constant (never hardcoded inline) so
it can be tuned without touching logic code.
"""
import logging
import os
import tempfile
from pathlib import Path

from dotenv import load_dotenv

logger = logging.getLogger("config")

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent

# Every backend/.env.example value is documented as "copy to .env and fill
# in what you have" — that only actually works if something loads the file.
# Real env vars (e.g. ones a PaaS like Pxxl sets directly) always win;
# load_dotenv() never overwrites a key that's already set.
load_dotenv(BACKEND_ROOT / ".env")


def _writable_instance_dir(preferred: Path) -> Path:
    """Prefer the repo-local `instance/` dir — matches every existing
    local-dev assumption (seed.py, .gitignore, every doc referencing
    `backend/instance/app.db`) — but fall back to a guaranteed-writable temp
    directory if the deployed filesystem won't allow creating it.

    `instance/` is gitignored, so on a fresh deploy it doesn't exist in the
    checked-out source and has to be created fresh on first boot. If the
    platform deploys the app code read-only (a real failure mode hit on a
    Pxxl deploy: the container's TCP port stayed open the whole time —
    gunicorn's arbiter binds the listen socket before forking workers — but
    no worker ever came up to answer a request, because this exact mkdir
    raised PermissionError on every worker's boot, so the platform's HTTP
    readiness check never succeeded and the deploy just timed out), fall
    back rather than crash-loop forever.
    """
    try:
        preferred.mkdir(parents=True, exist_ok=True)
        probe = preferred / ".write_test"
        probe.touch()
        probe.unlink()
        return preferred
    except OSError:
        fallback = Path(tempfile.gettempdir()) / "county-ward-tracker-instance"
        fallback.mkdir(parents=True, exist_ok=True)
        logger.warning(
            "%s is not writable (read-only deploy filesystem?) — falling back to %s. "
            "SQLite data and uploads here do NOT survive a restart/redeploy; "
            "point DATABASE_URL at a real database before relying on this for anything but a demo.",
            preferred, fallback,
        )
        return fallback


INSTANCE_DIR = _writable_instance_dir(BACKEND_ROOT / "instance")


class Config:
    BACKEND_ROOT = BACKEND_ROOT
    REPO_ROOT = REPO_ROOT
    INSTANCE_DIR = INSTANCE_DIR

    # --- Storage ---
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{INSTANCE_DIR / 'app.db'}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SEED_DATA_PATH = REPO_ROOT / "data" / "ward_projects.json"
    PHOTO_UPLOAD_DIR = INSTANCE_DIR / "uploads"

    # --- Languages ---
    # Kiswahili is the primary/default language (most residents' shared
    # language across this pilot's counties); English remains fully
    # supported as a translation choice, and is also the fallback used when
    # a specific string has no Kiswahili/Kikamba translation yet (see
    # services/translation.py's t()).
    SUPPORTED_LANGUAGES = ["sw", "en", "kam"]
    DEFAULT_LANGUAGE = "sw"

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
    # Free-tier Render (where ledger-sidecar/ is hosted) spins the service
    # down after 15 minutes idle; the first request after that pays a cold
    # start of up to ~60s. 10s (a reasonable default for an already-warm
    # sidecar) was timing out on exactly that cold start in production —
    # confirmed live via a ReadTimeoutError. 45s comfortably covers it
    # without leaving a genuinely-hung sidecar call blocking the request
    # forever.
    LEDGER_SIDECAR_TIMEOUT_S = float(os.environ.get("LEDGER_SIDECAR_TIMEOUT_S", "45"))

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
    VOICE_UPLOAD_DIR = INSTANCE_DIR / "voice_uploads"

    # --- Email notifications (SendByte) ---
    # "dummy" (default, logs instead of sending — no credentials needed) or
    # "sendbyte" once SENDBYTE_API_KEY is set (sandbox keys start sk_test_,
    # see https://docs.sendbyte.africa/). Fires on every report/issue
    # submission as a best-effort side notification to the county's contact
    # address — see services/notifications.py.
    EMAIL_BACKEND = os.environ.get("EMAIL_BACKEND", "dummy")
    SENDBYTE_API_KEY = os.environ.get("SENDBYTE_API_KEY", "")
    SENDBYTE_FROM_ADDRESS = os.environ.get("SENDBYTE_FROM_ADDRESS", "reports@wardtracker.ng")
    # Real deployment would look up each county's own contact address; this
    # pilot only ever seeds one county, so every notification goes to one
    # configured test address.
    COUNTY_NOTIFICATION_EMAIL = os.environ.get("COUNTY_NOTIFICATION_EMAIL", "josephbill00@gmail.com")
