"""Pure-Python rating math for the Bangkok district layer.

Kept free of numpy/shapely so `scripts/bangkok/test_bangkok.py` can import it
in the lightweight CI schema job (which only installs pytest + pydantic).

The normalisation deliberately mirrors `scripts/compute-ratings.py` (Tokyo):
percentile rank with midpoint ties → 1..10. What differs is the *unit*: a
Bangkok raw signal is already a resident-weighted average of log counts over
a 200 m sample grid inside the district, so no extra log is applied here.
"""
from __future__ import annotations

import math
from bisect import bisect_right

# THB/month → affordability. ฿8k (cheapest khet corridors) → 10, ฿38k
# (Pathum Wan / Watthana luxury stock) → 1. Linear, like Tokyo's ¥80k→¥300k.
RENT_FLOOR_THB = 8_000
RENT_CEILING_THB = 38_000

CONFIDENCE_LEVELS = ("strong", "moderate", "estimate", "editorial")


def percentile_normalize(values: dict[str, float], invert: bool = False) -> dict[str, int]:
    """Midpoint-rank percentile → integer rating 1..10 (Tokyo CRTKY-64/65 rule).

    Ties share the average of their lowest and highest rank, so a cluster of
    equal values straddles a rating boundary instead of all rounding down.
    """
    if not values:
        return {}
    ordered = sorted(values.values())
    n = len(ordered)
    midpoint: dict[float, float] = {}
    i = 0
    while i < n:
        j = bisect_right(ordered, ordered[i])
        midpoint[ordered[i]] = (i + j - 1) / 2.0
        i = j
    out: dict[str, int] = {}
    for key, value in values.items():
        pct = midpoint[value] / max(n - 1, 1)
        if invert:
            pct = 1.0 - pct
        out[key] = max(1, min(10, round(pct * 9 + 1)))
    return out


def weighted_percentile_normalize(
    values: list[float], weights: list[float], invert: bool = False
) -> list[int]:
    """Resident-weighted version of `percentile_normalize` for the 200 m grid.

    Each cell occupies a slice of the cumulative resident weight, so a block
    rates 8 when it beats ~75 % of *where people live*, not of all land —
    paddy fields and river water (weight 0.1) barely move the scale. Ties
    share their group's midpoint; the lowest group maps to 1 and the highest
    to 10, like the unweighted rule.
    """
    n = len(values)
    if n == 0:
        return []
    order = sorted(range(n), key=lambda i: values[i])
    centres: list[tuple[list[int], float]] = []
    acc = 0.0
    i = 0
    while i < n:
        j = i
        group_w = 0.0
        while j < n and values[order[j]] == values[order[i]]:
            group_w += weights[order[j]]
            j += 1
        centres.append((order[i:j], acc + group_w / 2))
        acc += group_w
        i = j
    lo, hi = centres[0][1], centres[-1][1]
    out = [0] * n
    for members, centre in centres:
        pct = (centre - lo) / (hi - lo) if hi > lo else 0.5
        if invert:
            pct = 1.0 - pct
        rating = max(1, min(10, round(pct * 9 + 1)))
        for k in members:
            out[k] = rating
    return out


def weighted_anchors(scores: list[float], weights: list[float]) -> dict[str, float]:
    """p5 / p50 / p95 of `scores` by cumulative weight (grid composite palette)."""
    pairs = sorted(zip(scores, weights))
    total = sum(w for _, w in pairs)
    out: dict[str, float] = {}
    for name, p in (("p5", 0.05), ("p50", 0.5), ("p95", 0.95)):
        acc = 0.0
        pick = pairs[-1][0]
        for score, w in pairs:
            acc += w
            if acc >= total * p:
                pick = score
                break
        out[name] = pick
    return out


def rent_to_affordability(rent_thb: float | None) -> int | None:
    """Linear ฿8k→10 … ฿38k→1, clamped. None for missing rent."""
    if not rent_thb or rent_thb <= 0:
        return None
    t = (rent_thb - RENT_FLOOR_THB) / (RENT_CEILING_THB - RENT_FLOOR_THB)
    t = max(0.0, min(1.0, t))
    return max(1, min(10, round(10 - 9 * t)))


def weighted_median(values: list[float], weights: list[float]) -> float:
    """Median of `values` where each carries `weights[i]` (resident weighting)."""
    if not values:
        raise ValueError("weighted_median of empty sequence")
    pairs = sorted(zip(values, weights))
    total = sum(w for _, w in pairs)
    acc = 0.0
    for value, weight in pairs:
        acc += weight
        if acc >= total / 2:
            return value
    return pairs[-1][0]


def median_int(values: list[int]) -> int:
    """Integer median used for the per-category 'city norm' tick."""
    s = sorted(values)
    n = len(s)
    mid = s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2
    return int(math.floor(mid + 0.5))


def composite(ratings: dict[str, int], weights: dict[str, float]) -> float:
    """Same weighted mean as app/src/lib/scoring.ts calculateWeightedScore."""
    total = sum(w for w in weights.values() if w > 0)
    if total == 0:
        return 0.0
    s = sum(ratings[k] * w for k, w in weights.items() if w > 0)
    return round(s / total * 10) / 10


def anchors(scores: list[float]) -> dict[str, float]:
    """p5 / p50 / p95 with the same index rule as computeCompositeAnchors()."""
    s = sorted(scores)
    n = len(s)

    def pick(p: float) -> float:
        return s[min(n - 1, max(0, math.floor(n * p)))]

    return {"p5": pick(0.05), "p50": pick(0.5), "p95": pick(0.95)}


def two_source_confidence(overture_ok: bool, osm_ok: bool) -> tuple[str, list[str]]:
    """Tokyo's rule, applied to Bangkok's two POI sources.

    strong   — both OSM and Overture map the category well in this district
    moderate — only one of them does
    estimate — neither reaches its threshold (formula over sparse data)
    """
    if overture_ok and osm_ok:
        return "strong", ["overture", "osm"]
    if overture_ok:
        return "moderate", ["overture"]
    if osm_ok:
        return "moderate", ["osm"]
    return "estimate", ["overture", "osm"]
