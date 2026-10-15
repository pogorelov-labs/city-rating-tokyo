"""Shared rating primitives; stdlib only, with city policy kept at call sites.

Hand-maintained (not generated). Python's round-to-even, input order and
pre-transform tie grouping are part of the existing scoring contract.
"""
from bisect import bisect_right
from collections.abc import Callable, Mapping
from typing import Literal


def midpoint_percentile(
    values: Mapping[str, float], invert: bool = False,
    *, pre: Callable[[float], float] | None = None,
) -> dict[str, int]:
    """Midpoint ranks → 1..10; singleton → 1 (10 inverted), all tied → 6.

    Tokyo passes log1p explicitly; Bangkok's already aggregated signals do
    not. Transform before grouping: even a monotonic transform can collapse
    adjacent floating-point values into a tie. No missing-value filtering.
    """
    if not values:
        return {}
    transformed = {key: pre(value) for key, value in values.items()} if pre else values
    ordered = sorted(transformed.values())
    n = len(ordered)
    midpoint = {}
    i = 0
    while i < n:
        j = bisect_right(ordered, ordered[i])
        midpoint[ordered[i]] = (i + j - 1) / 2.0
        i = j
    out = {}
    for key, value in transformed.items():
        pct = midpoint[value] / max(n - 1, 1)
        if invert:
            pct = 1.0 - pct
        out[key] = max(1, min(10, round(pct * 9 + 1)))
    return out


def rent_to_affordability(price: float | None, floor: float, ceiling: float) -> int | None:
    """Linear floor→10 / ceiling→1; nonpositive or absent rent stays unknown."""
    if not price or price <= 0:
        return None
    t = max(0.0, min(1.0, (price - floor) / (ceiling - floor)))
    return max(1, min(10, round(10 - 9 * t)))


def percentile_anchors(
    scores: list[float], *, empty: Mapping[str, float] | None = None,
) -> dict[str, float]:
    """Index-based p5/p50/p95, not interpolated percentiles.

    MCP supplies an empty fallback. Bangkok historically requires a nonempty
    population and raises IndexError otherwise; preserve that default.
    """
    if not scores and empty is not None:
        return dict(empty)
    ordered = sorted(scores)
    n = len(ordered)
    return {name: ordered[max(0, min(n - 1, int(n * pct)))]
            for name, pct in (("p5", .05), ("p50", .5), ("p95", .95))}


def two_source_confidence(
    a_ok: bool, b_ok: bool, *, sources: tuple[str, str],
    policy: Literal['symmetric', 'primary_required'],
) -> tuple[str, list[str]]:
    """Preserved policies, not a new definition of evidence quality.

    symmetric (Bangkok): either source qualifies as moderate; neither keeps
    both source names with estimate. primary_required (Tokyo food): without
    the primary source, estimate and an empty list even when B contributes.
    Thresholds/zero/missing handling belong to the existing consumers.
    """
    if policy not in ('symmetric', 'primary_required'):
        raise ValueError(f'Unknown confidence policy: {policy}')
    if a_ok and b_ok:
        return 'strong', list(sources)
    if a_ok:
        return 'moderate', [sources[0]]
    if policy == 'symmetric':
        if b_ok:
            return 'moderate', [sources[1]]
        return 'estimate', list(sources)
    return 'estimate', []
