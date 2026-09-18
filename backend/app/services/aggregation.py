"""
Section 5 of the spec: turns the raw pile of Report rows for a project into
one citizen-facing verification_status.

Independence rule (documented here since it's the one judgment call the spec
asks us to make explicit before building): two reports are "independent" if
they come from different reporters AND their GPS points are more than
DISPUTE_INDEPENDENCE_RADIUS_M apart. Reports with no GPS are always treated
as independent of everything else, since we have nothing to compare against
and refusing to count them would penalize SMS/no-GPS reporters. This is a
practical proxy for "not the same household" given we have no household
registry to check against directly.

Status changes to "Disputed" only once independent reports DISAGREE with the
county's own claimed status (`Project.county_claimed_status`) and their
count reaches config.DISPUTE_THRESHOLD_COUNT. Reputation score is used only
as an internal weighting signal (never a public score, never gates the
threshold on its own) — see docs/SPAM_DEFENSE.md for the one-paragraph
summary.
"""
from __future__ import annotations

import math
from collections import Counter

from ..config import Config
from ..db import db
from ..models import Project, Report, Reporter

EARTH_RADIUS_M = 6_371_000

# claim -> whether it agrees with a given county_claimed_status
_AGREEMENT_MATRIX = {
    "delivered": {"confirmed_delivered": True, "partially_delivered": False, "not_delivered": False},
    "ongoing": {"confirmed_delivered": False, "partially_delivered": True, "not_delivered": True},
    "not_started": {"confirmed_delivered": False, "partially_delivered": False, "not_delivered": True},
    "planned": {"confirmed_delivered": False, "partially_delivered": False, "not_delivered": True},
}

_CLAIM_TO_STATUS = {
    "confirmed_delivered": "confirmed",
    "partially_delivered": "partially_delivered",
    "not_delivered": "not_delivered",
}


def _haversine_m(lat1, lon1, lat2, lon2) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))


def _cluster_independent(reports: list[Report]) -> list[list[Report]]:
    """Greedy clustering: a report joins the first existing cluster whose
    representative (first member) is within DISPUTE_INDEPENDENCE_RADIUS_M;
    otherwise it starts a new cluster. Reports without GPS always start
    their own cluster. Returns one cluster per independent report/group."""
    clusters: list[list[Report]] = []
    for report in reports:
        if report.gps_lat is None or report.gps_lon is None:
            clusters.append([report])
            continue
        joined = False
        for cluster in clusters:
            rep = cluster[0]
            if rep.gps_lat is None or rep.gps_lon is None:
                continue
            dist = _haversine_m(report.gps_lat, report.gps_lon, rep.gps_lat, rep.gps_lon)
            if dist <= Config.DISPUTE_INDEPENDENCE_RADIUS_M:
                cluster.append(report)
                joined = True
                break
        if not joined:
            clusters.append([report])
    return clusters


def _cluster_weight(cluster: list[Report]) -> float:
    """Section 6: reputation affects internal aggregation weighting only
    (never a public score). A cluster of one independent report from a
    reporter with the default reputation (1.0) counts as exactly 1 toward
    the threshold, same as plain counting; a cluster containing a
    lower/higher-reputation reporter counts for correspondingly less/more.
    Averaged across a cluster's members so one independent "voice" is
    weighted consistently regardless of how many reports happened to land
    in the same location bucket."""
    reporters = [Reporter.query.get(r.reporter_id) for r in cluster]
    scores = [rep.reputation_score for rep in reporters if rep is not None]
    return sum(scores) / len(scores) if scores else 1.0


def _weights(project: Project) -> dict:
    """Shared by recompute_verification_status() (which WRITES the result)
    and verification_progress() (a read-only view of the same numbers for
    the "X of Y independent reports" UI — gap-fill Section 3) so the two
    never drift apart."""
    active_reports = (
        Report.query.filter_by(project_id=project.id, active=True, excluded_from_aggregation=False).all()
    )
    agreement_map = _AGREEMENT_MATRIX.get(project.county_claimed_status, {})
    disagreeing = [r for r in active_reports if agreement_map.get(r.claim) is False]
    agreeing = [r for r in active_reports if agreement_map.get(r.claim) is True]

    disagree_weight = sum(_cluster_weight(c) for c in _cluster_independent(disagreeing))
    agree_weight = sum(_cluster_weight(c) for c in _cluster_independent(agreeing))

    return {
        "active_reports": active_reports,
        "agreeing": agreeing,
        "disagreeing": disagreeing,
        "agree_weight": agree_weight,
        "disagree_weight": disagree_weight,
    }


def recompute_verification_status(project: Project) -> str:
    """Recomputes and WRITES project.verification_status. Returns the new
    status so callers can decide whether to log a status_change event."""
    w = _weights(project)

    if w["disagree_weight"] >= Config.DISPUTE_THRESHOLD_COUNT:
        new_status = "disputed"
    elif w["agree_weight"] >= Config.CONFIRMATION_THRESHOLD_COUNT:
        dominant_claim = Counter(r.claim for r in w["agreeing"]).most_common(1)[0][0]
        new_status = _CLAIM_TO_STATUS[dominant_claim]
    else:
        new_status = "reported"

    project.verification_status = new_status
    return new_status


def verification_progress(project: Project) -> dict:
    """Read-only "how close is this to Confirmed/Disputed" view — never
    mutates project.verification_status. Powers the report-count UI: a
    resident sees e.g. "1 of 2 independent reports needed to confirm" or
    "2 of 3 independent reports needed to dispute" instead of just a bare
    status label with no sense of how close/far it is from changing."""
    w = _weights(project)
    return {
        "agree_count": round(w["agree_weight"], 2),
        "agree_needed": Config.CONFIRMATION_THRESHOLD_COUNT,
        "disagree_count": round(w["disagree_weight"], 2),
        "disagree_needed": Config.DISPUTE_THRESHOLD_COUNT,
        "total_active_reports": len(w["active_reports"]),
    }


def distinct_ward_count_for_reporter(reporter_id: str) -> int:
    rows = (
        db.session.query(Project.ward)
        .join(Report, Report.project_id == Project.id)
        .filter(Report.reporter_id == reporter_id)
        .distinct()
        .all()
    )
    return len(rows)
