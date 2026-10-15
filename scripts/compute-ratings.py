#!/usr/bin/env python3
"""
Compute data-driven ratings v2 — research-backed formulas.
Reads all NocoDB tables, normalizes using log-then-percentile, writes computed_ratings.

Sources used per category:
  food:      HotPepper total + OSM food_count
  nightlife: HP midnight + izakaya + bar + OSM nightlife + karaoke + hostel
  transport: line_count + MLIT passengers
  rent:      Suumo price → linear interpolation (¥80k→10, ¥300k→1)
  safety:    official crime open data, 2024 (data/crime/station-safety.json): Tokyo 800 m
             町丁 catchments, municipal rates elsewhere; daytime-adjusted denominators
  green:     OSM green_count + green_area_sqm (when available)
  gym:       OSM gym_count
  vibe:      OSM cultural venues + pedestrian streets + cafes
  crowd:     MLIT passengers (inverted)

See research/01-06*.md and CLAUDE.md for full documentation.

Usage: python3 scripts/compute-ratings.py [--dry-run]
"""

import argparse
import json
import math
import sys
from bisect import bisect_left
from collections import defaultdict
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "scrapers"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "packages" / "schema" / "python"))
from utils import NocoDB, load_stations
from source_health import check_sources, check_source_mix, station_dates, encode_dates, conservative_month
from rating_store import DEFAULT_RECOVERY_DIR, NocoRatingStore, replace_ratings
from slugs import index_by_slug, load_slug_redirects
from city_rating_schema.constants import (
    RENT_FLOOR,
    RENT_CEILING,
    RATING_KEYS,
    PIPELINE_ONLY,
)

from city_rating_schema.normalize import (
    midpoint_percentile, rent_to_affordability as normalize_rent, two_source_confidence,
)

ROOT = Path(__file__).resolve().parent.parent

# Rent linear interpolation floor/ceiling and absolute caps now come from
# @city-rating/schema (single source of truth shared with app/src/lib/scoring.ts
# and mcp/src/city_rating_mcp/scoring.py). The ¥70k→¥80k history lives there.
TOKYO_STATION_LAT = PIPELINE_ONLY.tokyo_station_lat
TOKYO_STATION_LNG = PIPELINE_ONLY.tokyo_station_lng

# Absolute caps for rating tiers (CRTKY formula v3).
# Format: (min_rating, threshold) — "to score min_rating or higher, raw value must be >= threshold".
# Applied AFTER log-percentile normalization, so cap can only decrease a rating, never increase it.
# Purpose: prevent "top 5.6%" from automatically meaning "10" when the raw value isn't exceptional.
ABSOLUTE_CAPS = PIPELINE_ONLY.absolute_caps


def log_percentile_normalize(values, invert=False):
    """
    Log-then-percentile normalization.
    1. Apply log(1 + value) to compress skewed distributions
    2. Rank by percentile across all stations
    3. Map to 1-10

    This separates true zeroes from low-but-nonzero while compressing mega-peaks.
    Example for food: 0→1, 5→3, 25→5, 100→7, 500→9, 2000→10

    Uses midpoint rank for ties (CRTKY-64/65): when N stations share the
    same value, each gets the average of the lowest and highest rank in the
    group instead of all getting the lowest rank. This spreads tied clusters
    across the rating boundary instead of lumping them at one integer.
    """
    return midpoint_percentile(values, invert=invert, pre=math.log1p)


def rent_to_affordability(price):
    """Linear interpolation: ¥80k→10, ¥300k→1. Matches frontend scoring.ts rentToAffordability."""
    return normalize_rent(price, RENT_FLOOR, RENT_CEILING)


def haversine(lat1, lng1, lat2, lng2):
    """Distance in km between two lat/lng points."""
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlng / 2) ** 2)
    return R * 2 * math.asin(math.sqrt(a))


PASSENGERS_PATH = ROOT / "data" / "passengers" / "s12-passengers.json"


def load_passengers():
    """MLIT S12 daily passengers by current slug (CRTKY-84).

    Written by scripts/scrapers/ingest-mlit-s12.py. Replaces the NocoDB
    passenger_counts table, whose ingest was never committed.
    """
    doc = json.loads(PASSENGERS_PATH.read_text())
    return doc["stations"], doc["metadata"]["fiscal_year"]


SAFETY_PATH = ROOT / "data" / "crime" / "station-safety.json"


def load_station_safety():
    """Weighted crime rate per current slug (CRTKY-82).

    Written by scripts/scrapers/ingest-crime-open-data.py from police open data
    in all four prefectures. Replaces the NocoDB station_crime rows (Esri layer,
    ingest never committed) and crime_stats (hand-typed literals).
    """
    doc = json.loads(SAFETY_PATH.read_text())
    return doc["stations"], doc["metadata"]["year"]


def load_rent_data():
    """Load Suumo rent data from all possible locations."""
    for p in [
        ROOT / "app" / "src" / "data" / "rent-averages.json",
        ROOT / "data" / "rent" / "rent-averages-v2.json",
        ROOT / "data" / "rent" / "rent-averages.json",
    ]:
        if p.exists():
            return json.loads(p.read_text())
    return {}


def fit_rent_regression(rent_data, station_map):
    """
    Fit log-linear regression: log(rent) = a + b * distance_km.
    Trains on every row of rent-averages.json — Suumo listings and, since PR #91,
    e-Stat municipal averages — so it reflects outer-area municipalities too.
    Only used for the few stations with neither. Returns (intercept, slope, n_samples).
    Housing prices decay exponentially with distance, so log-linear fits well.

    Replaces the broken `max(50000, 160000 - dist*15000)` formula that was
    producing fake ¥50k rents for 507 stations (rating 10/10 for "affordability"
    when real Suumo data shows the cheapest actual rent in Greater Tokyo is ~¥83k).
    """
    xs, ys = [], []
    for slug, rd in rent_data.items():
        price = rd.get("1k_1ldk") if isinstance(rd, dict) else None
        if not price or price <= 0 or slug not in station_map:
            continue
        s = station_map[slug]
        dist = haversine(s["lat"], s["lng"], TOKYO_STATION_LAT, TOKYO_STATION_LNG)
        xs.append(dist)
        ys.append(math.log(price))

    if len(xs) < 10:
        # Not enough data — fall back to reasonable defaults
        return (math.log(230_000), -0.025, 0)

    n = len(xs)
    x_mean = sum(xs) / n
    y_mean = sum(ys) / n
    num = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys))
    den = sum((x - x_mean) ** 2 for x in xs)
    if den == 0:
        return (y_mean, 0.0, n)
    slope = num / den
    intercept = y_mean - slope * x_mean
    return (intercept, slope, n)


def apply_absolute_cap(rating, raw_value, caps):
    """
    Apply absolute caps to a rating.
    caps is a list of (min_rating, required_raw) — "to score >= min_rating, raw must be >= required".
    Returns the minimum of the original rating and the strictest applicable cap.
    Only decreases ratings; never increases.
    """
    max_allowed = 10
    for min_rating, required in sorted(caps, reverse=True):
        if raw_value < required:
            max_allowed = min(max_allowed, min_rating - 1)
    return min(rating, max_allowed)


def vibe_confidence(cultural, ped_streets):
    """
    Confidence level for the vibe rating (CRTKY-128).

    Vibe is measured from two independent OSM signals: cultural venues
    (theatres, cinemas, galleries, book/music shops) and pedestrian streets.
    Both present → 'strong', mirroring food and nightlife, where two
    corroborating sources earn 'strong'. Cultural venues alone → 'moderate'.
    Pedestrian streets alone carry only 0.15 of the formula, so they stay
    'estimate', as does the no-signal composite fallback.

    Confidence describes how well-grounded the number is, not how high it
    is, so there is deliberately no venue-count threshold here — magnitude
    is handled by ABSOLUTE_CAPS.
    """
    if cultural > 0 and ped_streets > 0:
        return "strong"
    if cultural > 0:
        return "moderate"
    return "estimate"


def main():
    parser = argparse.ArgumentParser(description="Compute data-driven ratings v2")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--no-strict",
        action="store_true",
        help="Do not exit 1 on spot-check divergences (debugging only — "
             "refresh-ratings.sh relies on the strict default).",
    )
    parser.add_argument("--max-source-age-days", type=int, required=True)
    parser.add_argument("--recovery-dir", type=Path, default=DEFAULT_RECOVERY_DIR)
    args = parser.parse_args()

    stations = load_stations()
    station_map = {s["slug"]: s for s in stations}
    all_slugs = [s["slug"] for s in stations]
    print(f"Total stations: {len(stations)}")

    # ===== Load all data sources =====
    print("\nLoading data sources from NocoDB...")
    # NocoDB rows scraped before the CRTKY-113 rename still use the old slugs;
    # index them by current slug or 334 stations silently get no data at all.
    redirects = load_slug_redirects()

    def load_by_slug(table):
        index, remapped = index_by_slug(NocoDB(table).get_all_records(), redirects)
        return index, (f"  ({remapped} via pre-rename slugs)" if remapped else "")

    osm, note = load_by_slug("osm_pois")
    print(f"  osm_pois:         {len(osm)} stations{note}")

    livability, note = load_by_slug("osm_livability")
    print(f"  osm_livability:   {len(livability)} stations{note}")

    hp, note = load_by_slug("hotpepper")
    print(f"  hotpepper:        {len(hp)} stations{note}")

    ext, note = load_by_slug("osm_extended")
    print(f"  osm_extended:     {len(ext)} stations{note}")

    source_tables = {"hotpepper": hp, "osm_pois": osm,
                     "osm_extended": ext, "osm_livability": livability}
    # Check the exact inputs used below, even if invoked outside refresh.
    print(json.dumps(check_sources(all_slugs, source_tables, args.max_source_age_days), indent=2))

    crime, crime_year = load_station_safety()
    print(f"  station safety:   {len(crime)} stations (police open data {crime_year})")
    # Fallback for a station without crime data: its prefecture's median rate,
    # on the same scale as everything else.
    pref_rates = defaultdict(list)
    for s in stations:
        if s["slug"] in crime:
            pref_rates[s.get("prefecture")].append(crime[s["slug"]]["rate"])
    pref_median = {pf: sorted(v)[len(v) // 2] for pf, v in pref_rates.items()}


    pax, pax_year = load_passengers()
    print(f"  passengers:       {len(pax)} stations (MLIT S12 FY{pax_year})")

    wards, note = load_by_slug("station_wards")
    print(f"  station_wards:    {len(wards)} stations{note}")

    rent_data = load_rent_data()
    print(f"  rent (Suumo):     {len(rent_data)} stations")

    # Fit log-linear rent regression from real Suumo data.
    # Used as fallback for stations without Suumo data AND without ward average.
    # Replaces the broken `max(50000, 160000 - dist*15000)` formula that gave
    # 507 stations a fake 10/10 affordability rating.
    rent_intercept, rent_slope, rent_n = fit_rent_regression(rent_data, station_map)
    print(f"  rent regression:  log(rent) = {rent_intercept:.3f} + {rent_slope:.5f} * km  (fit on n={rent_n})")
    if rent_n > 0:
        # Sanity-check predictions at 0, 20, 40 km
        for d in [0, 10, 20, 30, 40]:
            pred = math.exp(rent_intercept + rent_slope * d)
            print(f"                    at {d:2d} km → ¥{pred:>7,.0f}")

    # Compute ward-average rents for fallback
    ward_rents = defaultdict(list)
    for slug, rd in rent_data.items():
        price = rd.get("1k_1ldk")
        if price and price > 0:
            ward_info = wards.get(slug, {})
            ward_name = ward_info.get("city_name", "") or ward_info.get("ward_name", "")
            if ward_name:
                ward_rents[ward_name].append(price)
    ward_avg_rent = {w: int(sum(ps) / len(ps)) for w, ps in ward_rents.items() if ps}
    print(f"  ward avg rents:   {len(ward_avg_rent)} wards")

    # ===== Compute raw signals =====
    print("\nComputing raw signals...")

    raw = {cat: {} for cat in [
        "food", "nightlife", "transport", "rent", "safety",
        "green", "gym", "vibe", "crowd", "daily_essentials"
    ]}
    confidence = {}  # slug -> {category: 'strong'|'moderate'|'estimate'}
    sources_used = {}  # slug -> {category: [source_names]}
    # Track raw "cap values" per category per station for ABSOLUTE_CAPS check.
    # These are the actual user-facing counts (restaurants, lines, etc.) used to
    # gate the 8/9/10 tiers, separate from the weighted/log signals used for ranking.
    cap_raw = {cat: {} for cat in ABSOLUTE_CAPS.keys()}

    for slug in all_slugs:
        st = station_map[slug]
        o = osm.get(slug, {})
        h = hp.get(slug, {})
        e = ext.get(slug, {})
        p = pax.get(slug, {})
        cr = crime.get(slug, {})
        w = wards.get(slug, {})
        rent = rent_data.get(slug, {})
        line_count = st.get("line_count", 1) or 1

        conf = {}
        srcs = {}

        # --- FOOD: log(HP_total)*0.6 + log(OSM_food)*0.4 ---
        food_hp = h.get("total_count", 0) or 0
        food_osm = o.get("food_count", 0) or 0
        raw["food"][slug] = math.log1p(food_hp) * 0.6 + math.log1p(food_osm) * 0.4
        cap_raw["food"][slug] = food_hp + food_osm  # total restaurants for cap check
        conf["food"], srcs["food"] = two_source_confidence(
            food_hp > 0, food_osm > 0, sources=("hotpepper", "osm"),
            policy="primary_required",  # Preserve HP=0 → estimate/[], even with OSM.
        )

        # --- NIGHTLIFE: HP midnight + izakaya + bar + OSM night + karaoke + hostel ---
        midnight = h.get("midnight_count", 0) or 0
        izakaya = h.get("izakaya_count", 0) or 0
        bar_hp = h.get("bar_count", 0) or 0
        night_osm = o.get("nightlife_count", 0) or 0
        karaoke = e.get("karaoke_count", 0) or 0
        hostel = e.get("hostel_count", 0) or 0
        nightclub = e.get("nightclub_count", 0) or 0
        raw["nightlife"][slug] = (
            math.log1p(midnight) * 0.25 +
            math.log1p(izakaya) * 0.20 +
            math.log1p(bar_hp * 3) * 0.15 +
            math.log1p(night_osm) * 0.15 +
            math.log1p(nightclub * 10) * 0.10 +
            math.log1p(karaoke * 5) * 0.08 +
            math.log1p(hostel * 10) * 0.07
        )
        cap_raw["nightlife"][slug] = midnight  # late-night venue count for cap check
        night_sources = []
        if midnight > 0: night_sources.append("hotpepper_midnight")
        if izakaya > 0: night_sources.append("hotpepper")
        if night_osm > 0: night_sources.append("osm")
        if karaoke > 0: night_sources.append("osm_karaoke")
        conf["nightlife"] = "strong" if len(night_sources) >= 2 else ("moderate" if night_sources else "estimate")
        srcs["nightlife"] = night_sources

        # --- TRANSPORT: line_count * 2 + log(passengers) * 0.5 ---
        daily_pax = p.get("daily_passengers", 0) or 0
        raw["transport"][slug] = line_count * 2 + math.log1p(daily_pax) * 0.5
        cap_raw["transport"][slug] = line_count  # number of train lines for cap check
        conf["transport"] = "strong" if daily_pax > 0 else "moderate"
        srcs["transport"] = ["line_count"] + (["mlit_s12"] if daily_pax > 0 else [])

        # --- RENT: linear interpolation ¥70k→10, ¥300k→1 (matches frontend PR #28) ---
        rent_price = rent.get("1k_1ldk") or rent.get("2ldk")
        rent_source = rent.get("source", "suumo") if isinstance(rent, dict) else "suumo"
        if rent_price and rent_price > 0:
            raw["rent"][slug] = rent_price
            if rent_source in ("suumo", "homes"):
                conf["rent"] = "strong"
                srcs["rent"] = [rent_source]
                cap_raw["rent"][slug] = 2  # real scraped data → up to 10
            elif rent_source == "estat":
                conf["rent"] = "moderate"
                srcs["rent"] = ["estat"]
                cap_raw["rent"][slug] = 1  # govt survey municipality avg → capped at 9
            else:
                conf["rent"] = "moderate"
                srcs["rent"] = [rent_source]
                cap_raw["rent"][slug] = 1
        else:
            # Fallback: ward average
            ward_name = w.get("city_name", "") or w.get("ward_name", "")
            avg = ward_avg_rent.get(ward_name)
            if avg:
                raw["rent"][slug] = avg
                conf["rent"] = "moderate"
                srcs["rent"] = ["ward_average"]
                cap_raw["rent"][slug] = 1  # ward average → capped at 9
            else:
                # Log-linear regression fit on real Suumo data: log(rent) = a + b * distance
                # Replaces broken max(50000, 160000 - dist*15000) which produced ¥50k
                # for every station beyond 7km — a floor below what any real Tokyo rent touches.
                dist = haversine(st["lat"], st["lng"], TOKYO_STATION_LAT, TOKYO_STATION_LNG)
                raw["rent"][slug] = math.exp(rent_intercept + rent_slope * dist)
                conf["rent"] = "estimate"
                srcs["rent"] = ["distance_regression"]
                cap_raw["rent"][slug] = 0  # regression estimate → capped at 8

        # --- SAFETY: weighted crime per 10k people from police open data (CRTKY-82) ---
        # Tokyo: 町丁 within 800 m of the station ('strong'); elsewhere the
        # municipality/ward containing it ('moderate'). One year, one formula and
        # one denominator rule everywhere — see ingest-crime-open-data.py.
        if cr:
            raw["safety"][slug] = cr["rate"]
            conf["safety"] = cr["confidence"]
            srcs["safety"] = [cr["source"]]
        else:
            # Not reachable today (the ingest asserts full coverage); kept so a
            # new station without crime data degrades to an honest estimate.
            raw["safety"][slug] = pref_median.get(st.get("prefecture"), 20.0)
            conf["safety"] = "estimate"
            srcs["safety"] = ["prefecture_average"]

        # --- GREEN: green_area if available, else count only ---
        green_count = o.get("green_count", 0) or 0
        green_area = o.get("green_area_sqm", 0) or 0
        if green_area > 0:
            raw["green"][slug] = math.log1p(green_area) * 0.55 + green_count * 0.25
        else:
            raw["green"][slug] = green_count  # count-only fallback
        conf["green"] = "strong" if green_area > 0 else ("moderate" if green_count > 0 else "estimate")
        srcs["green"] = ["osm"] if green_count > 0 else []
        cap_raw["green"][slug] = green_count  # park count for cap check

        # --- GYM: OSM gym_count ---
        # CRTKY-65: for gym=0 stations, add a small tie-breaking jitter
        # from general walkability (food+transport). This spreads the large
        # cluster of zeros into ratings 1-2 instead of lumping all at 1.
        gym = o.get("gym_count", 0) or 0
        if gym > 0:
            raw["gym"][slug] = gym
        else:
            # Micro-jitter: 0 .. 0.5 based on surrounding activity density
            activity = math.log1p(food_hp + food_osm) / 20.0
            raw["gym"][slug] = min(0.5, activity)
        conf["gym_sports"] = "strong" if gym > 0 else "estimate"
        srcs["gym_sports"] = ["osm"] if gym > 0 else []
        cap_raw["gym_sports"][slug] = gym  # gym count for cap check

        # --- VIBE: cultural venues + pedestrian streets + cafes ---
        cultural = e.get("cultural_venue_count", 0) or 0
        ped_streets = e.get("pedestrian_street_count", 0) or 0
        cafe = h.get("cafe_count", 0) or 0
        if cultural > 0 or ped_streets > 0:
            raw["vibe"][slug] = (
                math.log1p(cultural) * 0.60 +
                math.log1p(ped_streets) * 0.15 +
                math.log1p(cafe) * 0.15 +
                (min(cultural, 20) / 20.0) * 0.10  # cultural_shop_ratio proxy
            )
            conf["vibe"] = vibe_confidence(cultural, ped_streets)
            srcs["vibe"] = (["osm_cultural"] if cultural > 0 else []) + (["osm_pedestrian"] if ped_streets > 0 else [])
        else:
            # Fallback: old composite (cafe + convenience + diversity)
            convenience = o.get("convenience_store_count", 0) or 0
            raw["vibe"][slug] = math.log1p(cafe) * 0.4 + math.log1p(convenience) * 0.3 + math.log1p(green_count) * 0.3
            conf["vibe"] = "estimate"
            srcs["vibe"] = ["composite_fallback"]
        cap_raw["vibe"][slug] = cultural  # cultural venue count for cap check

        # --- CROWD: MLIT passengers (inverted) ---
        if daily_pax > 0:
            raw["crowd"][slug] = daily_pax
            # 'moderate' when the count is an older-vintage fallback (unmanned
            # JR East stations drop out of the newest tables) — CRTKY-84.
            conf["crowd"] = p.get("confidence") or "strong"
            srcs["crowd"] = ["mlit_s12"]
        else:
            # Fallback: HP total as proxy + line_count
            raw["crowd"][slug] = food_hp * 300 + line_count * 10000
            conf["crowd"] = "estimate"
            srcs["crowd"] = ["hp_proxy"]

        # --- DAILY ESSENTIALS: supermarket + pharmacy + clinic + bank + laundry + dentist + post_office ---
        liv = livability.get(slug, {})
        supermarket = liv.get("supermarket_count", 0) or 0
        pharmacy = liv.get("pharmacy_count", 0) or 0
        clinic = liv.get("clinic_count", 0) or 0
        bank = liv.get("bank_count", 0) or 0
        laundry_cnt = liv.get("laundry_count", 0) or 0
        dentist = liv.get("dentist_count", 0) or 0
        post_office = liv.get("post_office_count", 0) or 0
        school = liv.get("school_count", 0) or 0
        kindergarten = liv.get("kindergarten_count", 0) or 0
        essentials_total = supermarket + pharmacy + clinic + bank + laundry_cnt + dentist + post_office
        if slug in livability:
            # Weighted: supermarket and pharmacy most important for daily life
            raw["daily_essentials"][slug] = (
                math.log1p(supermarket) * 0.25 +
                math.log1p(pharmacy) * 0.15 +
                math.log1p(clinic + dentist) * 0.20 +
                math.log1p(bank) * 0.10 +
                math.log1p(laundry_cnt) * 0.10 +
                math.log1p(post_office) * 0.05 +
                math.log1p(school + kindergarten) * 0.15
            )
            conf["daily_essentials"] = "strong" if essentials_total >= 5 else ("moderate" if essentials_total > 0 else "estimate")
            srcs["daily_essentials"] = ["osm_livability"]
        else:
            # Fallback: use convenience store count as proxy
            convenience = o.get("convenience_store_count", 0) or 0
            raw["daily_essentials"][slug] = math.log1p(convenience) * 0.5
            conf["daily_essentials"] = "estimate"
            srcs["daily_essentials"] = ["convenience_proxy"]

        confidence[slug] = conf
        sources_used[slug] = srcs

    # ===== Normalize =====
    print("\nNormalizing with log-percentile...")

    # food, nightlife, vibe, green, gym: already log-transformed in raw signals → just percentile
    food_ratings = log_percentile_normalize(raw["food"])
    nightlife_ratings = log_percentile_normalize(raw["nightlife"])
    green_ratings = log_percentile_normalize(raw["green"])
    gym_ratings = log_percentile_normalize(raw["gym"])
    transport_ratings = log_percentile_normalize(raw["transport"])
    vibe_ratings = log_percentile_normalize(raw["vibe"])

    daily_essentials_ratings = log_percentile_normalize(raw["daily_essentials"])

    # crowd, safety: inverted (lower = higher rating)
    crowd_ratings = log_percentile_normalize(raw["crowd"], invert=True)
    safety_ratings = log_percentile_normalize(raw["safety"], invert=True)

    # rent: use linear interpolation (matches frontend), not percentile
    rent_ratings = {}
    for slug in all_slugs:
        price = raw["rent"].get(slug)
        r = rent_to_affordability(price)
        rent_ratings[slug] = r if r else 5

    # ===== Apply absolute caps (Proposal B) =====
    # After log-percentile normalization, apply raw-value caps so that reaching a 10
    # requires hitting an absolute bar (e.g. 5+ train lines for transport=10),
    # not just being in the top 5.6% of a skewed distribution.
    print("\nApplying absolute caps...")
    rating_dicts = {
        "food": food_ratings,
        "nightlife": nightlife_ratings,
        "transport": transport_ratings,
        "green": green_ratings,
        "gym_sports": gym_ratings,
        "vibe": vibe_ratings,
        "rent": rent_ratings,
    }
    for cat, caps in ABSOLUTE_CAPS.items():
        rd = rating_dicts[cat]
        capped_count = 0
        before_top = sum(1 for v in rd.values() if v == 10)
        for slug in all_slugs:
            raw_val = cap_raw[cat].get(slug, 0)
            old = rd.get(slug, 5)
            new = apply_absolute_cap(old, raw_val, caps)
            if new < old:
                capped_count += 1
            rd[slug] = new
        after_top = sum(1 for v in rd.values() if v == 10)
        thresh_str = ", ".join(f"{r}≥{t}" for r, t in caps)
        print(f"  {cat:12s}: {capped_count:>4} stations capped  ·  top-10 count {before_top} → {after_top}  ·  thresholds: {thresh_str}")

    # ===== Build results =====
    categories = list(RATING_KEYS)
    results = {}
    for slug in all_slugs:
        dates = station_dates(slug, source_tables)
        results[slug] = {
            "slug": slug,
            "food": food_ratings.get(slug, 5),
            "nightlife": nightlife_ratings.get(slug, 5),
            "transport": transport_ratings.get(slug, 5),
            "rent": rent_ratings.get(slug, 5),
            "safety": safety_ratings.get(slug, 5),
            "green": green_ratings.get(slug, 5),
            "gym_sports": gym_ratings.get(slug, 5),
            "vibe": vibe_ratings.get(slug, 5),
            "crowd": crowd_ratings.get(slug, 5),
            "daily_essentials": daily_essentials_ratings.get(slug, 5),
            "confidence": json.dumps(confidence.get(slug, {})),
            "sources": json.dumps(sources_used.get(slug, {})),
            "data_date": conservative_month(dates),
            "source_dates": encode_dates(dates),
            "source": "computed_v2",
            "computed_at": date.today().isoformat(),
        }

    # ===== Distribution summary =====
    print("\nRating distribution:")
    for cat in categories:
        dist = defaultdict(int)
        for r in results.values():
            dist[r[cat]] += 1
        dist_str = " ".join(f"{k}:{dist[k]}" for k in sorted(dist.keys()))
        print(f"  {cat:12s}: {dist_str}")

    # ===== Confidence summary =====
    print("\nConfidence distribution:")
    for cat in categories:
        cat_key = cat
        counts = defaultdict(int)
        for slug in all_slugs:
            c = confidence.get(slug, {}).get(cat_key, "estimate")
            counts[c] += 1
        print(f"  {cat:12s}: strong={counts['strong']}  moderate={counts['moderate']}  estimate={counts['estimate']}")

    # ===== Spot-check =====
    print("\nSpot-check (known stations):")
    # Expected values calibrated to DATA (not AI estimates, which were too generous on safety).
    # Safety uses 町丁 within 800 m of Tokyo stations (CRTKY-82): Shinjuku's catchment
    # includes Kabukicho → 1; Sugamo's includes the Jizo-dori shopping street → ~5;
    # Otemachi is an office district whose rate uses daytime population → ~9. If
    # Otemachi drops toward 1, the daytime-population join has broken again.
    check_stations = [
        ("shinjuku", {"food": 9, "nightlife": 9, "transport": 10, "crowd": 1, "safety": 1}),
        ("shibuya", {"food": 9, "nightlife": 9, "transport": 10}),
        ("kichijoji", {"food": 8, "nightlife": 7}),
        ("sugamo", {"food": 7, "safety": 5}),
        ("otemachi", {"safety": 9}),
        ("roppongi", {"food": 8, "nightlife": 9}),
    ]
    spot_failures: list[str] = []
    for slug, expected in check_stations:
        if slug in results:
            r = results[slug]
            vals = " ".join(f"{c}={r[c]}" for c in categories)
            warnings = []
            for cat, exp_val in expected.items():
                actual = r[cat]
                if abs(actual - exp_val) > 3:
                    warnings.append(f"{cat}: computed={actual} expected~{exp_val} DIFF={abs(actual-exp_val)}")
            warn_str = f"  ⚠️  {'; '.join(warnings)}" if warnings else ""
            print(f"  {slug:20s}: {vals}{warn_str}")
            spot_failures.extend(f"{slug}: {w}" for w in warnings)

    # Integrity gate (CRTKY-160): a diverging canary means the join broke —
    # a print-only warning let corrupted output ship through refresh-ratings.sh.
    if spot_failures:
        print(
            f"\nFATAL: {len(spot_failures)} spot-check divergence(s) beyond ±3 — "
            "the daytime-population join or a source ingest has likely broken. "
            "Not writing to NocoDB.",
            file=sys.stderr,
        )
        if args.no_strict:
            print("  (--no-strict passed — continuing anyway)", file=sys.stderr)
        else:
            sys.exit(1)

    if args.dry_run:
        print("\nDry run — not writing to NocoDB.")
        return

    # ===== Write to NocoDB =====
    print(f"\nWriting {len(results)} computed ratings to NocoDB...")
    db = NocoDB("computed_ratings")

    records = list(results.values())
    journal = replace_ratings(NocoRatingStore(db), records, args.recovery_dir,
                              validate=check_source_mix)
    print(f"Done! Verified {len(records)} records. Recovery journal: {journal}")


if __name__ == "__main__":
    main()
