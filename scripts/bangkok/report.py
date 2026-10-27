"""Human-readable build summary and deterministic artifact writing."""
from __future__ import annotations
import json
import time
from collections import defaultdict
from pathlib import Path
import bangkok.ratings as R
from bangkok.bkk_config import APP, DATA, PUBLIC, ROOT, RATING_KEYS
from bangkok.population import population_metadata
from bangkok.rents import rent_audit


def print_report(districts, ratings, medians, anchors, source_agreement, out_districts,
                 default_weights, rail_stations, meta, rail_lines, agg, areas, rated,
                 area_agg, station_medians, area_ratings, stations, PX, nx, ny,
                 grid_packed, grid_medians, grid_anchors, verbose):
    # ── report ──
    print("\nRating distribution (value:count):")
    for k in RATING_KEYS:
        dist = defaultdict(int)
        for d in districts:
            dist[ratings[d["slug"]][k]] += 1
        print(f"  {k:17s} median {medians[k]:>2}  " + " ".join(f"{v}:{dist[v]}" for v in sorted(dist)))
    print(f"\nComposite anchors (default weights): {anchors}")
    print(f"OSM↔Overture agreement (Pearson r of log density per district): {source_agreement}")
    conf_counts = defaultdict(lambda: defaultdict(int))
    for od in out_districts:
        for k, v in od["confidence"].items():
            conf_counts[k][v] += 1
    print("Confidence:", {k: dict(v) for k, v in conf_counts.items()})
    top = sorted(districts, key=lambda d: -R.composite(ratings[d["slug"]], default_weights))
    print("Top 8:", ", ".join(f"{d['slug']} {R.composite(ratings[d['slug']], default_weights)}" for d in top[:8]))
    print("Bottom 5:", ", ".join(f"{d['slug']} {R.composite(ratings[d['slug']], default_weights)}" for d in top[-5:]))
    print(f"Stations: {len(rail_stations)} ({meta['stations_in_bangkok']} inside Bangkok), lines: {len(rail_lines)}")
    for slug in ("pathum-wan", "watthana", "phaya-thai", "chatuchak", "bang-na", "lat-krabang", "nong-chok"):
        a = agg[slug]
        print(f"  {slug:14s} {ratings[slug]}  hubs={a['hub_minutes']}")

    print(f"\nStation areas: {len(areas)} (from {len(rated)} stations inside Bangkok; "
          f"{sum(len(a['members']) > 1 for a in areas)} interchange complexes)")
    print("  interchanges:", ", ".join(a["name_en"] for a in areas if len(a["members"]) > 1))
    pts_per_area = sorted(area_agg[a["id"]]["points"] for a in areas)
    print(f"  grid points per area: min {pts_per_area[0]}, median {pts_per_area[len(pts_per_area) // 2]}, max {pts_per_area[-1]}")
    for k in RATING_KEYS:
        dist = defaultdict(int)
        for a in areas:
            dist[area_ratings[a["id"]][k]] += 1
        print(f"  {k:17s} median {station_medians[k]:>2}  " + " ".join(f"{v}:{dist[v]}" for v in sorted(dist)))
    area_top = sorted(areas, key=lambda a: -R.composite(area_ratings[a["id"]], default_weights))
    print("  top 10:", ", ".join(f"{a['id']} {R.composite(area_ratings[a['id']], default_weights)}" for a in area_top[:10]))
    print("  bottom 5:", ", ".join(f"{a['id']} {R.composite(area_ratings[a['id']], default_weights)}" for a in area_top[-5:]))
    conf_counts = defaultdict(lambda: defaultdict(int))
    for a in areas:
        for k, v in a["confidence"].items():
            conf_counts[k][v] += 1
    print("  confidence:", {k: dict(v) for k, v in conf_counts.items() if k in ("food", "nightlife", "daily_essentials", "gym_sports", "vibe")})
    missing_ja = [st["id"] for st in stations if st["district"] and not st["name_ja"]]
    print(f"  stations without a Japanese name: {missing_ja or 'none'}")
    print(f"\nGrid: {len(PX):,} cells, {nx}×{ny}, packed {len(grid_packed) / 1024:.0f} KB; medians {grid_medians}; "
          f"anchors {grid_anchors}")

    if verbose:
        print("\nAll districts (composite · ratings · min commute):")
        for d in top:
            r = ratings[d["slug"]]
            cells = " ".join(f"{k[:4]}={r[k]:>2}" for k in RATING_KEYS)
            print(f"  {d['slug']:22s} {R.composite(r, default_weights):4.1f}  {cells}  min={agg[d['slug']]['min_transit']:>3}")



def write_outputs(today, rent_overrides, out_districts, geometry, rail_lines, rail_stations,
                  out_areas, station_geometry, grid_header, grid_file, grid_packed,
                  meta, signals, started):
    APP.mkdir(parents=True, exist_ok=True)

    def dump(path: Path, obj, indent: int | None = None):
        path.write_text(json.dumps(obj, ensure_ascii=False, indent=indent, separators=None if indent else (",", ":")) + "\n")
        print(f"  wrote {path.relative_to(ROOT)} ({path.stat().st_size / 1024:.0f} KB)")

    dump(APP / "districts.json", {"_meta": {"generated": today.isoformat(), "source": "scripts/bangkok/build.py",
                                             "population": population_metadata(), "rent_audit": rent_audit(rent_overrides)},
                                  "districts": out_districts}, indent=1)
    dump(APP / "geometry.json", geometry)
    dump(APP / "rail.json", {"lines": rail_lines, "stations": rail_stations})
    dump(APP / "stations.json", {"_meta": {"generated": today.isoformat(), "source": "scripts/bangkok/build.py", "rent_audit": rent_audit(rent_overrides)},
                                 "areas": out_areas}, indent=1)
    dump(APP / "station-geometry.json", station_geometry)
    dump(APP / "grid.json", grid_header, indent=1)
    PUBLIC.mkdir(parents=True, exist_ok=True)
    for old in PUBLIC.glob("grid-*.bin"):
        if old.name != grid_file:
            old.unlink()
    (PUBLIC / grid_file).write_bytes(grid_packed)
    print(f"  wrote {(PUBLIC / grid_file).relative_to(ROOT)} ({len(grid_packed) / 1024:.0f} KB)")
    dump(APP / "meta.json", meta, indent=2)
    dump(DATA / "signals.json", signals, indent=1)
    print(f"\nDone in {time.time() - started:.1f}s")
