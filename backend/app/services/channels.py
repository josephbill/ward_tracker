"""
Outbound message clients for WhatsApp and SMS. Both follow the same pattern
as the ledger client: a small interface, a Dummy implementation that logs
instead of calling a real API (so the conversation flows are fully testable
with zero credentials), and a real implementation ready to switch in via
config once WHATSAPP_BACKEND / SMS_BACKEND / real credentials are set.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod

logger = logging.getLogger("channels")


class WhatsAppClient(ABC):
    @abstractmethod
    def send_text(self, to_phone: str, body: str) -> None: ...


class SmsClient(ABC):
    @abstractmethod
    def send_text(self, to_phone: str, body: str) -> None: ...


class DummyWhatsAppClient(WhatsAppClient):
    """Logs the outbound message instead of calling Twilio/Meta. Used by
    default so the whole conversation flow (backend/tests/test_whatsapp_bot.py)
    is exercisable without a real WhatsApp Business account."""

    def __init__(self):
        self.sent: list[tuple[str, str]] = []  # kept for test assertions

    def send_text(self, to_phone: str, body: str) -> None:
        self.sent.append((to_phone, body))
        logger.info("[DummyWhatsApp -> %s] %s", to_phone, body)


class DummySmsClient(SmsClient):
    def __init__(self):
        self.sent: list[tuple[str, str]] = []

    def send_text(self, to_phone: str, body: str) -> None:
        self.sent.append((to_phone, body))
        logger.info("[DummySMS -> %s] %s", to_phone, body)


class TwilioWhatsAppClient(WhatsAppClient):
    """Real client — needs TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN /
    TWILIO_WHATSAPP_FROM set. Not exercised in this PoC without those creds."""

    def __init__(self, account_sid: str, auth_token: str, from_number: str):
        from twilio.rest import Client  # imported lazily: twilio is an optional dep

        self._client = Client(account_sid, auth_token)
        self._from_number = from_number

    def send_text(self, to_phone: str, body: str) -> None:
        self._client.messages.create(
            from_=f"whatsapp:{self._from_number}", to=f"whatsapp:{to_phone}", body=body
        )


class AfricasTalkingSmsClient(SmsClient):
    """Real client — needs AFRICASTALKING_USERNAME / AFRICASTALKING_API_KEY.
    Not exercised in this PoC without a sandbox account."""

    def __init__(self, username: str, api_key: str, shortcode: str = ""):
        import africastalking  # imported lazily: optional dep

        africastalking.initialize(username, api_key)
        self._sms = africastalking.SMS
        self._shortcode = shortcode or None

    def send_text(self, to_phone: str, body: str) -> None:
        self._sms.send(body, [to_phone], sender_id=self._shortcode)


_whatsapp_client: WhatsAppClient | None = None
_sms_client: SmsClient | None = None


def get_whatsapp_client(config) -> WhatsAppClient:
    global _whatsapp_client
    if _whatsapp_client is not None:
        return _whatsapp_client
    if config.WHATSAPP_BACKEND == "twilio":
        _whatsapp_client = TwilioWhatsAppClient(
            config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN, config.TWILIO_WHATSAPP_FROM
        )
    else:
        _whatsapp_client = DummyWhatsAppClient()
    return _whatsapp_client


def get_sms_client(config) -> SmsClient:
    global _sms_client
    if _sms_client is not None:
        return _sms_client
    if config.SMS_BACKEND == "africas_talking":
        _sms_client = AfricasTalkingSmsClient(
            config.AFRICASTALKING_USERNAME, config.AFRICASTALKING_API_KEY, config.AFRICASTALKING_SHORTCODE
        )
    else:
        _sms_client = DummySmsClient()
    return _sms_client


def reset_channel_clients() -> None:
    global _whatsapp_client, _sms_client
    _whatsapp_client = None
    _sms_client = None
