#!/usr/bin/env python3
"""
Scrape seismic hazard data from J-SHIS (National Research Institute for
Earth Science and Disaster Resilience) for all 1493 stations.

API: https://www.j-shis.bosai.go.jp/map/api/
Data: Probabilistic Seismic Hazard Maps (Y2024, AVR case, all earthquake types)

Key outputs per station:
  - prob_intensity_6_30yr: probability of JMA intensity ≥6.0 in 30 years (%)
  - prob_intensity_55_30yr: probability of JMA intensity ≥5.5 in 30 years (%)
  - prob_intensity_5_30yr: probability of JMA intensity ≥5.0 in 30 years (%)
  - max_velocity_30yr_p03: max ground velocity (cm/s) at 3% exceedance in 30 years
  - seismic_intensity_50yr_p10: expected JMA intensity at 10% exceedance in 50 years

NocoDB table: station_seismic (created by this script if needed)

Usage on VPS:
  docker run -d --name seismic --restart=no \
    -e NOCODB_API_URL=https://nocodb.pogorelov.dev \
    -e NOCODB_API_TOKEN=<token> \
    -v /tmp/scrape-seismic.py:/app/scraper.py:ro \
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
TABLE_ID = None  # set after table creation
JSHIS_API = "https://www.j-shis.bosai.go.jp/map/api/pshm/Y2024/AVR/TTL_MTTL/meshinfo.geojson"
STATION_FILE = "/data/stations.json"
DELAY_S = 1.0  # polite delay between J-SHIS requests


# ---------- helpers ----------
def load_stations():
    paths = [STATION_FILE, "data/stations.json", "app/src/data/stations.json"]
    for p in paths:
        if os.path.exists(p):
            with open(p) as f:
                return json.load(f)
    print("ERROR: stations.json not found")
    sys.exit(1)


def nocodb_headers():
    return {"xc-token": NOCODB_TOKEN, "Content-Type": "application/json"}


def create_table():
    """Create the station_seismic table in NocoDB."""
    url = f"{NOCODB_URL}/api/v2/meta/bases/ph4flgay4kmcgk4/tables"
    payload = {
        "table_name": "station_seismic",
        "title": "station_seismic",
        "columns": [
            {"column_name": "slug", "title": "slug", "uidt": "SingleLineText"},
            {"column_name": "prob_i60_30yr", "title": "prob_i60_30yr", "uidt": "Number"},
            {"column_name": "prob_i55_30yr", "title": "prob_i55_30yr", "uidt": "Number"},
            {"column_name": "prob_i50_30yr", "title": "prob_i50_30yr", "uidt": "Number"},
            {"column_name": "prob_i45_30yr", "title": "prob_i45_30yr", "uidt": "Number"},
            {"column_name": "max_vel_30yr_p03", "title": "max_vel_30yr_p03", "uidt": "Number"},
            {"column_name": "intensity_50yr_p10", "title": "intensity_50yr_p10", "uidt": "Number"},
            {"column_name": "meshcode", "title": "meshcode", "uidt": "SingleLineText"},
            {"column_name": "scraped_at", "title": "scraped_at", "uidt": "SingleLineText"},
        ],
    }
    r = requests.post(url, headers=nocodb_headers(), json=payload)
    if r.status_code == 200:
        table_id = r.json().get("id")
        print(f"Created table station_seismic: {table_id}")
        return table_id
    else:
        print(f"Table creation failed ({r.status_code}): {r.text[:200]}")
        # Maybe already exists — try to find it
        return find_table_id()


def find_table_id():
    """Find existing station_seismic table."""
    url = f"{NOCODB_URL}/api/v2/meta/bases/ph4flgay4kmcgk4/tables"
    r = requests.get(url, headers=nocodb_headers())
    r.raise_for_status()
    for t in r.json().get("list", []):
        if t["title"] == "station_seismic":
            print(f"Found existing table: {t['id']}")
            return t["id"]
    return None


def get_existing_slugs(table_id):
    slugs = set()
    offset = 0
    while True:
        url = f"{NOCODB_URL}/api/v2/tables/{table_id}/records?fields=slug&limit=1000&offset={offset}"
        r = requests.get(url, headers=nocodb_headers())
        r.raise_for_status()
        records = r.json().get("list", [])
        if not records:
            break
        for rec in records:
            slugs.add(rec.get("slug"))
        offset += len(records)
    return slugs


def fetch_seismic(lat, lng):
    """Query J-SHIS for seismic hazard data at a point."""
    params = {
        "position": f"{lng},{lat}",
        "epsg": "4612",
        "lang": "ja",
    }
    try:
        r = requests.get(JSHIS_API, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()

        if data.get("status") != "Success":
            return None

        features = data.get("features", [])
        if not features:
            return None

        props = features[0].get("properties", {})
        return {
            "prob_i60_30yr": safe_float(props.get("T30_I60_PS")),
            "prob_i55_30yr": safe_float(props.get("T30_I55_PS")),
            "prob_i50_30yr": safe_float(props.get("T30_I50_PS")),
            "prob_i45_30yr": safe_float(props.get("T30_I45_PS")),
            "max_vel_30yr_p03": safe_float(props.get("T30_P03_BV")),
            "intensity_50yr_p10": safe_float(props.get("T50_P10_SI")),
            "meshcode": props.get("meshcode", ""),
        }
    except Exception as e:
        print(f"  ERROR: {e}")
        return None


def safe_float(val):
    try:
        return round(float(val), 6) if val is not None else None
    except (ValueError, TypeError):
        return None


def write_to_nocodb(table_id, records):
    url = f"{NOCODB_URL}/api/v2/tables/{table_id}/records"
    for i in range(0, len(records), 100):
        batch = records[i:i+100]
        r = requests.post(url, headers=nocodb_headers(), json=batch)
        r.raise_for_status()
        print(f"  Inserted {min(i+100, len(records))}/{len(records)}")


# ---------- main ----------
def main():
    global TABLE_ID

    print("=== J-SHIS Seismic Hazard Scraper ===")
    print(f"API: {JSHIS_API}")

    # Create or find table
    TABLE_ID = create_table()
    if not TABLE_ID:
        print("FATAL: Cannot create/find station_seismic table")
        sys.exit(1)

    stations = load_stations()
    print(f"Loaded {len(stations)} stations")

    existing = get_existing_slugs(TABLE_ID)
    print(f"Already scraped: {len(existing)}")

    to_scrape = [s for s in stations if s["slug"] not in existing]
    if not to_scrape:
        print("All stations already scraped. Done!")
        return

    print(f"To scrape: {len(to_scrape)}")
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    records = []
    failed = 0
    for i, station in enumerate(to_scrape):
        slug = station["slug"]
        lat, lng = station["lat"], station["lng"]

        data = fetch_seismic(lat, lng)
        if data:
            records.append({
                "slug": slug,
                "scraped_at": now,
                **data,
            })
        else:
            failed += 1

        if (i + 1) % 50 == 0 or i == len(to_scrape) - 1:
            print(f"[{i+1}/{len(to_scrape)}] OK: {len(records)}, Failed: {failed}")

        # Write in batches of 200 to avoid losing progress
        if len(records) >= 200:
            write_to_nocodb(TABLE_ID, records)
            records = []

        time.sleep(DELAY_S)

    # Final batch
    if records:
        write_to_nocodb(TABLE_ID, records)

    print(f"\n=== Done! Scraped: {len(to_scrape) - failed}, Failed: {failed} ===")


if __name__ == "__main__":
    main()
