import logging
import os

from app import create_app

# Without this, every logger.info()/logger.exception() call in the codebase
# (services/email_client.py, services/notifications.py, services/ledger/,
# services/channels.py, ...) goes nowhere: Python's root logger has no
# handler by default, so INFO records are silently dropped and even ERROR
# records only reach stderr via a bare "lastResort" fallback with no
# module name or level — indistinguishable from nothing happening at all.
# This was the actual root cause behind "I can't tell if SendByte emails
# are sending" — the calls were succeeding the whole time, just invisibly.
# Deliberately NOT called from app/__init__.py's create_app(): tests call
# that many times per session via pytest fixtures, and configuring the
# root logger from inside it would fight pytest's own log capture.
logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

app = create_app()

if __name__ == "__main__":
    # host="0.0.0.0" and reading PORT from the environment are both required
    # for this to work unmodified on a PaaS like Pxxl, which assigns the
    # port at runtime rather than letting the app pick one — binding only to
    # 127.0.0.1 or a hardcoded port is the #1 reason a Flask app that works
    # locally fails to come up on a host like this. Defaults (5055,
    # debug on) keep local `python run.py` behavior exactly as before.
    port = int(os.environ.get("PORT", 5055))
    debug = os.environ.get("FLASK_DEBUG", "true").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)
