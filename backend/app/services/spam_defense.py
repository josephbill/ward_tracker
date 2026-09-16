"""
Section 6 of the spec. Phone number (hashed) is the identity anchor for
every channel. These functions gate a report BEFORE it's written, and flag
suspicious reporters for internal review without ever exposing a public
score.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from ..config import Config
from ..models import Report, Reporter


def hash_phone(raw_phone: str) -> str:
    salted = f"{Config.PHONE_HASH_SALT}:{raw_phone.strip()}"
    return hashlib.sha256(salted.encode("utf-8")).hexdigest()


@dataclass
class GateResult:
    allowed: bool
    supersede_report_id: str | None = None  # existing active report to mark inactive
    exclude_from_aggregation: bool = False
    exclusion_reason: str | None = None
    user_message_key: str = "report_received"


def check_report_gate(reporter: Reporter, project_id: str, now: datetime | None = None) -> GateResult:
    """Runs every spam/abuse check for one incoming report and returns what
    the caller should do. Never silently drops a report — worst case it's
    accepted but excluded from the aggregate count pending review."""
    now = now or datetime.now(timezone.utc)

    existing = (
        Report.query.filter_by(project_id=project_id, reporter_id=reporter.id, active=True).first()
    )
    if existing is not None:
        edited_recently = existing.submitted_at.replace(tzinfo=timezone.utc) > now - timedelta(
            hours=Config.REPORT_EDIT_WINDOW_HOURS
        )
        # One active report per (phone, project): a new submission always
        # supersedes the old one (it's an edit), it just isn't allowed to
        # rack up unlimited *new* report rows within the edit window.
        return GateResult(allowed=True, supersede_report_id=existing.id, user_message_key="report_updated")

    window_start = now - timedelta(minutes=Config.BURST_WINDOW_MINUTES)
    recent_count = Report.query.filter(
        Report.reporter_id == reporter.id, Report.submitted_at >= window_start
    ).count()
    if recent_count >= Config.BURST_MAX_REPORTS:
        return GateResult(
            allowed=True,
            exclude_from_aggregation=True,
            exclusion_reason=f"burst: {recent_count}+ reports within {Config.BURST_WINDOW_MINUTES}m",
            user_message_key="report_flagged_review",
        )

    if not reporter.phone_verified:
        distinct_wards = (
            Report.query.join(Report.project)
            .filter(Report.reporter_id == reporter.id)
            .distinct()
            .count()
        )
        if distinct_wards == 0:
            # First-ever report from an unverified number: allow, but this is
            # exactly the profile spam-detection should watch — if it starts
            # showing up across many unrelated wards, later reports get flagged.
            pass

    from .aggregation import distinct_ward_count_for_reporter

    if distinct_ward_count_for_reporter(reporter.id) >= Config.NEW_NUMBER_MULTI_WARD_THRESHOLD and not reporter.flagged_for_review:
        reporter.flagged_for_review = True

    if reporter.flagged_for_review:
        return GateResult(
            allowed=True,
            exclude_from_aggregation=True,
            exclusion_reason="reporter flagged: reports across many unrelated wards with no prior history",
            user_message_key="report_flagged_review",
        )

    return GateResult(allowed=True)


def update_reputation(reporter: Reporter, corroborated: bool) -> None:
    """Internal-only weighting signal (Section 6): nudged up when a report is
    later corroborated by independent others, down otherwise. Never shown on
    any public API response — only consumed by aggregation.py's weighting."""
    delta = 0.1 if corroborated else -0.05
    reporter.reputation_score = max(0.1, min(3.0, reporter.reputation_score + delta))
