#!/usr/bin/env python3
"""
HotPepper Gourmet API scraper for restaurant/izakaya/bar data.
Queries by lat/lng around each station and stores results in NocoDB.

Covers: food (quality signal), nightlife (izakaya/bar count)

API docs: https://webservice.recruit.co.jp/doc/hotpepper/reference.html
Free key registration: https://webservice.recruit.co.jp/register/

Usage:
  export HOTPEPPER_API_KEY=your_key_here
  python3 scripts/scrapers/scrape-hotpepper.py [--delay 1] [--limit 10]
"""

import argparse
import os
import sys
import time
from datetime import date

import requests

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from utils import NocoDB, RateLimiter, load_stations

API_KEY = os.environ.get("HOTPEPPER_API_KEY", "")
BASE_URL = "https://webservice.recruit.co.jp/hotpepper/gourmet/v1/"

# HotPepper genre codes for nightlife categories
GENRE_IZAKAYA = "G001"  # 居酒屋
GENRE_BAR = "G012"       # バー・カクテル
GENRE_CAFE = "G014"      # カフェ・スイーツ


def query_hotpepper(lat, lng, radius=3, genre=None):
    """
    Query HotPepper API for restaurants near a location.
    radius: 1=300m, 2=500m, 3=1000m, 4=2000m, 5=3000m
    Returns: (count, avg_rating)
    """
    params = {
        "key": API_KEY,
        "lat": lat,
        "lng": lng,
        "range": radius,
        "count": 1,  # We just need the count, not all results
        "format": "json",
    }
    if genre:
        params["genre"] = genre

    try:
        resp = requests.get(BASE_URL, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results", {})
        total = int(results.get("results_available", 0))
        return total
    except Exception as e:
        print(f"  API error: {e}")
        return 0


def query_all_categories(lat, lng, limiter):
    """Query all restaurant categories for a station."""
    # Total restaurants
    limiter.wait()
    total = query_hotpepper(lat, lng, radius=3)

    # Izakaya
    limiter.wait()
    izakaya = query_hotpepper(lat, lng, radius=3, genre=GENRE_IZAKAYA)

    # Bars
    limiter.wait()
    bar = query_hotpepper(lat, lng, radius=3, genre=GENRE_BAR)

    # Cafes
    limiter.wait()
    cafe = query_hotpepper(lat, lng, radius=3, genre=GENRE_CAFE)

    return {
        "total_count": total,
        "izakaya_count": izakaya,
        "bar_count": bar,
        "cafe_count": cafe,
    }


def main():
    parser = argparse.ArgumentParser(description="Scrape HotPepper restaurant data")
    parser.add_argument("--delay", type=float, default=0.5, help="Delay between requests (seconds)")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of stations (0=all)")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not API_KEY:
        print("ERROR: Set HOTPEPPER_API_KEY environment variable.")
        print("Register at: https://webservice.recruit.co.jp/register/")
        sys.exit(1)

    stations = load_stations()
    db = NocoDB("hotpepper")
    limiter = RateLimiter(args.delay)
    today = date.today().isoformat()

    existing = db.get_existing_slugs()
    remaining = [s for s in stations if s["slug"] not in existing]

    if args.limit > 0:
        remaining = remaining[:args.limit]

    print(f"Total stations: {len(stations)}")
    print(f"Already scraped: {len(existing)}")
    print(f"Remaining: {len(remaining)}")

    if args.dry_run:
        print("Dry run.")
        return

    success = 0
    errors = 0
    for i, station in enumerate(remaining):
        slug = station["slug"]
        lat, lng = station["lat"], station["lng"]
        print(f"[{i+1}/{len(remaining)}] {slug}...", end=" ", flush=True)

        data = query_all_categories(lat, lng, limiter)

        record = {
            "slug": slug,
            **data,
            "avg_rating": 0,  # HotPepper count endpoint doesn't give ratings
            "scraped_at": today,
        }

        try:
            db.upsert_record(record)
            success += 1
            print(f"total={data['total_count']} izakaya={data['izakaya_count']} "
                  f"bar={data['bar_count']} cafe={data['cafe_count']}")
        except Exception as e:
            print(f"DB ERROR: {e}")
            errors += 1

    print(f"\nDone! Success: {success}, Errors: {errors}")


if __name__ == "__main__":
    main()
