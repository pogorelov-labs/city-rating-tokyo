#!/usr/bin/env python3
"""
Green area scraper — updates osm_pois records with green_area_sqm.

Runs the heavier `out geom` query for parks/gardens/nature_reserves
and calculates approximate area from bounding boxes.

Designed to run incrementally: skips stations that already have
green_area_sqm > 0 in NocoDB.

Usage:
  python3 scripts/scrapers/scrape-green-area.py [--delay 3] [--limit 50]

Run on VPS for reliability:
  docker run -d --name green-area --restart=no \
    -e NOCODB_API_URL=https://nocodb.pogorelov.dev \
    -e NOCODB_API_TOKEN=3hUf86bwbyw-OSJTlNwGOc1w8AcwrrgAkOuyIaTt \
    -v /tmp/scrape-green-area.py:/app/scraper.py:ro \
    -v /tmp/stations.json:/app/data/stations.json:ro \
    python:3.11-slim bash -c "pip install --quiet requests && python3 -u /app/scraper.py"
"""

import argparse
import math
import sys
import time
from datetime import date

import requests

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from utils import NocoDB, RateLimiter, load_stations

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

GREEN_AREA_QUERY = """
[out:json][timeout:45];
(
  way["leisure"~"park|garden|nature_reserve"](around:{radius},{lat},{lng});
  relation["leisure"~"park|garden|nature_reserve"](around:{radius},{lat},{lng});
  way["landuse"~"forest|religious"](around:{radius},{lat},{lng});
  relation["landuse"~"forest|religious"](around:{radius},{lat},{lng});
  way["natural"="wood"](around:{radius},{lat},{lng});
  relation["natural"="wood"](around:{radius},{lat},{lng});
);
out geom;
"""


def compute_area_sqm(elements):
    """Approximate total green area from OSM element bounding boxes."""
    total = 0.0
    seen_ids = set()
    for el in elements:
        eid = (el.get("type", ""), el.get("id", 0))
        if eid in seen_ids:
            continue
        seen_ids.add(eid)

        if "bounds" in el:
            b = el["bounds"]
            lat_mid = (b["maxlat"] + b["minlat"]) / 2.0
            lat_m = abs(b["maxlat"] - b["minlat"]) * 111_000
            lng_m = abs(b["maxlon"] - b["minlon"]) * 111_000 * math.cos(math.radians(lat_mid))
            total += lat_m * lng_m
        elif "geometry" in el:
            # Approximate from geometry points
            coords = el["geometry"]
            if len(coords) >= 3:
                # Shoelace formula approximation
                area = 0.0
                n = len(coords)
                for i in range(n):
                    j = (i + 1) % n
                    xi = coords[i]["lon"] * 111_000 * math.cos(math.radians(coords[i]["lat"]))
                    yi = coords[i]["lat"] * 111_000
                    xj = coords[j]["lon"] * 111_000 * math.cos(math.radians(coords[j]["lat"]))
                    yj = coords[j]["lat"] * 111_000
                    area += xi * yj - xj * yi
                total += abs(area) / 2.0

    return round(total, 0)


def query_green_area(lat, lng, radius=1000):
    """Query Overpass for green area geometry around a station."""
    query = GREEN_AREA_QUERY.format(lat=lat, lng=lng, radius=radius)
    for attempt in range(3):
        try:
            resp = requests.post(OVERPASS_URL, data={"data": query}, timeout=90)
            if resp.status_code == 429:
                wait = 60 * (attempt + 1)
                print(f"  Rate limited, waiting {wait}s...")
                time.sleep(wait)
                continue
            if resp.status_code >= 500:
                wait = 30 * (attempt + 1)
                print(f"  Server error {resp.status_code}, retrying in {wait}s...")
                time.sleep(wait)
                continue
            resp.raise_for_status()
            data = resp.json()
            elements = data.get("elements", [])
            area = compute_area_sqm(elements)
            large = sum(1 for e in elements if "bounds" in e and
                       abs(e["bounds"]["maxlat"] - e["bounds"]["minlat"]) * 111_000 > 200)
            return {
                "green_area_sqm": area,
                "large_park_count": large,
                "green_element_count": len(elements),
            }
        except requests.exceptions.Timeout:
            wait = 30 * (attempt + 1)
            print(f"  Timeout, retrying in {wait}s...")
            time.sleep(wait)
        except Exception as e:
            print(f"  Error: {e}")
            return None
    return None


def main():
    parser = argparse.ArgumentParser(description="Scrape green area data from OSM")
    parser.add_argument("--delay", type=float, default=3.0)
    parser.add_argument("--radius", type=int, default=1000)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    stations = load_stations()
    db = NocoDB("osm_pois")
    limiter = RateLimiter(args.delay)

    # Find stations that need area data
    existing = db.get_all_records()
    existing_map = {r["slug"]: r for r in existing if r.get("slug")}

    remaining = []
    for s in stations:
        rec = existing_map.get(s["slug"])
        if not rec:
            continue  # no POI record at all, skip
        area = rec.get("green_area_sqm")
        if area and float(area) > 0:
            continue  # already has area
        remaining.append((s, rec))

    if args.limit > 0:
        remaining = remaining[:args.limit]

    print(f"Total stations: {len(stations)}")
    print(f"With POI records: {len(existing_map)}")
    print(f"Need area scrape: {len(remaining)}")

    if args.dry_run:
        for s, _ in remaining[:5]:
            print(f"  Would query: {s['slug']}")
        return

    success = 0
    for i, (station, record) in enumerate(remaining):
        slug = station["slug"]
        print(f"[{i+1}/{len(remaining)}] {slug}...", end=" ", flush=True)

        limiter.wait()
        result = query_green_area(station["lat"], station["lng"], args.radius)

        if result is None:
            print("FAILED")
            continue

        # Update existing record
        try:
            db.update_record(record["Id"], {
                "green_area_sqm": result["green_area_sqm"],
            })
            print(f"area={result['green_area_sqm']:.0f}sqm ({result['green_element_count']} elements)")
            success += 1
        except Exception as e:
            print(f"NocoDB error: {e}")

    print(f"\nDone: {success}/{len(remaining)} updated")


if __name__ == "__main__":
    main()
