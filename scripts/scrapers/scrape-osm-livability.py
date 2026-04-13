#!/usr/bin/env python3
"""
OSM/Overpass livability scraper for city-rating stations.
Queries Overpass API for daily-essentials POI counts (supermarket, pharmacy,
clinic, school, kindergarten, post_office, bank, laundry, dentist)
around each station and stores results in NocoDB osm_livability table.

This scraper is incremental — it skips stations already in NocoDB.

Usage:
    python3 scripts/scrapers/scrape-osm-livability.py [--delay 2] [--radius 1000] [--dry-run]

VPS Docker:
    docker run -d --name livability --restart=no \
      -e NOCODB_API_URL=https://nocodb.pogorelov.dev \
      -e NOCODB_API_TOKEN=... \
      -v /tmp/scrape-osm-livability.py:/app/scraper.py:ro \
      -v /tmp/stations.json:/app/data/stations.json:ro \
      python:3.11-slim bash -c "pip install --quiet requests && python3 -u /app/scraper.py"
"""

import argparse
import sys
import time
from datetime import date

import requests

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from utils import NocoDB, RateLimiter, load_stations

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# Single query per station: 9 categories, each as a separate `out count` block.
QUERY_TEMPLATE = """
[out:json][timeout:60];

// 1. Supermarkets
(
  node["shop"="supermarket"](around:{r},{lat},{lng});
  way["shop"="supermarket"](around:{r},{lat},{lng});
);
out count;

// 2. Pharmacies
(
  node["amenity"="pharmacy"](around:{r},{lat},{lng});
  way["amenity"="pharmacy"](around:{r},{lat},{lng});
  node["shop"="chemist"](around:{r},{lat},{lng});
);
out count;

// 3. Clinics / doctors
(
  node["amenity"~"clinic|doctors"](around:{r},{lat},{lng});
  way["amenity"~"clinic|doctors"](around:{r},{lat},{lng});
);
out count;

// 4. Schools (primary + secondary)
(
  node["amenity"="school"](around:{r},{lat},{lng});
  way["amenity"="school"](around:{r},{lat},{lng});
);
out count;

// 5. Kindergartens
(
  node["amenity"="kindergarten"](around:{r},{lat},{lng});
  way["amenity"="kindergarten"](around:{r},{lat},{lng});
);
out count;

// 6. Post offices
(
  node["amenity"="post_office"](around:{r},{lat},{lng});
  way["amenity"="post_office"](around:{r},{lat},{lng});
);
out count;

// 7. Banks / ATMs
(
  node["amenity"~"bank|atm"](around:{r},{lat},{lng});
  way["amenity"~"bank|atm"](around:{r},{lat},{lng});
);
out count;

// 8. Laundry / dry cleaning
(
  node["shop"~"laundry|dry_cleaning"](around:{r},{lat},{lng});
  way["shop"~"laundry|dry_cleaning"](around:{r},{lat},{lng});
);
out count;

// 9. Dentists
(
  node["amenity"="dentist"](around:{r},{lat},{lng});
  way["amenity"="dentist"](around:{r},{lat},{lng});
  node["healthcare"="dentist"](around:{r},{lat},{lng});
);
out count;
"""

CATEGORIES = [
    "supermarket_count",
    "pharmacy_count",
    "clinic_count",
    "school_count",
    "kindergarten_count",
    "post_office_count",
    "bank_count",
    "laundry_count",
    "dentist_count",
]


def query_livability(lat: float, lng: float, radius: int = 1000) -> dict | None:
    """Query Overpass for livability POI counts around a station."""
    query = QUERY_TEMPLATE.format(lat=lat, lng=lng, r=radius)
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

    # Parse count results
    elements = data.get("elements", [])
    counts = []
    for el in elements:
        if el.get("type") == "count":
            total = int(el.get("tags", {}).get("total", 0))
            counts.append(total)

    if len(counts) < len(CATEGORIES):
        counts.extend([0] * (len(CATEGORIES) - len(counts)))

    return dict(zip(CATEGORIES, counts))


def main():
    parser = argparse.ArgumentParser(description="Scrape OSM livability data for stations")
    parser.add_argument("--delay", type=float, default=2.0, help="Delay between requests (seconds)")
    parser.add_argument("--radius", type=int, default=1000, help="Search radius (meters)")
    parser.add_argument("--dry-run", action="store_true", help="Print queries without executing")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of stations (0=all)")
    args = parser.parse_args()

    stations = load_stations()
    db = NocoDB("osm_livability")
    limiter = RateLimiter(args.delay)
    today = date.today().isoformat()

    # Incremental: skip already-scraped stations
    existing = db.get_existing_slugs()
    remaining = [s for s in stations if s["slug"] not in existing]

    if args.limit > 0:
        remaining = remaining[: args.limit]

    print(f"Total stations: {len(stations)}")
    print(f"Already scraped: {len(existing)}")
    print(f"Remaining: {len(remaining)}")

    if not remaining:
        print("All stations already scraped!")
        return

    if args.dry_run:
        print("Dry run — not executing queries.")
        for s in remaining[:5]:
            print(f"  Would query: {s['slug']} ({s['lat']}, {s['lng']})")
        return

    success = 0
    errors = 0
    for i, station in enumerate(remaining):
        slug = station["slug"]
        lat, lng = station["lat"], station["lng"]
        print(f"[{i + 1}/{len(remaining)}] {slug} ({lat:.4f}, {lng:.4f})...", end=" ", flush=True)

        limiter.wait()
        counts = query_livability(lat, lng, args.radius)
        if counts is None:
            print("ERROR")
            errors += 1
            continue

        record = {
            "slug": slug,
            **counts,
            "scraped_at": today,
        }

        try:
            db.upsert_record(record)
            success += 1
            summary = " ".join(f"{k.replace('_count', '')}={v}" for k, v in counts.items())
            print(summary)
        except Exception as e:
            print(f"DB ERROR: {e}")
            errors += 1

    print(f"\nDone! Success: {success}, Errors: {errors}")
    print(f"Total in NocoDB: {len(existing) + success}")


if __name__ == "__main__":
    main()
