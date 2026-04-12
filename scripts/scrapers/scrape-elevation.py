#!/usr/bin/env python3
"""
Scrape station elevations from Open-Elevation API.
Bulk POST endpoint: up to 1000 coordinates per request.
All 1493 stations in 2 requests — zero rate limit concerns.

Output: NocoDB table station_elevation (mkrugzx8z62hli4)

Usage on VPS:
  docker run -d --name elevation --restart=no \
    -e NOCODB_API_URL=https://nocodb.pogorelov.dev \
    -e NOCODB_API_TOKEN=<token> \
    -v /tmp/scrape-elevation.py:/app/scraper.py:ro \
    -v /tmp/green-data:/data:ro \
    python:3.11-slim bash -c "pip install --quiet requests && python3 -u /app/scraper.py"
"""

import json
import os
import sys
import time
import requests
from datetime import datetime, timezone

# ---------- config ----------
NOCODB_URL = os.environ.get("NOCODB_API_URL", "https://nocodb.pogorelov.dev")
NOCODB_TOKEN = os.environ.get("NOCODB_API_TOKEN", "")
TABLE_ID = "mkrugzx8z62hli4"  # station_elevation
ELEVATION_API = "https://api.open-elevation.com/api/v1/lookup"
BATCH_SIZE = 500  # safe batch (API allows 1000, use 500 for reliability)
STATION_FILE = "/data/stations.json"  # VPS mount path

# ---------- helpers ----------
def load_stations():
    """Load stations from mounted JSON."""
    paths = [STATION_FILE, "data/stations.json", "app/src/data/stations.json"]
    for p in paths:
        if os.path.exists(p):
            with open(p) as f:
                return json.load(f)
    print("ERROR: stations.json not found in any known path")
    sys.exit(1)


def nocodb_headers():
    return {"xc-token": NOCODB_TOKEN, "Content-Type": "application/json"}


def get_existing_slugs():
    """Get slugs already in NocoDB to support incremental runs."""
    slugs = set()
    offset = 0
    while True:
        url = f"{NOCODB_URL}/api/v2/tables/{TABLE_ID}/records?fields=slug&limit=1000&offset={offset}"
        r = requests.get(url, headers=nocodb_headers())
        r.raise_for_status()
        data = r.json()
        records = data.get("list", [])
        if not records:
            break
        for rec in records:
            slugs.add(rec.get("slug"))
        offset += len(records)
    return slugs


def fetch_elevations(locations):
    """POST to Open-Elevation API. Returns list of {latitude, longitude, elevation}."""
    payload = {"locations": [{"latitude": loc[0], "longitude": loc[1]} for loc in locations]}
    for attempt in range(3):
        try:
            r = requests.post(ELEVATION_API, json=payload, timeout=120)
            r.raise_for_status()
            return r.json().get("results", [])
        except Exception as e:
            print(f"  Attempt {attempt+1}/3 failed: {e}")
            if attempt < 2:
                time.sleep(5 * (attempt + 1))
    return None


def write_to_nocodb(records):
    """Bulk insert records to NocoDB."""
    url = f"{NOCODB_URL}/api/v2/tables/{TABLE_ID}/records"
    # NocoDB bulk insert max ~100 at a time
    for i in range(0, len(records), 100):
        batch = records[i:i+100]
        r = requests.post(url, headers=nocodb_headers(), json=batch)
        r.raise_for_status()
        print(f"  Inserted {min(i+100, len(records))}/{len(records)} records")


# ---------- main ----------
def main():
    print("=== Open-Elevation Scraper ===")
    print(f"NocoDB: {NOCODB_URL}")
    print(f"Table: {TABLE_ID}")

    stations = load_stations()
    print(f"Loaded {len(stations)} stations")

    existing = get_existing_slugs()
    print(f"Already in NocoDB: {len(existing)} records")

    # Filter to new stations only
    to_scrape = [s for s in stations if s["slug"] not in existing]
    if not to_scrape:
        print("All stations already scraped. Done!")
        return

    print(f"Stations to scrape: {len(to_scrape)}")
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Process in batches
    all_records = []
    for batch_start in range(0, len(to_scrape), BATCH_SIZE):
        batch = to_scrape[batch_start:batch_start + BATCH_SIZE]
        batch_num = batch_start // BATCH_SIZE + 1
        total_batches = (len(to_scrape) + BATCH_SIZE - 1) // BATCH_SIZE
        print(f"\nBatch {batch_num}/{total_batches} ({len(batch)} stations)...")

        locations = [(s["lat"], s["lng"]) for s in batch]
        results = fetch_elevations(locations)

        if results is None:
            print(f"  FAILED batch {batch_num} — skipping")
            continue

        if len(results) != len(batch):
            print(f"  WARNING: got {len(results)} results for {len(batch)} stations")

        for i, (station, result) in enumerate(zip(batch, results)):
            elev = result.get("elevation")
            if elev is not None:
                all_records.append({
                    "slug": station["slug"],
                    "elevation_m": round(elev, 1),
                    "lat": station["lat"],
                    "lng": station["lng"],
                    "scraped_at": now,
                })

        print(f"  Got {len(results)} elevations (batch total: {len(all_records)})")
        time.sleep(2)  # be polite between batches

    if all_records:
        print(f"\nWriting {len(all_records)} records to NocoDB...")
        write_to_nocodb(all_records)

    print(f"\n=== Done! {len(all_records)} elevations scraped ===")

    # Quick stats
    if all_records:
        elevs = [r["elevation_m"] for r in all_records]
        print(f"  Min: {min(elevs)}m, Max: {max(elevs)}m, Avg: {sum(elevs)/len(elevs):.1f}m")


if __name__ == "__main__":
    main()
