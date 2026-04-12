#!/usr/bin/env python3
"""
Export elevation + seismic data from NocoDB to a static JSON file
consumed by the Next.js app at build time.

Output: app/src/data/environment-data.json

Does NOT touch compute-ratings.py or demo-ratings.ts — this is a separate
data channel for non-rating informational data (elevation, seismic risk).

Usage: python3 scripts/export-environment.py [--dry-run]
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "scrapers"))
from utils import NocoDB

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "app" / "src" / "data" / "environment-data.json"

# Seismic risk tiers based on prob_i60_30yr (probability of JMA intensity ≥6.0 in 30 years)
# Thresholds align with J-SHIS hazard map color bands
SEISMIC_TIERS = [
    (0.26, "very_high"),  # ≥26%
    (0.06, "high"),       # 6-26%
    (0.03, "moderate"),   # 3-6%
    (0.00, "low"),        # <3%
]

# Elevation risk tiers for flood susceptibility
ELEVATION_TIERS = [
    (5, "very_low"),      # <5m — high flood risk (below/near sea level)
    (10, "low"),          # 5-10m — low-lying, check hazard maps
    (30, "moderate"),     # 10-30m
    (100, "elevated"),    # 30-100m
    (300, "high"),        # 100-300m
    (float("inf"), "mountain"),  # 300m+
]


def classify_seismic(prob_i60):
    """Classify seismic risk tier from prob_i60_30yr."""
    if prob_i60 is None:
        return "unknown"
    p = float(prob_i60)
    for threshold, tier in SEISMIC_TIERS:
        if p >= threshold:
            return tier
    return "low"


def classify_elevation(elev_m):
    """Classify elevation tier."""
    if elev_m is None:
        return "unknown"
    e = float(elev_m)
    for threshold, tier in ELEVATION_TIERS:
        if e < threshold:
            return tier
    return "mountain"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    print("Loading elevation data from NocoDB...")
    elev_rows = NocoDB("station_elevation").get_all_records()
    elev = {r["slug"]: r for r in elev_rows if r.get("slug")}
    print(f"  station_elevation: {len(elev)} records")

    print("Loading seismic data from NocoDB...")
    seis_rows = NocoDB("station_seismic").get_all_records()
    seis = {r["slug"]: r for r in seis_rows if r.get("slug")}
    print(f"  station_seismic: {len(seis)} records")

    # Build merged output
    result = {}
    for slug in sorted(set(list(elev.keys()) + list(seis.keys()))):
        entry = {}

        e = elev.get(slug, {})
        s = seis.get(slug, {})

        elev_m = e.get("elevation_m")
        if elev_m is not None:
            entry["elevation_m"] = round(float(elev_m), 1)
            entry["elevation_tier"] = classify_elevation(elev_m)

        prob_i60 = s.get("prob_i60_30yr")
        if prob_i60 is not None:
            entry["seismic_prob_i60"] = round(float(prob_i60), 4)
            entry["seismic_risk_tier"] = classify_seismic(prob_i60)

        prob_i55 = s.get("prob_i55_30yr")
        if prob_i55 is not None:
            entry["seismic_prob_i55"] = round(float(prob_i55), 4)

        if entry:
            result[slug] = entry

    print(f"\nMerged: {len(result)} stations with environment data")

    # Distribution stats
    tier_counts = {}
    for e in result.values():
        tier = e.get("seismic_risk_tier", "unknown")
        tier_counts[tier] = tier_counts.get(tier, 0) + 1
    print(f"  Seismic tiers: {tier_counts}")

    elev_tier_counts = {}
    for e in result.values():
        tier = e.get("elevation_tier", "unknown")
        elev_tier_counts[tier] = elev_tier_counts.get(tier, 0) + 1
    print(f"  Elevation tiers: {elev_tier_counts}")

    if args.dry_run:
        print("\nDry run — not writing file.")
        # Sample output
        for slug in ["shinjuku", "shibuya", "aoi", "shin-kiba"]:
            if slug in result:
                print(f"  {slug}: {result[slug]}")
        return

    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(f"\nWrote {OUTPUT} ({len(result)} stations, {OUTPUT.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
