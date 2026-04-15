#!/usr/bin/env python3
"""
Scrape municipality-level rent data from e-Stat Housing Survey API.
Source: 住宅・土地統計調査 (Housing and Land Statistical Survey) FY2023 (令和5年)
API: https://api.e-stat.go.jp/rest/3.0/

Table: 0004021434 — Average monthly rent by room size (tatami brackets)
  at 全国、都道府県、市区 (nation, prefecture, city/ward) level.

Room size mapping to our format:
  cat02=2 (6.0-11.9 tatami ≈ 10-20m²)  → 1K/1LDK equivalent
  cat02=3 (12.0-17.9 tatami ≈ 20-30m²) → 2LDK equivalent

Filters: cat01=1 (専用住宅 residential only), cat03=2 (exclude zero-rent)

Two modes:
  --estat-app-id / ESTAT_APP_ID  → fetch via API
  --csv-file path.csv            → parse manually downloaded CSV from e-Stat website

Output:
  - data/estat/estat-rent-raw.json  (raw cache, keyed by JIS area code)
  - NocoDB table: estat_rent

Usage:
  python3 scripts/scrapers/scrape-estat-rent.py --estat-app-id <appId>
  python3 scripts/scrapers/scrape-estat-rent.py --estat-app-id <appId> --dry-run
  python3 scripts/scrapers/scrape-estat-rent.py --csv-file data/estat/downloaded.csv
"""

import argparse
import csv
import io
import json
import os
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import requests

# ── Config ──────────────────────────────────────────────────────────
NOCODB_URL = os.environ.get("NOCODB_API_URL", "https://nocodb.pogorelov.dev")
NOCODB_TOKEN = os.environ.get("NOCODB_API_TOKEN", "")
ESTAT_APP_ID = os.environ.get("ESTAT_APP_ID", "")
BASE_ID = "ph4flgay4kmcgk4"

# e-Stat API
ESTAT_API = "https://api.e-stat.go.jp/rest/3.0/app/json"

# Table: avg monthly rent by room size at city/ward level
STATS_DATA_ID = "0004021434"

# Prefectures we cover
TARGET_PREFECTURES = {"11": "Saitama", "12": "Chiba", "13": "Tokyo", "14": "Kanagawa"}

# Output paths
ROOT = Path(__file__).resolve().parent.parent.parent
OUTPUT_RAW = ROOT / "data" / "estat" / "estat-rent-raw.json"


# ── NocoDB helpers ──────────────────────────────────────────────────
def nocodb_headers():
    return {"xc-token": NOCODB_TOKEN, "Content-Type": "application/json"}


def create_table():
    """Create the estat_rent table in NocoDB if it doesn't exist."""
    url = f"{NOCODB_URL}/api/v2/meta/bases/{BASE_ID}/tables"
    payload = {
        "table_name": "estat_rent",
        "title": "estat_rent",
        "columns": [
            {"column_name": "area_code", "title": "area_code", "uidt": "SingleLineText"},
            {"column_name": "area_name", "title": "area_name", "uidt": "SingleLineText"},
            {"column_name": "prefecture_code", "title": "prefecture_code", "uidt": "SingleLineText"},
            {"column_name": "avg_rent_total", "title": "avg_rent_total", "uidt": "Number"},
            {"column_name": "avg_rent_1k", "title": "avg_rent_1k", "uidt": "Number"},
            {"column_name": "avg_rent_2ldk", "title": "avg_rent_2ldk", "uidt": "Number"},
            {"column_name": "survey_year", "title": "survey_year", "uidt": "SingleLineText"},
            {"column_name": "scraped_at", "title": "scraped_at", "uidt": "SingleLineText"},
        ],
    }
    r = requests.post(url, headers=nocodb_headers(), json=payload)
    if r.status_code == 200:
        table_id = r.json().get("id")
        print(f"  Created table estat_rent: {table_id}")
        return table_id
    elif r.status_code == 400 and "already exists" in r.text.lower():
        return find_table_id("estat_rent")
    else:
        print(f"  ERROR creating table: {r.status_code} {r.text[:200]}")
        return None


def find_table_id(name):
    """Find table ID by name."""
    url = f"{NOCODB_URL}/api/v2/meta/bases/{BASE_ID}/tables"
    r = requests.get(url, headers=nocodb_headers())
    r.raise_for_status()
    for t in r.json().get("list", []):
        if t.get("title") == name:
            return t["id"]
    return None


def upload_to_nocodb(table_id, records):
    """Bulk insert records to NocoDB."""
    url = f"{NOCODB_URL}/api/v2/tables/{table_id}/records"
    batch_size = 50
    total = 0
    for i in range(0, len(records), batch_size):
        batch = records[i : i + batch_size]
        r = requests.post(url, headers=nocodb_headers(), json=batch)
        if r.status_code != 200:
            print(f"  ERROR uploading batch {i}: {r.status_code} {r.text[:200]}")
        else:
            total += len(batch)
    return total


# ── e-Stat API ──────────────────────────────────────────────────────
def fetch_estat_rent(app_id):
    """
    Fetch municipality-level rent from e-Stat table 0004021434.

    Filters:
      cdCat01=1  → 専用住宅 (residential only, excludes shop combos)
      cdCat02=0,2,3 → total, 6-11.9畳 (~1K/1LDK), 12-17.9畳 (~2LDK)
      cdCat03=2  → exclude zero-rent
    """
    url = f"{ESTAT_API}/getStatsData"
    params = {
        "appId": app_id,
        "statsDataId": STATS_DATA_ID,
        "cdCat01": "1",       # 専用住宅 residential
        "cdCat02": "0,2,3",   # total + our 2 room brackets
        "cdCat03": "2",       # exclude zero-rent
        "limit": 100000,
        "metaGetFlg": "Y",
    }

    print(f"  Fetching statsDataId={STATS_DATA_ID}...")
    r = requests.get(url, params=params, timeout=120)
    r.raise_for_status()
    data = r.json()

    stats = data.get("GET_STATS_DATA", {})
    result = stats.get("RESULT", {})
    if result.get("STATUS") != 0:
        print(f"  ERROR: {result.get('ERROR_MSG', 'unknown')}")
        return {}

    stat_data = stats.get("STATISTICAL_DATA", {})
    total = stat_data.get("RESULT_INF", {}).get("TOTAL_NUMBER", 0)
    values = stat_data.get("DATA_INF", {}).get("VALUE", [])
    if isinstance(values, dict):
        values = [values]

    # Get area names from metadata
    class_info = stat_data.get("CLASS_INF", {}).get("CLASS_OBJ", [])
    if isinstance(class_info, dict):
        class_info = [class_info]
    area_names = {}
    for cls in class_info:
        if cls.get("@id") == "area":
            classes = cls.get("CLASS", [])
            if isinstance(classes, dict):
                classes = [classes]
            for c in classes:
                area_names[c.get("@code", "")] = c.get("@name", "")

    print(f"  Received {len(values)} values, {len(area_names)} areas in metadata")

    # Parse values — group by area code
    rent_by_area = {}
    for v in values:
        area = v.get("@area", "")
        # Filter to our target prefectures + skip prefecture-level aggregates
        if area[:2] not in TARGET_PREFECTURES or len(area) < 4:
            continue

        cat02 = v.get("@cat02", "")
        val_str = v.get("$", "")
        if val_str in ("-", "***", "…", "", "x", "X"):
            continue
        try:
            val = int(float(val_str))
        except (ValueError, TypeError):
            continue
        if val <= 0:
            continue

        if area not in rent_by_area:
            rent_by_area[area] = {"area_name": area_names.get(area, "")}

        if cat02 == "0":
            rent_by_area[area]["avg_rent_total"] = val
        elif cat02 == "2":
            rent_by_area[area]["avg_rent_1k"] = val      # 6-11.9畳 ≈ 1K/1LDK
        elif cat02 == "3":
            rent_by_area[area]["avg_rent_2ldk"] = val     # 12-17.9畳 ≈ 2LDK

    # Filter: keep only municipalities with at least a total rent value
    result = {}
    for area_code, rd in rent_by_area.items():
        total_rent = rd.get("avg_rent_total", 0)
        if total_rent > 10000:  # sanity check: above ¥10k
            result[area_code] = {
                "area_code": area_code,
                "area_name": rd["area_name"],
                "prefecture_code": area_code[:2],
                "avg_rent_total": total_rent,
                "avg_rent_1k": rd.get("avg_rent_1k"),
                "avg_rent_2ldk": rd.get("avg_rent_2ldk"),
            }

    return result


# ── CSV fallback ────────────────────────────────────────────────────
def parse_csv_file(csv_path):
    """Parse manually downloaded e-Stat CSV file."""
    content = None
    for enc in ["utf-8-sig", "shift_jis", "cp932", "utf-8"]:
        try:
            with open(csv_path, "r", encoding=enc) as f:
                content = f.read()
            break
        except (UnicodeDecodeError, UnicodeError):
            continue

    if content is None:
        print(f"ERROR: Could not decode {csv_path}")
        return {}

    reader = csv.reader(io.StringIO(content))
    rows = list(reader)
    print(f"  CSV: {len(rows)} rows")

    # e-Stat CSV: skip metadata rows, find data
    result = {}
    for row in rows:
        if len(row) < 3:
            continue
        # Look for 5-digit area codes in our target prefectures
        for cell_idx, cell in enumerate(row):
            cell = cell.strip()
            if len(cell) == 5 and cell.isdigit() and cell[:2] in TARGET_PREFECTURES:
                area_code = cell
                # Next cells should be area_name and rent values
                area_name = row[cell_idx + 1].strip() if cell_idx + 1 < len(row) else ""
                # Find numeric values that look like rent (¥30k-500k range)
                rents = []
                for v in row[cell_idx + 2 :]:
                    v = v.strip().replace(",", "")
                    if v and v not in ("-", "***", "…"):
                        try:
                            val = int(float(v))
                            if 10000 <= val <= 500000:
                                rents.append(val)
                        except ValueError:
                            pass
                if rents:
                    result[area_code] = {
                        "area_code": area_code,
                        "area_name": area_name,
                        "prefecture_code": area_code[:2],
                        "avg_rent_total": rents[0] if rents else None,
                        "avg_rent_1k": rents[1] if len(rents) > 1 else None,
                        "avg_rent_2ldk": rents[2] if len(rents) > 2 else None,
                    }
                break

    return result


# ── Main ────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Scrape e-Stat Housing Survey rent data")
    parser.add_argument("--estat-app-id", help="e-Stat API application ID")
    parser.add_argument("--csv-file", help="Path to manually downloaded e-Stat CSV file")
    parser.add_argument("--skip-nocodb", action="store_true", help="Skip NocoDB upload")
    parser.add_argument("--dry-run", action="store_true", help="Fetch and parse but don't write")
    args = parser.parse_args()

    app_id = args.estat_app_id or ESTAT_APP_ID
    csv_file = args.csv_file

    if not app_id and not csv_file:
        print("ERROR: Provide --estat-app-id / ESTAT_APP_ID or --csv-file")
        sys.exit(1)

    print("=" * 60)
    print("e-Stat Housing Survey Rent Scraper")
    print(f"Table: {STATS_DATA_ID} (avg monthly rent by room size)")
    print("=" * 60)

    rent_data = {}

    if csv_file:
        print(f"\nMode: CSV file ({csv_file})")
        if not os.path.exists(csv_file):
            print(f"ERROR: File not found: {csv_file}")
            sys.exit(1)
        rent_data = parse_csv_file(csv_file)
    else:
        print(f"\nMode: e-Stat API (appId={app_id[:8]}...)")
        rent_data = fetch_estat_rent(app_id)

    if not rent_data:
        print("\nERROR: No rent data extracted.")
        sys.exit(1)

    # Summary by prefecture
    print(f"\nSummary:")
    for pcode, pname in sorted(TARGET_PREFECTURES.items()):
        areas = {k: v for k, v in rent_data.items() if v["prefecture_code"] == pcode}
        if areas:
            rents = [v["avg_rent_total"] for v in areas.values() if v.get("avg_rent_total")]
            avg_r = sum(rents) / len(rents) if rents else 0
            print(f"  {pname} ({pcode}): {len(areas)} municipalities, avg ¥{avg_r:,.0f}")
        else:
            print(f"  {pname} ({pcode}): 0 municipalities")

    print(f"\nTotal: {len(rent_data)} municipalities")

    # Show sample entries
    print(f"\n{'Code':<8} {'Name':<16} {'Total':>8} {'~1K':>8} {'~2LDK':>8}")
    print("-" * 55)
    sample = sorted(rent_data.items())[:15]
    for area_code, rd in sample:
        name = rd.get("area_name", "?")[:16]
        total = rd.get("avg_rent_total", "-")
        r1k = rd.get("avg_rent_1k", "-")
        r2ldk = rd.get("avg_rent_2ldk", "-")
        t_str = f"¥{total:,}" if isinstance(total, int) else str(total)
        k_str = f"¥{r1k:,}" if isinstance(r1k, int) else str(r1k)
        l_str = f"¥{r2ldk:,}" if isinstance(r2ldk, int) else str(r2ldk)
        print(f"{area_code:<8} {name:<16} {t_str:>8} {k_str:>8} {l_str:>8}")

    # Save raw data
    if not args.dry_run:
        print(f"\nSaving raw data to {OUTPUT_RAW}...")
        OUTPUT_RAW.parent.mkdir(parents=True, exist_ok=True)
        with open(OUTPUT_RAW, "w", encoding="utf-8") as f:
            json.dump(rent_data, f, ensure_ascii=False, indent=2)
        print(f"  Saved {len(rent_data)} entries")

    # Upload to NocoDB
    if not args.dry_run and not args.skip_nocodb and NOCODB_TOKEN:
        print("\nUploading to NocoDB...")
        table_id = find_table_id("estat_rent")
        if not table_id:
            table_id = create_table()
        if table_id:
            now = datetime.now(timezone.utc).isoformat()
            records = []
            for area_code, rd in rent_data.items():
                records.append({
                    "area_code": rd["area_code"],
                    "area_name": rd.get("area_name", ""),
                    "prefecture_code": rd["prefecture_code"],
                    "avg_rent_total": rd.get("avg_rent_total"),
                    "avg_rent_1k": rd.get("avg_rent_1k"),
                    "avg_rent_2ldk": rd.get("avg_rent_2ldk"),
                    "survey_year": "2023",
                    "scraped_at": now,
                })
            uploaded = upload_to_nocodb(table_id, records)
            print(f"  Uploaded {uploaded} records to NocoDB")
        else:
            print("  ERROR: Could not create/find NocoDB table")
    elif args.dry_run:
        print("\nDry run — skipping writes")

    print(f"\nDone! {len(rent_data)} municipalities with rent data.")


if __name__ == "__main__":
    main()
