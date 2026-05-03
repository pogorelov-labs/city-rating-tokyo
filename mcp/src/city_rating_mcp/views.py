"""Response shaping — compact, stable JSON views for tool outputs.

LLMs pay per token. Each view trims the datamart entry to the fields
actually useful in that context. Adding a new view? Keep field order
deterministic so MCP clients can diff results across calls.
"""

from __future__ import annotations

from typing import Any

from .scoring import _min_transit, _rent_value, composite_score


def _name(entry: dict[str, Any], locale: str) -> dict[str, str]:
    """Locale-aware primary/secondary names — mirrors stationDisplayName()."""
    name_en = entry.get("name_en", "")
    name_jp = entry.get("name_jp", "")
    name_ru = entry.get("name_ru")
    if locale == "ja":
        return {"primary": name_jp or name_en, "secondary": name_en}
    if locale == "ru" and name_ru:
        return {"primary": name_ru, "secondary": name_jp or name_en}
    return {"primary": name_en, "secondary": name_jp}


def search_row(entry: dict[str, Any], score: float | None, locale: str = "en", rent_unknown: bool = False) -> dict[str, Any]:
    """One row in a search/recommend list — compact."""
    names = _name(entry, locale)
    rent = _rent_value(entry.get("rent"))
    commute = _min_transit(entry.get("transit_minutes"))
    return {
        "slug": entry["slug"],
        "name": names["primary"],
        "name_jp": entry.get("name_jp"),
        "score": score,
        "ratings": entry.get("ratings") or None,
        "rent_1k_1ldk": rent,
        "min_transit_min": commute,
        "lines": [li.get("name_en") for li in (entry.get("lines") or [])],
        "ward": (entry.get("ward") or {}).get("ward_name"),
        "prefecture": entry.get("prefecture"),
        "lat": entry.get("lat"),
        "lng": entry.get("lng"),
        "has_livecam": bool(entry.get("livecams")),
        "rent_unknown": rent_unknown,
        "url": f"https://city-rating.pogorelov.dev/{locale}/station/{entry['slug']}"
        if locale != "en"
        else f"https://city-rating.pogorelov.dev/station/{entry['slug']}",
    }


def full_station(entry: dict[str, Any], locale: str = "en") -> dict[str, Any]:
    """Full station profile — used by get_station + compare_stations."""
    names = _name(entry, locale)
    ratings = entry.get("ratings") or {}
    desc = (entry.get("description") or {}).get(locale) if entry.get("description") else None
    return {
        "slug": entry["slug"],
        "name": names["primary"],
        "name_secondary": names["secondary"],
        "name_en": entry.get("name_en"),
        "name_jp": entry.get("name_jp"),
        "name_ru": entry.get("name_ru"),
        "lat": entry.get("lat"),
        "lng": entry.get("lng"),
        "prefecture": entry.get("prefecture"),
        "ward": entry.get("ward"),
        "lines": entry.get("lines") or [],
        "line_count": entry.get("line_count"),
        "ratings": ratings or None,
        "composite_score_default_weights": composite_score(ratings) if ratings else None,
        "confidence": entry.get("confidence"),
        "sources": entry.get("sources"),
        "data_date": entry.get("data_date"),
        "rent_avg": entry.get("rent"),
        "transit_minutes": entry.get("transit_minutes"),
        "last_train": entry.get("last_train"),
        "environment": entry.get("environment"),
        "description": desc,
        "livecams": entry.get("livecams"),
        "signals": {
            "food": entry.get("hotpepper", {}) | entry.get("osm_food", {}),
            "nightlife": entry.get("nightlife_signals"),
            "green": entry.get("green_signals"),
            "vibe": entry.get("vibe_signals"),
            "gym": entry.get("gym_signals"),
            "livability": entry.get("livability"),
            "passengers": entry.get("passengers"),
            "crime": entry.get("crime"),
        },
        "url": f"https://city-rating.pogorelov.dev/{locale}/station/{entry['slug']}"
        if locale != "en"
        else f"https://city-rating.pogorelov.dev/station/{entry['slug']}",
    }
