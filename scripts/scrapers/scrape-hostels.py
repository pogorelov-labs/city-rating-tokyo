#!/usr/bin/env python3
"""
Hostel/budget accommodation scraper using OSM Overpass API.
Queries for hostels, guest houses, and budget accommodation
around each station as a nightlife/backpacker area proxy.

Uses Overpass (same as OSM POI scraper) for consistency.

Usage: python3 scripts/scrapers/scrape-hostels.py [--delay 2] [--limit 10]
"""

import argparse
import sys
import time
from datetime import date

import requests

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from utils import NocoDB, RateLimiter, load_stations

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

QUERY_TEMPLATE = """
[out:json][timeout:30];
(
  node["tourism"~"hostel|guest_house"](around:{radius},{lat},{lng});
  way["tourism"~"hostel|guest_house"](around:{radius},{lat},{lng});
  node["tourism"="hotel"]["stars"~"^[12]$"](around:{radius},{lat},{lng});
  way["tourism"="hotel"]["stars"~"^[12]$"](around:{radius},{lat},{lng});
);
out count;
"""


def query_hostels(lat, lng, radius=1500):
    """Query Overpass for hostel/budget accommodation count."""
    query = QUERY_TEMPLATE.format(lat=lat, lng=lng, radius=radius)
    try:
        resp = requests.post(OVERPASS_URL, data={"data": query}, timeout=60)
        if resp.status_code == 429:
            print("  Rate limited, waiting 60s...")
            time.sleep(60)
            resp = requests.post(OVERPASS_URL, data={"data": query}, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        elements = data.get("elements", [])
        for el in elements:
            if el.get("type") == "count":
                return int(el.get("tags", {}).get("total", 0))
        return 0
    except Exception as e:
        print(f"  Error: {e}")
        return -1


def main():
    parser = argparse.ArgumentParser(description="Scrape hostel data from OSM")
    parser.add_argument("--delay", type=float, default=2.0)
    parser.add_argument("--radius", type=int, default=1500, help="Search radius in meters")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    stations = load_stations()
    db = NocoDB("hostels")
    limiter = RateLimiter(args.delay)
    today = date.today().isoformat()

    existing = db.get_existing_slugs()
    remaining = [s for s in stations if s["slug"] not in existing]
    if args.limit > 0:
        remaining = remaining[:args.limit]

    print(f"Total: {len(stations)}, Already: {len(existing)}, Remaining: {len(remaining)}")

    if args.dry_run:
        print("Dry run.")
        return

    success = 0
    for i, station in enumerate(remaining):
        slug = station["slug"]
        lat, lng = station["lat"], station["lng"]
        print(f"[{i+1}/{len(remaining)}] {slug}...", end=" ", flush=True)

        limiter.wait()
        count = query_hostels(lat, lng, args.radius)

        if count < 0:
            print("ERROR")
            continue

        record = {
            "slug": slug,
            "hostel_count": count,
            "avg_rating": 0,
            "source": "osm",
            "scraped_at": today,
        }

        try:
            db.upsert_record(record)
            success += 1
            print(f"hostels={count}")
        except Exception as e:
            print(f"DB ERROR: {e}")

    print(f"\nDone! {success} stations scraped.")


if __name__ == "__main__":
    main()
