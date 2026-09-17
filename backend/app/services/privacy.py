"""
Privacy hardening (gap-fill Section 3): shared helper for capping stored GPS
precision to roughly neighbourhood/ward-level resolution rather than a
resident's exact coordinates, used by both report_service.py and
issue_service.py so the same rule applies to every location a citizen shares.

3 decimal places is ~111m of precision at the equator (less at higher
latitudes) — coarse enough that it doesn't pin a specific household, but
still well inside aggregation.py's DISPUTE_INDEPENDENCE_RADIUS_M (500m
default), so rounding doesn't distort the independence-clustering logic.

This PoC has no escalation/investigation workflow that would need the
resident's exact original coordinates for a specific case — full precision
is simply never retained anywhere, which is the privacy-safe default. A real
deployment adding that workflow would need to capture higher precision
explicitly at that time (e.g. a separate, access-controlled field gated
behind an active investigation), not recover it from already-rounded data.
"""
from __future__ import annotations

GPS_PRECISION_DECIMALS = 3


def round_gps(lat: float | None, lon: float | None) -> tuple[float | None, float | None]:
    if lat is None or lon is None:
        return lat, lon
    return round(lat, GPS_PRECISION_DECIMALS), round(lon, GPS_PRECISION_DECIMALS)
