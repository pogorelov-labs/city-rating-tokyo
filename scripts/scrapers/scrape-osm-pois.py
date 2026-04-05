#!/usr/bin/env python3
"""
OSM/Overpass POI scraper for city-rating stations.
Queries Overpass API for food, nightlife, green, gym POI counts
around each station and stores results in NocoDB.

Covers 4 rating categories: food, nightlife, green, gym_sports

Usage: python3 scripts/scrapers/scrape-osm-pois.py [--delay 2] [--radius 800] [--dry-run]
"""

import argparse
import sys
import time
from datetime import date

import requests

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from utils import NocoDB, RateLimiter, load_stations

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# Overpass QL query template — single query per station, returns counts for all categories.
# Uses `out count` for fast counting without downloading full geometry.
QUERY_TEMPLATE = """
[out:json][timeout:30];
(
  // Food: restaurants, cafes, fast food
  node["amenity"~"restaurant|cafe|fast_food"](around:{food_r},{lat},{lng});
  way["amenity"~"restaurant|cafe|fast_food"](around:{food_r},{lat},{lng});
);
out count;

(
  // Nightlife: bars, pubs, nightclubs
  node["amenity"~"bar|pub|nightclub"](around:{food_r},{lat},{lng});
  way["amenity"~"bar|pub|nightclub"](around:{food_r},{lat},{lng});
);
out count;

(
  // Green: parks, gardens, nature reserves (ways/relations for area calc)
  way["leisure"~"park|garden|nature_reserve"](around:{green_r},{lat},{lng});
  relation["leisure"~"park|garden|nature_reserve"](around:{green_r},{lat},{lng});
);
out count;

(
  // Gym/Sports: fitness centres, sports centres, swimming pools
  node["leisure"~"fitness_centre|sports_centre|swimming_pool"](around:{green_r},{lat},{lng});
  way["leisure"~"fitness_centre|sports_centre|swimming_pool"](around:{green_r},{lat},{lng});
);
out count;

(
  // Convenience stores (useful signal for urban density)
  node["shop"="convenience"](around:{food_r},{lat},{lng});
);
out count;
"""

# Separate query for green area calculation (needs geometry)
GREEN_AREA_QUERY = """
[out:json][timeout:30];
(
  way["leisure"~"park|garden|nature_reserve"](around:{radius},{lat},{lng});
  relation["leisure"~"park|garden|nature_reserve"](around:{radius},{lat},{lng});
);
out geom;
"""


def query_poi_counts(lat, lng, food_radius=800, green_radius=1000):
    """Query Overpass for POI counts around a station."""
    query = QUERY_TEMPLATE.format(
        lat=lat, lng=lng,
        food_r=food_radius,
        green_r=green_radius,
    )
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
            break
        except requests.exceptions.Timeout:
            wait = 30 * (attempt + 1)
            print(f"  Timeout, retrying in {wait}s...")
            time.sleep(wait)
            continue
        except Exception as e:
            print(f"  Error querying Overpass: {e}")
            return None
    else:
        print("  Failed after 3 retries")
        return None

    # Parse the 5 count results from the response
    # Overpass returns elements array; `out count` produces a single element with tags.total
    elements = data.get("elements", [])

    counts = []
    for el in elements:
        if el.get("type") == "count":
            total = int(el.get("tags", {}).get("total", 0))
            counts.append(total)

    if len(counts) < 5:
        # Pad missing counts with 0
        counts.extend([0] * (5 - len(counts)))

    return {
        "food_count": counts[0],
        "nightlife_count": counts[1],
        "green_count": counts[2],
        "gym_count": counts[3],
        "convenience_store_count": counts[4],
    }


def query_green_area(lat: float, lng: float, radius: int = 1000) -> float:
    """Query Overpass for total green area (sqm) around a station.
    This is a heavier query, so only run when needed."""
    query = GREEN_AREA_QUERY.format(lat=lat, lng=lng, radius=radius)
    try:
        resp = requests.post(OVERPASS_URL, data={"data": query}, timeout=60)
        if resp.status_code == 429:
            time.sleep(60)
            resp = requests.post(OVERPASS_URL, data={"data": query}, timeout=60)
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return 0.0

    # Approximate area from bounding boxes of returned ways
    total_area = 0.0
    for el in data.get("elements", []):
        if "bounds" in el:
            b = el["bounds"]
            # Rough area in sqm using lat/lng bounds
            lat_diff = abs(b["maxlat"] - b["minlat"]) * 111_000
            lng_diff = abs(b["maxlon"] - b["minlon"]) * 111_000 * 0.82  # cos(35.7°) ≈ 0.82
            total_area += lat_diff * lng_diff

    return round(total_area, 0)


def main():
    parser = argparse.ArgumentParser(description="Scrape OSM POI data for stations")
    parser.add_argument("--delay", type=float, default=2.0, help="Delay between requests (seconds)")
    parser.add_argument("--radius", type=int, default=800, help="Search radius for food/nightlife (meters)")
    parser.add_argument("--green-radius", type=int, default=1000, help="Search radius for green/gym (meters)")
    parser.add_argument("--dry-run", action="store_true", help="Print queries without executing")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of stations (0=all)")
    parser.add_argument("--skip-area", action="store_true", help="Skip green area calculation (faster)")
    args = parser.parse_args()

    stations = load_stations()
    db = NocoDB("osm_pois")
    limiter = RateLimiter(args.delay)
    today = date.today().isoformat()

    # Get already-scraped stations
    existing = db.get_existing_slugs()
    remaining = [s for s in stations if s["slug"] not in existing]

    if args.limit > 0:
        remaining = remaining[:args.limit]

    print(f"Total stations: {len(stations)}")
    print(f"Already scraped: {len(existing)}")
    print(f"Remaining: {len(remaining)}")

    if args.dry_run:
        print("Dry run — not executing queries.")
        for s in remaining[:3]:
            print(f"  Would query: {s['slug']} ({s['lat']}, {s['lng']})")
        return

    success = 0
    errors = 0
    for i, station in enumerate(remaining):
        slug = station["slug"]
        lat, lng = station["lat"], station["lng"]
        print(f"[{i+1}/{len(remaining)}] {slug} ({lat:.4f}, {lng:.4f})...", end=" ", flush=True)

        limiter.wait()
        counts = query_poi_counts(lat, lng, args.radius, args.green_radius)
        if counts is None:
            print("ERROR")
            errors += 1
            continue

        # Green area (optional, slower)
        green_area = 0.0
        if not args.skip_area and counts["green_count"] > 0:
            limiter.wait()
            green_area = query_green_area(lat, lng, args.green_radius)

        record = {
            "slug": slug,
            **counts,
            "green_area_sqm": green_area,
            "scraped_at": today,
        }

        try:
            db.upsert_record(record)
            success += 1
            print(f"food={counts['food_count']} night={counts['nightlife_count']} "
                  f"green={counts['green_count']}({green_area:.0f}m²) gym={counts['gym_count']}")
        except Exception as e:
            print(f"DB ERROR: {e}")
            errors += 1

    print(f"\nDone! Success: {success}, Errors: {errors}")


if __name__ == "__main__":
    main()
