"""Validate a status-bearing OSM census and freeze a held-out station design.

No network, credentials, scoring, or database access. Counts describe mapped
node/way food features, not verified independent physical businesses.
"""
from __future__ import annotations

import hashlib
import math
from datetime import datetime, timezone

SEED = "crtky194-food-v1"
RADIUS_M = 800
PREFECTURES = ("13", "14", "11", "12")
FOOD = {"restaurant", "cafe", "fast_food"}


def tile_plan(stations):
    """Eight rectangles cover every complete 800 m spherical catchment.

    Rounding expands rather than contracts the envelope. Food ways use their
    bbox center after acquisition, matching the declared mapped-feature unit.
    """
    if not stations:
        raise ValueError("Empty station frame")
    pads = []
    angular = RADIUS_M / 6371000
    for station in stations:
        lat, lng = point(station["lat"], station["lng"]).values()
        if not (34 <= lat <= 37 and 138 <= lng <= 142):
            raise ValueError("Station outside Tokyo pilot geography")
        lat_pad = math.degrees(angular)
        lng_pad = math.degrees(math.asin(math.sin(angular) / math.cos(math.radians(lat))))
        pads.append((lat - lat_pad, lng - lng_pad, lat + lat_pad, lng + lng_pad))
    south = math.floor(min(p[0] for p in pads) * 1e6) / 1e6
    west = math.floor(min(p[1] for p in pads) * 1e6) / 1e6
    north = math.ceil(max(p[2] for p in pads) * 1e6) / 1e6
    east = math.ceil(max(p[3] for p in pads) * 1e6) / 1e6
    lat_edges = [south, (south + north) / 2, north]
    lng_edges = [west + (east - west) * i / 4 for i in range(5)]
    tiles = []
    for y in range(2):
        for x in range(4):
            bbox = [lat_edges[y], lng_edges[x], lat_edges[y + 1], lng_edges[x + 1]]
            bb = ",".join(str(v) for v in bbox)
            query = ('[out:json][timeout:90];('
                     f'node["amenity"~"^(restaurant|cafe|fast_food)$"]({bb});'
                     f'way["amenity"~"^(restaurant|cafe|fast_food)$"]({bb});'
                     ');out center tags;')
            tiles.append({"id": f"{y}-{x}", "bbox": bbox, "query": query,
                          "query_sha256": hashlib.sha256(query.encode()).hexdigest()})
    return {"bbox": [south, west, north, east], "tiles": tiles,
            "covered_catchments": len(pads), "radius_m": RADIUS_M,
            "coverage_proof": "contiguous 2x4 rectangular partition of outward-rounded spherical catchment envelopes"}


def distance(a, b):
    lat1, lat2 = math.radians(a["lat"]), math.radians(b["lat"])
    dlat = lat2 - lat1
    dlon = math.radians(b["lng"] - a["lng"])
    v = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 6371000 * 2 * math.asin(min(1, math.sqrt(v)))


def timestamp(value):
    if not isinstance(value, str):
        raise ValueError("Missing source timestamp")
    stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if stamp.tzinfo is None:
        raise ValueError("Source timestamp must include timezone")
    return stamp.astimezone(timezone.utc)


def point(lat, lng):
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v)
           for v in (lat, lng)) or not (-90 <= lat <= 90 and -180 <= lng <= 180):
        raise ValueError("Missing or invalid coordinates; cannot infer a zero")
    return {"lat": lat, "lng": lng}


def validate_osm(doc):
    """Reject partial payloads, including HTTP200 runtime remarks and bad points."""
    if not isinstance(doc, dict) or doc.get("remark") or not isinstance(doc.get("elements"), list):
        raise ValueError("Incomplete OSM response")
    stamp = timestamp(doc.get("osm3s", {}).get("timestamp_osm_base"))
    features = {}
    for row in doc["elements"]:
        if row.get("type") not in {"node", "way"} or row.get("tags", {}).get("amenity") not in FOOD:
            raise ValueError("Unexpected feature outside the frozen food contract")
        identity = row.get("id")
        if isinstance(identity, bool) or not isinstance(identity, int) or identity < 1:
            raise ValueError("Invalid OSM identity")
        coordinates = row if row["type"] == "node" else row.get("center", {})
        feature = {"id": f'{row["type"]}/{identity}',
                   **point(coordinates.get("lat"), coordinates.get("lon")),
                   "amenity": row["tags"]["amenity"]}
        if feature["id"] in features and features[feature["id"]] != feature:
            raise ValueError("Conflicting duplicate OSM identity")
        features[feature["id"]] = feature
    return stamp, features


def census(stations, tiles, expected_tile_ids, acquired_at):
    """Caller supplies a frozen covering tiling; missing tiles never yield zeros."""
    if len({t["id"] for t in tiles}) != len(tiles) or {t["id"] for t in tiles} != set(expected_tile_ids):
        raise ValueError("Incomplete or duplicate tile set")
    if not tiles:
        raise ValueError("Empty census")
    plan = {t["id"]: t for t in tile_plan(stations)["tiles"]}
    if set(expected_tile_ids) != set(plan):
        raise ValueError("Tile IDs differ from the covering station plan")
    now = timestamp(acquired_at)
    points, stamps = {}, []
    for tile in tiles:
        if tile.get("query_sha256") != plan[tile["id"]]["query_sha256"] or tile.get("bbox") != plan[tile["id"]]["bbox"]:
            raise ValueError("Tile geometry/query does not cover the frozen station frame")
        stamp, features = validate_osm(tile["response"])
        if not 0 <= (now - stamp).total_seconds() <= 7 * 86400:
            raise ValueError("OSM source timestamp outside the seven-day window")
        stamps.append(stamp)
        for identity, feature in features.items():
            if identity in points and points[identity] != feature:
                raise ValueError("Conflicting overlapping-tile feature")
            points[identity] = feature
    if len({s["slug"] for s in stations}) != len(stations):
        raise ValueError("Duplicate station slug")
    rows = []
    for station in stations:
        point(station["lat"], station["lng"])
        count = sum(distance(station, feature) <= RADIUS_M for feature in points.values()
                    if abs(station["lat"] - feature["lat"]) <= .008
                    and abs(station["lng"] - feature["lng"]) <= .01)
        rows.append({"slug": station["slug"], "count": count,
                     "status": "complete_zero" if count == 0 else "complete_positive",
                     "osm_base_min": min(stamps).isoformat(), "osm_base_max": max(stamps).isoformat(),
                     "radius_m": RADIUS_M, "count_unit": "mapped_food_feature"})
    return rows


def hash_order(slug):
    return hashlib.sha256(f"{SEED}|{slug}".encode()).hexdigest(), slug


def freeze_sample(stations, rows, old_centers):
    """Conservative deterministic selection; insufficiency is not proof of impossibility.

    Require all selected core circles to be disjoint (stronger than cross-split
    separation). Greedy exhaustion is reported, never repaired using outcomes.
    """
    source = {r["slug"]: r for r in rows}
    if len(source) != len(rows):
        raise ValueError("Duplicate census slug")
    eligible = []
    for station in stations:
        row = source.get(station["slug"], {})
        count = row.get("count")
        if row.get("status") not in {"complete_zero", "complete_positive"}:
            continue
        if isinstance(count, bool) or not isinstance(count, int) or count < 0 or row.get("radius_m") != RADIUS_M:
            raise ValueError("Invalid census count or radius")
        if (count == 0) != (row["status"] == "complete_zero"):
            raise ValueError("Inconsistent zero status")
        point(station["lat"], station["lng"])
        eligible.append({**station, "osm_food_count": count})
    boundaries, cells, selected, exclusions = {}, [], [], []
    for prefecture in PREFECTURES:
        pool = [s for s in eligible if s["prefecture"] == prefecture]
        values = sorted(s["osm_food_count"] for s in pool if s["osm_food_count"] > 0)
        if len(values) < 3:
            return {"status": "insufficient", "reason": "positive strata unavailable", "prefecture": prefecture}
        low, high = values[math.ceil(len(values) / 3) - 1], values[math.ceil(2 * len(values) / 3) - 1]
        if low == high or high == values[-1]:
            return {"status": "insufficient", "reason": "ties prevent three positive strata", "prefecture": prefecture}
        boundaries[prefecture] = [low, high]
        for station in pool:
            count = station["osm_food_count"]
            station["stratum"] = "zero" if count == 0 else "low" if count <= low else "middle" if count <= high else "high"
        for stratum in ("zero", "low", "middle", "high"):
            candidates = sorted((s for s in pool if s["stratum"] == stratum), key=lambda s: hash_order(s["slug"]))
            chosen = []
            for station in candidates:
                if any(distance(station, other) <= 2 * RADIUS_M for other in old_centers + selected):
                    exclusions.append(station["slug"])
                    continue
                chosen.append(station)
                selected.append(station)
                if len(chosen) == 4:
                    break
            cells.append({"prefecture": prefecture, "stratum": stratum,
                          "available": len(candidates), "selected": [s["slug"] for s in chosen],
                          "reserve_order": [s["slug"] for s in candidates if s not in chosen]})
            for i, station in enumerate(chosen):
                station["split"] = "development" if i < 2 else "holdout"
    complete = len(selected) == 64
    return {"status": "frozen" if complete else "insufficient", "seed": SEED,
            "reason": None if complete else "fixed greedy spatial design did not fill every cell; no outcome-driven replacement",
            "boundaries": boundaries, "cells": cells, "stations": selected,
            "spatially_excluded": sorted(set(exclusions)),
            "count_unit": "mapped_food_feature", "physical_deduplication": "not established"}
