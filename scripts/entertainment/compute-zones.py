#!/usr/bin/env python3
"""Curated entertainment zones + family-filter proximity (CRTKY-192, ADR #6).

Zone-level geofence (center + radius), not venues. Curated from open
knowledge (Wikipedia/Wikidata-verified coordinates), with OSM corroboration
counts recorded in the research notes:

  research/bangkok/notes/2026-10-13-redlight-crtky153.md  (Bangkok, 6 zones)
  research/notes/2026-10-13-redlight-crtky182.md          (Tokyo, 7 zones)

kind taxonomy (shared, owner-approved 2026-10-14):
  adult_entertainment  — family filter triggers
  club_district        — never triggers the filter
  afterwork_drinking   — never triggers the filter

Writes data/entertainment/zones.json + per-area flags:
  Tokyo:   data/entertainment/tokyo-station-flags.json  (station anchor in disc)
  Bangkok: data/entertainment/bangkok-area-flags.json   (district / area flags)

Output flags use the anchor-in-disc semantics (ADR #6: cell/area center inside
the disc). No score mixing: the flag feeds only the family-filter chip.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "data" / "entertainment"

NIGHTLIFE_ZONES: list[dict] = [
    # ── Bangkok (CRTKY-153) ──────────────────────────────────────────────
    {"city": "bangkok", "id": "soi-cowboy", "kind": "adult_entertainment",
     "lat": 13.7376, "lng": 100.5621, "radius_m": 250,
     "districts": ["watthana"], "wikidata": "Q1343629"},
    {"city": "bangkok", "id": "nana-plaza", "kind": "adult_entertainment",
     "lat": 13.7414, "lng": 100.5533, "radius_m": 250,
     "districts": ["khlong-toei"], "wikidata": "Q441839"},
    {"city": "bangkok", "id": "patpong", "kind": "adult_entertainment",
     "lat": 13.7286, "lng": 100.5329, "radius_m": 250,
     "districts": ["bang-rak"], "wikidata": "Q2057014"},
    {"city": "bangkok", "id": "huai-khwang-ratchada", "kind": "adult_entertainment",
     "lat": 13.7789, "lng": 100.5735, "radius_m": 450,
     "districts": ["din-daeng", "huai-khwang"], "wikidata": None},
    {"city": "bangkok", "id": "sukhumvit-soi-33", "kind": "adult_entertainment",
     "lat": 13.7332, "lng": 100.5682, "radius_m": 300,
     "districts": ["watthana"], "wikidata": None},
    {"city": "bangkok", "id": "rca", "kind": "club_district",
     "lat": 13.7498, "lng": 100.5759, "radius_m": 500,
     "districts": ["huai-khwang"], "wikidata": "Q6648577"},
    # ── Tokyo (CRTKY-182) ───────────────────────────────────────────────
    {"city": "tokyo", "id": "kabukicho", "kind": "adult_entertainment",
     "lat": 35.69536, "lng": 139.70291, "radius_m": 400,
     "districts": ["shinjuku"], "wikidata": "Q665216"},
    {"city": "tokyo", "id": "shinjuku-nichome", "kind": "adult_entertainment",
     "lat": 35.69143, "lng": 139.70622, "radius_m": 350,
     "districts": ["shinjuku"], "wikidata": "Q1420043"},
    {"city": "tokyo", "id": "roppongi", "kind": "club_district",
     "lat": 35.66365, "lng": 139.73123, "radius_m": 450,
     "districts": ["minato"], "wikidata": "Q265071"},
    {"city": "tokyo", "id": "ikebukuro-kitaguchi", "kind": "adult_entertainment",
     "lat": 35.73218, "lng": 139.71208, "radius_m": 450,
     "districts": ["toshima"], "wikidata": "Q542366"},
    {"city": "tokyo", "id": "kinshicho-minamiguchi", "kind": "adult_entertainment",
     "lat": 35.69485, "lng": 139.81480, "radius_m": 350,
     "districts": ["sumida"], "wikidata": "Q11650537"},
    {"city": "tokyo", "id": "ueno-ameyoko", "kind": "adult_entertainment",
     "lat": 35.70950, "lng": 139.77390, "radius_m": 450,
     "districts": ["taito"], "wikidata": "Q864815"},
    {"city": "tokyo", "id": "shimbashi-karasumori", "kind": "afterwork_drinking",
     "lat": 35.66600, "lng": 139.75710, "radius_m": 400,
     "districts": ["minato"], "wikidata": "Q1347299"},
]


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371000
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat/2)**2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def nearest_zones(lat: float, lng: float, zones: list[dict]) -> list[dict]:
    """Zones whose disc contains the point, with kind and distance."""
    hits = []
    for z in zones:
        d = haversine_m(lat, lng, z["lat"], z["lng"])
        if d <= z["radius_m"]:
            hits.append({"id": z["id"], "kind": z["kind"], "distance_m": round(d)})
    return hits


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    doc = {
        "_meta": {
            "description": "Curated entertainment zones (center + radius), zone-level. "
                           "Only adult_entertainment triggers the family filter (ADR #6).",
            "curated": "2026-10-13 (research waves); owner-approved 2026-10-14",
            "sources": "Wikipedia/Wikidata coordinates; OSM corroboration counts in the research notes",
        },
        "zones": NIGHTLIFE_ZONES,
    }
    (OUT_DIR / "zones.json").write_text(
        json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    # ── Tokyo: per-station flags ─────────────────────────────────────────
    tokyo_zones = [z for z in NIGHTLIFE_ZONES if z["city"] == "tokyo"]
    stations = json.loads((ROOT / "data" / "stations.json").read_text())
    t_flags: dict[str, dict] = {}
    for s in stations:
        hits = nearest_zones(float(s["lat"]), float(s["lng"]), tokyo_zones)
        if hits:
            t_flags[s["slug"]] = hits
    adult = [k for k, v in t_flags.items() if any(h["kind"] == "adult_entertainment" for h in v)]
    print(f"Tokyo: {len(t_flags)} stations in any zone, {len(adult)} in adult_entertainment")
    print(f"  adult_filter candidates: {adult}")
    (OUT_DIR / "tokyo-station-flags.json").write_text(
        json.dumps({"_meta": doc["_meta"], "stations": t_flags},
                   ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    # ── Bangkok: per-area + per-district flags ───────────────────────────
    bkk_zones = [z for z in NIGHTLIFE_ZONES if z["city"] == "bangkok"]
    areas_doc = json.loads((ROOT / "app" / "src" / "data" / "bangkok" / "stations.json").read_text())
    areas = areas_doc.get("areas", areas_doc)
    a_flags: dict[str, dict] = {}
    for a in areas:
        hits = nearest_zones(a["lat"], a["lng"], bkk_zones)
        if hits:
            a_flags[a["id"]] = hits
    adult_a = [k for k, v in a_flags.items() if any(h["kind"] == "adult_entertainment" for h in v)]
    print(f"Bangkok: {len(a_flags)} areas in any zone, {len(adult_a)} in adult_entertainment")
    print(f"  adult_filter candidates: {adult_a}")

    districts_doc = json.loads((ROOT / "app" / "src" / "data" / "bangkok" / "districts.json").read_text())
    districts = districts_doc.get("districts", districts_doc)
    d_flags: dict[str, dict] = {}
    for d in districts:
        hits = nearest_zones(d["lat"], d["lng"], bkk_zones)
        if hits:
            d_flags[d["slug"]] = hits
    (OUT_DIR / "bangkok-area-flags.json").write_text(
        json.dumps({"_meta": doc["_meta"], "areas": a_flags, "districts": d_flags},
                   ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"Bangkok districts (label point in zone): {list(d_flags)}")

    print(f"\nWrote {OUT_DIR.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
