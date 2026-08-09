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
    Returns: int count on success, or None on failure.

    Returns None (never 0) on error so the caller can skip the upsert rather
    than persisting a transient zero — the scraper is incremental, so a
    persisted 0 would never be retried and would permanently zero-rank the
    station's food/nightlife signal.
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

    # Retry with backoff — mirrors the pattern in scrape-osm-pois.py
    # (3 attempts, growing sleep on 429/5xx/timeout/network errors).
    for attempt in range(3):
        try:
            resp = requests.get(BASE_URL, params=params, timeout=15)
            if resp.status_code == 429:
                wait = 10 * (attempt + 1)
                print(f"  Rate limited, waiting {wait}s...")
                time.sleep(wait)
                continue
            if resp.status_code >= 500:
                wait = 5 * (attempt + 1)
                print(f"  Server error {resp.status_code}, retrying in {wait}s...")
                time.sleep(wait)
                continue
            resp.raise_for_status()
            data = resp.json()
            results = data.get("results", {})
            return int(results.get("results_available", 0))
        except requests.exceptions.Timeout:
            wait = 5 * (attempt + 1)
            print(f"  Timeout, retrying in {wait}s...")
            time.sleep(wait)
            continue
        except Exception as e:
            print(f"  API error (attempt {attempt+1}/3): {e}")
            if attempt < 2:
                time.sleep(5 * (attempt + 1))
                continue
    print("  Failed after 3 retries")
    return None


def query_all_categories(lat, lng, limiter):
    """Query all restaurant categories for a station.

    Returns a dict of counts, or None if any category query failed (so the
    caller can skip the upsert instead of persisting partial/zero data).
    """
    # Total restaurants
    limiter.wait()
    total = query_hotpepper(lat, lng, radius=3)
    if total is None:
        return None

    # Izakaya
    limiter.wait()
    izakaya = query_hotpepper(lat, lng, radius=3, genre=GENRE_IZAKAYA)
    if izakaya is None:
        return None

    # Bars
    limiter.wait()
    bar = query_hotpepper(lat, lng, radius=3, genre=GENRE_BAR)
    if bar is None:
        return None

    # Cafes
    limiter.wait()
    cafe = query_hotpepper(lat, lng, radius=3, genre=GENRE_CAFE)
    if cafe is None:
        return None

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
    skipped = 0
    for i, station in enumerate(remaining):
        slug = station["slug"]
        lat, lng = station["lat"], station["lng"]
        print(f"[{i+1}/{len(remaining)}] {slug}...", end=" ", flush=True)

        data = query_all_categories(lat, lng, limiter)

        if data is None:
            # Query failed after retries — do NOT persist a zero. The scraper
            # is incremental, so skipping means this station gets retried on
            # the next run rather than being permanently zero-ranked.
            print("SKIPPED (API error, will retry next run)")
            skipped += 1
            continue

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

    print(f"\nDone! Success: {success}, Errors: {errors}, Skipped: {skipped}")


if __name__ == "__main__":
    main()
