"""Load the frozen Bangkok boundary, POI and station source data."""
from __future__ import annotations
import difflib
import html
import json
import math
import re
import sys
import urllib.parse
from collections import defaultdict
import numpy as np
from shapely.geometry import Polygon
from bangkok.bkk_config import RAW
from bangkok.geom import assemble_multipolygon, xy
from bangkok.static_data import RU_NAMES, SLUG_OVERRIDES, STATION_JA_FALLBACK, STATION_NAME_ALIASES

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
            "qid": t.get("wikidata"),
        })
    return cands

def clean_ja_label(label: str | None) -> str | None:
    """"バーンスー駅 (MRT)" → "バーンスー": Tokyo's `name_jp` omits 駅 too."""
    if not label:
        return None
    label = re.sub(r"\s*[（(][^）)]*[）)]\s*$", "", label.strip())
    return re.sub(r"駅$", "", label).strip() or None

def commons_image(fname: str | None, commons: dict) -> dict | None:
    """Wikidata P18 file name → hot-link URLs + attribution from the Commons dump."""
    if not fname:
        return None
    normalized = commons.get("_normalized", {})
    pages_by_title = {p.get("title"): p for k, p in commons.items() if k != "_normalized"}
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
        "artist": clean_artist(strip_html(meta.get("Artist", {}).get("value", ""))),
        "license": strip_html(meta.get("LicenseShortName", {}).get("value", "")) or "see file page",
    }

def clean_artist(artist: str) -> str:
    """Commons "Artist" fields are free text; keep just the author for the
    one-line credit (the licence and file page link carry the rest):

      No machine-readable author provided. Cdha~commonswiki assumed (…)  → Cdha
      This Photo was taken by Supanut Arunoprayote. Feel free to …       → Supanut Arunoprayote
      The original uploader was Heuristics at Thai Wikipedia.            → Heuristics
      Fotograf / Photographer: Heinrich Damm (User:Hdamm, …)             → Heinrich Damm
    """
    a = artist.strip()
    for pattern in (
        r"No machine-readable author provided\.\s*(.+?)\s+assumed\b",
        r"(?:This )?Photo (?:was )?taken by\s+(.+?)[.,(]",
        r"The original uploader was\s+(.+?)\s+at\s+\w+ Wikipedia",
        r"(?:Fotograf\s*/\s*)?Photographer:\s*(.+?)\s*(?:\(|$)",
    ):
        m = re.search(pattern, a, flags=re.I)
        if m:
            a = m.group(1)
            break
    # Thai Commons boilerplate: "creator / submitted to Wikimedia Commons".
    a = a.replace("ผู้สร้างสรรค์ผลงาน/ส่งข้อมูลเก็บในคลังข้อมูลเสรีวิกิมีเดียคอมมอนส์", "").replace(" - ", " / ")
    a = re.sub(r"~\w+wiki\b", "", a)
    a = re.sub(r"\s+", " ", a).strip(" /")
    if len(a) > 60:
        a = a[:57].rstrip() + "…"
    return a or "Unknown"

def label_matches(station_norm: str, en_label: str) -> bool:
    """Does a Wikidata English label name this station? OSM `wikidata` tags are
    occasionally copied from the neighbouring station (Si Iam's node points at
    Si La Salle's item); spelling variants (Tao Pun / Tao Poon) still match."""
    if not en_label:
        return True  # nothing to check against
    label = re.sub(r"\b(mrt|bts|arl|srt|brt|station|central terminal)\b", " ", en_label, flags=re.I)
    a, b = station_norm.replace(" ", ""), norm_name(label).replace(" ", "")
    return a in b or b in a or difflib.SequenceMatcher(None, a, b).ratio() >= 0.7

def attach_station_wikidata(stations: list[dict]) -> None:
    """Japanese name, photo and Wikipedia links for each station, via the
    `wikidata` tag of its OSM station node(s).

    Interchanges have one OSM node (and item) per operator, so candidates
    within 350 m are matched by name first; the first item with a Japanese
    label / an image wins.
    """
    wd = load("station_wikidata")["entities"]
    commons = load("station_commons")["pages"]
    cands = [c for c in load_station_candidates() if c["qid"]]
    for s in stations:
        near = [c for c in cands if math.hypot(c["x"] - s["x"], c["y"] - s["y"]) < 350]
        named = [c for c in near if c["norm"] == s["norm"]]
        closest = sorted(near, key=lambda c: math.hypot(c["x"] - s["x"], c["y"] - s["y"]))
        pool = named or [c for c in closest[:1] if math.hypot(c["x"] - s["x"], c["y"] - s["y"]) < 120]
        ents = [
            wd[c["qid"]] for c in pool
            if c["qid"] in wd and label_matches(s["norm"], wd[c["qid"]].get("labels", {}).get("en", {}).get("value", ""))
        ]
        s["name_ja"] = next(
            (clean_ja_label(e.get("labels", {}).get("ja", {}).get("value")) for e in ents
             if e.get("labels", {}).get("ja")), None,
        ) or STATION_JA_FALLBACK.get(s["id"])
        s["image"] = None
        s["wikipedia"] = {}
        for e in ents:
            info = wikidata_info(e)
            if not s["image"] and info["image"]:
                s["image"] = commons_image(info["image"], commons)
            for lang, url in info["wikipedia"].items():
                s["wikipedia"].setdefault(lang, url)
