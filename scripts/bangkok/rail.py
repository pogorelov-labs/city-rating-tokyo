"""Bangkok rail topology and station-to-hub travel model."""
from __future__ import annotations
import heapq
import math
import sys
from collections import defaultdict
import numpy as np
from shapely.geometry import LineString, MultiLineString, Point
from shapely.ops import linemerge, unary_union
from bangkok.bkk_config import RAIL_DETOUR, TRANSFER_WALK_MAX_M, WALK_DETOUR, WALK_M_PER_MIN
from bangkok.geom import xy
from bangkok.sources import load, load_station_candidates, norm_name, slugify
from bangkok.static_data import CURATED_SEQUENCES, HUBS, LINES, STATION_NAME_ALIASES, STATION_TH_FALLBACK

def feeder_m_per_min(d: np.ndarray) -> np.ndarray:
    """Feeder speed to a station: ~15 km/h in soi traffic, up to ~25 km/h on
    the longer arterial runs of the outer districts."""
    return (15.0 + 10.0 * np.minimum(1.0, d / 15_000)) * 1000 / 60

def road_m_per_min(d: np.ndarray) -> np.ndarray:
    """Door-to-door road speed at peak: ~16 km/h for short inner trips rising to
    ~30 km/h for 25 km+ trips that can use the expressway / motorway network."""
    return (16.0 + 14.0 * np.minimum(1.0, d / 25_000)) * 1000 / 60

def line_tracks(routes: list[dict], rail_relations: dict[str, list[int]]) -> dict[str, MultiLineString]:
    by_line: dict[str, list[LineString]] = defaultdict(list)
    rel_to_line = {rid: lid for lid, spec in LINES.items() for rid in rail_relations[lid]}
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

def build_rail(districts: list[dict], rail_relations: dict[str, list[int]]):
    """Stations (merged interchanges), per-line ordered stop lists, track paths."""
    routes = load("rail_routes")["elements"]
    stop_tags = {e["id"]: e.get("tags", {}) for e in load("rail_stops")["elements"]}
    cands = load_station_candidates()
    tracks = line_tracks(routes, rail_relations)

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
    for lid, rel_ids in rail_relations.items():
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
