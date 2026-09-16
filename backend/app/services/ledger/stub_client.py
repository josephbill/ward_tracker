from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .base import LedgerClient, LedgerReceipt, compute_payload_hash

_lock = threading.Lock()


class StubLedgerClient(LedgerClient):
    """Local, deterministic stand-in for the Hedera Consensus Service.

    Appends one JSON line per event to `ledger_log_path` — a minimal
    append-only log that plays the same role a real HCS topic would in the
    demo: nothing already written can be edited without it being obvious
    (any edit changes the file's content, which a `git diff` or checksum
    would catch), and every ref is derived from a running sequence number +
    the payload hash, mirroring the shape of a real Hedera consensus
    timestamp + transaction id.
    """

    def __init__(self, ledger_log_path: Path):
        self.ledger_log_path = ledger_log_path
        self.ledger_log_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.ledger_log_path.exists():
            self.ledger_log_path.write_text("", encoding="utf-8")

    def _next_sequence(self) -> int:
        if not self.ledger_log_path.exists():
            return 1
        with open(self.ledger_log_path, "r", encoding="utf-8") as f:
            return sum(1 for _ in f) + 1

    def submit_event(self, event_type: str, payload: dict[str, Any]) -> LedgerReceipt:
        payload_hash = compute_payload_hash(payload)
        with _lock:
            seq = self._next_sequence()
            record = {
                "sequence_number": seq,
                "consensus_timestamp": datetime.now(timezone.utc).isoformat(),
                "event_type": event_type,
                "payload_hash": payload_hash,
            }
            with open(self.ledger_log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, sort_keys=True) + "\n")
        ledger_ref = f"stub-topic-0.0.0/{seq}"
        return LedgerReceipt(ledger_ref=ledger_ref, payload_hash=payload_hash, backend="stub")

    def verify(self, payload: dict[str, Any], ledger_ref: str) -> bool:
        expected_hash = compute_payload_hash(payload)
        try:
            seq = int(ledger_ref.rsplit("/", 1)[-1])
        except (ValueError, IndexError):
            return False
        with open(self.ledger_log_path, "r", encoding="utf-8") as f:
            for line in f:
                record = json.loads(line)
                if record["sequence_number"] == seq:
                    return record["payload_hash"] == expected_hash
        return False
