#!/usr/bin/env python3
"""
Compute estimated transit times from every station to 5 hub stations.

Approach: Geographic distance + line connectivity + calibration against
252 AI-researched ground-truth values.

Model:
  travel_time = (haversine_km * circuity) / speed_kmh * 60 + transfers * transfer_penalty

Where:
  - circuity: ratio of rail distance to straight-line distance (~1.3)
  - speed_kmh: varies by distance band (local/rapid/express)
  - transfers: estimated from shared line connectivity
  - transfer_penalty: walking + waiting time per interchange

Calibrated against 252 AI-researched stations with hand-curated transit times.

Usage:
  python3 scripts/compute-transit-times.py [--calibrate] [--output PATH]
"""

import argparse
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = ROOT / "data" / "transit-times.json"

# Hub stations
HUBS = {
    "shibuya":    (35.658871, 139.701238),
    "shinjuku":   (35.689729, 139.700464),
    "tokyo":      (35.681391, 139.766103),
    "ikebukuro":  (35.730256, 139.711086),
    "shinagawa":  (35.628760, 139.738999),
}

# Hub station line sets (loaded dynamically from stations.json)
HUB_LINES = {}


def haversine_km(lat1, lon1, lat2, lon2):
    """Great-circle distance between two points in km."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def build_line_graph(stations):
    """Build adjacency: line_id -> set of line_ids that share at least one station."""
    line_to_stations = {}
    for s in stations:
        for line in s.get("lines", []):
            line_to_stations.setdefault(line, set()).add(s["slug"])

    # Two lines are connected if they share a station
    line_adj = {}
    station_to_lines = {}
    for s in stations:
        station_to_lines[s["slug"]] = set(s.get("lines", []))

    for line, slugs in line_to_stations.items():
        connected = set()
        for slug in slugs:
            for other_line in station_to_lines.get(slug, []):
                if other_line != line:
                    connected.add(other_line)
        line_adj[line] = connected

    return line_adj, station_to_lines


def estimate_transfers(station_lines, hub_lines, line_adj):
    """
    Estimate minimum transfers between a station and a hub.
    0 = direct line, 1 = one transfer, 2 = two transfers.
    """
    # Direct connection: station and hub share a line
    if station_lines & hub_lines:
        return 0

    # One transfer: station line connects to a hub line via shared station
    for sl in station_lines:
        neighbors = line_adj.get(sl, set())
        if neighbors & hub_lines:
            return 1

    # Two transfers: station line -> intermediate -> hub line
    for sl in station_lines:
        for mid_line in line_adj.get(sl, set()):
            mid_neighbors = line_adj.get(mid_line, set())
            if mid_neighbors & hub_lines:
                return 2

    return 2  # fallback


def estimate_travel_time(distance_km, transfers, params):
    """
    Estimate travel time in minutes.
    params: dict with circuity, speed_bands, transfer_penalty, min_time
    """
    rail_km = distance_km * params["circuity"]

    # Speed varies by distance (express trains serve longer distances)
    if distance_km < 5:
        speed = params["speed_close"]
    elif distance_km < 15:
        speed = params["speed_mid"]
    elif distance_km < 35:
        speed = params["speed_far"]
    else:
        speed = params["speed_express"]

    ride_time = (rail_km / speed) * 60
    total = ride_time + transfers * params["transfer_penalty"]

    return max(params["min_time"], round(total))


# Default parameters (will be calibrated)
DEFAULT_PARAMS = {
    "circuity": 1.30,       # rail vs straight-line ratio
    "speed_close": 25.0,    # km/h for < 5km (local metro, frequent stops)
    "speed_mid": 32.0,      # km/h for 5-15km
    "speed_far": 38.0,      # km/h for 15-35km (rapid service)
    "speed_express": 48.0,  # km/h for 35+ km (express/limited express)
    "transfer_penalty": 8.0,  # minutes per transfer
    "min_time": 3,          # minimum travel time
}


def calibrate(stations, ai_transit, line_adj, station_to_lines):
    """
    Find parameters that minimize MAE against AI ground truth.
    Uses grid search over key parameters.
    """
    station_map = {s["slug"]: s for s in stations}
    best_mae = float("inf")
    best_params = dict(DEFAULT_PARAMS)

    # Grid search over most impactful parameters
    for circuity in [1.20, 1.25, 1.30, 1.35, 1.40]:
        for speed_close in [22, 25, 28]:
            for speed_mid in [30, 33, 36]:
                for speed_far in [36, 40, 44]:
                    for speed_express in [44, 48, 52, 56]:
                        for transfer_pen in [6, 8, 10]:
                            params = {
                                "circuity": circuity,
                                "speed_close": speed_close,
                                "speed_mid": speed_mid,
                                "speed_far": speed_far,
                                "speed_express": speed_express,
                                "transfer_penalty": transfer_pen,
                                "min_time": 3,
                            }
                            errors = []
                            for slug, truth in ai_transit.items():
                                st = station_map.get(slug)
                                if not st:
                                    continue
                                sl = station_to_lines.get(slug, set())
                                for hub, (hlat, hlng) in HUBS.items():
                                    true_val = truth.get(hub)
                                    if true_val is None:
                                        continue
                                    dist = haversine_km(st["lat"], st["lng"], hlat, hlng)
                                    tr = estimate_transfers(sl, HUB_LINES[hub], line_adj)
                                    est = estimate_travel_time(dist, tr, params)
                                    errors.append(abs(est - true_val))
                            if errors:
                                mae = sum(errors) / len(errors)
                                if mae < best_mae:
                                    best_mae = mae
                                    best_params = dict(params)

    return best_params, best_mae


def main():
    parser = argparse.ArgumentParser(description="Compute transit times to hub stations")
    parser.add_argument("--calibrate", action="store_true", help="Calibrate against AI data")
    parser.add_argument("--output", type=str, default=str(DEFAULT_OUTPUT))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    # Load stations
    with open(ROOT / "data" / "stations.json") as f:
        stations = json.load(f)
    station_map = {s["slug"]: s for s in stations}
    print(f"Loaded {len(stations)} stations")

    # Build hub line sets
    for hub in HUBS:
        st = station_map.get(hub)
        if st:
            HUB_LINES[hub] = set(st.get("lines", []))

    # Build line connectivity graph
    print("Building line connectivity graph...")
    line_adj, station_to_lines = build_line_graph(stations)
    print(f"  {len(line_adj)} lines in graph")

    # Load AI calibration data
    ai_transit_path = Path("/tmp/ai_transit.json")
    ai_transit = {}
    if ai_transit_path.exists():
        with open(ai_transit_path) as f:
            ai_transit = json.load(f)
        print(f"  AI calibration data: {len(ai_transit)} stations")

    # Calibrate or use defaults
    params = dict(DEFAULT_PARAMS)
    if args.calibrate and ai_transit:
        print("\nCalibrating parameters (grid search)...")
        params, mae = calibrate(stations, ai_transit, line_adj, station_to_lines)
        print(f"  Best MAE: {mae:.1f} min")
        print(f"  Params: {json.dumps(params, indent=2)}")
    elif ai_transit:
        # Quick evaluation with defaults
        errors = []
        for slug, truth in ai_transit.items():
            st = station_map.get(slug)
            if not st:
                continue
            sl = station_to_lines.get(slug, set())
            for hub, (hlat, hlng) in HUBS.items():
                true_val = truth.get(hub)
                if true_val is None:
                    continue
                dist = haversine_km(st["lat"], st["lng"], hlat, hlng)
                tr = estimate_transfers(sl, HUB_LINES[hub], line_adj)
                est = estimate_travel_time(dist, tr, params)
                errors.append(abs(est - true_val))
        if errors:
            print(f"  Default params MAE: {sum(errors)/len(errors):.1f} min")

    # Compute transit times for all stations
    print("\nComputing transit times for all stations...")
    results = {}
    for s in stations:
        slug = s["slug"]
        sl = station_to_lines.get(slug, set())
        transit = {}
        for hub, (hlat, hlng) in HUBS.items():
            if slug == hub:
                transit[hub] = 0
                continue
            dist = haversine_km(s["lat"], s["lng"], hlat, hlng)
            tr = estimate_transfers(sl, HUB_LINES[hub], line_adj)
            transit[hub] = estimate_travel_time(dist, tr, params)
        results[slug] = transit

    # Stats
    for hub in HUBS:
        vals = [r[hub] for r in results.values()]
        print(f"  {hub}: min={min(vals)}, max={max(vals)}, avg={sum(vals)/len(vals):.0f}")

    # Validation against AI data
    if ai_transit:
        errors_by_hub = {h: [] for h in HUBS}
        large_errors = []
        for slug, truth in ai_transit.items():
            est = results.get(slug, {})
            for hub in HUBS:
                true_val = truth.get(hub)
                est_val = est.get(hub)
                if true_val is not None and est_val is not None:
                    err = est_val - true_val
                    errors_by_hub[hub].append(abs(err))
                    if abs(err) > 15:
                        large_errors.append((slug, hub, true_val, est_val, err))

        print(f"\nValidation vs {len(ai_transit)} AI entries:")
        all_errors = []
        for hub in HUBS:
            errs = errors_by_hub[hub]
            all_errors.extend(errs)
            print(f"  {hub}: MAE={sum(errs)/len(errs):.1f}, within 5min={sum(1 for e in errs if e <= 5)/len(errs)*100:.0f}%")
        print(f"  Overall MAE: {sum(all_errors)/len(all_errors):.1f} min")
        print(f"  Within 5 min: {sum(1 for e in all_errors if e <= 5)/len(all_errors)*100:.0f}%")
        print(f"  Within 10 min: {sum(1 for e in all_errors if e <= 10)/len(all_errors)*100:.0f}%")
        if large_errors:
            print(f"  Errors > 15 min: {len(large_errors)}")
            for slug, hub, true_val, est_val, err in sorted(large_errors, key=lambda x: -abs(x[4]))[:5]:
                print(f"    {slug} -> {hub}: true={true_val}, est={est_val}, err={err:+d}")

    # Output
    output = {
        "metadata": {
            "method": "geographic_estimation",
            "calibrated_against": f"{len(ai_transit)} AI-researched stations",
            "params": params,
            "snapshot_date": "2026-04",
            "assumption": "weekday morning, fastest available service",
        },
        "transit_times": results,
    }

    if args.dry_run:
        print("\nDry run — not writing file.")
        # Show sample
        for slug in ["mitaka", "gakugei-daigaku", "machida", "yokohama"]:
            if slug in results:
                print(f"  {slug}: {results[slug]}")
        return

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, indent=2, ensure_ascii=False))
    print(f"\nWrote {output_path} ({len(results)} stations)")


if __name__ == "__main__":
    main()
