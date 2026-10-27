"""Synthetic, offline coverage for the Bangkok spatial build stages."""
import gzip
import math
import sys
from pathlib import Path

import duckdb
import numpy as np
import pytest
from shapely.geometry import box

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bangkok import areas, gridpack, rail, sources  # noqa: E402
from bangkok.geom import assemble_multipolygon, xy  # noqa: E402
from bangkok.rasters import Raster, rasterize  # noqa: E402
from bangkok.signal_grid import SignalGrid  # noqa: E402
from bangkok.static_data import HUBS  # noqa: E402


def _ring(x, y, size, role="outer"):
    points = [(x, y), (x + size, y), (x + size, y + size),
              (x, y + size), (x, y)]
    return {"type": "way", "role": role,
            "geometry": [{"lon": lon, "lat": lat} for lon, lat in points]}


def test_five_polygon_boundary_preserves_inner_hole():
    members = [_ring(100.5 + index * 0.02, 13.7, 0.01) for index in range(5)]
    members.append(_ring(100.502, 13.702, 0.002, "inner"))
    geometry = assemble_multipolygon(members)
    assert geometry is not None and geometry.is_valid
    assert len(geometry.geoms) == 5
    assert sum(len(p.interiors) for p in geometry.geoms) == 1
    assert assemble_multipolygon([_ring(100.5, 13.7, 0.01, "inner")]) is None


def test_raster_histogram_fft_and_polygon_centres():
    raster = Raster((0, 0, 4, 4), 1)
    xs = np.array([0.5, 1.5, 1.5, 3.5, 4.5])
    ys = np.array([0.5, 1.5, 1.5, 3.5, 1.5])
    hist = raster.hist(xs, ys)
    assert hist.shape == (4, 4)
    assert hist.sum() == 4 and hist[1, 1] == 2
    expected = np.zeros((4, 4))
    for row in range(4):
        for col in range(4):
            expected[row, col] = sum(
                hist[y, x] for y in range(4) for x in range(4)
                if (x - col) ** 2 + (y - row) ** 2 <= 1
            )
    np.testing.assert_array_equal(raster.within(hist, 1), expected)
    np.testing.assert_array_equal(raster.sample(hist, xs, ys), [1, 2, 2, 1, 0])
    mask = rasterize([box(0, 0, 2, 2)], raster)
    np.testing.assert_array_equal(mask[:2, :2], np.ones((2, 2)))
    assert mask.sum() == 4


def test_osm_poi_categories_and_provider_id_dedup(monkeypatch):
    cafe = {"type": "node", "id": 1, "lon": 100.6, "lat": 13.75,
            "tags": {"amenity": "cafe"}}
    private_gym = {"type": "node", "id": 2, "lon": 100.61, "lat": 13.75,
                   "tags": {"leisure": "fitness_centre", "access": "private"}}
    public_gym = {"type": "way", "id": 3, "center": {"lon": 100.62, "lat": 13.75},
                  "tags": {"leisure": "fitness_centre"}}
    payloads = {name: {"elements": []} for name in (
        "pois_food", "pois_nightlife", "pois_essentials", "pois_sports",
        "pois_culture", "pois_transit_other")}
    payloads["pois_food"]["elements"] = [cafe, cafe]
    payloads["pois_sports"]["elements"] = [private_gym, public_gym]
    monkeypatch.setattr(sources, "load", lambda name: payloads[name])
    result = sources.load_pois()
    assert len(result["food"][0]) == len(result["cafe"][0]) == 1
    assert len(result["sports"][0]) == 1
    assert result["sports"][0][0] == pytest.approx(xy(100.62, 13.75)[0])


def test_overture_taxonomy_mapping_from_synthetic_parquet(tmp_path, monkeypatch):
    path = tmp_path / "overture_places.parquet"
    db = duckdb.connect()
    db.execute("CREATE TABLE places (lon DOUBLE, lat DOUBLE, hierarchy VARCHAR[])")
    db.executemany("INSERT INTO places VALUES (?, ?, ?)", [
        (100.60, 13.75, ["food_and_drink", "non_alcoholic_beverage_venue"]),
        (100.61, 13.75, ["health_care", "clinic"]),
        (100.62, 13.75, ["food_and_drink", "nightlife_venue", "karaoke_bar"]),
        (100.63, 13.75, ["cultural_and_historic", "historic_site"]),
    ])
    db.execute("COPY places TO ? (FORMAT PARQUET)", [str(path)])
    db.close()
    monkeypatch.setattr(sources, "RAW", tmp_path)
    result = sources.load_overture()
    assert len(result["ovt_all"][0]) == 4
    assert len(result["ovt_food"][0]) == len(result["ovt_cafe"][0]) == 1
    assert len(result["ovt_health"][0]) == len(result["ovt_night"][0]) == 1
    assert len(result["ovt_karaoke"][0]) == 1
    assert "ovt_venue" not in result  # historic_site is deliberately excluded


def test_rail_uses_explicit_relations_and_dijkstra_on_three_stations(monkeypatch):
    spec = {"operator": "TEST", "speed_kmh": 30, "wait_min": 2, "dwell_min": 1}
    monkeypatch.setattr(rail, "LINES", {"toy": spec})
    monkeypatch.setattr(rail, "HUBS", {"center": "Central"})
    monkeypatch.setattr(rail, "CURATED_SEQUENCES", {})
    monkeypatch.setattr(rail, "load_station_candidates", lambda: [])
    coords = [(100.60, 13.75), (100.61, 13.75), (100.62, 13.75)]
    members = [{"type": "node", "role": "stop", "ref": index + 1,
                "lon": lon, "lat": lat} for index, (lon, lat) in enumerate(coords)]
    members += [{"type": "way", "role": "", "geometry": [
        {"lon": coords[index][0], "lat": coords[index][1]},
        {"lon": coords[index + 1][0], "lat": coords[index + 1][1]}]}
        for index in range(2)]
    route = {"id": 42, "members": members}
    payloads = {"rail_routes": {"elements": [route]}, "rail_stops": {"elements": [
        {"id": index + 1, "tags": {"name:en": name}}
        for index, name in enumerate(("West", "Central", "East"))]}}
    monkeypatch.setattr(rail, "load", lambda name: payloads[name])
    stations, sequences, tracks = rail.build_rail([{"slug": "toy", "geom": box(-10000, -10000, 10000, 10000)}], {"toy": [42]})
    assert [station["id"] for station in sequences["toy"]] == ["west", "central", "east"]
    assert len(stations) == 3 and "toy" in tracks
    assert rail.line_tracks([route], {"toy": [99]}) == {}
    times = rail.transit_model(stations, sequences)["center"]
    assert times["central"] == 0
    assert math.isfinite(times["west"]) and times["west"] > 0
    assert times["west"] == pytest.approx(times["east"], rel=1e-6)


def test_interchange_union_respects_shared_line_and_voronoi(monkeypatch):
    monkeypatch.setattr(areas, "LINES", {"a": {}, "b": {}})
    validated = []
    monkeypatch.setattr(areas, "validate_overrides", lambda _doc, ids: validated.append(ids))
    stations = [
        {"id": "one", "name_en": "One", "name_th": "", "name_ja": "One", "lines": ["a"], "x": 0, "y": 0, "district": "toy"},
        {"id": "two", "name_en": "Two", "name_th": "", "name_ja": "Two", "lines": ["b"], "x": 100, "y": 0, "district": "toy"},
        {"id": "three", "name_en": "Three", "name_th": "", "name_ja": "Three", "lines": ["a"], "x": 350, "y": 250, "district": "toy"},
    ]
    points = np.array([[0, 0], [100, 0], [350, 250], [1400, 1400]])
    distances = np.hypot(points[:, None, 0] - np.array([s["x"] for s in stations]),
                         points[:, None, 1] - np.array([s["y"] for s in stations]))
    rated, grouped, assignment, geoms, simplified = areas.build_station_areas(
        stations, distances, box(-1000, -1000, 1500, 1500), {})
    assert rated == [0, 1, 2] and len(grouped) == 2
    assert stations[0]["area"] == stations[1]["area"] != stations[2]["area"]
    assert assignment[-1] == -1 and len(geoms) == len(simplified) == 2
    assert all(g.is_valid and not g.is_empty for g in geoms)
    assert validated == [{a["id"] for a in grouped}]


def test_ten_cell_grid_packing_round_trip():
    gx, gy = np.arange(5) * 200, np.arange(3) * 200
    px, py = np.meshgrid(gx, gy)
    px, py = px.ravel()[:10], py.ravel()[:10]
    keys = ("food", "nightlife", "daily_essentials", "gym_sports", "vibe", "green", "transport", "crowd")
    ratings = {key: list(range(1, 11)) for key in keys}
    stations = [{"id": "z"}, {"id": "a"}]
    distances = np.tile([5.0, 7.0], (10, 1))
    kwargs = dict(gx=gx, gy=gy, PX=px, PY=py, OWN=np.array([0] * 5 + [1] * 5),
        encoded_weights=list(range(1, 11)), commute_pt={hub: np.arange(10) + 10 for hub in HUBS},
        stations=stations, D=distances, d_station=distances.min(axis=1),
        AREA=np.array([0] * 5 + [-1] * 5), grid_ratings=ratings,
        districts=[{"slug": "north"}, {"slug": "south"}], areas=[{"id": "area"}],
        grid_medians={}, grid_anchors={}, data_date="2026-10")
    nx, ny, packed, _name, header = gridpack.pack_grid(**kwargs)
    assert (nx, ny) == (5, 3) and packed == gridpack.pack_grid(**kwargs)[2]
    deltas = np.frombuffer(gzip.decompress(packed), dtype=np.uint8).reshape(len(header["fields"]), ny, nx)
    planes = np.cumsum(deltas.astype(np.int64), axis=2) % 256
    expected = np.vstack([np.zeros(5), np.array(ratings["food"]).reshape(2, 5)[::-1]])
    np.testing.assert_array_equal(planes[header["fields"].index("food")], expected)
    np.testing.assert_array_equal(planes[header["fields"].index("weight")], expected)


def test_signal_grid_blends_sources_and_uses_shared_rail_state():
    raster = Raster((0, 0, 4, 4), 1)
    hist = {"food": raster.hist(np.array([0.5]), np.array([0.5])),
            "ovt_food": raster.hist(np.array([0.5, 0.5]), np.array([0.5, 0.5]))}
    grid = SignalGrid(raster, hist, np.array([0.5]), np.array([0.5]),
        [{"id": "s", "x": 0, "y": 0}], {"hub": {"_xy": (0, 0), "s": 0}})
    assert grid.both("food", 0)[0] == pytest.approx(0.35 * math.log1p(1) + 0.65 * math.log1p(2))
    assert grid.commute_at(np.array([0.0]), np.array([0.0]))["hub"][0] == 0
