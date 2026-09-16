from flask import Blueprint, current_app, jsonify, request

from ..config import Config
from ..db import db
from ..services import otp
from ..services.channels import get_sms_client
from ..services.report_service import get_or_create_reporter

auth_bp = Blueprint("auth", __name__)


@auth_bp.post("/auth/request-otp")
def request_otp():
    data = request.get_json(force=True) or {}
    phone = (data.get("phone") or "").strip()
    if not phone:
        return jsonify({"error": "phone is required"}), 400

    code = otp.request_otp(phone)
    sms = get_sms_client(Config)
    sms.send_text(phone, f"Your County Ward Tracker verification code is {code}")
    return jsonify({"status": "sent"})


@auth_bp.post("/auth/verify-otp")
def verify_otp():
    data = request.get_json(force=True) or {}
    phone = (data.get("phone") or "").strip()
    code = (data.get("code") or "").strip()
    if not phone or not code:
        return jsonify({"error": "phone and code are required"}), 400

    if not otp.verify_otp(phone, code):
        return jsonify({"error": "invalid_or_expired_code"}), 400

    reporter = get_or_create_reporter(phone)
    reporter.phone_verified = True
    db.session.commit()
    return jsonify({"status": "verified", "reporter_id": reporter.id})
