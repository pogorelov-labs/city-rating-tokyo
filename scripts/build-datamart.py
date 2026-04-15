#!/usr/bin/env python3
"""
Build per-station datamart JSON from all NocoDB tables + local data files.

Output: data/station-datamart.json — one entry per station with ALL available
signals for the description generation pipeline.

Usage:
    python3 scripts/build-datamart.py              # build full datamart
    python3 scripts/build-datamart.py --slug akabane  # single station (debug)
"""

import json
import sys
import os
import re
from pathlib import Path

# NocoDB config
NOCODB_URL = os.getenv("NOCODB_API_URL", "https://nocodb.pogorelov.dev")
NOCODB_TOKEN = os.getenv("NOCODB_API_TOKEN", "3hUf86bwbyw-OSJTlNwGOc1w8AcwrrgAkOuyIaTt")

# Table IDs
TABLES = {
    "hotpepper": "mfk9j2qoj2bkeoo",
    "osm_pois": "mnnuqtldvt4jxlj",
    "osm_extended": "mrpqu8o796e6xzk",
    "osm_livability": "m3vasnsm4y09xez",
    "station_crime": "mxwixub7d0q5i00",
    "passenger_counts": "m36bbxcv8t0asur",
    "station_wards": "m74rdmspn3trrqc",
    "station_elevation": "mkrugzx8z62hli4",
    "station_seismic": "mhtnqvmi1kwbth9",
    "computed_ratings": "mkp046vo42kj55w",
}

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
APP_DATA = ROOT / "app" / "src" / "data"


def fetch_all_records(table_id: str) -> dict[str, dict]:
    """Fetch all records from a NocoDB table, keyed by slug."""
    import requests

    records = {}
    offset = 0
    page_size = 200

    while True:
        url = f"{NOCODB_URL}/api/v2/tables/{table_id}/records?limit={page_size}&offset={offset}"
        resp = requests.get(url, headers={"xc-token": NOCODB_TOKEN})
        resp.raise_for_status()
        data = resp.json()

        for row in data.get("list", []):
            slug = row.get("slug") or row.get("Slug")
            if slug:
                # Strip NocoDB metadata
                fields = {k: v for k, v in row.items()
                          if k not in ("Id", "CreatedAt", "UpdatedAt", "id", "nc_order")}
                records[slug] = fields

        if len(data.get("list", [])) < page_size:
            break
        offset += page_size

    return records


def load_local_json(path: str) -> dict:
    """Load a local JSON file."""
    with open(path) as f:
        return json.load(f)


def build_datamart(single_slug: str | None = None):
    """Build the complete datamart."""

    print("Loading local data files...")
    stations = load_local_json(APP_DATA / "stations.json")
    stations_by_slug = {s["slug"]: s for s in stations}

    # Transit times
    transit_data = load_local_json(DATA_DIR / "transit-times.json")
    transit_times = transit_data.get("transit_times", {})

    # Rent averages (274 Suumo + 826 e-Stat = 1100 total)
    rent_data = load_local_json(APP_DATA / "rent-averages.json")

    # Environment data
    env_data = load_local_json(APP_DATA / "environment-data.json")

    # Line names (127 entries: id → {name_ja, name_en, operator, color, type})
    line_names = load_local_json(APP_DATA / "line-names.json")

    # Ward data (1493 entries: slug → {city_name, ward_name, prefecture_name})
    ward_data = load_local_json(APP_DATA / "ward-data.json")

    # Last trains (1483 entries: slug → {weekday, holiday, sources})
    last_trains = load_local_json(APP_DATA / "last-trains.json")

    # Demo ratings (for existing descriptions + computed scores)
    with open(APP_DATA / "demo-ratings.ts") as f:
        ts_content = f.read()

    # Extract which stations have existing descriptions
    desc_slugs = set(re.findall(
        r'description:\s*\{',
        ts_content,
    ))
    # More precise: find slugs with description field
    has_desc = set()
    for m in re.finditer(r"(?:^  |^  ')([a-z0-9-]+?)(?:')?:\s*\{.*?description:\s*\{", ts_content, re.MULTILINE | re.DOTALL):
        has_desc.add(m.group(1))

    print(f"  stations.json: {len(stations_by_slug)}")
    print(f"  transit-times: {len(transit_times)}")
    print(f"  rent-averages: {len(rent_data)} (Suumo + e-Stat)")
    print(f"  environment:   {len(env_data)}")
    print(f"  line-names:    {len(line_names)}")
    print(f"  ward-data:     {len(ward_data)}")
    print(f"  last-trains:   {len(last_trains)}")
    print(f"  has description: {len(has_desc)}")

    # Fetch NocoDB tables
    print("\nFetching NocoDB tables...")
    nocodb_data = {}
    for name, table_id in TABLES.items():
        print(f"  {name}...", end="", flush=True)
        nocodb_data[name] = fetch_all_records(table_id)
        print(f" {len(nocodb_data[name])} records")

    # Build per-station datamart
    print("\nBuilding datamart...")
    datamart = {}
    slugs = sorted(stations_by_slug.keys())

    if single_slug:
        slugs = [single_slug] if single_slug in stations_by_slug else []
        if not slugs:
            print(f"Slug '{single_slug}' not found!")
            return

    for slug in slugs:
        station = stations_by_slug[slug]

        # Resolve line IDs to rich LineInfo (name, operator, color, type)
        resolved_lines = []
        for lid in station.get("lines", []):
            info = line_names.get(lid)
            if info:
                resolved_lines.append({"id": lid, **info})

        entry = {
            # Identity
            "slug": slug,
            "name_en": station["name_en"],
            "name_jp": station["name_jp"],
            "lat": station["lat"],
            "lng": station["lng"],
            "line_count": station["line_count"],
            "lines": resolved_lines,  # resolved names + operators + types
            "prefecture": station["prefecture"],

            # Location context (ward_data has richer structure than NocoDB station_wards)
            "ward": ward_data.get(slug, nocodb_data["station_wards"].get(slug, {})),

            # Last train
            "last_train": last_trains.get(slug, {}),

            # Ratings (computed)
            "ratings": nocodb_data["computed_ratings"].get(slug, {}),

            # Food signals
            "hotpepper": nocodb_data["hotpepper"].get(slug, {}),
            "osm_food": {
                k: v for k, v in nocodb_data["osm_pois"].get(slug, {}).items()
                if k in ("food_count", "convenience_store_count")
            },

            # Nightlife signals
            "nightlife_signals": {
                **{k: v for k, v in nocodb_data["hotpepper"].get(slug, {}).items()
                   if k in ("midnight_count", "izakaya_count", "bar_count", "dining_bar_count")},
                **{k: v for k, v in nocodb_data["osm_extended"].get(slug, {}).items()
                   if k in ("karaoke_count", "nightclub_count", "hostel_count", "music_venue_count")},
                **{k: v for k, v in nocodb_data["osm_pois"].get(slug, {}).items()
                   if k in ("nightlife_count",)},
            },

            # Green / nature
            "green_signals": {
                k: v for k, v in nocodb_data["osm_pois"].get(slug, {}).items()
                if k in ("green_count", "green_area_sqm")
            },

            # Vibe / culture
            "vibe_signals": {
                k: v for k, v in nocodb_data["osm_extended"].get(slug, {}).items()
                if k in ("cultural_venue_count", "pedestrian_street_count")
            },

            # Gym / sports
            "gym_signals": {
                "gym_count": nocodb_data["osm_pois"].get(slug, {}).get("gym_count", 0),
            },

            # Daily essentials
            "livability": nocodb_data["osm_livability"].get(slug, {}),

            # Safety / crime
            "crime": nocodb_data["station_crime"].get(slug, {}),

            # Transport
            "passengers": nocodb_data["passenger_counts"].get(slug, {}),
            "transit_minutes": transit_times.get(slug, {}),

            # Rent
            "rent": rent_data.get(slug, {}),

            # Environment
            "environment": env_data.get(slug, {}),

            # Metadata
            "has_existing_description": slug in has_desc,
        }

        # Clean: remove NocoDB metadata fields
        for section in entry.values():
            if isinstance(section, dict):
                for key in ["slug", "scraped_at", "CreatedAt", "UpdatedAt", "source", "computed_at"]:
                    section.pop(key, None)

        datamart[slug] = entry

    # Compute composite scores for ordering
    for slug, entry in datamart.items():
        r = entry.get("ratings", {})
        if r:
            vals = [r.get(k, 5) for k in ["food", "nightlife", "transport", "rent", "safety", "green", "gym_sports", "vibe", "crowd"]]
            entry["composite_score"] = round(sum(vals) / len(vals), 1) if vals else 0
        else:
            entry["composite_score"] = 0

    # Sort by composite score descending
    sorted_slugs = sorted(datamart.keys(), key=lambda s: datamart[s].get("composite_score", 0), reverse=True)

    output = {
        "metadata": {
            "total_stations": len(datamart),
            "with_descriptions": sum(1 for e in datamart.values() if e["has_existing_description"]),
            "without_descriptions": sum(1 for e in datamart.values() if not e["has_existing_description"]),
        },
        "generation_order": sorted_slugs,
        "stations": datamart,
    }

    if single_slug:
        print(json.dumps(output["stations"][single_slug], indent=2, ensure_ascii=False))
    else:
        out_path = DATA_DIR / "station-datamart.json"
        with open(out_path, "w") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        print(f"\n✓ Wrote {out_path} ({len(datamart)} stations)")
        print(f"  With descriptions: {output['metadata']['with_descriptions']}")
        print(f"  Need generation:   {output['metadata']['without_descriptions']}")
        print(f"  Top 5 by score:    {sorted_slugs[:5]}")


# Simple score computation (avoid importing from app)
class scoring_utils:
    @staticmethod
    def compute_score(ratings):
        return 0

if __name__ == "__main__":
    slug = None
    if "--slug" in sys.argv:
        idx = sys.argv.index("--slug")
        if idx + 1 < len(sys.argv):
            slug = sys.argv[idx + 1]
    build_datamart(slug)
