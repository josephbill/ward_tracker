"""
Submission logic for citizen-initiated infrastructure/improvement issues
(Section 9, item 3) — the "report a pothole/broken borehole even though
there's no budgeted project for it" flow. Mirrors report_service.py's shape
(same ledger anchoring, same phone-verification gate) but deliberately
simpler: there's no existing official claim to aggregate against, so no
dispute-threshold logic applies here — every issue is just logged and
made visible, same trust bar (OTP-verified phone) as a project report.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from flask import current_app

from ..config import Config
from ..db import db
from ..models import IssueReport, Reporter, ISSUE_CATEGORIES
from .ledger import get_ledger_client
from .notifications import notify_county_of_issue
from .privacy import round_gps
from .report_service import get_or_create_reporter


class PhoneNotVerifiedError(Exception):
    pass


class RateLimitedError(Exception):
    pass


class InvalidCategoryError(Exception):
    pass


def submit_issue(
    *,
    raw_phone: str,
    county: str,
    ward: str,
    category: str,
    title: str,
    description: str | None = None,
    channel: str = "app",
    photo_path: str | None = None,
    gps_lat: float | None = None,
    gps_lon: float | None = None,
) -> IssueReport:
    if category not in ISSUE_CATEGORIES:
        raise InvalidCategoryError(category)

    reporter = get_or_create_reporter(raw_phone)
    if not reporter.phone_verified:
        raise PhoneNotVerifiedError()

    window_start = datetime.now(timezone.utc) - timedelta(minutes=Config.BURST_WINDOW_MINUTES)
    recent_count = IssueReport.query.filter(
        IssueReport.reporter_id == reporter.id, IssueReport.submitted_at >= window_start
    ).count()
    if recent_count >= Config.BURST_MAX_REPORTS:
        raise RateLimitedError()

    gps_lat, gps_lon = round_gps(gps_lat, gps_lon)

    issue = IssueReport(
        reporter_id=reporter.id,
        county=county,
        ward=ward,
        category=category,
        title=title,
        description=description,
        channel=channel,
        photo_path=photo_path,
        gps_lat=gps_lat,
        gps_lon=gps_lon,
    )
    db.session.add(issue)
    db.session.flush()

    ledger = get_ledger_client(current_app.config_class)
    payload = {
        "issue_id": issue.id,
        "reporter_id": reporter.id,
        "county": county,
        "ward": ward,
        "category": category,
        "title": title,
        "submitted_at": issue.submitted_at.isoformat(),
    }
    receipt = ledger.submit_event("issue_submission", payload)
    issue.ledger_ref = receipt.ledger_ref

    db.session.commit()

    # Best-effort county email notification — see notify_county_of_issue's
    # docstring: the issue is already durably saved by this point.
    notify_county_of_issue(issue, reporter)

    return issue
