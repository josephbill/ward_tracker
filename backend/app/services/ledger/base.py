"""
LedgerClient interface. Every report event (submission, status change,
dispute resolution) gets anchored through this — Flask keeps the actual
report data in its own database as usual, and only a hash/reference of the
event goes to the ledger, per Section 5 of the spec.

Two implementations:
  - StubLedgerClient (default): computes the same SHA-256 anchor a real HCS
    submission would be built from, and "publishes" it to a local append-only
    JSONL file with a deterministic fake sequence number. No network calls,
    fully testable, and the anchor format is identical to what the real
    client produces — swapping in the real client later doesn't change how
    callers use this.
  - HederaSidecarClient: calls the Node.js sidecar in ledger-sidecar/, which
    uses the Hedera JavaScript SDK to actually submit to an HCS topic on
    testnet. Requires HEDERA_OPERATOR_ID / HEDERA_OPERATOR_KEY /
    HEDERA_TOPIC_ID to be set in ledger-sidecar/.env — not run in this PoC
    without those credentials, but ready to use once they exist.
"""
from __future__ import annotations

import hashlib
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


class LedgerUnavailableError(Exception):
    """The configured ledger backend couldn't be reached (sidecar down,
    timed out, DNS failure, ...). Raised instead of letting the underlying
    network exception surface as an unhandled 500 — callers (api/reports.py,
    api/issues.py) catch this specifically and return a clean 503 so the
    mobile app's offline queue can tell "the server rejected this" apart
    from "we couldn't even reach the ledger" and retry accordingly."""


@dataclass
class LedgerReceipt:
    ledger_ref: str
    payload_hash: str
    backend: str


class LedgerClient(ABC):
    @abstractmethod
    def submit_event(self, event_type: str, payload: dict[str, Any]) -> LedgerReceipt:
        """Anchor one event. `payload` should be the full event data (ids,
        claim, timestamps, etc) — it is hashed, and only the hash plus a
        small set of non-sensitive fields are sent to the ledger itself."""
        raise NotImplementedError

    def verify(self, payload: dict[str, Any], ledger_ref: str) -> bool:
        """Recompute the hash for `payload` and confirm it matches what's
        anchored under `ledger_ref`. Used by the audit-trail endpoint so
        anyone can confirm a record hasn't been altered."""
        raise NotImplementedError


def compute_payload_hash(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
