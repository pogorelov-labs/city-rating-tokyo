#!/usr/bin/env python3
"""
Compute data-driven ratings v2 — research-backed formulas.
Reads all NocoDB tables, normalizes using log-then-percentile, writes computed_ratings.

Sources used per category:
  food:      HotPepper total + OSM food_count
  nightlife: HP midnight + izakaya + bar + OSM nightlife + karaoke + hostel
  transport: line_count + MLIT passengers
  rent:      Suumo price → linear interpolation (¥70k→10, ¥300k→1)
  safety:    ArcGIS weighted crime (Tokyo) / ward-level (others) + daytime adj
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
from utils import NocoDB, load_stations

ROOT = Path(__file__).resolve().parent.parent

# Rent linear interpolation (aligned with frontend rentToAffordability in app/src/lib/scoring.ts)
# Floor raised from ¥70k → ¥80k because no real Suumo station is below ¥83,500;
# the old floor only existed to absorb the broken distance_estimate fake prices.
# MUST stay in sync with app/src/lib/scoring.ts RENT_FLOOR.
RENT_FLOOR = 80_000   # ¥80k → rating 10
RENT_CEILING = 300_000  # ¥300k → rating 1

# Tokyo Station coordinates (used as reference point for rent regression)
TOKYO_STATION_LAT = 35.6812
TOKYO_STATION_LNG = 139.7671

# Absolute caps for rating tiers (CRTKY formula v3).
# Format: (min_rating, threshold) — "to score min_rating or higher, raw value must be >= threshold".
# Applied AFTER log-percentile normalization, so cap can only decrease a rating, never increase it.
# Purpose: prevent "top 5.6%" from automatically meaning "10" when the raw value isn't exceptional.
ABSOLUTE_CAPS = {
    "food":       [(8, 100), (9, 400),  (10, 1000)],  # hp_total + osm_food
    "nightlife":  [(8, 20),  (9, 100),  (10, 300)],   # hp_midnight
    "transport":  [(8, 2),   (9, 3),    (10, 5)],     # line_count (5+ lines for a 10)
    "green":      [(8, 25),  (9, 50),   (10, 80)],    # green_count (area_sqm not scraped yet)
    "gym_sports": [(8, 7),   (9, 12),   (10, 20)],    # gym_count
    "vibe":       [(8, 8),   (9, 20),   (10, 50)],    # cultural_venue_count
    # Rent uses SOURCE QUALITY as the cap dimension (not raw price):
    # 2 = Suumo real data, 1 = ward average, 0 = distance regression estimate.
    # Ensures regression fallbacks can never surface as "exceptional affordability".
    "rent":       [(9, 1),   (10, 2)],
}


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
    if not values:
        return {}

    # Step 1: log transform
    log_values = {slug: math.log1p(v) for slug, v in values.items()}

    # Step 2: percentile ranking with midpoint for ties
    sorted_vals = sorted(log_values.values())
    n = len(sorted_vals)

    # Build value → midpoint rank mapping (average of first and last occurrence)
    from bisect import bisect_right
    midpoint_rank = {}
    i = 0
    while i < n:
        val = sorted_vals[i]
        j = bisect_right(sorted_vals, val)  # one past last occurrence
        mid = (i + j - 1) / 2.0
        midpoint_rank[val] = mid
        i = j

    result = {}
    for slug, val in log_values.items():
        rank = midpoint_rank[val]
        percentile = rank / max(n - 1, 1)
        if invert:
            percentile = 1.0 - percentile
        rating = max(1, min(10, round(percentile * 9 + 1)))
        result[slug] = rating

    return result


def rent_to_affordability(price):
    """Linear interpolation: ¥70k→10, ¥300k→1. Matches frontend PR #28."""
    if not price or price <= 0:
        return None
    t = max(0.0, min(1.0, (price - RENT_FLOOR) / (RENT_CEILING - RENT_FLOOR)))
    return max(1, min(10, round(10 - 9 * t)))


def haversine(lat1, lng1, lat2, lng2):
    """Distance in km between two lat/lng points."""
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlng / 2) ** 2)
    return R * 2 * math.asin(math.sqrt(a))


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
    Uses real Suumo data as training set. Returns (intercept, slope, n_samples).
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


def main():
    parser = argparse.ArgumentParser(description="Compute data-driven ratings v2")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    stations = load_stations()
    station_map = {s["slug"]: s for s in stations}
    all_slugs = [s["slug"] for s in stations]
    print(f"Total stations: {len(stations)}")

    # ===== Load all data sources =====
    print("\nLoading data sources from NocoDB...")

    osm = {r["slug"]: r for r in NocoDB("osm_pois").get_all_records() if r.get("slug")}
    print(f"  osm_pois:         {len(osm)} stations")

    hp = {r["slug"]: r for r in NocoDB("hotpepper").get_all_records() if r.get("slug")}
    print(f"  hotpepper:        {len(hp)} stations")

    ext = {r["slug"]: r for r in NocoDB("osm_extended").get_all_records() if r.get("slug")}
    print(f"  osm_extended:     {len(ext)} stations")

    crime = {r["slug"]: r for r in NocoDB("station_crime").get_all_records() if r.get("slug")}
    print(f"  station_crime:    {len(crime)} stations (Tokyo neighborhood-level)")

    crime_ward = {r["ward_code"]: r for r in NocoDB("crime_stats").get_all_records() if r.get("ward_code")}
    print(f"  crime_stats:      {len(crime_ward)} wards (legacy fallback)")

    pax = {r["slug"]: r for r in NocoDB("passenger_counts").get_all_records() if r.get("slug")}
    print(f"  passenger_counts: {len(pax)} stations")

    wards = {r["slug"]: r for r in NocoDB("station_wards").get_all_records() if r.get("slug")}
    print(f"  station_wards:    {len(wards)} stations")

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
        "green", "gym", "vibe", "crowd"
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
        if food_hp > 0 and food_osm > 0:
            conf["food"] = "strong"
            srcs["food"] = ["hotpepper", "osm"]
        elif food_hp > 0:
            conf["food"] = "moderate"
            srcs["food"] = ["hotpepper"]
        else:
            conf["food"] = "estimate"
            srcs["food"] = []

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
        if rent_price and rent_price > 0:
            raw["rent"][slug] = rent_price
            conf["rent"] = "strong"
            srcs["rent"] = ["suumo"]
            cap_raw["rent"][slug] = 2  # real Suumo data → up to 10 allowed
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

        # --- SAFETY: weighted crime from ArcGIS (Tokyo) or ward-level (others) ---
        if cr and cr.get("weighted_crime_score") is not None:
            # ArcGIS neighborhood-level (Tokyo)
            # IMPORTANT: crimes_per_10k from scraper may be distorted for tiny-population
            # neighborhoods (e.g., Shinjuku 3-chome: pop=101, crimes=879 → rate=11161).
            # Use weighted_crime_score directly and normalize separately.
            # For neighborhoods with pop < 500, cap the rate to avoid distortion.
            pop = cr.get("population", 0) or 0
            weighted = cr.get("weighted_crime_score", 0) or 0
            if pop >= 500:
                raw["safety"][slug] = weighted / pop * 10000
            elif pop > 0:
                # Commercial area with tiny residential pop — use a blended rate
                # Assume effective daytime pop is at least 5000 for any station area
                effective_pop = max(pop, 5000)
                raw["safety"][slug] = weighted / effective_pop * 10000
            else:
                raw["safety"][slug] = weighted * 0.1  # raw score as proxy
            conf["safety"] = "strong"
            srcs["safety"] = ["keishicho_arcgis"]
        else:
            # Fallback: ward-level from crime_stats (legacy) or Nominatim ward match
            ward_name = w.get("city_name", "")
            matched_ward = None
            for wc, wd in crime_ward.items():
                if wd.get("ward_name", "") == ward_name:
                    matched_ward = wd
                    break
            if matched_ward:
                raw["safety"][slug] = matched_ward.get("crimes_per_10k", 0) or 0
                conf["safety"] = "moderate"
                srcs["safety"] = ["ward_crime_stats"]
            else:
                # Prefecture average fallback.
                # CRTKY-64: add distance-based jitter to avoid 4 fixed values
                # creating gaps in the distribution. Suburban stations (farther
                # from Tokyo Station) tend slightly safer → lower rate.
                pref = st.get("prefecture", "13")
                pref_avgs = {"13": 120, "14": 65, "11": 60, "12": 55}
                base = pref_avgs.get(pref, 80)
                dist = haversine(st["lat"], st["lng"], TOKYO_STATION_LAT, TOKYO_STATION_LNG)
                # ±15% jitter scaled by distance (30km = ~15% less crime)
                jitter_factor = 1.0 - min(0.15, dist * 0.005)
                raw["safety"][slug] = base * jitter_factor
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
            conf["vibe"] = "moderate" if cultural > 0 else "estimate"
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
            conf["crowd"] = "strong"
            srcs["crowd"] = ["mlit_s12"]
        else:
            # Fallback: HP total as proxy + line_count
            raw["crowd"][slug] = food_hp * 300 + line_count * 10000
            conf["crowd"] = "estimate"
            srcs["crowd"] = ["hp_proxy"]

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
    categories = ["food", "nightlife", "transport", "rent", "safety", "green", "gym_sports", "vibe", "crowd"]
    data_date = date.today().strftime("%Y-%m")
    results = {}
    for slug in all_slugs:
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
            "confidence": json.dumps(confidence.get(slug, {})),
            "sources": json.dumps(sources_used.get(slug, {})),
            "data_date": data_date,
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
    # Expected values calibrated to DATA (not AI estimates which were too generous on safety)
    # Shinjuku 3-chome: 879 crimes/yr → safety 1-2 is CORRECT (Kabukicho adjacent)
    # Sugamo: 44 crimes, pop 3916 → safety 7-8 is CORRECT
    check_stations = [
        ("shinjuku", {"food": 9, "nightlife": 9, "transport": 10, "crowd": 1}),
        ("shibuya", {"food": 9, "nightlife": 9, "transport": 10}),
        ("kichijoji", {"food": 8, "nightlife": 7}),
        ("sugamo", {"food": 7, "safety": 7}),
        ("roppongi", {"food": 8, "nightlife": 9}),
    ]
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

    if args.dry_run:
        print("\nDry run — not writing to NocoDB.")
        return

    # ===== Write to NocoDB =====
    print(f"\nWriting {len(results)} computed ratings to NocoDB...")
    db = NocoDB("computed_ratings")

    # Clear existing
    existing = db.get_all_records(fields=["Id"])
    if existing:
        import requests as req
        for i in range(0, len(existing), 100):
            batch = existing[i:i + 100]
            ids = [{"Id": r["Id"]} for r in batch if r.get("Id")]
            if ids:
                req.delete(f"{db.base_url}/records", headers=db.headers, json=ids)

    # Insert (includes confidence, sources, data_date columns)
    records = list(results.values())
    db.bulk_insert(records)
    print(f"Done! Wrote {len(records)} records.")


if __name__ == "__main__":
    main()
