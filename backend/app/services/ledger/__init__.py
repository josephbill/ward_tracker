from pathlib import Path

from .base import LedgerClient, LedgerReceipt, compute_payload_hash
from .stub_client import StubLedgerClient
from .hedera_sidecar_client import HederaSidecarClient

_client: LedgerClient | None = None


def get_ledger_client(config) -> LedgerClient:
    """Factory returning the configured LedgerClient singleton. Callers
    depend only on the LedgerClient interface, so LEDGER_BACKEND can be
    flipped from "stub" to "hedera_sidecar" without touching any of the
    aggregation/report-submission code that calls submit_event()."""
    global _client
    if _client is not None:
        return _client

    if config.LEDGER_BACKEND == "hedera_sidecar":
        _client = HederaSidecarClient(config.LEDGER_SIDECAR_URL)
    else:
        log_path = Path(config.BACKEND_ROOT) / "instance" / "ledger_log.jsonl"
        _client = StubLedgerClient(log_path)
    return _client


def reset_ledger_client() -> None:
    """Test helper — clears the cached singleton so tests can reconfigure."""
    global _client
    _client = None


__all__ = [
    "LedgerClient",
    "LedgerReceipt",
    "compute_payload_hash",
    "StubLedgerClient",
    "HederaSidecarClient",
    "get_ledger_client",
    "reset_ledger_client",
]
