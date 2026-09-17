from flask import Flask
from flask_cors import CORS

from .config import Config
from .db import db


def create_app(config_object: type = Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_object)
    # Flask's app.config is a dict copy of config_object's attributes — the
    # get_*_client() factories (ledger, WhatsApp, SMS, STT, email) all read
    # attribute-style config (config.EMAIL_BACKEND, not config["EMAIL_BACKEND"]),
    # so every call site needs the ORIGINAL class, not a re-import of the
    # plain Config. Stashing it here is what lets tests' TestConfig actually
    # override backend behavior instead of every client silently reading the
    # real process-wide Config class regardless of what was passed in here.
    app.config_class = config_object

    # The React Native app's Expo web preview runs on its own dev-server
    # origin (e.g. :19100) and calls this API (e.g. :5055) cross-origin.
    # Native iOS/Android builds don't enforce CORS, so this only matters for
    # the web preview target used in local dev/demo.
    CORS(app)

    config_object.BACKEND_ROOT.mkdir(parents=True, exist_ok=True)
    (config_object.BACKEND_ROOT / "instance").mkdir(parents=True, exist_ok=True)
    config_object.PHOTO_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    config_object.VOICE_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    db.init_app(app)

    from .api.projects import projects_bp
    from .api.reports import reports_bp
    from .api.auth import auth_bp
    from .api.whatsapp import whatsapp_bp
    from .api.sms import sms_bp
    from .api.issues import issues_bp
    from .api.voice import voice_bp

    app.register_blueprint(projects_bp, url_prefix="/api")
    app.register_blueprint(reports_bp, url_prefix="/api")
    app.register_blueprint(auth_bp, url_prefix="/api")
    app.register_blueprint(issues_bp, url_prefix="/api")
    app.register_blueprint(voice_bp, url_prefix="/api")
    app.register_blueprint(whatsapp_bp, url_prefix="/webhooks")
    app.register_blueprint(sms_bp, url_prefix="/webhooks")

    with app.app_context():
        db.create_all()

    @app.get("/healthz")
    def healthz():
        return {"status": "ok"}

    return app
