"""get_station + compare_stations + lookup helpers."""

from __future__ import annotations

from typing import Any

from ..data import Datamart
from ..views import full_station


def get_station(dm: Datamart, slug: str, locale: str = "en") -> dict[str, Any]:
    entry = dm.get(slug)
    if entry is None:
        # Fuzzy hint: a typo on a known slug is the common failure mode
        candidates = [s for s in dm.slugs() if slug.lower() in s][:5]
        raise ValueError(
            f"Station '{slug}' not found. "
            + (f"Did you mean one of: {', '.join(candidates)}?" if candidates else "")
        )
    return full_station(entry, locale=locale)


def compare_stations(dm: Datamart, slugs: list[str], locale: str = "en") -> dict[str, Any]:
    if len(slugs) < 2:
        raise ValueError("compare_stations needs at least 2 slugs")
    if len(slugs) > 5:
        raise ValueError("compare_stations supports at most 5 slugs (UI parity)")
    profiles = []
    missing: list[str] = []
    for s in slugs:
        entry = dm.get(s)
        if entry is None:
            missing.append(s)
            continue
        profiles.append(full_station(entry, locale=locale))
    return {"profiles": profiles, "missing": missing}
