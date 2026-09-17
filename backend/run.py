import os

from app import create_app

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
