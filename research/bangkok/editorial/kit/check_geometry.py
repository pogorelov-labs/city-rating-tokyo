#!/usr/bin/env python3
"""Point-in-polygon + haversine checks against the app's own polygons.

The unit definition is `geometry.json` (khet polygons) and
`station-geometry.json` (station-area catchments: Voronoi cell ∩ 800 m disc).
Both store rings as [lat, lng] pairs; station keys are unprefixed
(`nana`, not `st.nana`).

Usage:
  python3 check_geometry.py --entity nana --point 13.7463 100.5526 --label "Bumrungrad"
  python3 check_geometry.py --file points.json      # [{"name":"...","entity":"nana","lat":..,"lng":..}, ...]
  python3 check_geometry.py --entity nana --info
  python3 check_geometry.py --khet --entity chatuchak --info   # force khet lookup

B-8: keys that exist in BOTH station-geometry.json and geometry.json (e.g.
`chatuchak`) normally resolve to the station catchment; `--khet` forces the
khet/district ring (the batch-3 chatuchak agent's documented workaround).

Membership rule (HANDOFF + research guides): the app polygon decides
inside/outside — never raw radius. Distances are reported for context only.
"""
import argparse
import json
import math
import os

def repo_root(start):
    d = os.path.abspath(start)
    while d != os.path.dirname(d):
        if os.path.isdir(os.path.join(d, ".git")):
            return d
        d = os.path.dirname(d)
    raise SystemExit("repo root not found")

def load():
    root = repo_root(__file__)
    sg = json.load(open(os.path.join(root, "app/src/data/bangkok/station-geometry.json"), encoding="utf-8"))
    dg = json.load(open(os.path.join(root, "app/src/data/bangkok/geometry.json"), encoding="utf-8"))
    return sg, dg

def rings_for(src, key):
    try:
        g = src[key]["polygons"]
    except KeyError:
        raise SystemExit(f"unknown entity key {key!r} (station keys are unprefixed; district keys are slugs)")
    return [ring for part in g for ring in part]

def haversine(lat1, lng1, lat2, lng2):
    R = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def pip(point, ring):
    x, y = point  # x = lat, y = lng
    inside = False
    n = len(ring)
    for i in range(n):
        lat1, lng1 = ring[i]
        lat2, lng2 = ring[(i + 1) % n]
        if (lng1 > y) != (lng2 > y):
            xin = lat1 + (y - lng1) * (lat2 - lat1) / (lng2 - lng1)
            if x < xin:
                inside = not inside
    return inside

def center_of(rings):
    lats = [p[0] for r in rings for p in r]
    lngs = [p[1] for r in rings for p in r]
    return (sum(lats) / len(lats), sum(lngs) / len(lngs))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--entity", help="station id without 'st.' prefix, or district slug")
    ap.add_argument("--point", nargs=2, type=float, metavar=("LAT", "LNG"))
    ap.add_argument("--label", default="")
    ap.add_argument("--file", help="JSON file: [{name, entity, lat, lng}, ...]")
    ap.add_argument("--info", action="store_true", help="print center, bbox, ring size")
    ap.add_argument("--khet", action="store_true",
                    help="force khet/district geometry lookup (bypasses station-key shadowing)")
    args = ap.parse_args()

    sg, dg = load()
    tests = []
    if args.file:
        for t in json.load(open(args.file, encoding="utf-8")):
            tests.append((t.get("name", ""), t["entity"], t["lat"], t["lng"]))
    elif args.entity and args.point:
        tests.append((args.label, args.entity, args.point[0], args.point[1]))
    elif args.entity and args.info:
        src = dg if args.khet else (sg if args.entity in sg else dg)
        rings = rings_for(src, args.entity)
        c = center_of(rings)
        lats = [p[0] for r in rings for p in r]
        lngs = [p[1] for r in rings for p in r]
        print(f"{args.entity}: center≈({c[0]:.5f}, {c[1]:.5f}) "
              f"lat[{min(lats):.5f},{max(lats):.5f}] lng[{min(lngs):.5f},{max(lngs):.5f}] "
              f"rings={len(rings)} vertices={sum(len(r) for r in rings)}")
        return
    else:
        ap.error("provide --entity with --point/--info, or --file")

    for name, ent, lat, lng in tests:
        src = dg if args.khet else (sg if ent in sg else dg)
        rings = rings_for(src, ent)
        c = center_of(rings)
        d = haversine(c[0], c[1], lat, lng)
        inside = any(pip((lat, lng), r) for r in rings)
        print(f"{ent:16s} {name:44s} dist_from_ring_centroid={d:7.0f} m  in_polygon={inside}")

if __name__ == "__main__":
    main()
