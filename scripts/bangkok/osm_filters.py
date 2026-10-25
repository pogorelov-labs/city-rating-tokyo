"""Shared OSM selectors for Overpass and the offline Geofabrik extractor.

A selector is (element type, tag key, exact values), with None meaning key
existence. Keep query rendering here so the two acquisition paths cannot drift.
"""
from __future__ import annotations

Selector = tuple[str, str, tuple[str, ...] | None]

POI_FILTERS: dict[str, tuple[Selector, ...]] = {
    "pois_food": (
        ("nwr", "amenity", ("restaurant", "cafe", "fast_food", "food_court", "ice_cream")),
        ("nwr", "shop", ("bakery", "coffee", "pastry")),
    ),
    "pois_nightlife": (
        ("nwr", "amenity", ("bar", "pub", "nightclub", "biergarten", "karaoke_box")),
        ("nwr", "tourism", ("hostel",)),
    ),
    "pois_essentials": (
        ("nwr", "shop", ("supermarket", "convenience", "chemist", "laundry", "dry_cleaning", "greengrocer", "mall", "department_store")),
        ("nwr", "amenity", ("pharmacy", "clinic", "doctors", "dentist", "hospital", "bank", "post_office", "school", "kindergarten", "marketplace")),
    ),
    "pois_sports": (
        ("nwr", "leisure", ("fitness_centre", "sports_centre", "swimming_pool", "stadium", "fitness_station")),
    ),
    "pois_culture": (
        ("nwr", "amenity", ("theatre", "cinema", "arts_centre", "library", "place_of_worship")),
        ("nwr", "tourism", ("museum", "gallery", "attraction")),
        ("nwr", "shop", ("books", "music", "art", "antiques", "second_hand", "musical_instrument", "craft")),
        ("nwr", "historic", None),
        ("way", "highway", ("pedestrian",)),
    ),
    "pois_transit_other": (
        ("nwr", "amenity", ("ferry_terminal",)),
        ("node", "highway", ("bus_stop",)),
    ),
}
GREEN_FILTERS: tuple[Selector, ...] = (
    ("nwr", "leisure", ("park", "garden", "nature_reserve")),
    ("nwr", "landuse", ("forest", "recreation_ground", "village_green")),
    ("nwr", "natural", ("wood",)),
)
STATION_FILTERS: tuple[Selector, ...] = (
    ("node", "railway", ("station",)),
    ("node", "public_transport", ("station",)),
    ("way", "railway", ("station",)),
    ("way", "public_transport", ("station",)),
)
OSM_FILTERS = {**POI_FILTERS, "green": GREEN_FILTERS, "rail_stations": STATION_FILTERS}


def matches(kind: str, tags: dict[str, str], selectors: tuple[Selector, ...]) -> bool:
    return any(
        (types == "nwr" or types == kind) and key in tags
        and (values is None or tags[key] in values)
        for types, key, values in selectors
    )


def query_body(selectors: tuple[Selector, ...]) -> str:
    parts = []
    for types, key, values in selectors:
        if values is None:
            tag = f'"{key}"'
        elif len(values) == 1:
            tag = f'"{key}"="{values[0]}"'
        else:
            tag = f'"{key}"~"^({"|".join(values)})$"'
        parts.append(f"{types}[{tag}];")
    return "".join(parts)
