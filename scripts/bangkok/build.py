#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy>=2", "shapely>=2.1", "duckdb>=1.1"]
# ///
"""Build the Bangkok district dataset from the raw dumps fetched by fetch.py.

    uv run scripts/bangkok/fetch.py     # once (network, cached)
    uv run scripts/bangkok/build.py     # offline, ~20 s

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

Outputs
  app/src/data/bangkok/districts.json  — app data (ratings, facts, names, …)
  app/src/data/bangkok/geometry.json   — simplified polygons + label points
  app/src/data/bangkok/rail.json       — rail lines (paths) + stations
  app/src/data/bangkok/meta.json       — medians, composite anchors, counts
  data/bangkok/signals.json            — raw per-district signals (audit trail)
"""
from __future__ import annotations

import argparse
import heapq
import html
import json
import math
import re
import sys
import time
import urllib.parse
from collections import defaultdict
from datetime import date
from pathlib import Path

import numpy as np
import shapely
from shapely.geometry import LineString, MultiLineString, MultiPolygon, Point, Polygon
from shapely.ops import linemerge, polygonize, polylabel, unary_union

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ratings as R  # noqa: E402
from static_data import (  # noqa: E402
    BBOX,
    CURATED_SEQUENCES,
    RAIL_ROUTE_RELATIONS,
    HUBS,
    LINES,
    RU_NAMES,
    SLUG_OVERRIDES,
    STATION_NAME_ALIASES,
    STATION_TH_FALLBACK,
)

ROOT = HERE.parent.parent
RAW = ROOT / "data" / "bangkok" / "raw"
DATA = ROOT / "data" / "bangkok"
APP = ROOT / "app" / "src" / "data" / "bangkok"
SCHEMA_CONSTANTS = ROOT / "packages" / "schema" / "constants.json"

# Local equirectangular projection in metres. Over Bangkok's ~60 km extent the
# scale error against UTM 47N stays under 0.3 %, far below OSM positional noise.
LAT0, LON0 = 13.75, 100.60
KX = 111_320.0 * math.cos(math.radians(LAT0))
KY = 110_574.0

GRID_M = 200  # resident sample grid
CELL_M = 100  # raster cell for "count within radius" convolutions
SIMPLIFY_M = 18  # polygon simplification tolerance for the app geometry

WALK_M_PER_MIN = 75.0  # 4.5 km/h


def feeder_m_per_min(d: np.ndarray) -> np.ndarray:
    """Feeder speed to a station: ~15 km/h in soi traffic, up to ~25 km/h on
    the longer arterial runs of the outer districts."""
    return (15.0 + 10.0 * np.minimum(1.0, d / 15_000)) * 1000 / 60


def road_m_per_min(d: np.ndarray) -> np.ndarray:
    """Door-to-door road speed at peak: ~16 km/h for short inner trips rising to
    ~30 km/h for 25 km+ trips that can use the expressway / motorway network."""
    return (16.0 + 14.0 * np.minimum(1.0, d / 25_000)) * 1000 / 60
WALK_DETOUR = 1.3
FEEDER_WAIT = 6.0  # motorbike taxi / bus / songthaew to a station
ROAD_OVERHEAD = 10.0  # door-to-door taxi or bus: hail/wait + last walk
ROAD_DETOUR = 1.4
TRANSFER_WALK_MAX_M = 500.0
RAIL_DETOUR = 1.05  # track length vs. straight line between station nodes

RATING_KEYS = [
    "transport", "rent", "daily_essentials", "safety", "food",
    "green", "gym_sports", "vibe", "nightlife", "crowd",
]


# ─────────────────────────────── helpers ────────────────────────────────

def xy(lon: float, lat: float) -> tuple[float, float]:
    return ((lon - LON0) * KX, (lat - LAT0) * KY)


def xy_arr(lon: np.ndarray, lat: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    return ((lon - LON0) * KX, (lat - LAT0) * KY)


def lonlat(x: float, y: float) -> tuple[float, float]:
    return (x / KX + LON0, y / KY + LAT0)


def latlng_pair(x: float, y: float) -> list[float]:
    lon, lat = lonlat(x, y)
    return [round(lat, 5), round(lon, 5)]


def load(name: str) -> dict:
    path = RAW / f"{name}.json"
    if not path.exists():
        sys.exit(f"missing {path} — run `uv run scripts/bangkok/fetch.py` first")
    return json.loads(path.read_text())


def slugify(name: str) -> str:
    base = re.sub(r"\s+district$", "", name.strip(), flags=re.I).lower()
    base = re.sub(r"[^a-z0-9]+", "-", base).strip("-")
    return SLUG_OVERRIDES.get(base, base)


def norm_name(name: str) -> str:
    name = STATION_NAME_ALIASES.get(name.strip().lower(), STATION_NAME_ALIASES.get(name.strip(), name))
    return re.sub(r"[^a-z0-9฀-๿]+", " ", name.lower()).strip()


def element_lonlat(el: dict) -> tuple[float, float] | None:
    if "lon" in el and "lat" in el:
        return el["lon"], el["lat"]
    c = el.get("center")
    if c:
        return c["lon"], c["lat"]
    return None


def strip_html(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", value or ""))).strip()


# ─────────────────────────────── districts ───────────────────────────────

def ring_lines(members: list[dict], roles: tuple[str, ...]):
    for m in members:
        if m.get("type") != "way" or m.get("role", "") not in roles or "geometry" not in m:
            continue
        pts = [xy(p["lon"], p["lat"]) for p in m["geometry"]]
        if len(pts) >= 2:
            yield LineString(pts)


def assemble_multipolygon(members: list[dict]) -> MultiPolygon | None:
    outer = list(polygonize(unary_union(list(ring_lines(members, ("outer", ""))))))
    if not outer:
        return None
    geom = unary_union(outer)
    inner_lines = list(ring_lines(members, ("inner",)))
    if inner_lines:
        inner = list(polygonize(unary_union(inner_lines)))
        if inner:
            geom = geom.difference(unary_union(inner))
    if geom.geom_type == "Polygon":
        geom = MultiPolygon([geom])
    return geom if geom.geom_type == "MultiPolygon" and not geom.is_empty else None


def wikidata_info(ent: dict) -> dict:
    def claim_values(prop: str) -> list[tuple[object, str | None]]:
        out = []
        for c in ent.get("claims", {}).get(prop, []):
            value = c.get("mainsnak", {}).get("datavalue", {}).get("value")
            when = None
            for q in c.get("qualifiers", {}).get("P585", []):
                when = q.get("datavalue", {}).get("value", {}).get("time")
            out.append((value, when))
        return out

    pop = pop_year = None
    for value, when in claim_values("P1082"):
        if not isinstance(value, dict):
            continue
        year = int(when[1:5]) if when else 0
        if pop_year is None or year > pop_year:
            pop, pop_year = int(float(value["amount"])), year
    area = None
    for value, _ in claim_values("P2046"):
        if isinstance(value, dict) and value.get("unit", "").endswith("Q712226"):  # km²
            area = float(value["amount"])
            break
    image = next((v for v, _ in claim_values("P18") if isinstance(v, str)), None)
    labels = {lang: ent.get("labels", {}).get(lang, {}).get("value") for lang in ("en", "th", "ja", "ru")}
    wiki = {}
    for lang in ("en", "ja", "ru", "th"):
        title = ent.get("sitelinks", {}).get(f"{lang}wiki", {}).get("title")
        if title:
            wiki[lang] = f"https://{lang}.wikipedia.org/wiki/" + urllib.parse.quote(title.replace(" ", "_"))
    return {"labels": labels, "population": pop, "population_year": pop_year or None,
            "area_km2": area, "image": image, "wikipedia": wiki}


def load_districts() -> list[dict]:
    boundaries = load("boundaries")
    wd = load("wikidata")["entities"]
    districts = []
    for rel in boundaries["elements"]:
        tags = rel.get("tags", {})
        geom = assemble_multipolygon(rel.get("members", []))
        if geom is None:
            sys.exit(f"could not assemble boundary for relation {rel['id']} ({tags.get('name:en')})")
        info = wikidata_info(wd.get(tags.get("wikidata", ""), {}))
        name_en_raw = info["labels"]["en"] or tags.get("name:en") or tags["name"]
        slug = slugify(tags.get("name:en") or name_en_raw)
        name_en = re.sub(r"\s+district$", "", name_en_raw, flags=re.I).strip()
        if slug == "watthana":
            name_en = "Watthana"
        name_th = re.sub(r"^เขต\s*", "", info["labels"]["th"] or tags.get("name", "")).strip()
        districts.append({
            "slug": slug,
            "osm_id": rel["id"],
            "qid": tags.get("wikidata"),
            "name_en": name_en,
            "name_th": name_th,
            "name_jp": info["labels"]["ja"] or name_en,
            "name_ru": RU_NAMES[slug],
            "geom": geom,
            "wd": info,
        })
    districts.sort(key=lambda d: d["slug"])
    slugs = [d["slug"] for d in districts]
    assert len(slugs) == 50 and len(set(slugs)) == 50, f"expected 50 unique khet, got {len(set(slugs))}"
    missing_ru = set(slugs) - set(RU_NAMES)
    assert not missing_ru, f"RU_NAMES missing {missing_ru}"
    return districts


def simplify_coverage(geoms: list[MultiPolygon]) -> list[MultiPolygon]:
    """Simplify shared borders once so neighbouring polygons stay gap-free."""
    arr = np.array(geoms, dtype=object)
    try:
        if not shapely.coverage_is_valid(arr):
            raise ValueError("district coverage not edge-matched")
        simp = shapely.coverage_simplify(arr, SIMPLIFY_M, simplify_boundary=True)
    except Exception as err:  # fall back to per-polygon simplification
        print(f"  coverage_simplify unavailable ({err}); simplifying polygons independently")
        simp = [g.simplify(SIMPLIFY_M, preserve_topology=True) for g in geoms]
    out = []
    for g in simp:
        if g.geom_type == "Polygon":
            g = MultiPolygon([g])
        parts = [p for p in g.geoms if p.area > 20_000] or [max(g.geoms, key=lambda p: p.area)]
        out.append(MultiPolygon(parts))
    return out


def polygon_to_latlng(poly: Polygon) -> list[list[list[float]]]:
    rings = [poly.exterior, *poly.interiors]
    return [[latlng_pair(x, y) for x, y in ring.coords] for ring in rings]


# ─────────────────────────────── rasters ────────────────────────────────

def fft_convolve_same(a: np.ndarray, k: np.ndarray) -> np.ndarray:
    ky, kx = k.shape
    sy, sx = a.shape[0] + ky - 1, a.shape[1] + kx - 1
    full = np.fft.irfft2(np.fft.rfft2(a, s=(sy, sx)) * np.fft.rfft2(k, s=(sy, sx)), s=(sy, sx))
    cy, cx = ky // 2, kx // 2
    return np.clip(np.round(full[cy : cy + a.shape[0], cx : cx + a.shape[1]], 6), 0, None)


class Raster:
    """Regular grid over the POI bbox; turns point sets into 'count within r'."""

    def __init__(self, bounds: tuple[float, float, float, float], cell: float):
        self.x0, self.y0 = bounds[0], bounds[1]
        self.cell = cell
        self.nx = int(math.ceil((bounds[2] - bounds[0]) / cell))
        self.ny = int(math.ceil((bounds[3] - bounds[1]) / cell))
        self._kernels: dict[float, np.ndarray] = {}

    def index(self, xs: np.ndarray, ys: np.ndarray):
        ix = np.floor((xs - self.x0) / self.cell).astype(int)
        iy = np.floor((ys - self.y0) / self.cell).astype(int)
        ok = (ix >= 0) & (ix < self.nx) & (iy >= 0) & (iy < self.ny)
        return ix, iy, ok

    def hist(self, xs: np.ndarray, ys: np.ndarray, weights: np.ndarray | None = None) -> np.ndarray:
        h = np.zeros((self.ny, self.nx))
        if len(xs) == 0:
            return h
        ix, iy, ok = self.index(xs, ys)
        w = np.ones(len(xs)) if weights is None else weights
        np.add.at(h, (iy[ok], ix[ok]), w[ok])
        return h

    def kernel(self, radius: float) -> np.ndarray:
        if radius not in self._kernels:
            r = int(math.ceil(radius / self.cell))
            yy, xx = np.mgrid[-r : r + 1, -r : r + 1]
            self._kernels[radius] = ((xx * xx + yy * yy) * self.cell**2 <= radius**2).astype(float)
        return self._kernels[radius]

    def within(self, h: np.ndarray, radius: float) -> np.ndarray:
        return fft_convolve_same(h, self.kernel(radius))

    def sample(self, a: np.ndarray, xs: np.ndarray, ys: np.ndarray) -> np.ndarray:
        ix, iy, ok = self.index(xs, ys)
        out = np.zeros(len(xs))
        out[ok] = a[iy[ok], ix[ok]]
        return out

    def cell_centres(self, x0: float, y0: float, x1: float, y1: float):
        """Cell-centre coordinates (and indices) inside a bbox."""
        i0 = max(0, int((x0 - self.x0) / self.cell))
        i1 = min(self.nx - 1, int((x1 - self.x0) / self.cell))
        j0 = max(0, int((y0 - self.y0) / self.cell))
        j1 = min(self.ny - 1, int((y1 - self.y0) / self.cell))
        if i1 < i0 or j1 < j0:
            return None
        ii, jj = np.meshgrid(np.arange(i0, i1 + 1), np.arange(j0, j1 + 1))
        cx = self.x0 + (ii + 0.5) * self.cell
        cy = self.y0 + (jj + 0.5) * self.cell
        return ii.ravel(), jj.ravel(), cx.ravel(), cy.ravel()


# ───────────────────────────────── POIs ─────────────────────────────────

def load_pois() -> dict[str, tuple[np.ndarray, np.ndarray]]:
    """Category → projected (x, y) arrays. One element can feed several categories."""
    buckets: dict[str, list[tuple[float, float]]] = defaultdict(list)
    seen: set[tuple[str, int, str]] = set()

    def add(cat: str, el: dict, pt: tuple[float, float]):
        key = (el["type"], el["id"], cat)
        if key not in seen:
            seen.add(key)
            buckets[cat].append(pt)

    for name in ("pois_food", "pois_nightlife", "pois_essentials", "pois_sports", "pois_culture", "pois_transit_other"):
        for el in load(name)["elements"]:
            ll = element_lonlat(el)
            if ll is None:
                continue
            pt = xy(*ll)
            t = el.get("tags", {})
            amenity, shop, leisure, tourism = t.get("amenity"), t.get("shop"), t.get("leisure"), t.get("tourism")
            private = t.get("access") in ("private", "no")
            if amenity in ("restaurant", "cafe", "fast_food", "food_court", "ice_cream") or shop in ("bakery", "coffee", "pastry"):
                add("food", el, pt)
            if amenity == "cafe" or shop == "coffee":
                add("cafe", el, pt)
            if amenity in ("bar", "pub", "nightclub", "biergarten"):
                add("night", el, pt)
            if amenity == "karaoke_box":
                add("karaoke", el, pt)
            if tourism == "hostel":
                add("hostel", el, pt)
            if shop in ("supermarket", "convenience", "greengrocer") or amenity == "marketplace":
                add("grocery", el, pt)
            if shop == "convenience":
                add("convenience", el, pt)
            if amenity == "marketplace":
                add("market", el, pt)
            if amenity == "pharmacy" or shop == "chemist":
                add("pharmacy", el, pt)
            if amenity in ("clinic", "doctors", "dentist", "hospital"):
                add("health", el, pt)
            if amenity == "bank":
                add("bank", el, pt)
            if shop in ("laundry", "dry_cleaning"):
                add("laundry", el, pt)
            if amenity == "post_office":
                add("post", el, pt)
            if amenity in ("school", "kindergarten"):
                add("school", el, pt)
            if shop in ("mall", "department_store"):
                add("mall", el, pt)
            if leisure in ("fitness_centre", "sports_centre", "stadium", "fitness_station") and not private:
                add("sports", el, pt)
            if leisure == "swimming_pool":
                add("pool", el, pt)
            if amenity in ("theatre", "cinema", "arts_centre", "library") or tourism in ("museum", "gallery") or shop in (
                "books", "music", "art", "antiques", "second_hand", "musical_instrument", "craft"
            ):
                add("venue", el, pt)
            if tourism == "attraction":
                add("attraction", el, pt)
            if amenity == "place_of_worship":
                add("temple", el, pt)
            if "historic" in t:
                add("historic", el, pt)
            if t.get("highway") == "pedestrian":
                add("pedestrian", el, pt)
            if t.get("highway") == "bus_stop":
                add("bus", el, pt)
            if amenity == "ferry_terminal":
                add("pier", el, pt)

    out = {}
    for cat, pts in buckets.items():
        arr = np.array(pts)
        out[cat] = (arr[:, 0], arr[:, 1])
    return out


def load_green() -> tuple[list[Polygon], list[Polygon]]:
    """(park-like public green, all green incl. woodland) as projected polygons."""
    parks: list[Polygon] = []
    green: list[Polygon] = []
    for el in load("green")["elements"]:
        t = el.get("tags", {})
        geom = None
        if el["type"] == "way" and "geometry" in el:
            pts = [xy(p["lon"], p["lat"]) for p in el["geometry"]]
            if len(pts) >= 4 and pts[0] == pts[-1]:
                geom = Polygon(pts)
        elif el["type"] == "relation":
            geom = assemble_multipolygon(el.get("members", []))
        if geom is None or geom.is_empty:
            continue
        if not geom.is_valid:
            geom = geom.buffer(0)
        polys = list(geom.geoms) if geom.geom_type == "MultiPolygon" else [geom]
        leisure, landuse = t.get("leisure"), t.get("landuse")
        private = t.get("access") in ("private", "no")
        is_park = (
            leisure in ("park", "nature_reserve")
            or landuse == "recreation_ground"
            or (leisure == "garden" and not private and geom.area >= 2_000)
        )
        is_green = is_park or landuse in ("forest", "village_green") or t.get("natural") == "wood" or leisure == "garden"
        for p in polys:
            if p.area < 200:
                continue
            if is_park:
                parks.append(p)
            if is_green:
                green.append(p)
    return parks, green


def load_overture() -> dict[str, tuple[np.ndarray, np.ndarray]]:
    """Overture Places → `ovt_<category>` point sets (same buckets as OSM).

    Mapping is by taxonomy hierarchy, e.g. ['food_and_drink', 'restaurant',
    'thai_restaurant']. Deliberately excluded: `historic_site`, which in
    Bangkok is dominated by mis-classified apartment buildings (~12k rows).
    """
    import duckdb

    path = RAW / "overture_places.parquet"
    if not path.exists():
        sys.exit(f"missing {path} — run `uv run scripts/bangkok/fetch.py --only overture_places`")
    rows = duckdb.connect().execute(f"SELECT lon, lat, hierarchy FROM '{path}'").fetchall()
    buckets: dict[str, list[tuple[float, float]]] = defaultdict(list)
    for lon, lat, hier in rows:
        pt = xy(lon, lat)
        buckets["all"].append(pt)
        h = hier or []
        top = h[0] if h else None
        second = h[1] if len(h) > 1 else None
        hs = set(h)
        if top == "food_and_drink" and second in ("restaurant", "casual_eatery", "non_alcoholic_beverage_venue") or hs & {
            "bakery", "dessert_shop", "food_court", "food_truck_stand"
        }:
            buckets["food"].append(pt)
        if "non_alcoholic_beverage_venue" in hs:
            buckets["cafe"].append(pt)
        if hs & {"alcoholic_beverage_venue", "nightlife_venue", "music_venue"}:
            buckets["night"].append(pt)
        if any("karaoke" in x for x in h):
            buckets["karaoke"].append(pt)
        if "hostel" in hs:
            buckets["hostel"].append(pt)
        if hs & {"convenience_store", "grocery_store", "supermarket", "market", "farmers_market"}:
            buckets["grocery"].append(pt)
        if "convenience_store" in hs:
            buckets["convenience"].append(pt)
        if hs & {"market", "farmers_market", "night_market"}:
            buckets["market"].append(pt)
        if "pharmacy" in hs:
            buckets["pharmacy"].append(pt)
        if top == "health_care":
            buckets["health"].append(pt)
        if "bank_or_credit_union" in hs:
            buckets["bank"].append(pt)
        if hs & {"laundry_service", "laundromat"}:
            buckets["laundry"].append(pt)
        if "post_office" in hs:
            buckets["post"].append(pt)
        if top == "education" and second == "place_of_learning":
            buckets["school"].append(pt)
        if top == "sports_and_recreation" and second == "sport_or_fitness_facility":
            buckets["sports"].append(pt)
        if hs & {"museum", "art_gallery", "performing_arts_venue", "movie_theater", "library", "bookstore",
                 "arts_and_crafts_space", "music_venue"}:
            buckets["venue"].append(pt)
        if top == "cultural_and_historic" and second == "place_of_worship":
            buckets["temple"].append(pt)
    out = {}
    for cat, pts in buckets.items():
        arr = np.array(pts)
        out[f"ovt_{cat}"] = (arr[:, 0], arr[:, 1])
    return out


def pearson(a: list[float], b: list[float]) -> float:
    ma, mb = sum(a) / len(a), sum(b) / len(b)
    cov = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    va = math.sqrt(sum((x - ma) ** 2 for x in a))
    vb = math.sqrt(sum((y - mb) ** 2 for y in b))
    return cov / (va * vb) if va and vb else float("nan")


def rasterize(polys: list[Polygon], raster: Raster, min_area: float = 0.0) -> np.ndarray:
    """1 where a cell centre lies inside any polygon (each cell = cell² m²)."""
    grid = np.zeros((raster.ny, raster.nx))
    for p in polys:
        if p.area < min_area:
            continue
        cc = raster.cell_centres(*p.bounds)
        if cc is None:
            continue
        ii, jj, cx, cy = cc
        inside = shapely.contains_xy(p, cx, cy)
        grid[jj[inside], ii[inside]] = 1.0
    return grid


# ───────────────────────────────── rail ─────────────────────────────────

def load_station_candidates() -> list[dict]:
    cands = []
    for el in load("rail_stations")["elements"]:
        t = el.get("tags", {})
        ll = element_lonlat(el)
        if ll is None:
            continue
        name = t.get("name:en") or t.get("name")
        if not name or t.get("railway") in ("construction", "site", "proposed") or "construction" in t:
            continue
        x, y = xy(*ll)
        cands.append({
            "name": name,
            "norm": norm_name(name),
            "name_th": t.get("name:th") or (t.get("name") if re.search(r"[฀-๿]", t.get("name", "")) else ""),
            "x": x,
            "y": y,
            "rail": t.get("railway") in ("station", "halt"),
        })
    return cands


def line_tracks(routes: list[dict]) -> dict[str, MultiLineString]:
    by_line: dict[str, list[LineString]] = defaultdict(list)
    rel_to_line = {rid: lid for lid, spec in LINES.items() for rid in RAIL_RELATIONS[lid]}
    for rel in routes:
        lid = rel_to_line.get(rel["id"])
        if not lid:
            continue
        for m in rel.get("members", []):
            if m.get("type") == "way" and "geometry" in m and m.get("role", "") in ("", "forward", "backward"):
                pts = [xy(p["lon"], p["lat"]) for p in m["geometry"]]
                if len(pts) >= 2:
                    by_line[lid].append(LineString(pts))
    tracks = {}
    for lid, parts in by_line.items():
        merged = linemerge(unary_union(parts))
        tracks[lid] = merged if merged.geom_type == "MultiLineString" else MultiLineString([merged])
    return tracks


def build_rail(districts: list[dict]):
    """Stations (merged interchanges), per-line ordered stop lists, track paths."""
    routes = load("rail_routes")["elements"]
    stop_tags = {e["id"]: e.get("tags", {}) for e in load("rail_stops")["elements"]}
    cands = load_station_candidates()
    tracks = line_tracks(routes)

    stations: list[dict] = []

    def find_or_create(name: str, x: float, y: float, name_th: str = "") -> dict:
        n = norm_name(name)
        for s in stations:
            if s["norm"] == n and math.hypot(s["x"] - x, s["y"] - y) < 600:
                if not s["name_th"] and name_th:
                    s["name_th"] = name_th
                return s
        s = {"norm": n, "name_en": STATION_NAME_ALIASES.get(name.lower(), name), "name_th": name_th,
             "x": x, "y": y, "lines": []}
        stations.append(s)
        return s

    def nearest_candidate(x: float, y: float, max_d: float, norm: str | None = None) -> dict | None:
        best, best_d = None, max_d
        for c in cands:
            if norm is not None and c["norm"] != norm:
                continue
            d = math.hypot(c["x"] - x, c["y"] - y)
            if d < best_d:
                best, best_d = c, d
        return best

    sequences: dict[str, list[dict]] = {}
    rel_by_id = {r["id"]: r for r in routes}
    for lid, rel_ids in RAIL_RELATIONS.items():
        seq: list[dict] = []
        if lid in CURATED_SEQUENCES:
            track = tracks.get(lid)
            for name in CURATED_SEQUENCES[lid]:
                n = norm_name(name)
                options = [c for c in cands if c["norm"] == n]
                if track is not None:
                    options.sort(key=lambda c: (not c["rail"], track.distance(Point(c["x"], c["y"]))))
                if not options:
                    sys.exit(f"curated station {name!r} ({lid}) not found in rail_stations")
                c = options[0]
                seq.append(find_or_create(name, c["x"], c["y"], c["name_th"]))
        else:
            # Primary = the direction relation with the most stop members.
            rels = [rel_by_id[r] for r in rel_ids if r in rel_by_id]
            rel = max(rels, key=lambda r: sum(1 for m in r["members"] if m["type"] == "node" and m["role"].startswith("stop")))
            for m in rel["members"]:
                if m["type"] != "node" or not m["role"].startswith("stop"):
                    continue
                x, y = xy(m["lon"], m["lat"])
                tags = stop_tags.get(m["ref"], {})
                name = tags.get("name:en") or tags.get("name")
                name_th = tags.get("name:th") or ""
                cand = nearest_candidate(x, y, 350, norm_name(name) if name else None) or nearest_candidate(x, y, 350)
                if not name:
                    if cand is None:
                        continue
                    name = cand["name"]
                if cand is not None:  # snap to the station node, not the track stop position
                    x, y = cand["x"], cand["y"]
                    name_th = name_th or cand["name_th"]
                s = find_or_create(name, x, y, name_th)
                if not seq or seq[-1] is not s:
                    seq.append(s)
        for s in seq:
            if lid not in s["lines"]:
                s["lines"].append(lid)
        sequences[lid] = seq

    for s in stations:
        s["name_th"] = s["name_th"] or STATION_TH_FALLBACK.get(s["name_en"], "")

    # Stable ids: slug of the English name, disambiguated by operator if needed.
    used: dict[str, int] = defaultdict(int)
    for s in sorted(stations, key=lambda s: (s["name_en"], s["x"])):
        base = slugify(s["name_en"])
        used[base] += 1
        s["id"] = base if used[base] == 1 else f"{base}-{LINES[s['lines'][0]]['operator'].lower()}"
        s["district"] = None
        for d in districts:
            if d["geom"].contains(Point(s["x"], s["y"])):
                s["district"] = d["slug"]
                break
    return stations, sequences, tracks


def transit_model(stations: list[dict], sequences: dict[str, list[dict]]) -> dict[str, dict[str, float]]:
    """Minutes from each station's street entrance to each hub (reverse Dijkstra).

    Graph: a street node per station and a platform node per (station, line).
    Boarding costs half the peak headway, riding costs dwell + distance at the
    line's schedule speed, alighting 1 min; separate stations ≤ 500 m apart
    (Asok↔Sukhumvit, Sala Daeng↔Si Lom, Mo Chit↔Chatuchak Park …) get a
    walking transfer. Distances are "to hub", so edges are traversed reversed.
    """
    rev: dict[tuple, list[tuple[tuple, float]]] = defaultdict(list)

    def edge(a: tuple, b: tuple, cost: float):
        rev[b].append((a, cost))  # reversed for distance-to-target

    for lid, seq in sequences.items():
        spec = LINES[lid]
        m_per_min = spec["speed_kmh"] * 1000 / 60
        for s in seq:
            edge(("s", s["id"]), ("p", s["id"], lid), spec["wait_min"])
            edge(("p", s["id"], lid), ("s", s["id"]), 1.0)
        for a, b in zip(seq, seq[1:]):
            dist = math.hypot(a["x"] - b["x"], a["y"] - b["y"]) * RAIL_DETOUR
            cost = spec["dwell_min"] + dist / m_per_min
            edge(("p", a["id"], lid), ("p", b["id"], lid), cost)
            edge(("p", b["id"], lid), ("p", a["id"], lid), cost)
    for i, a in enumerate(stations):
        for b in stations[i + 1 :]:
            d = math.hypot(a["x"] - b["x"], a["y"] - b["y"])
            if d <= TRANSFER_WALK_MAX_M:
                cost = 2.0 + d * WALK_DETOUR / WALK_M_PER_MIN
                edge(("s", a["id"]), ("s", b["id"]), cost)
                edge(("s", b["id"]), ("s", a["id"]), cost)

    by_name = {s["norm"]: s for s in stations}
    out: dict[str, dict[str, float]] = {}
    for hub, station_name in HUBS.items():
        target = by_name.get(norm_name(station_name))
        if target is None:
            sys.exit(f"hub station {station_name!r} not in rail network")
        dist: dict[tuple, float] = {("s", target["id"]): 0.0}
        heap = [(0.0, ("s", target["id"]))]
        while heap:
            d, node = heapq.heappop(heap)
            if d > dist.get(node, math.inf):
                continue
            for prev, cost in rev[node]:
                nd = d + cost
                if nd < dist.get(prev, math.inf):
                    dist[prev] = nd
                    heapq.heappush(heap, (nd, prev))
        out[hub] = {s["id"]: dist.get(("s", s["id"]), math.inf) for s in stations}
        out[hub]["_xy"] = (target["x"], target["y"])  # type: ignore[assignment]
    return out


RAIL_RELATIONS: dict[str, list[int]] = {}


# ────────────────────────────────── main ─────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="compute and print, write nothing")
    parser.add_argument("--verbose", action="store_true", help="print every district's ratings")
    args = parser.parse_args()
    started = time.time()


    RAIL_RELATIONS.update(RAIL_ROUTE_RELATIONS)
    schema = json.loads(SCHEMA_CONSTANTS.read_text())
    default_weights = schema["default_weights"]
    editorial = json.loads((DATA / "editorial.json").read_text())["districts"]

    print("→ districts")
    districts = load_districts()
    missing_editorial = {d["slug"] for d in districts} - set(editorial)
    assert not missing_editorial, f"editorial.json missing {missing_editorial}"
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

    def near(cat: str, radius: float, extra: np.ndarray | None = None) -> np.ndarray:
        h = H.get(cat, np.zeros((raster.ny, raster.nx)))
        if extra is not None:
            h = h + extra
        return raster.sample(raster.within(h, radius), PX, PY)

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
    stations, sequences, tracks = build_rail(districts)
    hub_times = transit_model(stations, sequences)
    SX = np.array([s["x"] for s in stations])
    SY = np.array([s["y"] for s in stations])
    D = np.hypot(PX[:, None] - SX[None, :], PY[:, None] - SY[None, :])  # points × stations
    d_station = D.min(axis=1)
    walk = D * WALK_DETOUR / WALK_M_PER_MIN
    feeder = FEEDER_WAIT + D * ROAD_DETOUR / feeder_m_per_min(D)
    access = np.minimum(walk, feeder)
    # distinct lines with a station within 1.5 km of each point
    line_ids = list(LINES)
    lines_near = np.zeros(len(PX))
    for lid in line_ids:
        cols = [j for j, s in enumerate(stations) if lid in s["lines"]]
        if cols:
            lines_near += (D[:, cols].min(axis=1) <= 1500).astype(float)
    commute_pt: dict[str, np.ndarray] = {}
    for hub, times in hub_times.items():
        hx, hy = times["_xy"]  # type: ignore[misc]
        tvec = np.array([times[s["id"]] for s in stations])
        via_rail = (access + tvec[None, :]).min(axis=1)
        dh = np.hypot(PX - hx, PY - hy)
        road = ROAD_OVERHEAD + dh * ROAD_DETOUR / road_m_per_min(dh)
        on_foot = dh * WALK_DETOUR / WALK_M_PER_MIN
        commute_pt[hub] = np.minimum(np.minimum(via_rail, road), on_foot)
    commute_min_pt = np.min(np.vstack(list(commute_pt.values())), axis=0)

    print("→ per-point signals")
    L = np.log1p

    def both(cat: str, radius: float, osm_extra: np.ndarray | None = None) -> np.ndarray:
        """Blend of the two POI sources (Overture is ~5-10× denser, so it leads)."""
        return 0.35 * L(near(cat, radius, extra=osm_extra)) + 0.65 * L(near(f"ovt_{cat}", radius))

    pt = {
        "food": both("food", 800),
        "nightlife": (
            0.80 * both("night", 1000)
            + 0.15 * L(2 * (near("karaoke", 1000) + near("ovt_karaoke", 1000)))
            # Hostels only weakly: airport-side guesthouses (Don Mueang, Lat
            # Krabang) are not a nightlife signal, Khao San's are.
            + 0.05 * L(near("hostel", 1000) + near("ovt_hostel", 1000))
        ),
        "daily_essentials": (
            0.30 * both("grocery", 800) + 0.15 * both("pharmacy", 800) + 0.20 * both("health", 1000)
            + 0.10 * both("bank", 800) + 0.10 * both("laundry", 800) + 0.05 * both("post", 1200)
            + 0.10 * both("school", 1000)
        ),
        "gym_sports": both("sports", 1200, osm_extra=0.3 * pool_h),
        "vibe": (
            0.40 * both("venue", 1000) + 0.20 * both("cafe", 800)
            + 0.20 * L(near("temple", 1000) + near("ovt_temple", 1000) + 0.5 * near("historic", 800))
            + 0.10 * L(near("attraction", 1000)) + 0.10 * L(near("pedestrian", 1000) + near("market", 1000))
        ),
        "green": 0.6 * L(park_ha_1k) + 0.25 * L(green_ha_1k) + 0.15 * np.exp(-d_park / 600),
        "transport": (
            0.45 * np.exp(-d_station / 800)
            + 0.25 * np.minimum(1, L(lines_near) / math.log1p(4))
            + 0.10 * np.minimum(1, L(near("bus", 500)) / math.log1p(8))
            + 0.05 * np.minimum(1, near("pier", 800))
            + 0.15 * np.clip(1 - (commute_min_pt - 10) / 80, 0, 1)
        ),
    }

    print("→ district aggregates")
    raw: dict[str, dict[str, float]] = {k: {} for k in RATING_KEYS}
    agg: dict[str, dict] = {}
    for i, d in enumerate(districts):
        m = OWN == i
        w = weight[m]
        for key, arr in pt.items():
            raw[key][d["slug"]] = float((arr[m] * w).sum() / w.sum())
        hub_minutes = {
            hub: int(round(R.weighted_median(commute_pt[hub][m].tolist(), w.tolist()))) for hub in HUBS
        }
        agg[d["slug"]] = {
            "points": int(m.sum()),
            "inhabited_share": round(float((weight[m] > 0.5).mean()), 3),
            "hub_minutes": hub_minutes,
            "min_transit": min(hub_minutes.values()),
            "mean_station_distance_m": int(round(float((d_station[m] * w).sum() / w.sum()))),
        }

    # Facts: raw counts inside each boundary (the "by the numbers" card).
    def count_inside(cat: str, geom) -> int:
        if cat not in pois:
            return 0
        xs, ys = pois[cat]
        return int(shapely.contains_xy(geom, xs, ys).sum())

    for d in districts:
        g = d["geom"]
        area_km2 = g.area / 1e6
        park_area_ha = sum(p.intersection(g).area for p in parks if p.intersects(g)) / 10_000
        wd = d["wd"]
        pop = wd["population"]
        essential_cats = ("grocery", "pharmacy", "health", "bank", "laundry", "post")
        # Displayed counts come from Overture (the denser source); the OSM
        # counts ride along for the two-source confidence rule and the audit.
        facts = {
            "area_km2": round(wd["area_km2"] or area_km2, 2),
            "population": pop,
            "population_year": wd["population_year"],
            "density": int(round(pop / (wd["area_km2"] or area_km2))) if pop else None,
            "food": count_inside("ovt_food", g),
            "nightlife": count_inside("ovt_night", g),
            "convenience": count_inside("ovt_convenience", g),
            "markets": count_inside("ovt_market", g) + count_inside("market", g),
            "essentials": sum(count_inside(f"ovt_{c}", g) for c in essential_cats),
            "sports": count_inside("ovt_sports", g),
            "culture": count_inside("ovt_venue", g),
            "temples": count_inside("ovt_temple", g),
            "park_ha": round(park_area_ha, 1),
            "park_share": round(100 * park_area_ha / (area_km2 * 100), 1),
            "piers": count_inside("pier", g),
        }
        d["facts"] = facts
        d["osm_counts"] = {
            "food": count_inside("food", g),
            "nightlife": count_inside("night", g) + count_inside("karaoke", g),
            "essentials": sum(count_inside(c, g) for c in essential_cats) + count_inside("convenience", g),
            "sports": count_inside("sports", g),
            "culture": count_inside("venue", g) + count_inside("attraction", g) + count_inside("temple", g),
        }
        places_per_km2 = count_inside("ovt_all", g) / facts["area_km2"]
        raw["crowd"][d["slug"]] = (
            0.5 * math.log(max(facts["density"] or 1, 1)) + 0.5 * math.log1p(places_per_km2)
        )

    print("→ ratings")
    ratings: dict[str, dict[str, int]] = defaultdict(dict)
    for key in ("food", "nightlife", "daily_essentials", "gym_sports", "vibe", "green", "transport"):
        for slug, v in R.percentile_normalize(raw[key]).items():
            ratings[slug][key] = v
    for slug, v in R.percentile_normalize(raw["crowd"], invert=True).items():
        ratings[slug]["crowd"] = v
    for d in districts:
        e = editorial[d["slug"]]
        ratings[d["slug"]]["rent"] = R.rent_to_affordability(e["rent_1br"]) or 5
        ratings[d["slug"]]["safety"] = int(e["safety"])
        raw["rent"][d["slug"]] = e["rent_1br"]
        raw["safety"][d["slug"]] = e["safety"]

    medians = {k: R.median_int([ratings[d["slug"]][k] for d in districts]) for k in RATING_KEYS}
    scores = [R.composite(ratings[d["slug"]], default_weights) for d in districts]
    anchors = R.anchors(scores)

    # Neighbours, label points, simplified geometry
    geoms = [d["geom"] for d in districts]
    simplified = simplify_coverage(geoms)
    for i, d in enumerate(districts):
        d["neighbors"] = [
            districts[j]["slug"] for j in range(len(districts))
            if j != i and geoms[i].buffer(10).intersects(geoms[j])
        ]
        largest = max(d["geom"].geoms, key=lambda p: p.area)
        lp = polylabel(largest, tolerance=15)
        d["label"] = latlng_pair(lp.x, lp.y)
        d["simplified"] = simplified[i]

    # Stations per district. A station on the boundary road itself (Sukhumvit
    # is the Watthana/Khlong Toei border; the BTS runs above its centre line)
    # belongs to both sides — residents of either use it. So "in district" =
    # inside or within BORDER_M of the boundary; "nearby" = up to 800 m out.
    BORDER_M = 150
    for d in districts:
        dist = {s["id"]: d["geom"].distance(Point(s["x"], s["y"])) for s in stations}
        inside_ids = sorted(sid for sid, v in dist.items() if v <= BORDER_M)
        nearby = sorted(sid for sid, v in dist.items() if BORDER_M < v <= 800)
        near500 = {sid for sid, v in dist.items() if v <= 500}
        order = list(LINES)
        lines_serving = sorted({lid for s in stations if s["id"] in near500 for lid in s["lines"]}, key=order.index)
        d["station_ids"], d["nearby_station_ids"], d["line_ids"] = inside_ids, nearby, lines_serving

    # Confidence + sources
    # (category, facts key for Overture count, OSM count key, Overture threshold, OSM threshold)
    TWO_SOURCE = [
        ("food", "food", "food", 100, 30),
        ("nightlife", "nightlife", "nightlife", 20, 10),
        ("daily_essentials", "essentials", "essentials", 60, 30),
        ("gym_sports", "sports", "sports", 10, 5),
        ("vibe", "culture", "culture", 15, 20),
    ]

    def conf_and_sources(d: dict) -> tuple[dict, dict]:
        f, o = d["facts"], d["osm_counts"]
        conf: dict[str, str] = {}
        sources: dict[str, list[str]] = {}
        for cat, fkey, okey, ovt_min, osm_min in TWO_SOURCE:
            ovt_ok, osm_ok = f[fkey] >= ovt_min, o[okey] >= osm_min
            level, srcs = R.two_source_confidence(ovt_ok, osm_ok)
            conf[cat], sources[cat] = level, srcs
        conf.update({"transport": "moderate", "rent": "editorial", "safety": "editorial",
                     "green": "moderate", "crowd": "moderate"})
        sources.update({"transport": ["osm_rail", "transit_model"], "rent": ["listing_research"],
                        "safety": ["ai_research"], "green": ["osm"], "crowd": ["dopa_population", "overture"]})
        return conf, sources

    # Images (Wikimedia Commons via Wikidata P18)
    commons = load("commons")["pages"]
    normalized = commons.get("_normalized", {})
    pages_by_title = {p.get("title"): p for k, p in commons.items() if k != "_normalized"}

    def image_for(d: dict) -> dict | None:
        fname = d["wd"]["image"]
        if not fname:
            return None
        title = normalized.get(f"File:{fname}", f"File:{fname}")
        page = pages_by_title.get(title)
        info = (page or {}).get("imageinfo", [{}])[0]
        if not info.get("thumburl"):
            return None
        meta = info.get("extmetadata", {})
        # Commons now serves thumbnails from thumb.wikimedia.org in fixed
        # "standard" widths (…, 330, 500, 960, …) and appends utm_* params.
        # Drop the tracking query and derive a 500 px variant for map popups.
        hero = info["thumburl"].split("?")[0]
        thumb = re.sub(r"/\d+px-", "/500px-", hero) if "/thumb/" in hero else hero
        return {
            "thumb": thumb,
            "hero": hero,
            "page": info.get("descriptionurl", ""),
            "artist": strip_html(meta.get("Artist", {}).get("value", "")) or "Unknown",
            "license": strip_html(meta.get("LicenseShortName", {}).get("value", "")) or "see file page",
        }

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

    today = date.today()
    data_date = today.strftime("%Y-%m")
    out_districts = []
    for d in districts:
        slug = d["slug"]
        e = editorial[slug]
        conf, sources = conf_and_sources(d)
        out_districts.append({
            "slug": slug,
            "name_en": d["name_en"],
            "name_th": d["name_th"],
            "name_jp": d["name_jp"],
            "name_ru": d["name_ru"],
            "lat": d["label"][0],
            "lng": d["label"][1],
            "ratings": {k: ratings[slug][k] for k in RATING_KEYS},
            "confidence": conf,
            "sources": sources,
            "data_date": data_date,
            "rent": {"one_bed": e["rent_1br"], "two_bed": e["rent_2br"], "source": "listing_research",
                     "updated": json.loads((DATA / "editorial.json").read_text())["_meta"]["updated"]},
            "transit_minutes": agg[slug]["hub_minutes"],
            "min_transit": agg[slug]["min_transit"],
            "station_ids": d["station_ids"],
            "nearby_station_ids": d["nearby_station_ids"],
            "line_ids": d["line_ids"],
            "neighbors": d["neighbors"],
            "aliases": e["aliases"],
            "facts": d["facts"],
            "description": description_for(slug),
            "image": image_for(d),
            "wikipedia": d["wd"]["wikipedia"],
        })

    geometry = {
        d["slug"]: {
            "polygons": [polygon_to_latlng(p) for p in d["simplified"].geoms],
            "bbox": [
                [round(lonlat(*d["simplified"].bounds[:2])[1], 5), round(lonlat(*d["simplified"].bounds[:2])[0], 5)],
                [round(lonlat(*d["simplified"].bounds[2:])[1], 5), round(lonlat(*d["simplified"].bounds[2:])[0], 5)],
            ],
            "label": d["label"],
        }
        for d in districts
    }

    rail_lines = []
    for lid, spec in LINES.items():
        track = tracks.get(lid)
        paths = []
        if track is not None:
            simp = track.simplify(12)
            parts = simp.geoms if simp.geom_type == "MultiLineString" else [simp]
            paths = [[latlng_pair(x, y) for x, y in part.coords] for part in parts if part.length > 50]
        rail_lines.append({
            "id": lid,
            **{k: spec[k] for k in ("name_en", "name_th", "name_ja", "name_ru", "operator", "color", "kind")},
            "paths": paths,
        })
    rail_stations = sorted(
        [{
            "id": s["id"], "name_en": s["name_en"], "name_th": s["name_th"],
            "lat": latlng_pair(s["x"], s["y"])[0], "lng": latlng_pair(s["x"], s["y"])[1],
            "lines": s["lines"], "district": s["district"],
        } for s in stations],
        key=lambda s: s["id"],
    )

    source_agreement = {}
    for cat, fkey, okey, _, _ in TWO_SOURCE:
        a = [math.log1p(d["facts"][fkey] / d["facts"]["area_km2"]) for d in districts]
        b = [math.log1p(d["osm_counts"][okey] / d["facts"]["area_km2"]) for d in districts]
        source_agreement[cat] = round(pearson(a, b), 3)

    meta = {
        "_comment": "GENERATED by scripts/bangkok/build.py — do not edit by hand.",
        "source_agreement_r": source_agreement,
        "district_count": len(districts),
        "station_count": len(rail_stations),
        "stations_in_bangkok": sum(1 for s in rail_stations if s["district"]),
        "medians": medians,
        "default_anchors": anchors,
        "rent_scale": {"floor": R.RENT_FLOOR_THB, "ceiling": R.RENT_CEILING_THB},
        "data_date": data_date,
    }

    signals = {
        "_meta": {
            "generated": today.isoformat(),
            "grid_m": GRID_M,
            "note": "Raw per-district signals (resident-weighted means of per-point values) before percentile normalisation. See scripts/bangkok/build.py.",
        },
        "districts": {
            d["slug"]: {
                "raw": {k: round(raw[k][d["slug"]], 4) for k in RATING_KEYS},
                "ratings": {k: ratings[d["slug"]][k] for k in RATING_KEYS},
                **agg[d["slug"]],
                "facts": d["facts"],
                "osm_counts": d["osm_counts"],
                "stations": d["station_ids"],
                "lines": d["line_ids"],
            }
            for d in districts
        },
    }

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

    if args.verbose:
        print("\nAll districts (composite · ratings · min commute):")
        for d in top:
            r = ratings[d["slug"]]
            cells = " ".join(f"{k[:4]}={r[k]:>2}" for k in RATING_KEYS)
            print(f"  {d['slug']:22s} {R.composite(r, default_weights):4.1f}  {cells}  min={agg[d['slug']]['min_transit']:>3}")

    if args.dry_run:
        print("\n(dry run — nothing written)")
        return

    APP.mkdir(parents=True, exist_ok=True)

    def dump(path: Path, obj, indent: int | None = None):
        path.write_text(json.dumps(obj, ensure_ascii=False, indent=indent, separators=None if indent else (",", ":")) + "\n")
        print(f"  wrote {path.relative_to(ROOT)} ({path.stat().st_size / 1024:.0f} KB)")

    dump(APP / "districts.json", {"_meta": {"generated": today.isoformat(), "source": "scripts/bangkok/build.py"},
                                  "districts": out_districts}, indent=1)
    dump(APP / "geometry.json", geometry)
    dump(APP / "rail.json", {"lines": rail_lines, "stations": rail_stations})
    dump(APP / "meta.json", meta, indent=2)
    dump(DATA / "signals.json", signals, indent=1)
    print(f"\nDone in {time.time() - started:.1f}s")


if __name__ == "__main__":
    main()
