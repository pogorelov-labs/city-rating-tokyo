"""Scoring + filtering helpers — Python mirror of app/src/lib/scoring.ts.

Constants (RATING_KEYS, DEFAULT_WEIGHTS, DEFAULT_FILTERS, RENT_FLOOR,
RENT_CEILING) are now imported from the shared `city_rating_schema` package
so this file, the frontend scoring.ts, and compute-ratings.py all read from
one source of truth. The functions below remain a hand-maintained mirror of
the TS implementations — keep their behaviour aligned when either changes.
"""

from __future__ import annotations

from typing import Any

from city_rating_schema.constants import (
    RATING_KEYS,
    DEFAULT_WEIGHTS,
    DEFAULT_FILTERS,
    DEFAULT_ENVIRONMENT_FILTERS,
    RENT_FLOOR,
    RENT_CEILING,
)

# Re-export for backwards compatibility with existing callers that import
# these names from this module. DEFAULT_FILTERS from the schema package is
# the 6 core fields; we merge in the environment-filter defaults so existing
# callers that read DEFAULT_FILTERS["hide_flood_risk"] keep working.
DEFAULT_FILTERS = {
    **DEFAULT_FILTERS,
    "hide_flood_risk": DEFAULT_ENVIRONMENT_FILTERS["hide_flood_risk"],
    "hide_high_seismic": DEFAULT_ENVIRONMENT_FILTERS["hide_high_seismic"],
}


def composite_score(ratings: dict[str, float] | None, weights: dict[str, float] | None = None) -> float | None:
    """Weighted composite of the 10 ratings.

    Returns None if ratings are missing. Mirrors `calculateWeightedScore`.
    Keys with weight ≤ 0 are skipped (matches the frontend behaviour where
    a 0-weight slider drops the dimension entirely).
    """
    if not ratings:
        return None
    w = weights or DEFAULT_WEIGHTS
    total = 0.0
    weighted = 0.0
    for key in RATING_KEYS:
        weight = w.get(key, 0)
        if weight <= 0:
            continue
        val = ratings.get(key)
        if val is None:
            continue
        total += weight
        weighted += val * weight
    if total == 0:
        return 0.0
    return round(weighted / total * 10) / 10


def percentile_anchors(scores: list[float]) -> dict[str, float]:
    """p5 / p50 / p95 anchors — mirrors `computeCompositeAnchors`."""
    if not scores:
        return {"p5": 1.0, "p50": 5.5, "p95": 10.0}
    s = sorted(scores)
    n = len(s)

    def pick(pct: float) -> float:
        idx = max(0, min(n - 1, int(n * pct)))
        return s[idx]

    return {"p5": pick(0.05), "p50": pick(0.5), "p95": pick(0.95)}


def _rent_value(rent_avg: dict[str, Any] | None) -> float | None:
    if not rent_avg:
        return None
    v = rent_avg.get("1k_1ldk")
    if v is None:
        v = rent_avg.get("2ldk")
    return v


def _min_transit(transit: dict[str, Any] | None) -> float | None:
    if not transit:
        return None
    vals = [v for v in transit.values() if isinstance(v, (int, float)) and v > 0]
    return min(vals) if vals else None


def passes_dealbreakers(
    entry: dict[str, Any],
    *,
    min_rent: float | None = None,
    max_rent: float | None = None,
    min_commute: float | None = None,
    max_commute: float | None = None,
    category_mins: dict[str, float] | None = None,
    has_live_camera: bool = False,
    hide_flood_risk: bool = False,
    hide_high_seismic: bool = False,
) -> tuple[bool, dict[str, Any]]:
    """Apply hard filters — Python mirror of `applyDealbreakers`.

    Returns (passes, debug_flags). `rent_unknown=True` when rent filter
    is active but the station's rent is missing — the frontend renders
    these dimmed; we surface the flag so MCP clients can do the same.
    """
    rent = _rent_value(entry.get("rent"))
    commute = _min_transit(entry.get("transit_minutes"))
    ratings = entry.get("ratings") or {}
    env = entry.get("environment") or {}
    has_cam = bool(entry.get("livecams"))

    rent_active = (min_rent is not None and min_rent > DEFAULT_FILTERS["min_rent"]) or (
        max_rent is not None and max_rent < DEFAULT_FILTERS["max_rent"]
    )

    if max_rent is not None and rent is not None and rent > max_rent:
        return False, {}
    if min_rent is not None and rent is not None and rent < min_rent:
        return False, {}
    if max_commute is not None and commute is not None and commute > max_commute:
        return False, {}
    if min_commute is not None and commute is not None and commute < min_commute:
        return False, {}

    for key, floor in (category_mins or {}).items():
        v = ratings.get(key)
        if v is not None and v < floor:
            return False, {}

    if hide_flood_risk:
        elev = env.get("elevation_m")
        if elev is not None and elev < 5:
            return False, {}
    if hide_high_seismic and env.get("seismic_risk_tier") == "very_high":
        return False, {}
    if has_live_camera and not has_cam:
        return False, {}

    return True, {"rent_unknown": rent_active and rent is None}
