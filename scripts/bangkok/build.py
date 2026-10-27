#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy>=2", "shapely>=2.1", "duckdb>=1.1", "rasterio>=1.4,<2"]
# ///
"""Build the Bangkok district dataset from the raw dumps fetched by fetch.py.

    uv run scripts/bangkok/fetch.py     # once (network, cached)
    uv run scripts/bangkok/build.py     # offline, ~20 s
    uv run scripts/bangkok/build.py --rent-only  # use committed spatial outputs

Unit of rating = khet (district), all 50. Instead of counting POIs inside a
boundary (which rewards big districts and ignores what lies just across a
border), every district is covered by a 200 m sample grid; each sample point
records what a resident standing there can reach — POIs within walking radius,
distance to rail, park hectares within 1 km, modelled commute to five hubs.
The district's raw signal is the *resident-weighted* mean of its points:
points near shops/food count fully, empty paddy fields and river water barely
(`inhabited_weight`). Signals are then percentile-normalised across the 50
districts exactly like Tokyo's stations (scripts/bangkok/ratings.py).

POI signals blend two independent sources — OpenStreetMap and Overture Maps
Places (Meta/Microsoft/Foursquare/AllThePlaces) — the way Tokyo blends
HotPepper with OSM; a category is `strong` only where both are well mapped.

Rent and safety have no open district-level source: they come from
data/bangkok/editorial.json and are labelled `editorial` in the UI.

Three levels of detail share that grid:
  * districts — the 50 khet, as above;
  * station areas — the walkable catchment of each rail station inside
    Bangkok (nearest-station cell within AREA_RADIUS_M; interchange pairs such
    as Asok + Sukhumvit form one area), percentile-normalised across areas;
  * grid cells — every 200 m point itself, rated by resident-weighted
    percentile across the city (a block rates 8 when it beats ~75 % of the
    places people live, not of paddy fields).
Safety stays district-level (blended by resident weight across borders).
Station rents use documented rent-overrides.json proxies where available,
otherwise the resident-weighted district blend. Grid rent stays district-level.

Outputs
  app/src/data/bangkok/districts.json  — app data (ratings, facts, names, …)
  app/src/data/bangkok/geometry.json   — simplified polygons + label points
  app/src/data/bangkok/stations.json   — station areas (ratings, facts, names, …)
  app/src/data/bangkok/station-geometry.json — station-area polygons
  app/src/data/bangkok/grid.json       — 200 m grid header (index lists, medians)
  app/public/data/bangkok/grid-<hash>.bin — 200 m grid cells (packed, gzip)
  app/src/data/bangkok/rail.json       — rail lines (paths) + stations
  app/src/data/bangkok/meta.json       — medians, composite anchors, counts
  data/bangkok/signals.json            — raw per-district / per-area signals (audit trail)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import shapely
from shapely.ops import unary_union

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from bangkok import ratings as R  # noqa: E402
from bangkok.bkk_config import ROOT, DATA, APP, SCHEMA_CONSTANTS, GRID_M, CELL_M  # noqa: E402
from bangkok.geom import xy, simplify_coverage, polygon_to_latlng  # noqa: E402
from bangkok.rasters import Raster, rasterize  # noqa: E402
from bangkok.sources import (  # noqa: E402
    load, load_districts, load_pois, load_green, load_overture,
    commons_image, attach_station_wikidata,
)
from bangkok.rail import build_rail, transit_model  # noqa: E402
from bangkok.rents import refresh_committed_rents  # noqa: E402
from bangkok.population import load_population  # noqa: E402
from bangkok.static_data import BBOX, LINES, RAIL_ROUTE_RELATIONS  # noqa: E402
from bangkok.signal_grid import SignalGrid, build_point_signals  # noqa: E402
from bangkok.districts import build_district_data  # noqa: E402
from bangkok.outputs import build_documents, build_metadata_and_signals  # noqa: E402
from bangkok.areas import aggregate_station_areas, build_station_areas  # noqa: E402
from bangkok.gridpack import pack_grid, rate_grid  # noqa: E402
from bangkok.report import print_report, write_outputs  # noqa: E402

# ────────────────────────────────── main ─────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="compute and print, write nothing")
    parser.add_argument("--inputs-manifest", type=Path, help="verify frozen inputs and use its build date")
    parser.add_argument("--verbose", action="store_true", help="print every district's ratings")
    parser.add_argument("--rent-only", action="store_true", help="refresh rent from committed spatial outputs; rejects district rent changes")
    args = parser.parse_args()
    started = time.time()
    frozen = None
    if args.inputs_manifest:
        from bangkok.refresh_inputs import verify_inputs
        frozen = verify_inputs(ROOT, args.inputs_manifest)

    schema = json.loads(SCHEMA_CONSTANTS.read_text())
    default_weights = schema["default_weights"]
    editorial_doc = json.loads((DATA / "editorial.json").read_text())
    editorial = editorial_doc["districts"]
    rent_meta = editorial_doc["_meta"]["rent"]
    rent_overrides = json.loads((DATA / "rent-overrides.json").read_text())
    if args.rent_only:
        paths = [APP / "districts.json", APP / "stations.json", APP / "meta.json", APP / "grid.json", DATA / "signals.json"]
        originals = [p.read_text() for p in paths]
        docs = [json.loads(text) for text in originals]
        packed = (ROOT / "app" / "public" / docs[3]["file"].lstrip("/")).read_bytes()
        if len(packed) != docs[3]["bytes"] or hashlib.sha256(packed).hexdigest()[:12] not in docs[3]["file"]:
            raise ValueError("Committed grid binary does not match its header")
        refresh_committed_rents(editorial_doc, rent_overrides, *docs, R, default_weights)
        if not args.dry_run:
            for path, doc, original in zip(paths, docs, originals):
                compact = "\n" not in original.rstrip("\n")
                indent = None if compact else (2 if path.name == "meta.json" else 1)
                path.write_text(json.dumps(doc, ensure_ascii=False, indent=indent,
                                           separators=(",", ":") if compact else None) + "\n")
                print(f"  wrote {path.relative_to(ROOT)}")
        print(f"Rent refresh: {len(docs[0]['districts'])} districts, {len(docs[1]['areas'])} areas, "
              f"{len(rent_overrides['areas'])} overrides; grid binary unchanged ({hashlib.sha256(packed).hexdigest()[:12]})")
        return
    flood_doc = json.loads((DATA / "flood.json").read_text())
    flood = flood_doc["districts"]

    def flood_exposed(f: dict) -> bool:
        """Flood dealbreaker flag: ≥30 reported episodes 2021–2026 (22/50
        districts) OR ≥50% of the district flooded in 2011 (GISTDA satellite;
        covers districts with ~0 recent reports — Nong Chok, Thawi Watthana).
        The two signals are complementary, not redundant (research note §1.2)."""
        return f["episodes_total"] >= 30 or (f["share_flooded_2011_pct"] or 0) >= 50

    print("→ districts")
    districts = load_districts()
    # Use the same published, rounded polygons as the adoption comparison.
    # Summing the original unsimplified boundaries would introduce a second,
    # undocumented methodological change relative to CRTKY-140 research.
    population_geometry = {
        d["slug"]: {"polygons": [polygon_to_latlng(p) for p in g.geoms]}
        for d, g in zip(districts, simplify_coverage([d["geom"] for d in districts]))
    }
    population, population_summary = load_population(population_geometry, {d["slug"] for d in districts})
    print(f"  WorldPop: {len(population)} districts, {population_summary['population']:,.0f} people (2020 model)")
    missing_editorial = {d["slug"] for d in districts} - set(editorial)
    assert not missing_editorial, f"editorial.json missing {missing_editorial}"
    missing_flood = {d["slug"] for d in districts} - set(flood)
    assert not missing_flood, f"flood.json missing {missing_flood} — run scripts/bangkok/fetch-flood.py"
    for d in districts:
        area = d["geom"].area / 1e6
        wd_area = d["wd"]["area_km2"]
        if wd_area and abs(area - wd_area) / wd_area > 0.12:
            print(f"  note: {d['slug']} polygon {area:.1f} km² vs Wikidata {wd_area:.1f} km²")

    print("→ sample grid")
    province = unary_union([d["geom"] for d in districts])
    minx, miny, maxx, maxy = province.bounds
    gx = np.arange(minx + GRID_M / 2, maxx, GRID_M)
    gy = np.arange(miny + GRID_M / 2, maxy, GRID_M)
    GX, GY = np.meshgrid(gx, gy)
    GX, GY = GX.ravel(), GY.ravel()
    owner = np.full(GX.shape, -1)
    for i, d in enumerate(districts):
        inside = shapely.contains_xy(d["geom"], GX, GY)
        owner[inside & (owner < 0)] = i
    keep = owner >= 0
    PX, PY, OWN = GX[keep], GY[keep], owner[keep]
    print(f"  {len(PX):,} sample points ({GRID_M} m)")

    print("→ POIs + green rasters")
    s0, w0, n0, e0 = BBOX
    rx0, ry0 = xy(w0, s0)
    rx1, ry1 = xy(e0, n0)
    raster = Raster((rx0, ry0, rx1, ry1), CELL_M)
    pois = load_pois()
    pois.update(load_overture())
    H = {cat: raster.hist(*pts) for cat, pts in pois.items()}
    pool_h = H.get("pool", np.zeros((raster.ny, raster.nx)))

    signal_grid = SignalGrid(raster, H, PX, PY)
    near = signal_grid.near

    parks, green = load_green()
    park_r = rasterize(parks, raster)
    big_park_r = rasterize(parks, raster, min_area=10_000)
    green_r = rasterize(green, raster)
    cell_ha = CELL_M * CELL_M / 10_000
    park_ha_1k = raster.sample(raster.within(park_r, 1000), PX, PY) * cell_ha
    green_ha_1k = raster.sample(raster.within(green_r, 1000), PX, PY) * cell_ha
    d_park = np.full(len(PX), 3000.0)
    for radius in (2500, 1500, 1000, 700, 400, 200):
        has = raster.sample(raster.within(big_park_r, radius), PX, PY) > 0
        d_park[has] = radius

    # Resident weighting: a point "counts" once ≥ 10 shops / eateries / clinics
    # (both sources) are within 500 m — a proxy for built-up, inhabited land
    # (7-Elevens are wherever people live). Saturation stops dense cores from
    # dominating; empty paddy fields and river water keep a 0.1 floor.
    activity = sum(near(p + c, 500) for p in ("", "ovt_") for c in ("food", "grocery", "health"))
    weight = 0.1 + 0.9 * np.minimum(1.0, activity / 10.0)

    print("→ rail network + commute model")
    stations, sequences, tracks = build_rail(districts, RAIL_ROUTE_RELATIONS)
    attach_station_wikidata(stations)
    hub_times = transit_model(stations, sequences)
    signal_grid.stations = stations
    signal_grid.hub_times = hub_times
    SX = np.array([s["x"] for s in stations])
    SY = np.array([s["y"] for s in stations])
    commute_at = signal_grid.commute_at

    D = np.hypot(PX[:, None] - SX[None, :], PY[:, None] - SY[None, :])  # points × stations
    d_station = D.min(axis=1)
    # distinct lines with a station within 1.5 km of each point
    line_ids = list(LINES)
    lines_near = np.zeros(len(PX))
    for lid in line_ids:
        cols = [j for j, s in enumerate(stations) if lid in s["lines"]]
        if cols:
            lines_near += (D[:, cols].min(axis=1) <= 1500).astype(float)
    commute_pt = commute_at(PX, PY, D)
    commute_min_pt = np.min(np.vstack(list(commute_pt.values())), axis=0)

    pt, pt_crowd = build_point_signals(signal_grid, pool_h, park_ha_1k, green_ha_1k,
                                       d_park, d_station, lines_near, commute_min_pt)

    raw, agg, ratings, medians, anchors, TWO_SOURCE, conf_and_sources, count_inside = build_district_data(
        districts, pt, OWN, weight, commute_pt, d_station, pois, parks, population,
        editorial, default_weights, rent_meta, stations)

    # Images (Wikimedia Commons via Wikidata P18)
    commons = load("commons")["pages"]

    def image_for(d: dict) -> dict | None:
        return commons_image(d["wd"]["image"], commons)

    def description_for(slug: str) -> dict | None:
        path = DATA / "descriptions" / f"{slug}.json"
        if not path.exists():
            return None
        desc = json.loads(path.read_text())
        for lang in ("en", "ja", "ru"):
            fields = desc.get(lang, {})
            assert all(fields.get(k) for k in ("atmosphere", "landmarks", "food", "nightlife")), f"{slug}.{lang} incomplete"
        return {lang: {k: desc[lang][k].strip() for k in ("atmosphere", "landmarks", "food", "nightlife")}
                for lang in ("en", "ja", "ru")}

    # ───────────────────────────── station areas ─────────────────────────────
    print("→ station areas")
    rated, areas, AREA, area_geoms, area_simplified = build_station_areas(
        stations, D, province, rent_overrides)

    area_raw, area_agg, area_rents, area_ratings, area_neighbors, station_medians, station_anchors = aggregate_station_areas(
        areas, AREA, PX, PY, weight, pt, pt_crowd, OWN, districts, editorial, stations,
        commute_at, commute_pt, rent_meta, rent_overrides, area_geoms, parks, count_inside,
        sequences, default_weights)

    # ─────────────────────────────── 200 m grid ──────────────────────────────
    print("→ grid ratings")
    grid_ratings, encoded_weights, grid_medians, grid_anchors = rate_grid(
        weight, pt, pt_crowd, ratings, districts, OWN, PX, default_weights)

    today, data_date, out_districts, geometry, rail_lines, rail_stations, out_areas, station_geometry = build_documents(
        frozen, districts, editorial, conf_and_sources, ratings, agg, rent_meta, flood,
        flood_exposed, description_for, image_for, tracks, stations, areas, area_agg,
        area_ratings, area_rents, area_neighbors, area_simplified)

    # 200 m grid, packed for the browser: one uint8 plane per field over the
    # full nx × ny bbox (rows north → south, 0 = outside Bangkok), each row
    # delta-coded (mod 256) so gzip sees long zero runs, then gzip'd.
    print("→ grid export")
    nx, ny, grid_packed, grid_file, grid_header = pack_grid(
        gx, gy, PX, PY, OWN, encoded_weights, commute_pt, stations, D,
        d_station, AREA, grid_ratings, districts, areas, grid_medians,
        grid_anchors, data_date)

    source_agreement, meta, signals = build_metadata_and_signals(
        TWO_SOURCE, districts, rail_stations, medians, anchors, areas, station_medians,
        station_anchors, PX, grid_medians, grid_anchors, rent_overrides, data_date,
        out_districts, out_areas, today, raw, population, count_inside, ratings, agg,
        area_raw, area_ratings, area_agg)

    print_report(districts, ratings, medians, anchors, source_agreement, out_districts,
                 default_weights, rail_stations, meta, rail_lines, agg, areas, rated,
                 area_agg, station_medians, area_ratings, stations, PX, nx, ny,
                 grid_packed, grid_medians, grid_anchors, args.verbose)

    if args.dry_run:
        print("\n(dry run — nothing written)")
        return

    write_outputs(today, rent_overrides, out_districts, geometry, rail_lines, rail_stations,
                  out_areas, station_geometry, grid_header, grid_file, grid_packed,
                  meta, signals, started)

if __name__ == "__main__":
    main()
