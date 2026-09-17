"""
County email notifications — fires whenever a citizen report or issue is
captured, per the explicit instruction to add this without changing the
existing submission flow's behavior or return values. Both entry points
here are deliberately fire-and-forget: they catch and log every exception
rather than letting an email failure roll back, delay, or change the
outcome of a report/issue submission that has already succeeded.

Recipient: a real deployment would look up the receiving county's own
contact address (a table keyed by county, not built yet — this pilot only
ever seeds one county). For now every notification goes to
COUNTY_NOTIFICATION_EMAIL, which defaults to the test address the project
was built against — see backend/.env.example.
"""
from __future__ import annotations

import logging

from flask import current_app

from ..models import IssueReport, Project, Report, Reporter
from .email_client import get_email_client

logger = logging.getLogger("notifications")

_CLAIM_LABELS = {
    "confirmed_delivered": "Confirmed delivered",
    "not_delivered": "Not delivered",
    "partially_delivered": "Partially delivered",
}


def notify_county_of_report(report: Report, project: Project, reporter: Reporter) -> None:
    try:
        config = current_app.config_class
        client = get_email_client(config)
        subject = f"[{project.county} Ward Tracker] New report on {project.id}: {project.project_name}"
        html = f"""
        <h2>New citizen report</h2>
        <p><b>Project:</b> {project.project_name} ({project.id})</p>
        <p><b>Ward:</b> {project.ward}, {project.county}</p>
        <p><b>County's own record says:</b> {project.county_claimed_status}</p>
        <p><b>Resident reports:</b> {_CLAIM_LABELS.get(report.claim, report.claim)}</p>
        <p><b>Remarks:</b> {report.remarks or "(none)"}</p>
        <p><b>Channel:</b> {report.channel}</p>
        <p><b>Reported by:</b> anonymized reporter {reporter.id} (phone never shared)</p>
        <p><b>Submitted:</b> {report.submitted_at.isoformat() if report.submitted_at else ""}</p>
        <p><b>Ledger reference:</b> {report.ledger_ref}</p>
        <hr>
        <p style="color:#888;font-size:12px">Automated notification from the County Ward Tracker pilot. This is a
        test deployment — see docs/ARCHITECTURE.md.</p>
        """
        client.send(to=config.COUNTY_NOTIFICATION_EMAIL, subject=subject, html=html)
    except Exception:
        logger.exception(
            "Failed to send county notification email for report %s — the report itself was already "
            "saved successfully and is unaffected.", report.id,
        )


def notify_county_of_issue(issue: IssueReport, reporter: Reporter) -> None:
    try:
        config = current_app.config_class
        client = get_email_client(config)
        subject = f"[{issue.county} Ward Tracker] New issue reported: {issue.title}"
        html = f"""
        <h2>New citizen-reported issue</h2>
        <p><b>Title:</b> {issue.title}</p>
        <p><b>Category:</b> {issue.category}</p>
        <p><b>Ward:</b> {issue.ward}, {issue.county}</p>
        <p><b>Description:</b> {issue.description or "(none)"}</p>
        <p><b>Channel:</b> {issue.channel}</p>
        <p><b>Reported by:</b> anonymized reporter {reporter.id} (phone never shared)</p>
        <p><b>Submitted:</b> {issue.submitted_at.isoformat() if issue.submitted_at else ""}</p>
        <p><b>Ledger reference:</b> {issue.ledger_ref}</p>
        <hr>
        <p style="color:#888;font-size:12px">Automated notification from the County Ward Tracker pilot. This is a
        test deployment — see docs/ARCHITECTURE.md.</p>
        """
        client.send(to=config.COUNTY_NOTIFICATION_EMAIL, subject=subject, html=html)
    except Exception:
        logger.exception(
            "Failed to send county notification email for issue %s — the issue itself was already "
            "saved successfully and is unaffected.", issue.id,
        )
