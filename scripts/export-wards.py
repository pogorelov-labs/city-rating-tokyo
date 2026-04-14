#!/usr/bin/env python3
"""Export station ward data from NocoDB to app/src/data/ward-data.json.

Usage:
    python scripts/export-wards.py             # write to app/src/data/ward-data.json
    python scripts/export-wards.py --dry-run   # print stats only
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "scrapers"))
from utils import NocoDB

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "app", "src", "data", "ward-data.json")


def main():
    parser = argparse.ArgumentParser(description="Export ward data from NocoDB")
    parser.add_argument("--dry-run", action="store_true", help="Print stats only")
    args = parser.parse_args()

    db = NocoDB("station_wards")
    records = db.get_all_records(fields=["slug", "city_name", "ward_name", "prefecture_name"])

    ward_data = {}
    for r in records:
        slug = r.get("slug", "").strip()
        if not slug:
            continue
        ward_data[slug] = {
            "city_name": r.get("city_name", "").strip(),
            "ward_name": r.get("ward_name", "").strip(),
            "prefecture_name": r.get("prefecture_name", "").strip(),
        }

    print(f"Fetched {len(ward_data)} station wards from NocoDB")

    # Stats
    tokyo_wards = sum(1 for w in ward_data.values() if not w["prefecture_name"] and w["city_name"].endswith("区"))
    designated = sum(1 for w in ward_data.values() if w["ward_name"] and w["city_name"].endswith("市"))
    other = len(ward_data) - tokyo_wards - designated
    print(f"  Tokyo 23 wards: {tokyo_wards}")
    print(f"  Designated cities (city+ward): {designated}")
    print(f"  Other: {other}")

    if args.dry_run:
        print("Dry run — not writing file")
        return

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(ward_data, f, ensure_ascii=False, indent=2)
    print(f"Written to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
