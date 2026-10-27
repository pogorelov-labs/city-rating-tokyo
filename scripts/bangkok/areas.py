"""Station interchange grouping and bounded Voronoi catchments."""
from __future__ import annotations
import math
from collections import defaultdict
import numpy as np
import shapely
from shapely.geometry import MultiPolygon, Point, Polygon
from shapely.ops import unary_union
from bangkok.bkk_config import AREA_RADIUS_M, INTERCHANGE_MERGE_M, RATING_KEYS
from bangkok.geom import simplify_coverage
from bangkok.rents import station_rent, validate_overrides
from bangkok.static_data import HUBS, LINES
import bangkok.ratings as R


def build_station_areas(stations, D, province, rent_overrides):
    rated = [j for j, st in enumerate(stations) if st["district"]]
    parent = list(range(len(stations)))

    def find(a: int) -> int:
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    # Interchange complexes (Asok + Sukhumvit, Sala Daeng + Si Lom, Mo Chit +
    # Chatuchak Park …) are one neighbourhood: splitting them would draw two
    # half-areas around one set of streets.
    # Closest pairs first; a merge is refused when the two groups share a line,
    # so no chain (A–X–B) can pull two stops of one line into one area.
    group_lines = {j: set(stations[j]["lines"]) for j in rated}
    pairs = sorted(
        (math.hypot(stations[a]["x"] - stations[b]["x"], stations[a]["y"] - stations[b]["y"]), a, b)
        for ii, a in enumerate(rated)
        for b in rated[ii + 1:]
    )
    for dist, a, b in pairs:
        if dist > INTERCHANGE_MERGE_M:
            break
        ra, rb = find(a), find(b)
        if ra == rb or group_lines[ra] & group_lines[rb]:
            continue
        parent[ra] = rb
        group_lines[rb] |= group_lines.pop(ra)
    groups: dict[int, list[int]] = defaultdict(list)
    for j in rated:
        groups[find(j)].append(j)
    line_order = list(LINES)

    def member_key(j: int):
        st = stations[j]
        return (-len(st["lines"]), min(line_order.index(lid) for lid in st["lines"]), st["name_en"])

    areas: list[dict] = []
    for members in groups.values():
        members.sort(key=member_key)
        ms = [stations[j] for j in members]
        areas.append({
            "id": ms[0]["id"],
            "members": members,
            "name_en": " / ".join(st["name_en"] for st in ms),
            "name_th": " / ".join(st["name_th"] for st in ms if st["name_th"]),
            "name_jp": " / ".join(st["name_ja"] or st["name_en"] for st in ms),
            "lines": sorted({lid for st in ms for lid in st["lines"]}, key=line_order.index),
            "x": ms[0]["x"],
            "y": ms[0]["y"],
        })
    areas.sort(key=lambda a: a["id"])
    validate_overrides(rent_overrides, {a["id"] for a in areas})
    area_of_station = np.full(len(stations), -1)
    for k, a in enumerate(areas):
        for j in a["members"]:
            area_of_station[j] = k
    for j, st in enumerate(stations):
        st["area"] = areas[area_of_station[j]]["id"] if area_of_station[j] >= 0 else None

    # Each grid point belongs to its nearest rated station's area when that
    # station is within walking range; the polygons below draw the same rule
    # (Voronoi cell ∩ AREA_RADIUS_M disc ∩ Bangkok).
    D_rated = D[:, rated]
    nearest_rated = np.array(rated)[D_rated.argmin(axis=1)]
    AREA = np.where(D_rated.min(axis=1) <= AREA_RADIUS_M, area_of_station[nearest_rated], -1)

    rated_pts = [Point(stations[j]["x"], stations[j]["y"]) for j in rated]
    vor = shapely.voronoi_polygons(shapely.MultiPoint(rated_pts), extend_to=province.envelope.buffer(10_000))
    vor_cells = list(vor.geoms)
    cell_of: dict[int, Polygon] = {}
    for j, pnt in zip(rated, rated_pts):
        cell_of[j] = next(c for c in vor_cells if c.contains(pnt))
    area_geoms = []
    for a in areas:
        parts = [
            cell_of[j].intersection(Point(stations[j]["x"], stations[j]["y"]).buffer(AREA_RADIUS_M, quad_segs=24))
            for j in a["members"]
        ]
        g = unary_union(parts).intersection(province)
        area_geoms.append(g if g.geom_type == "MultiPolygon" else MultiPolygon([g] if g.geom_type == "Polygon" else [
            p for p in getattr(g, "geoms", []) if p.geom_type == "Polygon"
        ]))
    area_simplified = simplify_coverage(area_geoms, tolerance=12, min_part_m2=5_000)

    return rated, areas, AREA, area_geoms, area_simplified


def aggregate_station_areas(areas, AREA, PX, PY, weight, pt, pt_crowd, OWN, districts,
                            editorial, stations, commute_at, commute_pt, rent_meta, rent_overrides,
                            area_geoms, parks, count_inside, sequences, default_weights):
    area_raw: dict[str, dict[str, float]] = {k: {} for k in RATING_KEYS}
    area_agg: dict[str, dict] = {}
    for k, a in enumerate(areas):
        m = AREA == k
        if m.sum() < 3:  # tiny catchment on the city edge: use every point within walking range
            m = np.hypot(PX - a["x"], PY - a["y"]) <= AREA_RADIUS_M
        w = weight[m]
        for key, arr in pt.items():
            area_raw[key][a["id"]] = float((arr[m] * w).sum() / w.sum())
        area_raw["crowd"][a["id"]] = float((pt_crowd[m] * w).sum() / w.sum())
        own = OWN[m]
        share: dict[str, float] = defaultdict(float)
        for i_d, w_i in zip(own.tolist(), w.tolist()):
            share[districts[i_d]["slug"]] += w_i
        total_w = sum(share.values())
        shares = sorted(((slug, v / total_w) for slug, v in share.items()), key=lambda x: -x[1])
        blend = lambda field: sum(editorial[slug][field] * sh for slug, sh in shares)  # noqa: E731
        members_xy = np.array([[stations[j]["x"], stations[j]["y"]] for j in a["members"]])
        from_station = commute_at(members_xy[:, 0], members_xy[:, 1])
        hub_minutes = {hub: int(round(float(v.min()))) for hub, v in from_station.items()}
        area_agg[a["id"]] = {
            "points": int(m.sum()),
            "districts": [{"slug": slug, "share": round(sh, 3)} for slug, sh in shares if sh >= 0.05],
            "rent_1br": int(round(blend("rent_1br") / 500) * 500),
            "rent_2br": int(round(blend("rent_2br") / 500) * 500),
            "safety": blend("safety"),
            "hub_minutes": hub_minutes,
            "min_transit": min(hub_minutes.values()),
            "resident_minutes": {
                hub: int(round(R.weighted_median(commute_pt[hub][m].tolist(), w.tolist()))) for hub in HUBS
            },
        }

    area_rents = {
        a["id"]: station_rent(a["id"], area_agg[a["id"]], rent_meta, rent_overrides)
        for a in areas
    }
    for aid, rent in area_rents.items():
        area_agg[aid].update({"rent_1br": rent["one_bed"], "rent_2br": rent["two_bed"]})

    area_ratings: dict[str, dict[str, int]] = defaultdict(dict)
    for key in ("food", "nightlife", "daily_essentials", "gym_sports", "vibe", "green", "transport"):
        for aid, v in R.percentile_normalize(area_raw[key]).items():
            area_ratings[aid][key] = v
    for aid, v in R.percentile_normalize(area_raw["crowd"], invert=True).items():
        area_ratings[aid]["crowd"] = v
    for a in areas:
        g = area_agg[a["id"]]
        area_ratings[a["id"]]["rent"] = R.rent_to_affordability(g["rent_1br"]) or 5
        area_ratings[a["id"]]["safety"] = int(round(g["safety"]))
        area_raw["rent"][a["id"]] = g["rent_1br"]
        area_raw["safety"][a["id"]] = round(g["safety"], 2)

    # Facts inside the area polygon (same sources as the district card).
    AREA_TWO_SOURCE = [  # (category, Overture key, OSM key, Overture min, OSM min) per ~1–2 km² area
        ("food", "food", "food", 80, 20),
        ("nightlife", "nightlife", "nightlife", 10, 4),
        ("daily_essentials", "essentials", "essentials", 40, 15),
        ("gym_sports", "sports", "sports", 6, 3),
        ("vibe", "culture", "culture", 6, 8),
    ]
    for k, a in enumerate(areas):
        g = area_geoms[k]
        area_km2 = g.area / 1e6
        park_ha = sum(p.intersection(g).area for p in parks if p.intersects(g)) / 10_000
        essential_cats = ("grocery", "pharmacy", "health", "bank", "laundry", "post")
        a["facts"] = {
            "area_km2": round(area_km2, 2),
            "food": count_inside("ovt_food", g),
            "cafes": count_inside("ovt_cafe", g),
            "nightlife": count_inside("ovt_night", g),
            "convenience": count_inside("ovt_convenience", g),
            "markets": count_inside("ovt_market", g) + count_inside("market", g),
            "essentials": sum(count_inside(f"ovt_{c}", g) for c in essential_cats),
            "sports": count_inside("ovt_sports", g),
            "culture": count_inside("ovt_venue", g),
            "temples": count_inside("ovt_temple", g),
            "park_ha": round(park_ha, 1),
            "piers": count_inside("pier", g),
        }
        a["osm_counts"] = {
            "food": count_inside("food", g),
            "nightlife": count_inside("night", g) + count_inside("karaoke", g),
            "essentials": sum(count_inside(c, g) for c in essential_cats) + count_inside("convenience", g),
            "sports": count_inside("sports", g),
            "culture": count_inside("venue", g) + count_inside("attraction", g) + count_inside("temple", g),
        }
        conf: dict[str, str] = {}
        srcs: dict[str, list[str]] = {}
        for cat, fkey, okey, ovt_min, osm_min in AREA_TWO_SOURCE:
            conf[cat], srcs[cat] = R.two_source_confidence(a["facts"][fkey] >= ovt_min, a["osm_counts"][okey] >= osm_min)
        conf.update({"transport": "moderate", "rent": "editorial", "safety": "editorial",
                     "green": "moderate", "crowd": "moderate"})
        srcs.update({"transport": ["osm_rail", "transit_model"], "rent": ["listing_research"],
                     "safety": ["ai_research"], "green": ["osm"], "crowd": ["overture"]})
        conf["rent"] = area_rents[a["id"]]["confidence"]
        srcs["rent"] = [area_rents[a["id"]]["source"]]
        a["confidence"], a["sources"] = conf, srcs

    # Neighbouring areas = the next stop(s) along each line.
    area_neighbors: dict[str, set[str]] = defaultdict(set)
    for lid, seq in sequences.items():
        ids = [st.get("area") for st in seq]
        for x_id, y_id in zip(ids, ids[1:]):
            if x_id and y_id and x_id != y_id:
                area_neighbors[x_id].add(y_id)
                area_neighbors[y_id].add(x_id)

    station_medians = {k: R.median_int([area_ratings[a["id"]][k] for a in areas]) for k in RATING_KEYS}
    station_anchors = R.anchors([R.composite(area_ratings[a["id"]], default_weights) for a in areas])

    return area_raw, area_agg, area_rents, area_ratings, area_neighbors, station_medians, station_anchors
