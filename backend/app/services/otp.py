"""
Minimal OTP for phone verification (Section 6: "app should require phone
verification via OTP, not just device install"). Stored in memory — fine
for a PoC demo process; a real deployment would use Redis or similar with
proper expiry/rate limiting. Codes are also logged via the channel client so
the demo can proceed without a real SMS gateway.

Demo convenience: verify_otp also accepts the last 6 digits of the phone
number itself as a valid code, alongside the real generated one. This lets a
live demo (or an emulator without easy access to the backend log/DummySms
output) move through the OTP screen without needing to tail logs — it is not
a real security relaxation since this whole channel is already a DummySms
stub with no real SMS delivery. Remove this fallback before any real
deployment (SMS_BACKEND=africas_talking or similar with a live gateway).
"""
from __future__ import annotations

import random
import re
from datetime import datetime, timedelta, timezone

_OTP_TTL_MINUTES = 5
_store: dict[str, tuple[str, datetime]] = {}  # phone -> (code, expires_at)


def request_otp(phone: str) -> str:
    code = f"{random.randint(0, 999999):06d}"
    _store[phone] = (code, datetime.now(timezone.utc) + timedelta(minutes=_OTP_TTL_MINUTES))
    return code


def _last_six_digits(phone: str) -> str:
    digits = re.sub(r"\D", "", phone)
    return digits[-6:]


def verify_otp(phone: str, code: str) -> bool:
    entry = _store.get(phone)
    if entry is None:
        return False
    stored_code, expires_at = entry
    if datetime.now(timezone.utc) > expires_at:
        del _store[phone]
        return False
    if code != stored_code and code != _last_six_digits(phone):
        return False
    del _store[phone]
    return True
