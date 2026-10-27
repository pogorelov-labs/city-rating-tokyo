"""District signal aggregation, geometry and source confidence."""
from __future__ import annotations
import math
from collections import defaultdict
import shapely
from shapely.geometry import Point
from shapely.ops import polylabel
import bangkok.ratings as R
from bangkok.bkk_config import RATING_KEYS
from bangkok.geom import latlng_pair, simplify_coverage
from bangkok.population import crowd_raw
from bangkok.static_data import HUBS, LINES


def build_district_data(districts, pt, OWN, weight, commute_pt, d_station,
                        pois, parks, population, editorial, default_weights,
                        rent_meta, stations):
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
        raw["crowd"][d["slug"]] = crowd_raw(
            population[d["slug"]]["population"] / facts["area_km2"],
            0.5 * math.log1p(places_per_km2),
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
        conf.update({"transport": "moderate", "rent": editorial[d["slug"]].get("rent_confidence", rent_meta["confidence"]), "safety": "editorial",
                     "green": "moderate", "crowd": "moderate"})
        sources.update({"transport": ["osm_rail", "transit_model"], "rent": ["listing_research"],
                        "safety": ["ai_research"], "green": ["osm"], "crowd": ["worldpop_2020", "overture"]})
        return conf, sources

    return raw, agg, ratings, medians, anchors, TWO_SOURCE, conf_and_sources, count_inside
