from app.services.ledger.stub_client import StubLedgerClient


def test_submit_and_verify_round_trip(tmp_path):
    client = StubLedgerClient(tmp_path / "ledger.jsonl")
    payload = {"project_id": "P1", "claim": "not_delivered"}

    receipt = client.submit_event("submission", payload)

    assert client.verify(payload, receipt.ledger_ref) is True


def test_tampered_payload_fails_verification(tmp_path):
    """This is the core trust guarantee: if the data Flask has doesn't hash
    to what was anchored, verification must fail loudly, not silently pass."""
    client = StubLedgerClient(tmp_path / "ledger.jsonl")
    original_payload = {"project_id": "P1", "claim": "not_delivered"}
    receipt = client.submit_event("submission", original_payload)

    tampered_payload = {"project_id": "P1", "claim": "confirmed_delivered"}
    assert client.verify(tampered_payload, receipt.ledger_ref) is False


def test_sequence_numbers_increment_across_events(tmp_path):
    client = StubLedgerClient(tmp_path / "ledger.jsonl")
    r1 = client.submit_event("submission", {"a": 1})
    r2 = client.submit_event("submission", {"a": 2})
    r3 = client.submit_event("status_change", {"a": 3})

    seqs = [int(r.ledger_ref.rsplit("/", 1)[-1]) for r in (r1, r2, r3)]
    assert seqs == [1, 2, 3]
