from pathlib import Path

import pytest

from app.services.pdf_ingest import DEFAULT_PDF_PATH, _clean, _normalize_status, _parse_budget, parse_pdf

pdfplumber = pytest.importorskip("pdfplumber")


def test_clean_repairs_encoding_artifact():
    # U+FFFD is what this PDF's custom font decodes en-dashes/bullets as —
    # see _clean()'s docstring. Using the literal replacement char here
    # (not a real en-dash) to match what pdfplumber actually extracts.
    assert _clean("Kithina � Kitivo\nMarket") == "Kithina - Kitivo Market"
    assert _clean(None) == ""


def test_parse_budget_strips_commas():
    assert _parse_budget("1,000,000") == 1_000_000
    assert _parse_budget("") == 0


def test_normalize_status_maps_variants():
    assert _normalize_status("Complete") == "delivered"
    assert _normalize_status("Ongoing") == "ongoing"
    assert _normalize_status("Not started") == "not_started"
    assert _normalize_status("Not Started") == "not_started"


@pytest.mark.skipif(not DEFAULT_PDF_PATH.exists(), reason="real Kasikeu PDF not downloaded in this environment")
def test_parse_real_pdf_produces_expected_shape():
    records = parse_pdf()
    assert len(records) >= 60

    delivered = [r for r in records if r.county_claimed_status == "delivered"]
    planned = [r for r in records if r.county_claimed_status == "planned"]
    assert len(delivered) >= 30
    assert len(planned) >= 10

    for r in records:
        assert r.ward == "Kasikeu"
        assert r.county == "Makueni"
        assert r.allocated_amount_ksh > 0
        assert r.financial_year in {"2022/23", "2023/24", "2024/25", "2025/26"}
        assert r.county_claimed_status in {"delivered", "ongoing", "not_started", "planned"}
        assert "�" not in r.description  # font-encoding artifact must be repaired
        # Traceability (gap-fill Section 1): every record must cite the
        # specific table/section it was lifted from, not just the document.
        assert r.source_reference
        assert str(r.source_page) in r.source_reference
        assert "Kasikeu" in r.source_reference

    ids = [r.id for r in records]
    assert len(ids) == len(set(ids)), "project ids must be unique"
