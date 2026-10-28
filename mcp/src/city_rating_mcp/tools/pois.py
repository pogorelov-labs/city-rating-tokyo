"""list_pois — count summaries for a station's signal sources.

The datamart already exposes counts (HotPepper restaurant totals, OSM POI
counts, livability counts). Raw place lists with names/addresses live in
NocoDB; we keep them out of the bundled MCP for now since they balloon
RAM and the LLM use case is "describe the area", not "list every izakaya".
If we add per-place lists later, do it via a separate `nocodb_query` tool
or a per-station JSON sidecar in `data/pois/<slug>.json`.
"""

from __future__ import annotations

from typing import Any

from ..data import Datamart

CATEGORY_FIELDS: dict[str, list[tuple[str, str]]] = {
    # (datamart_section, field) pairs aggregated under each category
    "food": [
        ("hotpepper", "total_count"),
        ("hotpepper", "izakaya_count"),
        ("hotpepper", "bar_count"),
        ("hotpepper", "dining_bar_count"),
        ("osm_food", "food_count"),
        ("osm_food", "convenience_store_count"),
    ],
    "nightlife": [
        ("nightlife_signals", "midnight_count"),
        ("nightlife_signals", "izakaya_count"),
        ("nightlife_signals", "bar_count"),
        ("nightlife_signals", "dining_bar_count"),
        ("nightlife_signals", "karaoke_count"),
        ("nightlife_signals", "nightclub_count"),
        ("nightlife_signals", "music_venue_count"),
        ("nightlife_signals", "hostel_count"),
        ("nightlife_signals", "nightlife_count"),
    ],
    "green": [
        ("green_signals", "green_count"),
        ("green_signals", "green_area_sqm"),
    ],
    "vibe": [
        ("vibe_signals", "cultural_venue_count"),
        ("vibe_signals", "pedestrian_street_count"),
    ],
    "gym": [
        ("gym_signals", "gym_count"),
    ],
    "essentials": [
        ("livability", "supermarket_count"),
        ("livability", "pharmacy_count"),
        ("livability", "clinic_count"),
        ("livability", "school_count"),
        ("livability", "kindergarten_count"),
        ("livability", "post_office_count"),
        ("livability", "bank_count"),
        ("livability", "laundry_count"),
        ("livability", "dentist_count"),
    ],
}


def list_pois(dm: Datamart, slug: str, category: str | None = None) -> dict[str, Any]:
    entry = dm.get(slug)
    if entry is None:
        raise ValueError(f"Station '{slug}' not found")
    if entry.get("_city") == "bangkok":
        fields = {"food": ["food"], "nightlife": ["nightlife"], "green": ["park_ha", "park_share"],
                  "vibe": ["culture", "temples"], "gym": ["sports"],
                  "essentials": ["essentials", "convenience", "markets"]}
        if category is not None and category not in fields:
            raise ValueError(f"Unknown category '{category}'")
        facts = entry.get("facts") or {}
        source_keys = {"food": "food", "nightlife": "nightlife", "green": "green",
                       "vibe": "vibe", "gym": "gym_sports", "essentials": "daily_essentials"}
        cats = [category] if category else list(fields)
        return {"slug": slug, "city": "bangkok", "unit": "district",
                "categories": {cat: {key: facts[key] for key in fields[cat] if key in facts}
                               for cat in cats},
                "sources": {cat: (entry.get("sources") or {}).get(source_keys[cat], []) for cat in cats},
                "caveat": "District-wide source counts and park-area measures, not station catchments."}
    cats = [category] if category else list(CATEGORY_FIELDS.keys())
    out: dict[str, dict[str, int | float]] = {}
    for cat in cats:
        if cat not in CATEGORY_FIELDS:
            raise ValueError(
                f"Unknown category '{cat}'. Valid: {', '.join(CATEGORY_FIELDS)}"
            )
        bucket: dict[str, int | float] = {}
        for section, field in CATEGORY_FIELDS[cat]:
            val = (entry.get(section) or {}).get(field)
            if val is not None:
                bucket[field] = val
        out[cat] = bucket
    return {"slug": slug, "categories": out}
