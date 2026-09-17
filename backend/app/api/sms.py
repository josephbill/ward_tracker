from flask import Blueprint, current_app, request

from ..services.channels import get_sms_client
from ..services.sms_bot import handle_sms

sms_bp = Blueprint("sms", __name__)


@sms_bp.post("/sms")
def sms_webhook():
    """Accepts an Africa's Talking-style inbound-SMS webhook (form fields:
    from, text). Africa's Talking is the Kenya-native gateway per Section 8;
    this handler only depends on the field names, so Twilio SMS's payload
    (From/Body) is also accepted as a fallback."""
    form = request.form
    from_phone = (form.get("from") or form.get("From") or "").strip()
    text = form.get("text") or form.get("Body") or ""

    if not from_phone:
        return {"error": "missing from"}, 400

    reply_text = handle_sms(from_phone, text)

    client = get_sms_client(current_app.config_class)
    client.send_text(from_phone, reply_text)

    return {"status": "ok", "reply": reply_text}
