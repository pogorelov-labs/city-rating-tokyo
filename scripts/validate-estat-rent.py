#!/usr/bin/env python3
"""
Cross-validate e-Stat rent data against existing Suumo data.

For municipalities where we have both Suumo-scraped rent and e-Stat government
statistics, compare them to:
  1. Measure systematic bias (e-Stat expected ~15-20% lower — includes old buildings)
  2. Compute a calibration factor to apply when using e-Stat for gap-fill
  3. Check rank correlation (do municipalities sort in the same order?)

Usage:
  python3 scripts/validate-estat-rent.py [--estat-file data/estat/estat-rent-raw.json]
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    parser = argparse.ArgumentParser(description="Cross-validate e-Stat vs Suumo rent data")
    parser.add_argument("--estat-file", default="data/estat/estat-rent-raw.json",
                        help="Path to e-Stat raw JSON")
    args = parser.parse_args()

    print("=" * 60)
    print("Rent Data Cross-Validation: Suumo vs e-Stat")
    print("=" * 60)

    # Load rent-averages.json and filter to Suumo-only
    rent_path = ROOT / "app" / "src" / "data" / "rent-averages.json"
    all_rent = json.loads(rent_path.read_text())
    suumo = {k: v for k, v in all_rent.items() if v.get("source", "suumo") != "estat"}

    # Load e-Stat raw data
    estat_path = Path(args.estat_file)
    if not estat_path.exists():
        print(f"ERROR: {estat_path} not found")
        sys.exit(1)
    estat = json.loads(estat_path.read_text())

    print(f"\nSuumo entries: {len(suumo)}")
    print(f"e-Stat municipalities: {len(estat)}")

    # Group Suumo entries by area_code
    suumo_by_code = defaultdict(list)
    for slug, rd in suumo.items():
        area_code = rd.get("area_code", "")
        if area_code:
            price = rd.get("1k_1ldk")
            if price and price > 0:
                suumo_by_code[area_code].append(price)

    print(f"Suumo: {len(suumo_by_code)} unique area_codes")

    # Match by area_code
    matched = []
    for area_code, ed in estat.items():
        estat_1k = ed.get("avg_rent_1k") or ed.get("avg_rent_total")
        if not estat_1k:
            continue

        suumo_prices = suumo_by_code.get(area_code, [])
        if not suumo_prices:
            continue

        estat_name = ed.get("area_name", "")
        suumo_median = sorted(suumo_prices)[len(suumo_prices) // 2]
        suumo_mean = sum(suumo_prices) / len(suumo_prices)
        matched.append({
            "area_code": area_code,
            "area_name": estat_name,
            "suumo_median": suumo_median,
            "suumo_mean": suumo_mean,
            "suumo_count": len(suumo_prices),
            "estat_rent": estat_1k,
            "ratio": suumo_median / estat_1k if estat_1k > 0 else None,
            "pct_diff": (suumo_median - estat_1k) / estat_1k * 100,
        })

    if not matched:
        print("\nERROR: No matching municipalities found!")
        sys.exit(1)

    # Sort by ratio for display
    matched.sort(key=lambda x: x["ratio"] or 0, reverse=True)

    print(f"\n{'=' * 60}")
    print(f"Matched municipalities: {len(matched)}")
    print(f"{'=' * 60}")
    print(f"\n{'Area':<16} {'Suumo':>8} {'e-Stat':>8} {'Ratio':>6} {'Diff%':>7}")
    print("-" * 50)
    for m in matched:
        print(f"{m['area_name']:<16} ¥{m['suumo_median']:>6,} ¥{m['estat_rent']:>6,} "
              f"{m['ratio']:>5.2f}x {m['pct_diff']:>+6.1f}%")

    # Summary statistics
    ratios = [m["ratio"] for m in matched if m["ratio"]]
    pct_diffs = [m["pct_diff"] for m in matched]
    mean_ratio = sum(ratios) / len(ratios)
    median_ratio = sorted(ratios)[len(ratios) // 2]
    mape = sum(abs(d) for d in pct_diffs) / len(pct_diffs)

    # Spearman rank correlation
    n = len(matched)
    suumo_order = sorted(range(n), key=lambda i: matched[i]["suumo_median"])
    estat_order = sorted(range(n), key=lambda i: matched[i]["estat_rent"])
    suumo_ranks = [0] * n
    estat_ranks = [0] * n
    for rank, idx in enumerate(suumo_order):
        suumo_ranks[idx] = rank
    for rank, idx in enumerate(estat_order):
        estat_ranks[idx] = rank
    d_sq_sum = sum((suumo_ranks[i] - estat_ranks[i]) ** 2 for i in range(n))
    spearman = 1 - (6 * d_sq_sum) / (n * (n * n - 1)) if n > 1 else 0

    print(f"\n{'=' * 60}")
    print(f"VALIDATION RESULTS")
    print(f"{'=' * 60}")
    print(f"  Matched municipalities: {len(matched)}")
    print(f"  Mean Suumo/e-Stat ratio: {mean_ratio:.3f}")
    print(f"  Median ratio:            {median_ratio:.3f}")
    print(f"  MAPE:                    {mape:.1f}%")
    print(f"  Spearman rank corr:      {spearman:.3f}")
    print()

    if median_ratio > 1.0:
        print(f"  FINDING: Suumo rents are ~{(median_ratio - 1) * 100:.0f}% higher than e-Stat")
        print(f"  RECOMMENDED calibration factor: {median_ratio:.3f}")
    elif median_ratio < 1.0:
        print(f"  FINDING: e-Stat rents are ~{(1 - median_ratio) * 100:.0f}% higher than Suumo")

    # Save calibration
    calibration = {
        "calibration_factor": round(median_ratio, 4),
        "mean_ratio": round(mean_ratio, 4),
        "mape_percent": round(mape, 1),
        "spearman_rank_correlation": round(spearman, 3),
        "matched_count": len(matched),
    }
    cal_path = ROOT / "data" / "estat" / "calibration.json"
    cal_path.parent.mkdir(parents=True, exist_ok=True)
    with open(cal_path, "w") as f:
        json.dump(calibration, f, indent=2)
    print(f"\n  Calibration saved to: {cal_path}")


if __name__ == "__main__":
    main()
