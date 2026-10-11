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

# CHANGED: Only load a .env file when we are NOT running on a platform that
# injects env vars directly (Pxxl sets PXXL_ENV, Render sets RENDER, etc.).
# A stray committed .env in the deploy source can otherwise shadow platform
# values for any key not already set. load_dotenv() never overwrites an
# existing key, but this guard makes the intent explicit and prevents a
# surprise if someone commits a .env by accident.
_ENV_FILE = BACKEND_ROOT / ".env"
_ON_PLATFORM = bool(
    os.environ.get("PXXL_ENV")
    or os.environ.get("PXXL")
    or os.environ.get("RENDER")
    or os.environ.get("DYNO")  # Heroku-style
)
if _ENV_FILE.exists() and not _ON_PLATFORM:
    load_dotenv(_ENV_FILE)


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

    CHANGED: When DATABASE_URL is set, the fallback directory is used only
    for uploads (photos/voice), never for the DB. Log that distinction at
    INFO instead of WARNING so a correctly-configured deploy doesn't look
    like it's misconfigured. When DATABASE_URL is missing *and* the
    fallback is used, log at WARNING — that's the genuinely scary case.
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
        if os.environ.get("DATABASE_URL"):
            # DB is on a real server; only uploads land in /tmp.
            logger.info(
                "%s is not writable (read-only deploy filesystem) — using %s "
                "for uploads only. DB is on DATABASE_URL, so no DB data is "
                "at risk. NOTE: uploaded photos/voice notes will NOT survive "
                "a redeploy; move uploads to object storage or a mounted "
                "volume before this is anything but a demo.",
                preferred, fallback,
            )
        else:
            logger.warning(
                "%s is not writable (read-only deploy filesystem?) — falling back to %s. "
                "SQLite data and uploads here do NOT survive a restart/redeploy; "
                "point DATABASE_URL at a real database before relying on this for anything but a demo.",
                preferred, fallback,
            )
        return fallback


INSTANCE_DIR = _writable_instance_dir(BACKEND_ROOT / "instance")


# CHANGED: Hard-fail in production when PHONE_HASH_SALT is unset. The
# previous default ("dev-only-salt-change-in-prod") was documented as
# insecure but nothing enforced replacing it. With a publicly-known salt,
# phone-number hashes are trivially reversible for a space as small as
# Kenyan MSISDNs. In dev, keep the old default so local runs still work.
_PHONE_HASH_SALT_DEFAULT = "dev-only-salt-change-in-prod"
_phone_hash_salt = os.environ.get("PHONE_HASH_SALT", "")
if not _phone_hash_salt:
    if _ON_PLATFORM or os.environ.get("FLASK_ENV") == "production":
        raise RuntimeError(
            "PHONE_HASH_SALT must be set in production. Generate one with: "
            "python -c 'import secrets; print(secrets.token_urlsafe(32))'"
        )
    _phone_hash_salt = _PHONE_HASH_SALT_DEFAULT


class Config:
    BACKEND_ROOT = BACKEND_ROOT
    REPO_ROOT = REPO_ROOT
    INSTANCE_DIR = INSTANCE_DIR

    # --- Storage ---
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{INSTANCE_DIR / 'app.db'}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # CHANGED: Engine options. Without these, a slow or idle-closed
    # connection to Render Postgres (Oregon) from a Paris runtime blocks
    # the gunicorn worker until gunicorn's --timeout fires and SIGKILLs
    # it. The browser then sees a dead socket and reports it as a CORS
    # error ("no Access-Control-Allow-Origin header") because no response
    # was ever produced. These options turn that into a visible 500.
    #
    #   pool_pre_ping    — detect Render's idle-closed connections (~5min)
    #   pool_recycle     — recycle before Render's 300s idle timeout
    #   connect_timeout  — bound TCP+auth handshake (seconds)
    #   statement_timeout— let Postgres abort a runaway query at 15s
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 280,
        "pool_size": 5,
        "max_overflow": 5,
        "connect_args": {
            "connect_timeout": 10,
            "options": "-c statement_timeout=15000",
        },
    }

    SEED_DATA_PATH = REPO_ROOT / "data" / "ward_projects.json"
    PHOTO_UPLOAD_DIR = INSTANCE_DIR / "uploads"

    # --- Languages ---
    SUPPORTED_LANGUAGES = ["sw", "en", "kam"]
    DEFAULT_LANGUAGE = "sw"

    # --- Dispute aggregation (Section 5) ---
    DISPUTE_THRESHOLD_COUNT = int(os.environ.get("DISPUTE_THRESHOLD_COUNT", 3))
    DISPUTE_INDEPENDENCE_RADIUS_M = float(os.environ.get("DISPUTE_INDEPENDENCE_RADIUS_M", 500))
    CONFIRMATION_THRESHOLD_COUNT = int(os.environ.get("CONFIRMATION_THRESHOLD_COUNT", 2))

    # --- Spam / abuse defense (Section 6) ---
    REPORT_EDIT_WINDOW_HOURS = int(os.environ.get("REPORT_EDIT_WINDOW_HOURS", 24))
    BURST_MAX_REPORTS = int(os.environ.get("BURST_MAX_REPORTS", 5))
    BURST_WINDOW_MINUTES = int(os.environ.get("BURST_WINDOW_MINUTES", 10))
    NEW_NUMBER_MULTI_WARD_THRESHOLD = int(os.environ.get("NEW_NUMBER_MULTI_WARD_THRESHOLD", 3))

    # CHANGED: value now resolved above (with a production hard-fail),
    # rather than resolved inline with a known-insecure default.
    PHONE_HASH_SALT = _phone_hash_salt

    # --- Ledger (Hedera) ---
    LEDGER_BACKEND = os.environ.get("LEDGER_BACKEND", "stub")
    LEDGER_SIDECAR_URL = os.environ.get("LEDGER_SIDECAR_URL", "http://localhost:4001")
    LEDGER_SIDECAR_TIMEOUT_S = float(os.environ.get("LEDGER_SIDECAR_TIMEOUT_S", "45"))

    # --- WhatsApp / SMS channel clients ---
    WHATSAPP_BACKEND = os.environ.get("WHATSAPP_BACKEND", "dummy")
    SMS_BACKEND = os.environ.get("SMS_BACKEND", "dummy")
    TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "")
    TWILIO_WHATSAPP_FROM = os.environ.get("TWILIO_WHATSAPP_FROM", "")
    AFRICASTALKING_USERNAME = os.environ.get("AFRICASTALKING_USERNAME", "sandbox")
    AFRICASTALKING_API_KEY = os.environ.get("AFRICASTALKING_API_KEY", "")
    AFRICASTALKING_SHORTCODE = os.environ.get("AFRICASTALKING_SHORTCODE", "")

    # --- Speech-to-text (voice-to-text reporting) ---
    STT_BACKEND = os.environ.get("STT_BACKEND", "dummy")
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
    VOICE_UPLOAD_DIR = INSTANCE_DIR / "voice_uploads"

    # --- Email notifications (SendByte) ---
    EMAIL_BACKEND = os.environ.get("EMAIL_BACKEND", "dummy")
    SENDBYTE_API_KEY = os.environ.get("SENDBYTE_API_KEY", "")
    SENDBYTE_FROM_ADDRESS = os.environ.get("SENDBYTE_FROM_ADDRESS", "reports@wardtracker.ng")
    COUNTY_NOTIFICATION_EMAIL = os.environ.get("COUNTY_NOTIFICATION_EMAIL", "josephbill00@gmail.com")