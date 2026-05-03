"""search_stations — top-N by weighted composite under hard filters."""

from __future__ import annotations

from typing import Any

from ..data import Datamart
from ..scoring import DEFAULT_WEIGHTS, composite_score, passes_dealbreakers
from ..views import search_row


def search_stations(
    dm: Datamart,
    *,
    weights: dict[str, float] | None = None,
    min_rent: float | None = None,
    max_rent: float | None = None,
    min_commute: float | None = None,
    max_commute: float | None = None,
    category_mins: dict[str, float] | None = None,
    has_live_camera: bool = False,
    hide_flood_risk: bool = False,
    hide_high_seismic: bool = False,
    locale: str = "en",
    limit: int = 20,
) -> dict[str, Any]:
    """Return top-N stations sorted by weighted composite score.

    Mirrors the homepage ranking: composite score under user-tunable weights,
    hard dealbreakers as binary filters. Same defaults as the frontend
    (DEFAULT_WEIGHTS / DEFAULT_FILTERS) — see app/src/lib/types.ts.
    """
    w = {**DEFAULT_WEIGHTS, **(weights or {})}
    rows: list[tuple[float, dict[str, Any], dict[str, Any]]] = []

    for entry in dm.all():
        ok, flags = passes_dealbreakers(
            entry,
            min_rent=min_rent,
            max_rent=max_rent,
            min_commute=min_commute,
            max_commute=max_commute,
            category_mins=category_mins,
            has_live_camera=has_live_camera,
            hide_flood_risk=hide_flood_risk,
            hide_high_seismic=hide_high_seismic,
        )
        if not ok:
            continue
        score = composite_score(entry.get("ratings"), w)
        if score is None:
            continue
        rows.append((score, entry, flags))

    rows.sort(key=lambda r: r[0], reverse=True)
    top = rows[: max(1, min(limit, 200))]

    return {
        "total_matches": len(rows),
        "returned": len(top),
        "weights": w,
        "results": [
            search_row(entry, score, locale=locale, rent_unknown=flags.get("rent_unknown", False))
            for score, entry, flags in top
        ],
    }
