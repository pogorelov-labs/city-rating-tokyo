#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["requests>=2.31", "duckdb>=1.1"]
# ///
"""Fetch raw open data for the Bangkok district layer (CRTKY Bangkok pilot).

Everything lands in data/bangkok/raw/ (gitignored). Each file is a cache:
re-running skips files that already exist unless --refresh is passed, so a
half-finished run can be resumed without hammering public APIs.

Sources (all open):
  - OpenStreetMap via Overpass (ODbL): the 50 khet boundaries, POIs used by
    the rating signals, green-space polygons, rail stations and routes.
  - Wikidata (CC0): district names in EN/TH/JA/RU, population, area, image.
  - Wikimedia Commons (per-file CC licences): thumbnail URL + attribution for
    each district's Wikidata image.
  - Overture Maps Places (CDLA-Permissive-2.0; Meta, Microsoft, Foursquare,
    AllThePlaces sources): ~300k places in the Bangkok bbox — the second,
    independent POI source next to OSM (the role HotPepper plays for Tokyo).
    Read straight from the public S3 release with DuckDB; no account needed.

Usage:
    uv run scripts/bangkok/fetch.py              # fetch whatever is missing
    uv run scripts/bangkok/fetch.py --refresh    # re-download everything
    uv run scripts/bangkok/fetch.py --only pois_food rail_routes
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Callable

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from static_data import BBOX, RAIL_ROUTE_RELATIONS  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent.parent
RAW = ROOT / "data" / "bangkok" / "raw"

USER_AGENT = "city-rating-bangkok/1.0 (https://city-rating.pogorelov.dev; open-data research)"
OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]

BBOX_STR = ",".join(str(v) for v in BBOX)
BANGKOK_AREA = 'area["name:en"="Bangkok"]["admin_level"="4"]->.bkk;'

# Pinned so a rebuild is reproducible; bump deliberately (monthly releases).
OVERTURE_RELEASE = "2026-09-23.1"
# Overture's own guidance: below ~0.6 "existence confidence" many entries are
# stale or duplicate pages. Filter here so the raw file stays small.
OVERTURE_MIN_CONFIDENCE = 0.6



def overpass(query: str, label: str) -> dict:
    """POST a query to Overpass, rotating mirrors and backing off on failure."""
    last_err: Exception | None = None
    for attempt in range(6):
        endpoint = OVERPASS_ENDPOINTS[attempt % len(OVERPASS_ENDPOINTS)]
        try:
            resp = requests.post(
                endpoint,
                data={"data": query},
                headers={"User-Agent": USER_AGENT},
                timeout=300,
            )
            if resp.status_code == 200:
                payload = resp.json()  # raises on the HTML error pages Overpass sometimes returns
                if "remark" in payload and "runtime error" in payload["remark"]:
                    raise RuntimeError(payload["remark"])
                return payload
            last_err = RuntimeError(f"HTTP {resp.status_code} from {endpoint}")
        except (requests.RequestException, ValueError, RuntimeError) as err:
            last_err = err
        wait = 10 * (attempt + 1)
        print(f"  [{label}] attempt {attempt + 1} failed ({last_err}); retrying in {wait}s", flush=True)
        time.sleep(wait)
    raise RuntimeError(f"Overpass query '{label}' failed: {last_err}")


def q_bbox(body: str, out: str = "out center tags;") -> str:
    return f"[out:json][timeout:240][bbox:{BBOX_STR}];({body});{out}"


def fetch_boundaries() -> dict:
    return overpass(
        f'[out:json][timeout:240];{BANGKOK_AREA}'
        'rel(area.bkk)["boundary"="administrative"]["admin_level"="6"];out geom;',
        "boundaries",
    )


def fetch_province() -> dict:
    return overpass(
        '[out:json][timeout:240];rel["boundary"="administrative"]["admin_level"="4"]["name:en"="Bangkok"];out geom;',
        "province",
    )


POI_QUERIES: dict[str, str] = {
    "pois_food": (
        'nwr["amenity"~"^(restaurant|cafe|fast_food|food_court|ice_cream)$"];'
        'nwr["shop"~"^(bakery|coffee|pastry)$"];'
    ),
    "pois_nightlife": (
        'nwr["amenity"~"^(bar|pub|nightclub|biergarten|karaoke_box)$"];'
        'nwr["tourism"="hostel"];'
    ),
    "pois_essentials": (
        'nwr["shop"~"^(supermarket|convenience|chemist|laundry|dry_cleaning|greengrocer|mall|department_store)$"];'
        'nwr["amenity"~"^(pharmacy|clinic|doctors|dentist|hospital|bank|post_office|school|kindergarten|marketplace)$"];'
    ),
    "pois_sports": (
        'nwr["leisure"~"^(fitness_centre|sports_centre|swimming_pool|stadium|fitness_station)$"];'
    ),
    "pois_culture": (
        'nwr["amenity"~"^(theatre|cinema|arts_centre|library|place_of_worship)$"];'
        'nwr["tourism"~"^(museum|gallery|attraction)$"];'
        'nwr["shop"~"^(books|music|art|antiques|second_hand|musical_instrument|craft)$"];'
        'nwr["historic"];'
        'way["highway"="pedestrian"];'
    ),
    "pois_transit_other": (
        'nwr["amenity"="ferry_terminal"];'
        'node["highway"="bus_stop"];'
    ),
}


def fetch_green() -> dict:
    return overpass(
        q_bbox(
            'nwr["leisure"~"^(park|garden|nature_reserve)$"];'
            'nwr["landuse"~"^(forest|recreation_ground|village_green)$"];'
            'nwr["natural"="wood"];',
            out="out geom;",
        ),
        "green",
    )


def fetch_rail_routes() -> dict:
    ids = ",".join(str(i) for ids in RAIL_ROUTE_RELATIONS.values() for i in ids)
    return overpass(f"[out:json][timeout:240];rel(id:{ids});out geom;", "rail_routes")


def fetch_rail_stops() -> dict:
    """Tags for every node referenced by the selected routes (stop positions + platforms)."""
    ids = ",".join(str(i) for ids in RAIL_ROUTE_RELATIONS.values() for i in ids)
    return overpass(f"[out:json][timeout:240];rel(id:{ids});node(r);out tags;", "rail_stops")


def fetch_rail_stations() -> dict:
    return overpass(
        q_bbox(
            'node["railway"="station"];'
            'node["public_transport"="station"];'
            'way["railway"="station"];'
            'way["public_transport"="station"];',
        ),
        "rail_stations",
    )


def _district_qids() -> list[str]:
    boundaries = json.loads((RAW / "boundaries.json").read_text())
    qids = [el["tags"]["wikidata"] for el in boundaries["elements"] if el.get("tags", {}).get("wikidata")]
    if len(qids) != 50:
        print(f"  warning: expected 50 district QIDs, found {len(qids)}", file=sys.stderr)
    return qids


def fetch_wikidata() -> dict:
    qids = _district_qids()
    entities: dict = {}
    for i in range(0, len(qids), 50):
        chunk = qids[i : i + 50]
        resp = requests.get(
            "https://www.wikidata.org/w/api.php",
            params={
                "action": "wbgetentities",
                "ids": "|".join(chunk),
                "props": "labels|claims|sitelinks",
                "languages": "en|th|ja|ru",
                "format": "json",
            },
            headers={"User-Agent": USER_AGENT},
            timeout=60,
        )
        resp.raise_for_status()
        entities.update(resp.json()["entities"])
        time.sleep(1)
    return {"entities": entities}


def fetch_commons() -> dict:
    wd = json.loads((RAW / "wikidata.json").read_text())["entities"]
    files: list[str] = []
    for ent in wd.values():
        for claim in ent.get("claims", {}).get("P18", [])[:1]:
            value = claim.get("mainsnak", {}).get("datavalue", {}).get("value")
            if value:
                files.append(f"File:{value}")
    pages: dict = {}
    for i in range(0, len(files), 50):
        chunk = files[i : i + 50]
        resp = requests.get(
            "https://commons.wikimedia.org/w/api.php",
            params={
                "action": "query",
                "titles": "|".join(chunk),
                "prop": "imageinfo",
                "iiprop": "url|extmetadata|size",
                "iiurlwidth": "640",
                "format": "json",
            },
            headers={"User-Agent": USER_AGENT},
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        pages.update(data.get("query", {}).get("pages", {}))
        # Record title normalisation so build.py can map Wikidata values → pages.
        for norm in data.get("query", {}).get("normalized", []):
            pages.setdefault("_normalized", {})[norm["from"]] = norm["to"]
        time.sleep(1)
    return {"pages": pages}


def fetch_overture() -> dict:
    """Slim Bangkok extract of Overture Places → raw/overture_places.parquet.

    Keeps position, category taxonomy, confidence and provenance only (no
    names/phones), which is all the rating signals need.
    """
    import duckdb

    out = RAW / "overture_places.parquet"
    s, w, n, e = BBOX
    con = duckdb.connect()
    con.execute("INSTALL httpfs; LOAD httpfs; SET s3_region='us-west-2';")
    src = (
        f"read_parquet('s3://overturemaps-us-west-2/release/{OVERTURE_RELEASE}"
        "/theme=places/type=place/*', hive_partitioning=1)"
    )
    con.execute(
        f"""
        COPY (
          SELECT id, basic_category, taxonomy.hierarchy AS hierarchy, confidence,
                 sources[1].dataset AS dataset, sources[1].license AS license,
                 (bbox.xmin + bbox.xmax) / 2 AS lon, (bbox.ymin + bbox.ymax) / 2 AS lat
          FROM {src}
          WHERE bbox.xmin BETWEEN {w} AND {e} AND bbox.ymin BETWEEN {s} AND {n}
            AND confidence >= {OVERTURE_MIN_CONFIDENCE}
            AND coalesce(operating_status, 'open') = 'open'
        ) TO '{out}' (FORMAT parquet)
        """
    )
    rows = con.execute(f"SELECT count(*) FROM '{out}'").fetchone()[0]
    return {"_self_written": str(out.name), "rows": rows, "release": OVERTURE_RELEASE}


TASKS: dict[str, Callable[[], dict]] = {
    "boundaries": fetch_boundaries,
    "province": fetch_province,
    **{name: (lambda body=body, name=name: overpass(q_bbox(body), name)) for name, body in POI_QUERIES.items()},
    "green": fetch_green,
    "rail_routes": fetch_rail_routes,
    "rail_stops": fetch_rail_stops,
    "rail_stations": fetch_rail_stations,
    "wikidata": fetch_wikidata,  # depends on boundaries
    "commons": fetch_commons,  # depends on wikidata
    "overture_places": fetch_overture,
}
# Tasks that write their own (non-JSON) output file.
SELF_WRITTEN = {"overture_places": "overture_places.parquet"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--refresh", action="store_true", help="re-download files that already exist")
    parser.add_argument("--only", nargs="*", choices=sorted(TASKS), help="limit to these outputs")
    args = parser.parse_args()

    RAW.mkdir(parents=True, exist_ok=True)
    wanted = args.only or list(TASKS)
    for name in wanted:
        path = RAW / SELF_WRITTEN.get(name, f"{name}.json")
        if path.exists() and not args.refresh:
            print(f"✓ {name}: cached ({path.stat().st_size / 1e6:.1f} MB)")
            continue
        print(f"→ {name} …", flush=True)
        started = time.time()
        payload = TASKS[name]()
        if name in SELF_WRITTEN:
            print(f"✓ {name}: {payload['rows']:,} rows (release {payload['release']}), "
                  f"{path.stat().st_size / 1e6:.1f} MB in {time.time() - started:.0f}s")
            continue
        payload["_fetched_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        path.write_text(json.dumps(payload, ensure_ascii=False))
        n = len(payload.get("elements", payload.get("entities", payload.get("pages", {}))))
        print(f"✓ {name}: {n} items, {path.stat().st_size / 1e6:.1f} MB in {time.time() - started:.0f}s")
        if name.startswith(("pois_", "green", "rail", "boundaries", "province")):
            time.sleep(5)  # Overpass etiquette between heavy queries


if __name__ == "__main__":
    main()
