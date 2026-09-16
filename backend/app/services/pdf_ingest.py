"""
Parses the Kasikeu Ward Development Profile 2025 PDF (Makueni County) into
structured project records.

This is a one-off parser tailored to this specific document's table layout —
it does not attempt to generalize to other counties' PDFs. Two tables are
present:

  Section 3 "List of Ward Development Projects" (pages 10-14 in the source
  PDF): historical projects for FY2022/23, FY2023/24 and FY2024/25, each with
  a status the county claims (Complete / Ongoing / Not Started). Rows are
  grouped under sector header rows (a single non-empty cell spanning the
  row, e.g. "Health").

  Section 4 "List of FY2025/26 Projects" (page 15): budgeted-but-not-yet-
  implemented projects for the upcoming financial year, with no status field
  (the FY hasn't started).

Run directly to (re)generate data/ward_projects.json:
    python -m app.services.pdf_ingest
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

import pdfplumber

WARD = "Kasikeu"
COUNTY = "Makueni"
SOURCE_DOCUMENT = "Kasikeu Ward Development Profile, 2025 (Government of Makueni County)"

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_PDF_PATH = REPO_ROOT / "data" / "raw" / "Kasikeu-Ward-Development-Profile-2025.pdf"
DEFAULT_OUTPUT_PATH = REPO_ROOT / "data" / "ward_projects.json"

# Pages 10-14 (0-indexed) hold the FY22/23-24/25 project table; page 15 holds
# the FY2025/26 planned-projects table. Both were confirmed by inspecting the
# actual extracted tables in this document.
HISTORICAL_TABLE_PAGES = range(10, 15)
PLANNED_TABLE_PAGE = 15

HISTORICAL_HEADER = ["No", "Project Name", "Project Description", "Subward", "Budget", "FY", "Status", "Current Remarks"]
PLANNED_HEADER = ["No", "Department", "Subward", "Project Name", "Budget"]

# County's own claimed delivery status -> our normalized enum. This is what
# citizens are being asked to confirm or dispute.
STATUS_MAP = {
    "complete": "delivered",
    "ongoing": "ongoing",
    "not started": "not_started",
    "not start": "not_started",
}


@dataclass
class ProjectRecord:
    id: str
    ward: str
    county: str
    subward: str
    sector: str
    project_name: str
    description: str
    financial_year: str
    allocated_amount_ksh: int
    county_claimed_status: str  # delivered | ongoing | not_started | planned
    county_remarks: str
    source_document: str
    source_page: int
    verification_status: str = "reported"  # citizen-facing status; see aggregation.py


def _clean(text: Optional[str]) -> str:
    """Normalize whitespace and repair a font-encoding artifact in this PDF
    where en-dashes/bullets decode as U+FFFD (replacement character)."""
    if not text:
        return ""
    text = text.replace("\n", " ").replace("�", "-")
    return re.sub(r"\s+", " ", text).strip()


def _normalize_subward(raw: str) -> str:
    """The source PDF spells "Cross-cutting" inconsistently (a stray space
    before the hyphen on some rows: "Cross- cutting") — normalize both to
    one canonical form so translate_subward()'s lookup in translation.py
    actually matches every row, not just some."""
    cleaned = _clean(raw)
    if cleaned.lower().replace(" ", "") == "cross-cutting":
        return "Cross-cutting"
    return cleaned


def _parse_budget(raw: str) -> int:
    digits = re.sub(r"[^\d]", "", raw or "")
    return int(digits) if digits else 0


def _normalize_fy(raw: str) -> str:
    raw = (raw or "").strip().replace("\\", "/")
    return raw


def _normalize_status(raw: str) -> str:
    key = _clean(raw).lower()
    return STATUS_MAP.get(key, "ongoing" if "ongo" in key else "not_started" if "not" in key else "delivered")


def _is_section_header_row(row: list) -> bool:
    first = (row[0] or "").strip()
    rest_empty = all(c is None for c in row[1:])
    return rest_empty and first != "" and not first[0].isdigit()


def _is_data_row(row: list, expected_len: int) -> bool:
    return len(row) == expected_len and (row[0] or "").strip().isdigit()


def parse_historical_projects(pdf: "pdfplumber.PDF") -> list[ProjectRecord]:
    records: list[ProjectRecord] = []
    current_sector = "General"
    seq = 0

    for page_index in HISTORICAL_TABLE_PAGES:
        page = pdf.pages[page_index]
        for table in page.extract_tables():
            for row in table:
                if row == HISTORICAL_HEADER:
                    continue
                if _is_section_header_row(row):
                    current_sector = _clean(row[0])
                    continue
                if not _is_data_row(row, len(HISTORICAL_HEADER)):
                    continue

                _, name, description, subward, budget, fy, status, remarks = row
                seq += 1
                name = _clean(name) or _clean(description)[:60] or f"Ward project #{seq}"
                fy_norm = _normalize_fy(fy)
                records.append(
                    ProjectRecord(
                        id=f"KASIKEU-{fy_norm.replace('/', '-')}-{seq:03d}",
                        ward=WARD,
                        county=COUNTY,
                        subward=_normalize_subward(subward) or "Cross-cutting",
                        sector=current_sector,
                        project_name=name,
                        description=_clean(description),
                        financial_year=fy_norm,
                        allocated_amount_ksh=_parse_budget(budget),
                        county_claimed_status=_normalize_status(status),
                        county_remarks=_clean(remarks),
                        source_document=SOURCE_DOCUMENT,
                        source_page=page_index + 1,
                    )
                )
    return records


def parse_planned_projects(pdf: "pdfplumber.PDF") -> list[ProjectRecord]:
    records: list[ProjectRecord] = []
    page = pdf.pages[PLANNED_TABLE_PAGE]
    seq = 0
    for table in page.extract_tables():
        for row in table:
            if row == PLANNED_HEADER:
                continue
            if not _is_data_row(row, len(PLANNED_HEADER)):
                continue
            _, department, subward, name, budget = row
            seq += 1
            records.append(
                ProjectRecord(
                    id=f"KASIKEU-2025-26-{seq:03d}",
                    ward=WARD,
                    county=COUNTY,
                    subward=_clean(subward) or "Cross-cutting",
                    sector=_clean(department),
                    project_name=_clean(name)[:80] or f"Planned project #{seq}",
                    description=_clean(name),
                    financial_year="2025/26",
                    allocated_amount_ksh=_parse_budget(budget),
                    county_claimed_status="planned",
                    county_remarks="Budgeted for FY2025/26; implementation not yet due to begin.",
                    source_document=SOURCE_DOCUMENT,
                    source_page=PLANNED_TABLE_PAGE + 1,
                )
            )
    return records


def parse_pdf(pdf_path: Path = DEFAULT_PDF_PATH) -> list[ProjectRecord]:
    with pdfplumber.open(pdf_path) as pdf:
        return parse_historical_projects(pdf) + parse_planned_projects(pdf)


def main() -> None:
    records = parse_pdf()
    DEFAULT_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(DEFAULT_OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump([asdict(r) for r in records], f, indent=2, ensure_ascii=False)
    print(f"Parsed {len(records)} project records -> {DEFAULT_OUTPUT_PATH}")
    delivered = sum(1 for r in records if r.county_claimed_status == "delivered")
    ongoing = sum(1 for r in records if r.county_claimed_status == "ongoing")
    not_started = sum(1 for r in records if r.county_claimed_status == "not_started")
    planned = sum(1 for r in records if r.county_claimed_status == "planned")
    print(f"  delivered={delivered} ongoing={ongoing} not_started={not_started} planned(FY25/26)={planned}")


if __name__ == "__main__":
    main()
