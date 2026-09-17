"""
Email delivery via SendByte (https://sendbyte.africa/) — the transactional
email API used to notify a county's contact address whenever a citizen
report or issue is captured. Same pattern as every other external
integration in this repo (ledger, WhatsApp, SMS, STT): a small interface, a
Dummy implementation that logs instead of sending (default, no credentials
needed), and a real client ready to switch in via one config flag.

SendByte API (confirmed from https://docs.sendbyte.africa/):
  POST https://api.sendbyte.africa/v1/emails
  Authorization: Bearer <api_key>          (sk_test_... in sandbox, sk_live_... in production)
  Body: {"from": "...", "to": "...", "subject": "...", "html": "..."}
Sandbox is selected by the key itself (sk_test_ prefix) — no separate URL or
flag, no domain verification needed, emails appear in SendByte's own
dashboard without being actually delivered.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod

logger = logging.getLogger("email_client")

SENDBYTE_API_URL = "https://api.sendbyte.africa/v1/emails"


class EmailClient(ABC):
    @abstractmethod
    def send(self, to: str, subject: str, html: str) -> None: ...


class DummyEmailClient(EmailClient):
    """Logs instead of sending — lets every call site (report/issue
    notifications) be exercised and tested with zero credentials, same as
    DummyWhatsAppClient/DummySmsClient."""

    def __init__(self):
        self.sent: list[tuple[str, str, str]] = []  # kept for test assertions

    def send(self, to: str, subject: str, html: str) -> None:
        self.sent.append((to, subject, html))
        logger.info("[DummyEmail -> %s] %s", to, subject)


class SendByteEmailClient(EmailClient):
    """Real client — needs SENDBYTE_API_KEY (and SENDBYTE_FROM_ADDRESS)."""

    def __init__(self, api_key: str, from_address: str):
        self.api_key = api_key
        self.from_address = from_address

    def send(self, to: str, subject: str, html: str) -> None:
        import requests  # already a hard dependency of this backend

        resp = requests.post(
            SENDBYTE_API_URL,
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json={"from": self.from_address, "to": to, "subject": subject, "html": html},
            timeout=10,
        )
        resp.raise_for_status()
        logger.info("[SendByte -> %s] %s (id=%s, status=%s)", to, subject, resp.json().get("id"), resp.json().get("status"))


_client: EmailClient | None = None


def get_email_client(config) -> EmailClient:
    global _client
    if _client is not None:
        return _client
    if config.EMAIL_BACKEND == "sendbyte":
        _client = SendByteEmailClient(config.SENDBYTE_API_KEY, config.SENDBYTE_FROM_ADDRESS)
    else:
        _client = DummyEmailClient()
    return _client


def reset_email_client() -> None:
    """Test helper."""
    global _client
    _client = None
