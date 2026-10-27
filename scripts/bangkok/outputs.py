"""Assemble the app's district, station and geometry documents."""
from __future__ import annotations
from datetime import date
import math
import bangkok.ratings as R
from bangkok.bkk_config import GRID_M, RATING_KEYS, ROOT
from bangkok.geom import latlng_pair, lonlat, polygon_to_latlng
from bangkok.rents import editorial_rent, rent_audit
from bangkok.static_data import LINES
from bangkok.population import population_metadata


def build_documents(frozen, districts, editorial, conf_and_sources, ratings, agg, rent_meta,
                    flood, flood_exposed, description_for, image_for, tracks, stations, areas,
                    area_agg, area_ratings, area_rents, area_neighbors, area_simplified):
    today = date.fromisoformat(frozen['build_date']) if frozen else date.today()
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
            "rent": editorial_rent(e, rent_meta),
            "transit_minutes": agg[slug]["hub_minutes"],
            "min_transit": agg[slug]["min_transit"],
            "station_ids": d["station_ids"],
            "nearby_station_ids": d["nearby_station_ids"],
            "line_ids": d["line_ids"],
            "neighbors": d["neighbors"],
            "aliases": e["aliases"],
            "facts": d["facts"],
            "flood": {**flood[slug], "exposed": flood_exposed(flood[slug])},
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
            "id": s["id"], "name_en": s["name_en"], "name_th": s["name_th"], "name_ja": s["name_ja"],
            "lat": latlng_pair(s["x"], s["y"])[0], "lng": latlng_pair(s["x"], s["y"])[1],
            "lines": s["lines"], "district": s["district"], "area": s["area"],
        } for s in stations],
        key=lambda s: s["id"],
    )

    out_areas = []
    for k, a in enumerate(areas):
        g = area_agg[a["id"]]
        primary = stations[a["members"][0]]
        wiki: dict[str, str] = {}
        for j in a["members"]:
            for lang, url in stations[j]["wikipedia"].items():
                wiki.setdefault(lang, url)
        lat, lng = latlng_pair(primary["x"], primary["y"])
        out_areas.append({
            "id": a["id"],
            "name_en": a["name_en"],
            "name_th": a["name_th"],
            "name_jp": a["name_jp"],
            "lat": lat,
            "lng": lng,
            "station_ids": [stations[j]["id"] for j in a["members"]],
            "line_ids": a["lines"],
            "district": primary["district"],
            "districts": g["districts"],
            "ratings": {key: area_ratings[a["id"]][key] for key in RATING_KEYS},
            "confidence": a["confidence"],
            "sources": a["sources"],
            "data_date": data_date,
            "rent": area_rents[a["id"]],
            "transit_minutes": g["hub_minutes"],
            "min_transit": g["min_transit"],
            "resident_minutes": g["resident_minutes"],
            "neighbors": sorted(area_neighbors[a["id"]]),
            "facts": a["facts"],
            "image": next((stations[j]["image"] for j in a["members"] if stations[j]["image"]), None),
            "wikipedia": wiki,
        })

    def bbox_latlng(geom) -> list[list[float]]:
        x0, y0, x1, y1 = geom.bounds
        return [latlng_pair(x0, y0), latlng_pair(x1, y1)]

    station_geometry = {
        a["id"]: {
            "polygons": [polygon_to_latlng(poly) for poly in area_simplified[k].geoms],
            "bbox": bbox_latlng(area_simplified[k]),
        }
        for k, a in enumerate(areas)
    }

    return today, data_date, out_districts, geometry, rail_lines, rail_stations, out_areas, station_geometry


def pearson(a: list[float], b: list[float]) -> float:
    ma, mb = sum(a) / len(a), sum(b) / len(b)
    cov = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    va = math.sqrt(sum((x - ma) ** 2 for x in a))
    vb = math.sqrt(sum((y - mb) ** 2 for y in b))
    return cov / (va * vb) if va and vb else float("nan")

def build_metadata_and_signals(TWO_SOURCE, districts, rail_stations, medians, anchors,
                               areas, station_medians, station_anchors, PX, grid_medians,
                               grid_anchors, rent_overrides, data_date, out_districts, out_areas,
                               today, raw, population, count_inside, ratings, agg, area_raw,
                               area_ratings, area_agg):
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
        "station_area_count": len(areas),
        "station_medians": station_medians,
        "station_default_anchors": station_anchors,
        "grid_cell_count": int(len(PX)),
        "grid_medians": grid_medians,
        "grid_default_anchors": grid_anchors,
        "rent_scale": {"floor": R.RENT_FLOOR_THB, "ceiling": R.RENT_CEILING_THB},
        "rent_audit": rent_audit(rent_overrides),
        "data_date": data_date,
    }

    # Facts are shared with the audit signals below. Validate retained source
    # observations and joins before writing any generated outputs.
    from bangkok.enrichments import apply_enrichments
    apply_enrichments(ROOT, out_districts, out_areas)

    signals = {
        "_meta": {
            "generated": today.isoformat(),
            "grid_m": GRID_M,
            "population": population_metadata(),
            "note": "Raw per-district signals (resident-weighted means of per-point values) before percentile normalisation. See scripts/bangkok/build.py.",
        },
        "districts": {
            d["slug"]: {
                "raw": {k: round(raw[k][d["slug"]], 4) for k in RATING_KEYS},
                "crowd_input": {
                    "population": population[d["slug"]]["population"],
                    "official_area_km2": d["facts"]["area_km2"],
                    "poi_log_term": 0.5 * math.log1p(count_inside("ovt_all", d["geom"]) / d["facts"]["area_km2"]),
                },
                "ratings": {k: ratings[d["slug"]][k] for k in RATING_KEYS},
                **agg[d["slug"]],
                "facts": d["facts"],
                "osm_counts": d["osm_counts"],
                "stations": d["station_ids"],
                "lines": d["line_ids"],
            }
            for d in districts
        },
        "station_areas": {
            a["id"]: {
                "raw": {k: round(area_raw[k][a["id"]], 4) for k in RATING_KEYS},
                "ratings": area_ratings[a["id"]],
                **area_agg[a["id"]],
                "facts": a["facts"],
                "osm_counts": a["osm_counts"],
            }
            for a in areas
        },
    }

    return source_agreement, meta, signals
