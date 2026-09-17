from flask import Blueprint, current_app, request

from ..services.channels import get_whatsapp_client
from ..services.whatsapp_bot import IncomingMessage, handle_message

whatsapp_bp = Blueprint("whatsapp", __name__)


@whatsapp_bp.post("/whatsapp")
def whatsapp_webhook():
    """Accepts a Twilio-style WhatsApp webhook payload (From, Body,
    MediaUrl0, Latitude, Longitude as form fields). Twilio's sandbox is the
    fastest way to get a real number wired up per Section 8 — this handler
    doesn't care which provider sent the request as long as the fields match."""
    form = request.form
    from_phone = form.get("From", "").replace("whatsapp:", "").strip()
    body = form.get("Body", "")
    media_path = form.get("MediaUrl0")
    media_content_type = form.get("MediaContentType0")
    lat = form.get("Latitude", type=float)
    lon = form.get("Longitude", type=float)

    if not from_phone:
        return {"error": "missing From"}, 400

    msg = IncomingMessage(
        from_phone=from_phone, text=body, media_path=media_path,
        media_content_type=media_content_type, latitude=lat, longitude=lon,
    )
    replies = handle_message(msg)

    client = get_whatsapp_client(current_app.config_class)
    for reply in replies:
        client.send_text(from_phone, reply)

    return {"status": "ok", "replies": replies}
