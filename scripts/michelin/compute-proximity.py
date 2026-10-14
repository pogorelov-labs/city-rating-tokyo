#!/usr/bin/env python3
"""Michelin proximity counts per station/district (CRTKY-191)."""
import json, math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
R = 6371000

def hav(lat1, lon1, lat2, lon2):
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(dlon/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

STAR_MAP = {"3 Stars": 3, "2 Stars": 2, "1 Star": 1, "Bib Gourmand": 0}

def load_pts(city):
    g = json.load(open(ROOT / f"research/snapshots/2026-10-14/michelin/michelin-{city}.geojson"))
    return [(f["geometry"]["coordinates"][1], f["geometry"]["coordinates"][0],
             STAR_MAP.get(f["properties"]["distinction"], 0), f["properties"]["distinction"])
            for f in g["features"] if f["geometry"] and f["geometry"].get("coordinates")]

def count(entries):
    return {
        "stars": sum(1 for p in entries if p[2] > 0),
        "max_stars": max(p[2] for p in entries) if entries else 0,
        "bib_gourmand": sum(1 for p in entries if p[3] == "Bib Gourmand"),
        "guide_year": "2026",
    }

pts_t = load_pts("tokyo")
stations = json.load(open(ROOT / "data" / "stations.json"))
out_t = {}
for s in stations:
    slat, slng = float(s["lat"]), float(s["lng"])
    in800 = [p for p in pts_t if hav(slat, slng, p[0], p[1]) <= 800]
    if in800:
        out_t[s["slug"]] = count(in800)

pts_b = load_pts("bangkok")
dd = json.load(open(ROOT / "app/src/data/bangkok/districts.json"))
districts = dd if isinstance(dd, list) else dd["districts"]
out_b = {}
for d in districts:
    in800 = [p for p in pts_b if hav(d["lat"], d["lng"], p[0], p[1]) <= 800]
    if in800:
        out_b[d["slug"]] = count(in800)

out_dir = ROOT / "data" / "michelin"
out_dir.mkdir(parents=True, exist_ok=True)
(out_dir / "proximity.json").write_text(json.dumps({
    "_meta": {
        "source": "guide.michelin.com 2026, © Michelin — factual data with attribution",
        "tokyo": f"{len(pts_t)} restaurants, {len(out_t)} stations",
        "bangkok": f"{len(pts_b)} restaurants, {len(out_b)} districts",
        "computed": "2026-10-15",
    },
    "stations": out_t,
    "districts": out_b,
}, ensure_ascii=False, indent=1) + "\n")
print(f"Wrote: {len(out_t)} Tokyo stations, {len(out_b)} Bangkok districts")
