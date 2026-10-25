#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["osmium>=4.3,<5", "shapely>=2.1,<3"]
# ///
"""Fetch all 12 Bangkok OSM caches from a single Geofabrik Thailand PBF.

    uv run scripts/bangkok/fetch-geofabrik.py
    uv run scripts/bangkok/fetch-geofabrik.py --pbf /path/to/thailand.osm.pbf

No Overpass requests. Other API inputs still use fetch.py --only; see README.md.
Reuses the checksummed download unless --refresh is given. Extraction always
replaces the complete OSM cache set, after validating all geometries/coverage.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from osm_filters import OSM_FILTERS, matches  # noqa: E402
from static_data import BBOX, RAIL_ROUTE_RELATIONS  # noqa: E402

RAW = Path(__file__).resolve().parents[2] / "data/bangkok/raw"
URL = "https://download.geofabrik.de/asia/thailand-latest.osm.pbf"
USER_AGENT = "city-rating-bangkok/1.0 (https://city-rating.pogorelov.dev; open-data research)"
ROUTE_IDS = {rid for ids in RAIL_ROUTE_RELATIONS.values() for rid in ids}
KINDS = {"n": "node", "w": "way", "r": "relation"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as src:
        while chunk := src.read(4 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_json(path: Path, payload: dict) -> None:
    part = path.with_name(path.name + ".part")
    part.write_text(json.dumps(payload, ensure_ascii=False) + "\n")
    part.replace(path)


def provenance(path: Path) -> dict:
    sidecar = path.with_suffix(path.suffix + ".source.json")
    meta = json.loads(sidecar.read_text()) if sidecar.exists() else {"local_file": path.name}
    actual = {"bytes": path.stat().st_size, "sha256": sha256(path)}
    for key, value in actual.items():
        if key in meta and meta[key] != value:
            raise ValueError(f"PBF {key} differs from {sidecar}; restore it or use --refresh")
    return {**meta, **actual, "license": "ODbL-1.0", "license_url": "https://www.openstreetmap.org/copyright"}


def download(path: Path, url: str, refresh: bool = False) -> dict:
    if path.exists() and not refresh:
        if not path.with_suffix(path.suffix + ".source.json").exists():
            raise ValueError("Cached PBF has no source manifest; use --pbf explicitly or --refresh")
        meta = provenance(path)
        if meta.get("requested_url") != url:
            raise ValueError("Cached PBF was fetched from a different URL; use --refresh or --pbf")
        return meta
    part = path.with_name(path.name + ".part")
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=120) as response, part.open("wb") as dest:
            length = response.headers.get("Content-Length")
            meta = {
                "requested_url": url, "resolved_url": response.url,
                "last_modified": response.headers.get("Last-Modified"),
                "content_length": int(length) if length else None,
            }
            while chunk := response.read(4 * 1024 * 1024):
                dest.write(chunk)
        size = part.stat().st_size
        if meta["content_length"] is not None and size != meta["content_length"]:
            raise ValueError(f"Short PBF download: {size} != {meta['content_length']}")
        meta.update(bytes=size, sha256=sha256(part), retrieved_at=utc_now(), license="ODbL-1.0")
        part.replace(path)
        atomic_json(path.with_suffix(path.suffix + ".source.json"), meta)
    finally:
        part.unlink(missing_ok=True)
    return provenance(path)


def in_bbox(point: dict, bbox: tuple = BBOX) -> bool:
    south, west, north, east = bbox
    return south <= point["lat"] <= north and west <= point["lon"] <= east


def way_intersects_bbox(points: list[dict], bbox: tuple = BBOX) -> bool:
    """Include vertices and crossing/touching segments in the Bangkok bbox."""
    if any(in_bbox(p, bbox) for p in points):
        return True
    south, west, north, east = bbox
    for start, end in zip(points, points[1:]):
        # Clip the segment's parameter interval [0, 1] against each axis.
        # Overlapping coordinate bounds alone would admit corner near-misses.
        enter, leave = 0.0, 1.0
        for key, lower, upper in (("lat", south, north), ("lon", west, east)):
            delta = end[key] - start[key]
            if delta == 0:
                if not lower <= start[key] <= upper:
                    break
            else:
                first, last = sorted(((lower - start[key]) / delta, (upper - start[key]) / delta))
                enter, leave = max(enter, first), min(leave, last)
                if enter > leave:
                    break
        else:
            return True
    return False


def center(points: list[dict]) -> dict:
    """Overpass out center: bounding-box midpoint, not vertex/polygon centroid."""
    if not points:
        raise ValueError("Cannot compute a center without coordinates")
    return {
        key: (min(p[key] for p in points) + max(p[key] for p in points)) / 2
        for key in ("lat", "lon")
    }


def member_geometry(members: list[dict], nodes: dict[int, dict], ways: dict[int, list[dict]]) -> list[dict]:
    """Copy ordered members, preserving roles and *complete* way geometries.

    Nested relations remain references, as in Overpass out geom. The builder
    consumes direct way members; out center also ignores nested relations.
    Missing direct members are fatal, never silently truncated.
    """
    result = []
    for member in members:
        out = dict(member)
        kind, ref = member["type"], member["ref"]
        if kind == "way":
            if ref not in ways or len(ways[ref]) < 2:
                raise ValueError(f"Missing/empty member way {ref}")
            out["geometry"] = ways[ref]
        elif kind == "node":
            if ref not in nodes:
                raise ValueError(f"Missing member node {ref}")
            out.update(lat=nodes[ref]["lat"], lon=nodes[ref]["lon"])
        result.append(out)
    return result


def element_points(element: dict) -> list[dict]:
    if element["type"] == "node":
        return [element]
    if element["type"] == "way":
        return element["geometry"]
    return [point for m in element["members"] for point in (
        m.get("geometry", []) if m["type"] == "way" else [m] if m["type"] == "node" else []
    )]


def point_element(element: dict) -> dict:
    out = {key: element[key] for key in ("type", "id", "tags")}
    if element["type"] == "node":
        out.update(lat=element["lat"], lon=element["lon"])
    else:
        out["center"] = center(element_points(element))
    return out


def append_filtered(outputs: dict[str, list], element: dict) -> None:
    for name, selectors in OSM_FILTERS.items():
        if matches(element["type"], element["tags"], selectors):
            outputs[name].append(element if name == "green" else point_element(element))


def select_bbox_way(outputs: dict[str, list], inside: dict[str, set], referenced_ways: set[int], way: dict) -> None:
    if not way_intersects_bbox(way["geometry"]):
        return
    if way["id"] in referenced_ways:
        inside["way"].add(way["id"])
    append_filtered(outputs, way)


def select_bbox_relations(relations: dict[int, dict], inside: dict[str, set], province_id: int) -> dict[int, dict]:
    # Way membership includes segment intersections, even without inside nodes.
    return {rid: r for rid, r in relations.items() if rid in ROUTE_IDS or rid == province_id or any(
        m["ref"] in inside.get(m["type"], ()) for m in r["members"]
    )}


def is_boundary(tags: dict, level: str) -> bool:
    return tags.get("boundary") == "administrative" and tags.get("admin_level") == level


def polygon(element: dict):
    """Same direct outer/inner line assembly as build.assemble_multipolygon."""
    from shapely.geometry import LineString
    from shapely.ops import polygonize, unary_union

    def rings(roles):
        lines = [LineString([(p["lon"], p["lat"]) for p in m["geometry"]])
                 for m in element["members"] if m["type"] == "way" and m["role"] in roles]
        return unary_union(list(polygonize(unary_union(lines))))

    geom = rings(("outer", "")).difference(rings(("inner",)))
    if geom.is_empty or not geom.is_valid:
        raise ValueError(f"Invalid administrative geometry: relation {element['id']}")
    return geom


def extract(path: Path) -> tuple[dict[str, list], dict]:
    import osmium

    with osmium.io.Reader(str(path)) as reader:
        timestamp = reader.header().get("osmosis_replication_timestamp")
    if not timestamp:
        raise ValueError("PBF has no osmosis_replication_timestamp; source date is required")
    outputs = {name: [] for name in (*OSM_FILTERS, "boundaries", "province", "rail_routes", "rail_stops")}

    # 1: relation inventory. All copies are ordinary Python values: pyosmium
    # objects become invalid as soon as the iterator advances.
    print("1/4: inventory candidate relations", flush=True)
    relations = {}
    for rel in osmium.FileProcessor(str(path), entities=osmium.osm.RELATION):
        tags = dict(rel.tags)
        if (rel.id in ROUTE_IDS or is_boundary(tags, "6")
                or (is_boundary(tags, "4") and tags.get("name:en") == "Bangkok")
                or any(matches("relation", tags, filters) for filters in OSM_FILTERS.values())):
            relations[rel.id] = {"type": "relation", "id": rel.id, "tags": tags, "members": [
                {"type": KINDS[m.type], "ref": m.ref, "role": m.role} for m in rel.members
            ]}
    missing_routes = ROUTE_IDS - relations.keys()
    if missing_routes:
        raise ValueError(f"PBF missing selected route relations: {sorted(missing_routes)}")
    provinces = [r for r in relations.values() if is_boundary(r["tags"], "4") and r["tags"].get("name:en") == "Bangkok"]
    if len(provinces) != 1:
        raise ValueError(f"Expected one Bangkok province relation, got {len(provinces)}")
    province_id = provinces[0]["id"]
    refs = {kind: {m["ref"] for r in relations.values() for m in r["members"] if m["type"] == kind}
            for kind in ("node", "way")}
    inside = {"node": set(), "way": set()}

    # 2: one compact libosmium location index, freed at end of pass. Retain
    # matched Bangkok elements, not every Thailand way geometry in Python.
    print("2/4: select bbox nodes/ways and relation membership", flush=True)
    processor = osmium.FileProcessor(str(path), entities=osmium.osm.NODE | osmium.osm.WAY).with_locations("flex_mem")
    for obj in processor:
        if obj.is_node():
            point = {"lat": obj.location.lat, "lon": obj.location.lon}
            if not in_bbox(point):
                continue
            if obj.id in refs["node"]:
                inside["node"].add(obj.id)
            append_filtered(outputs, {"type": "node", "id": obj.id, "tags": dict(obj.tags), **point})
        else:
            tags = dict(obj.tags)
            matched = any(matches("way", tags, filters) for filters in OSM_FILTERS.values())
            if obj.id not in refs["way"] and not matched:
                continue
            points = [{"lat": n.lat, "lon": n.lon} for n in obj.nodes]
            select_bbox_way(outputs, inside, refs["way"], {
                "type": "way", "id": obj.id, "tags": tags, "geometry": points,
            })
    del processor
    selected = select_bbox_relations(relations, inside, province_id)
    del relations, refs, inside

    # 3/4: now retrieve EVERY node of EVERY selected way, even outside the
    # bbox. A second location index is unnecessary: only these IDs are kept.
    way_ids = {m["ref"] for r in selected.values() for m in r["members"] if m["type"] == "way"}
    node_ids = {m["ref"] for r in selected.values() for m in r["members"] if m["type"] == "node"}
    print(f"3/4: resolve {len(way_ids):,} complete member ways for {len(selected):,} relations", flush=True)
    way_nodes = {}
    for way in osmium.FileProcessor(str(path), entities=osmium.osm.WAY):
        if way.id in way_ids:
            way_nodes[way.id] = [n.ref for n in way.nodes]
            node_ids.update(way_nodes[way.id])
    print(f"4/4: resolve {len(node_ids):,} member nodes", flush=True)
    nodes = {}
    for node in osmium.FileProcessor(str(path), entities=osmium.osm.NODE):
        if node.id in node_ids:
            nodes[node.id] = {"type": "node", "id": node.id, "tags": dict(node.tags),
                              "lat": node.location.lat, "lon": node.location.lon}
    if node_ids - nodes.keys() or way_ids - way_nodes.keys():
        raise ValueError(f"Incomplete PBF: {len(node_ids - nodes.keys())} nodes / {len(way_ids - way_nodes.keys())} ways missing")
    ways = {wid: [{"lat": nodes[n]["lat"], "lon": nodes[n]["lon"]} for n in ids] for wid, ids in way_nodes.items()}
    for rel in selected.values():
        rel["members"] = member_geometry(rel["members"], nodes, ways)
    province = selected[province_id]
    province_geom = polygon(province)
    outputs["province"] = [province]  # parity; build.py uses the district union
    for rel in selected.values():
        if is_boundary(rel["tags"], "6") and province_geom.covers(polygon(rel).representative_point()):
            outputs["boundaries"].append(rel)
        if rel["id"] in ROUTE_IDS:
            outputs["rail_routes"].append(rel)
        append_filtered(outputs, rel)
    stop_ids = {m["ref"] for rel in outputs["rail_routes"] for m in rel["members"] if m["type"] == "node"}
    outputs["rail_stops"] = [{"type": "node", "id": nid, "tags": nodes[nid]["tags"]} for nid in sorted(stop_ids)]
    districts = outputs["boundaries"]
    qids = [r["tags"].get("wikidata") for r in districts]
    if len(districts) != 50 or None in qids or len(set(qids)) != 50:
        raise ValueError(f"Expected 50 Bangkok khet with unique Wikidata IDs, got {len(districts)} / {len(set(qids))}")
    for name, elements in outputs.items():
        if not elements:
            raise ValueError(f"Empty required OSM output: {name}")
        elements.sort(key=lambda e: ({"node": 0, "way": 1, "relation": 2}[e["type"]], e["id"]))
    return outputs, {"timestamp_osm_base": timestamp, "bbox": BBOX}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--pbf", type=Path, help="use a local PBF without downloading")
    parser.add_argument("--url", default=URL, help="Geofabrik download URL (can pin a dated extract)")
    parser.add_argument("--refresh", action="store_true", help="replace the cached download from --url")
    parser.add_argument("--download-only", action="store_true", help="download/verify PBF without extracting")
    args = parser.parse_args()
    if args.pbf and args.refresh:
        parser.error("--refresh cannot be combined with --pbf")
    RAW.mkdir(parents=True, exist_ok=True)
    path = args.pbf or RAW / "thailand.osm.pbf"
    started = time.monotonic()
    source = provenance(path) if args.pbf else download(path, args.url, args.refresh)
    print(f"PBF: {source['bytes']:,} bytes, SHA-256 {source['sha256']}", flush=True)
    if args.download_only:
        return
    outputs, header = extract(path)
    source.update(header, extracted_at=utc_now(), counts={k: len(v) for k, v in outputs.items()})
    for name, elements in outputs.items():
        payload = {"version": 0.6, "generator": "city-rating Geofabrik/pyosmium", "osm3s": {
            "timestamp_osm_base": header["timestamp_osm_base"]}, "_fetched_at": source["extracted_at"],
            "_source": source, "elements": elements}
        atomic_json(RAW / f"{name}.json", payload)
        print(f"✓ {name}: {len(elements):,} elements", flush=True)
    atomic_json(RAW / "geofabrik-source.json", source)
    print(f"Completed in {time.monotonic() - started:.1f}s; all OSM inputs share one snapshot", flush=True)


if __name__ == "__main__":
    main()
