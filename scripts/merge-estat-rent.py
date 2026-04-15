#!/usr/bin/env python3
"""
Merge e-Stat municipality rent data into rent-averages.json as gap-fill.

Flow:
  1. Load existing rent-averages.json (274 Suumo entries)
  2. Load e-Stat raw data (data/estat/estat-rent-raw.json)
  3. Load station_wards from NocoDB (1493 station → municipality mappings)
  4. Optionally load calibration factor (data/estat/calibration.json)
  5. For each station NOT in rent-averages.json:
     - Find municipality via station_wards
     - Look up e-Stat rent for that municipality (by area_name or area_code)
     - Apply calibration factor
     - Add entry with source: "estat"
  6. Write merged rent-averages.json

Merge policy: Suumo always wins — e-Stat only fills gaps.

Usage:
  python3 scripts/merge-estat-rent.py
  python3 scripts/merge-estat-rent.py --dry-run       # preview without writing
  python3 scripts/merge-estat-rent.py --calibration 1.15  # manual calibration factor
"""

import argparse
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent

# NocoDB config (for fetching station_wards)
NOCODB_URL = os.environ.get("NOCODB_API_URL", "https://nocodb.pogorelov.dev")
NOCODB_TOKEN = os.environ.get("NOCODB_API_TOKEN", "3hUf86bwbyw-OSJTlNwGOc1w8AcwrrgAkOuyIaTt")
STATION_WARDS_TABLE = "m74rdmspn3trrqc"


def load_rent_averages():
    path = ROOT / "app" / "src" / "data" / "rent-averages.json"
    if not path.exists():
        print(f"ERROR: {path} not found")
        sys.exit(1)
    return json.loads(path.read_text()), path


def load_estat_data():
    path = ROOT / "data" / "estat" / "estat-rent-raw.json"
    if not path.exists():
        print(f"ERROR: {path} not found")
        print("Run scrape-estat-rent.py first.")
        sys.exit(1)
    return json.loads(path.read_text())


def load_calibration():
    path = ROOT / "data" / "estat" / "calibration.json"
    if path.exists():
        cal = json.loads(path.read_text())
        return cal.get("calibration_factor", 1.0)
    return 1.0


def fetch_station_wards():
    """Fetch all station_wards records from NocoDB."""
    headers = {"xc-token": NOCODB_TOKEN, "Content-Type": "application/json"}
    base_url = f"{NOCODB_URL}/api/v2/tables/{STATION_WARDS_TABLE}/records"

    all_records = []
    offset = 0
    limit = 200
    while True:
        r = requests.get(base_url, headers=headers, params={
            "fields": "slug,city_name,ward_name,prefecture_name",
            "limit": limit,
            "offset": offset,
        })
        r.raise_for_status()
        data = r.json()
        rows = data.get("list", [])
        if not rows:
            break
        all_records.extend(rows)
        if len(rows) < limit:
            break
        offset += limit

    return all_records


def build_municipality_key(city_name, ward_name=""):
    """
    Build a normalized municipality key for matching against e-Stat area names.

    Patterns:
      Tokyo 23-ku: city_name="新宿区" → "新宿区"
      Designated cities: city_name="横浜市" + ward_name="西区" → "横浜市西区"
      Regular cities: city_name="鎌倉市" → "鎌倉市"
    """
    city = (city_name or "").strip()
    ward = (ward_name or "").strip()

    if not city:
        return ""

    # Designated cities: append ward if it looks like a ward name
    # (ends with 区 and city ends with 市)
    if city.endswith("市") and ward.endswith("区"):
        return city + ward

    return city


def match_estat_to_municipality(estat_data, municipality_key, prefecture_name=""):
    """
    Try to match a municipality key against e-Stat data.
    Returns the best matching e-Stat entry or None.

    Matching strategy:
      1. Exact match on area_name
      2. For designated city wards (e.g., "さいたま市大宮区"):
         try matching just the ward part ("大宮区") with prefecture filter
      3. e-Stat area_name contains our key
      4. Our key contains e-Stat area_name (with prefecture filter)
    """
    if not municipality_key:
        return None

    # Determine prefecture code from prefecture_name for disambiguation
    pref_code = ""
    pref_map = {"東京都": "13", "神奈川県": "14", "埼玉県": "11", "千葉県": "12"}
    for pname, pcode in pref_map.items():
        if pname in (prefecture_name or ""):
            pref_code = pcode
            break

    # Strategy 1: exact area_name match
    for area_code, ed in estat_data.items():
        if ed.get("area_name") == municipality_key:
            return ed

    # Strategy 2: for designated city wards, match just the ward part
    # e.g., "さいたま市大宮区" → try "大宮区" but only in the right prefecture
    if "市" in municipality_key and municipality_key.endswith("区"):
        # Extract the ward part after the last 市
        parts = municipality_key.split("市", 1)
        if len(parts) == 2:
            ward_only = parts[1]  # "大宮区"
            city_only = parts[0] + "市"  # "さいたま市"
            # First try: find the city aggregate (e.g., "さいたま市")
            city_entry = None
            ward_entry = None
            for area_code, ed in estat_data.items():
                name = ed.get("area_name", "")
                if name == city_only:
                    city_entry = ed
                elif name == ward_only:
                    # Disambiguate by prefecture if possible
                    if pref_code and area_code.startswith(pref_code):
                        ward_entry = ed
                    elif not pref_code:
                        ward_entry = ed
            # Prefer ward-level over city-level
            if ward_entry:
                return ward_entry
            if city_entry:
                return city_entry

    # Strategy 3: our key contains e-Stat area_name (with prefecture filter)
    for area_code, ed in estat_data.items():
        area_name = ed.get("area_name", "")
        if area_name and len(area_name) >= 2 and area_name in municipality_key:
            # Skip prefecture aggregates
            if len(area_code) < 4:
                continue
            if pref_code and not area_code.startswith(pref_code):
                continue
            return ed

    return None


def main():
    parser = argparse.ArgumentParser(description="Merge e-Stat rent into rent-averages.json")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    parser.add_argument("--calibration", type=float, default=None,
                        help="Manual calibration factor (overrides calibration.json)")
    args = parser.parse_args()

    print("=" * 60)
    print("Merge e-Stat Rent Data into rent-averages.json")
    print("=" * 60)

    # Load data
    print("\n1. Loading data...")
    rent_data, rent_path = load_rent_averages()
    estat_data = load_estat_data()

    cal_factor = args.calibration if args.calibration is not None else load_calibration()
    print(f"  rent-averages.json: {len(rent_data)} entries")
    print(f"  e-Stat raw: {len(estat_data)} municipalities")
    print(f"  Calibration factor: {cal_factor:.4f}")

    # Fetch station_wards and build slug→ward lookup
    print("\n2. Fetching station_wards from NocoDB...")
    ward_records = fetch_station_wards()
    print(f"  {len(ward_records)} station-ward mappings")

    # Build ward lookup indexed by slug
    wards_by_slug = {}
    for w in ward_records:
        s = w.get("slug", "")
        if s:
            wards_by_slug[s] = w

    # Load stations.json (canonical slug list)
    stations_path = ROOT / "data" / "stations.json"
    stations = json.loads(stations_path.read_text())
    print(f"  {len(stations)} stations from stations.json")

    # Match stations to e-Stat data
    print("\n3. Matching stations to e-Stat municipalities...")
    new_entries = {}
    already_in_suumo = 0
    matched = 0
    unmatched = 0
    unmatched_list = []

    for st in stations:
        slug = st.get("slug", "")
        if not slug:
            continue

        # Skip if already has Suumo data
        if slug in rent_data:
            already_in_suumo += 1
            continue

        # Look up ward info from station_wards
        w = wards_by_slug.get(slug, {})
        city_name = w.get("city_name", "")
        ward_name = w.get("ward_name", "")
        prefecture_name = w.get("prefecture_name", "")
        # Tokyo 23-ku has empty prefecture_name — infer from city_name ending in 区
        if not prefecture_name and city_name.endswith("区") and not city_name.endswith("市"):
            prefecture_name = "東京都"

        # Build municipality key
        muni_key = build_municipality_key(city_name, ward_name)
        if not muni_key:
            unmatched += 1
            unmatched_list.append(slug)
            continue

        # Try to find in e-Stat data
        estat_entry = match_estat_to_municipality(estat_data, muni_key, prefecture_name)

        if estat_entry:
            # Use room-specific rents if available, fall back to total
            rent_1k = estat_entry.get("avg_rent_1k") or estat_entry.get("avg_rent_total")
            rent_2ldk = estat_entry.get("avg_rent_2ldk") or estat_entry.get("avg_rent_total")
            if rent_1k and rent_1k > 0:
                new_entries[slug] = {
                    "1k_1ldk": int(rent_1k * cal_factor),
                    "2ldk": int(rent_2ldk * cal_factor) if rent_2ldk else int(rent_1k * cal_factor * 1.2),
                    "source": "estat",
                    "updated": "2026-04",
                    "area_code": estat_entry.get("area_code", ""),
                    "area_name": estat_entry.get("area_name", ""),
                }
                matched += 1
            else:
                unmatched += 1
                unmatched_list.append(slug)
        else:
            unmatched += 1
            unmatched_list.append(slug)

    print(f"\n  Results:")
    print(f"    Already in Suumo: {already_in_suumo}")
    print(f"    Matched to e-Stat: {matched}")
    print(f"    Unmatched: {unmatched}")

    if unmatched_list:
        print(f"\n  First 20 unmatched stations:")
        for s in unmatched_list[:20]:
            ward = wards_by_slug.get(s, {})
            city = ward.get("city_name", "?")
            ward_n = ward.get("ward_name", "")
            print(f"    {s}: city={city}, ward={ward_n}")

    # Summary by prefecture
    print(f"\n  By prefecture:")
    pref_names = {"11": "Saitama", "12": "Chiba", "13": "Tokyo", "14": "Kanagawa"}
    by_pref = defaultdict(list)
    for slug, entry in new_entries.items():
        pcode = entry.get("area_code", "")[:2]
        by_pref[pcode].append(entry["1k_1ldk"])

    for pcode in sorted(by_pref.keys()):
        rents = by_pref[pcode]
        pname = pref_names.get(pcode, pcode)
        print(f"    {pname}: {len(rents)} stations, avg ¥{sum(rents)/len(rents):,.0f}")

    # Merge
    if not args.dry_run and new_entries:
        print(f"\n4. Writing merged rent-averages.json...")
        merged = {**rent_data, **new_entries}
        with open(rent_path, "w", encoding="utf-8") as f:
            json.dump(merged, f, ensure_ascii=False, indent=2)
        print(f"  Wrote {len(merged)} entries ({len(rent_data)} Suumo + {len(new_entries)} e-Stat)")
    elif args.dry_run:
        print(f"\n4. Dry run — would add {len(new_entries)} entries to rent-averages.json")
    else:
        print(f"\n4. No new entries to merge")

    # Final coverage report
    total_stations = len(stations)
    suumo_count = len(rent_data)
    estat_count = len(new_entries)
    remaining = total_stations - suumo_count - estat_count

    print(f"\n{'=' * 60}")
    print(f"COVERAGE REPORT")
    print(f"{'=' * 60}")
    print(f"  Total stations:         {total_stations}")
    print(f"  Suumo (strong):         {suumo_count} ({suumo_count/total_stations*100:.0f}%)")
    print(f"  e-Stat (moderate):      {estat_count} ({estat_count/total_stations*100:.0f}%)")
    print(f"  Regression (estimate):  {remaining} ({remaining/total_stations*100:.0f}%)")
    print(f"  Total covered:          {suumo_count+estat_count} ({(suumo_count+estat_count)/total_stations*100:.0f}%)")


if __name__ == "__main__":
    main()
