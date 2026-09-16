from __future__ import annotations

from typing import Any

import requests

from .base import LedgerClient, LedgerReceipt, compute_payload_hash


class HederaSidecarClient(LedgerClient):
    """Talks to the Node.js sidecar (ledger-sidecar/) which holds the real
    Hedera JavaScript SDK client. Swap LEDGER_BACKEND=hedera_sidecar in
    config once ledger-sidecar/.env has real testnet credentials — no other
    code changes needed, since this implements the same LedgerClient
    interface as the stub.
    """

    def __init__(self, sidecar_url: str, timeout_s: float = 10.0):
        self.sidecar_url = sidecar_url.rstrip("/")
        self.timeout_s = timeout_s

    def submit_event(self, event_type: str, payload: dict[str, Any]) -> LedgerReceipt:
        payload_hash = compute_payload_hash(payload)
        resp = requests.post(
            f"{self.sidecar_url}/submit",
            json={"event_type": event_type, "payload_hash": payload_hash},
            timeout=self.timeout_s,
        )
        resp.raise_for_status()
        data = resp.json()
        return LedgerReceipt(ledger_ref=data["ledger_ref"], payload_hash=payload_hash, backend="hedera_sidecar")

    def verify(self, payload: dict[str, Any], ledger_ref: str) -> bool:
        expected_hash = compute_payload_hash(payload)
        resp = requests.get(
            f"{self.sidecar_url}/verify",
            params={"ledger_ref": ledger_ref, "payload_hash": expected_hash},
            timeout=self.timeout_s,
        )
        resp.raise_for_status()
        return bool(resp.json().get("valid"))
