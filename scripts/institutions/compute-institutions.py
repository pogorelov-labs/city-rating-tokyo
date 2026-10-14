#!/usr/bin/env python3
"""Compute per-area proximity counts for institutions (CRTKY-190).

Inputs (wave-4 snapshots):
  research/snapshots/2026-10-14/embassies/embassies-{tokyo,bangkok}.geojson
  research/snapshots/2026-10-14/medicine-jnto/medicine-jnto.json

Outputs:
  data/institutions/station-institutions.json   (Tokyo: per-station)
  data/institutions/district-institutions.json  (Bangkok: per-district + per-area)

Counts within walking range:
  embassies: 800 m (same as the station catchment convention)
  english_medicine: 2 km (clinics cluster; 800 m is too sparse outside central)

Attribution: OSM ODbL 1.0 (embassies), JNTO © (medicine — counts + link only,
no row republication).
"""

from __future__ import annotations

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SNAP = ROOT / "research" / "snapshots" / "2026-10-14"
OUT_DIR = ROOT / "data" / "institutions"

EMBASSY_RADIUS_M = 800
MEDICINE_RADIUS_M = 2000


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371000
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))


def count_nearby(points: list[tuple[float, float]], lat: float, lng: float, radius_m: int) -> int:
    return sum(1 for p_lat, p_lng in points if haversine_m(lat, lng, p_lat, p_lng) <= radius_m)


def load_embassies(city: str) -> list[tuple[float, float]]:
    g = json.loads((SNAP / "embassies" / f"embassies-{city}.geojson").read_text())
    out = []
    for f in g["features"]:
        c = f.get("geometry", {}).get("coordinates")
        if c and len(c) >= 2:
            out.append((c[1], c[0]))  # (lat, lng)
    return out


def load_medicine_tokyo() -> list[tuple[float, float]]:
    data = json.loads((SNAP / "medicine-jnto" / "medicine-jnto.json").read_text())
    out = []
    for r in data:
        if r.get("pref") != "Tokyo":
            continue
        if r.get("lat") and r.get("lon"):
            out.append((float(r["lat"]), float(r["lon"])))
    return out


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # ── Tokyo: per-station ─────────────────────────────────────────────
    emb_tky = load_embassies("tokyo")
    med_tky = load_medicine_tokyo()
    print(f"Tokyo: {len(emb_tky)} embassies, {len(med_tky)} English-speaking medical facilities")

    stations = json.loads((ROOT / "data" / "stations.json").read_text())
    station_out: dict[str, dict] = {}
    for s in stations:
        lat, lng = float(s["lat"]), float(s["lng"])
        e = count_nearby(emb_tky, lat, lng, EMBASSY_RADIUS_M)
        m = count_nearby(med_tky, lat, lng, MEDICINE_RADIUS_M)
        if e or m:
            station_out[s["slug"]] = {
                "embassies_within_800m": e,
                "english_medicine_within_2km": m,
            }
    print(f"  stations with data: {len(station_out)}/{len(stations)}")

    doc_tky = {
        "_meta": {
            "embassies": f"OSM office=diplomatic + Wikidata, {len(emb_tky)} POIs, ODbL 1.0 / CC0",
            "english_medicine": f"JNTO 'Guide for when you are feeling ill', {len(med_tky)} Tokyo facilities, © JNTO — counts only, no row republication",
            "computed": "2026-10-14",
        },
        "stations": station_out,
    }
    (OUT_DIR / "station-institutions.json").write_text(
        json.dumps(doc_tky, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    top_e = sorted(station_out.items(), key=lambda kv: -kv[1]["embassies_within_800m"])[:5]
    print("  top embassies:", [(k, v["embassies_within_800m"]) for k, v in top_e])

    # ── Bangkok: per-district + per-station-area ────────────────────────
    emb_bkk = load_embassies("bangkok")
    print(f"\nBangkok: {len(emb_bkk)} embassies")

    districts_doc = json.loads((ROOT / "app" / "src" / "data" / "bangkok" / "districts.json").read_text())
    districts = districts_doc.get("districts", districts_doc)
    district_out: dict[str, dict] = {}
    for d in districts:
        lat, lng = d["lat"], d["lng"]
        e = count_nearby(emb_bkk, lat, lng, EMBASSY_RADIUS_M)
        if e:
            district_out[d["slug"]] = {"embassies_within_800m": e}
    print(f"  districts with embassies: {len(district_out)}/{len(districts)}")

    areas_doc = json.loads((ROOT / "app" / "src" / "data" / "bangkok" / "stations.json").read_text())
    areas = areas_doc.get("areas", areas_doc)
    area_out: dict[str, dict] = {}
    for a in areas:
        lat, lng = a["lat"], a["lng"]
        e = count_nearby(emb_bkk, lat, lng, EMBASSY_RADIUS_M)
        if e:
            area_out[a["id"]] = {"embassies_within_800m": e}
    print(f"  station areas with embassies: {len(area_out)}/{len(areas)}")

    doc_bkk = {
        "_meta": {
            "embassies": f"OSM office=diplomatic + Wikidata, {len(emb_bkk)} POIs, ODbL 1.0 / CC0",
            "computed": "2026-10-14",
        },
        "districts": district_out,
        "station_areas": area_out,
    }
    (OUT_DIR / "district-institutions.json").write_text(
        json.dumps(doc_bkk, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    top_d = sorted(district_out.items(), key=lambda kv: -kv[1]["embassies_within_800m"])[:5]
    print("  top districts:", [(k, v["embassies_within_800m"]) for k, v in top_d])


if __name__ == "__main__":
    main()
