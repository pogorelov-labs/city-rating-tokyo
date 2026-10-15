#!/usr/bin/env python3
"""Tourist-load proximity counts per station (CRTKY-193, ADR #8).

Counts accommodation (tourism=hotel|guest_house|hostel) and attractions
(tourism=attraction|museum) within 800 m of each station, for both cities.
Writes data/tourism/proximity.json.

Thresholds (ADR #8, from the research notes):
  Tokyo:   H800 >= 15   (bimodal distribution; Asakusa 62 vs Kichijoji 5)
  Bangkok: H800 >= 50 OR A800 >= 8  (continuous corridor; natural break 54→49)

Needs network (Overpass). Run via a workflow agent or a machine with access:
  python3 scripts/scrapers/fetch-tourism-counts.py
"""

from __future__ import annotations

import json
import math
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "tourism" / "proximity.json"

ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]

BBOXES = {
    "tokyo": (35.49, 139.20, 36.02, 139.95),
    "bangkok": (13.4907, 100.3279, 13.9556, 100.9383),
}

RADIUS_M = 800

HOTEL_QUERY = """
[out:json][timeout:180];
(
  nwr["tourism"~"^(hotel|guest_house|hostel)$"]({bbox});
);
out center tags;
"""

ATTRACTION_QUERY = """
[out:json][timeout:180];
(
  nwr["tourism"~"^(attraction|museum)$"]({bbox});
);
out center tags;
"""


def overpass(query: str, label: str) -> dict:
    last_err: Exception | None = None
    for attempt in range(6):
        endpoint = ENDPOINTS[attempt % len(ENDPOINTS)]
        try:
            data = urllib.parse.urlencode({"data": query}).encode()
            req = urllib.request.Request(
                endpoint,
                data=data,
                headers={
                    "User-Agent": "city-rating-tourism/1.0 (data fetch for city-rating.pogorelov.dev)",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
            )
            with urllib.request.urlopen(req, timeout=240) as resp:
                payload = json.loads(resp.read())
            n = len(payload.get("elements", []))
            if n == 0 and attempt < 3:
                raise RuntimeError("empty response — retrying")
            print(f"    {label}: {n} elements via {endpoint.split('/')[2]}")
            return payload
        except Exception as e:  # noqa: BLE001 — retry across mirrors
            last_err = e
            print(f"    {label}: attempt {attempt+1} failed via {endpoint.split('/')[2]}: {e}")
            time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"Overpass query '{label}' failed: {last_err}")


def coords_of(el: dict) -> tuple[float, float] | None:
    if "lat" in el and "lon" in el:
        return float(el["lat"]), float(el["lon"])
    c = el.get("center")
    if c:
        return float(c["lat"]), float(c["lon"])
    return None


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371000
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat/2)**2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def counts_for(stations: list[tuple[str, float, float]],
               hotels: list[tuple[float, float]],
               attractions: list[tuple[float, float]]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for slug, slat, slng in stations:
        h = sum(1 for a, o in hotels if haversine_m(slat, slng, a, o) <= RADIUS_M)
        a = sum(1 for la, lo in attractions if haversine_m(slat, slng, la, lo) <= RADIUS_M)
        out[slug] = {"hotels_800m": h, "attractions_800m": a}
    return out


def gate(name: str, counts: dict[str, dict], min_total_hotels: int) -> None:
    total = sum(v["hotels_800m"] for v in counts.values())
    if total < min_total_hotels:
        sys.exit(f"FATAL: {name} hotel total {total} below floor {min_total_hotels} — dump looks incomplete")
    print(f"  {name}: {total} hotel hits across {len(counts)} stations")


def main() -> None:
    result: dict[str, dict] = {}
    meta: dict[str, dict] = {}

    for city, bbox in BBOXES.items():
        print(f"→ {city}")
        bb = ",".join(str(x) for x in bbox)
        hotels_raw = overpass(HOTEL_QUERY.format(bbox=bb), f"{city} hotels")
        attr_raw = overpass(ATTRACTION_QUERY.format(bbox=bb), f"{city} attractions")

        hotels = [c for c in (coords_of(el) for el in hotels_raw["elements"]) if c]
        attractions = [c for c in (coords_of(el) for el in attr_raw["elements"]) if c]
        print(f"    {len(hotels)} hotels, {len(attractions)} attractions with coords")

        if city == "tokyo":
            stations = json.loads((ROOT / "data" / "stations.json").read_text())
            pts = [(s["slug"], float(s["lat"]), float(s["lng"])) for s in stations]
            gate_floor = 800
        else:
            areas_doc = json.loads((ROOT / "app" / "src" / "data" / "bangkok" / "stations.json").read_text())
            areas = areas_doc.get("areas", areas_doc)
            pts = [(a["id"], a["lat"], a["lng"]) for a in areas]
            gate_floor = 500

        counts = counts_for(pts, hotels, attractions)
        gate(city, counts, gate_floor)
        result[city] = counts
        meta[city] = {
            "hotels_total": len(hotels),
            "attractions_total": len(attractions),
            "stations": len(pts),
        }

    # Thresholds (ADR #8).
    tokyo_badge = [s for s, v in result["tokyo"].items() if v["hotels_800m"] >= 15]
    bkk_badge = [s for s, v in result["bangkok"].items()
                 if v["hotels_800m"] >= 50 or v["attractions_800m"] >= 8]
    print(f"\nTokyo badge (>=15 hotels): {len(tokyo_badge)}/{len(result['tokyo'])}")
    print(f"Bangkok badge (>=50 hotels OR >=8 attractions): {len(bkk_badge)}/{len(result['bangkok'])}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "_meta": {
            "source": "OpenStreetMap via Overpass, ODbL 1.0",
            "radius_m": RADIUS_M,
            "thresholds": {"tokyo_hotels": 15, "bangkok_hotels": 50, "bangkok_attractions": 8},
            "fetched": time.strftime("%Y-%m-%d"),
            **meta,
        },
        "stations": result,
    }, ensure_ascii=False, indent=1) + "\n")
    print(f"\nWrote {OUT.relative_to(ROOT)}")

    # Badge previews.
    for slug, v in sorted(result["tokyo"].items(), key=lambda kv: -kv[1]["hotels_800m"])[:5]:
        print(f"  tokyo  {slug:20s} H800={v['hotels_800m']:4d} A800={v['attractions_800m']:3d}")
    for slug, v in sorted(result["bangkok"].items(), key=lambda kv: -kv[1]["hotels_800m"])[:5]:
        print(f"  bkk    {slug:20s} H800={v['hotels_800m']:4d} A800={v['attractions_800m']:3d}")


if __name__ == "__main__":
    main()
