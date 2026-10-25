"""Offline acquisition contracts. No osmium, shapely, PBF or network needed."""
import importlib.util
import io
import sys
from copy import deepcopy
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from osm_filters import GREEN_FILTERS, POI_FILTERS, STATION_FILTERS, matches, query_body  # noqa: E402

spec = importlib.util.spec_from_file_location("fetch_geofabrik", HERE / "fetch-geofabrik.py")
G = importlib.util.module_from_spec(spec)
spec.loader.exec_module(G)


@pytest.mark.parametrize("task,kind,tags,expected", [
    ("pois_food", "node", {"amenity": "restaurant"}, True),
    ("pois_food", "relation", {"shop": "pastry"}, True),
    ("pois_food", "way", {"amenity": "restaurant;cafe"}, False),
    ("pois_food", "node", {"amenity": "Restaurant"}, False),
    ("pois_food", "node", {"amenity": "bar"}, False),
    ("pois_nightlife", "way", {"amenity": "karaoke_box"}, True),
    ("pois_nightlife", "node", {"tourism": "hostel"}, True),
    ("pois_nightlife", "node", {"tourism": "hotel"}, False),
    ("pois_essentials", "relation", {"amenity": "kindergarten"}, True),
    ("pois_essentials", "way", {"shop": "dry_cleaning"}, True),
    ("pois_essentials", "node", {"shop": "clothes"}, False),
    ("pois_sports", "way", {"leisure": "swimming_pool", "access": "private"}, True),
    ("pois_sports", "node", {"leisure": "fitness_station"}, True),
    ("pois_sports", "node", {"sport": "fitness"}, False),
    ("pois_culture", "relation", {"historic": ""}, True),
    ("pois_culture", "node", {"historic": "no"}, True),
    ("pois_culture", "way", {"highway": "pedestrian"}, True),
    ("pois_culture", "node", {"highway": "pedestrian"}, False),
    ("pois_culture", "relation", {"highway": "pedestrian"}, False),
    ("pois_culture", "node", {"shop": "musical_instrument"}, True),
    ("pois_culture", "node", {}, False),
    ("pois_transit_other", "relation", {"amenity": "ferry_terminal"}, True),
    ("pois_transit_other", "node", {"highway": "bus_stop"}, True),
    ("pois_transit_other", "way", {"highway": "bus_stop"}, False),
])
def test_tag_filters(task, kind, tags, expected):
    assert matches(kind, tags, POI_FILTERS[task]) is expected


def test_green_and_station_filters():
    assert matches("relation", {"natural": "wood"}, GREEN_FILTERS)
    assert matches("node", {"leisure": "garden", "access": "no"}, GREEN_FILTERS)
    assert not matches("way", {"landuse": "grass"}, GREEN_FILTERS)
    assert matches("way", {"railway": "station"}, STATION_FILTERS)
    assert matches("node", {"public_transport": "station"}, STATION_FILTERS)
    assert not matches("relation", {"railway": "station"}, STATION_FILTERS)
    assert not matches("node", {"railway": "halt"}, STATION_FILTERS)


def test_overpass_rendering_retains_exact_and_existence_selectors():
    assert query_body(POI_FILTERS["pois_food"]) == (
        'nwr["amenity"~"^(restaurant|cafe|fast_food|food_court|ice_cream)$"];'
        'nwr["shop"~"^(bakery|coffee|pastry)$"];'
    )
    assert query_body(POI_FILTERS["pois_culture"]).endswith('nwr["historic"];way["highway"="pedestrian"];')
    assert query_body(STATION_FILTERS) == (
        'node["railway"="station"];node["public_transport"="station"];'
        'way["railway"="station"];way["public_transport"="station"];'
    )


def test_bbox_midpoint_is_not_vertex_average_or_clipped_center():
    points = [{"lat": 10, "lon": 100}, {"lat": 10, "lon": 100}, {"lat": 16, "lon": 108}]
    assert G.center(points) == {"lat": 13, "lon": 104}
    with pytest.raises(ValueError, match="without coordinates"):
        G.center([])
    # Select ways by any vertex in the bbox, then center the full geometry.
    way = {"type": "way", "id": 1, "tags": {"amenity": "cafe"}, "geometry": [
        {"lat": 13.5, "lon": 100.5}, {"lat": 15, "lon": 102},
    ]}
    assert any(G.in_bbox(p) for p in way["geometry"])
    assert G.point_element(way)["center"] == {"lat": 14.25, "lon": 101.25}
    assert not G.in_bbox(G.point_element(way)["center"])
    assert G.in_bbox({"lat": 13.47, "lon": 100.30})
    assert not G.in_bbox({"lat": 13.46, "lon": 100.30})


def test_members_keep_full_geometry_order_roles_and_direct_node_coordinates():
    members = [
        {"type": "node", "ref": 1, "role": "stop"},
        {"type": "way", "ref": 2, "role": "outer"},
        {"type": "way", "ref": 3, "role": "inner"},
        {"type": "way", "ref": 2, "role": "backward"},
        {"type": "relation", "ref": 4, "role": "subarea"},
    ]
    before = deepcopy(members)
    nodes = {1: {"lat": 13.6, "lon": 100.6, "tags": {"name:en": "Station"}}}
    ways = {
        2: [{"lat": 13.5, "lon": 100.5}, {"lat": 14.5, "lon": 101.5}],
        3: [{"lat": 13.6, "lon": 100.6}, {"lat": 13.7, "lon": 100.7}],
    }
    mapped = G.member_geometry(members, nodes, ways)
    assert members == before
    assert mapped[0] == {**members[0], "lat": 13.6, "lon": 100.6}
    assert mapped[1] == {**members[1], "geometry": ways[2]}
    assert mapped[2] == {**members[2], "geometry": ways[3]}
    assert mapped[3] == {**members[3], "geometry": ways[2]}
    assert mapped[4] == members[4]
    relation = {"type": "relation", "id": 10, "tags": {"shop": "bakery"}, "members": mapped}
    assert G.point_element(relation) == {
        "type": "relation", "id": 10, "tags": {"shop": "bakery"}, "center": {"lat": 14, "lon": 101},
    }
    outputs = {name: [] for name in G.OSM_FILTERS}
    G.append_filtered(outputs, relation)
    G.append_filtered(outputs, {**relation, "tags": {"leisure": "park"}})
    assert outputs["pois_food"][0] == G.point_element(relation)
    assert outputs["green"][0]["members"] == mapped
    node = {"type": "node", "id": 1, "tags": {}, "lat": 13.6, "lon": 100.6}
    assert G.point_element(node) == node


@pytest.mark.parametrize("members,nodes,ways", [
    ([{"type": "node", "ref": 1, "role": "stop"}], {}, {}),
    ([{"type": "way", "ref": 2, "role": "outer"}], {}, {}),
    ([{"type": "way", "ref": 2, "role": "outer"}], {}, {2: []}),
])
def test_missing_member_geometry_fails(members, nodes, ways):
    with pytest.raises(ValueError, match="Missing"):
        G.member_geometry(members, nodes, ways)


def test_local_pbf_manifest_is_verified(tmp_path):
    pbf = tmp_path / "synthetic.osm.pbf"
    pbf.write_bytes(b"synthetic fixture, not a real PBF")
    meta = G.provenance(pbf)
    assert meta["bytes"] == pbf.stat().st_size
    assert meta["license"] == "ODbL-1.0"
    G.atomic_json(pbf.with_suffix(".pbf.source.json"), meta)
    assert G.provenance(pbf) == meta
    pbf.write_bytes(b"modified")
    with pytest.raises(ValueError, match="differs"):
        G.provenance(pbf)


def test_cached_download_requires_source_manifest_and_matching_url(tmp_path):
    pbf = tmp_path / "cached.osm.pbf"
    pbf.write_bytes(b"cached fixture")
    with pytest.raises(ValueError, match="no source manifest"):
        G.download(pbf, G.URL)
    meta = {**G.provenance(pbf), "requested_url": G.URL}
    G.atomic_json(pbf.with_suffix(".pbf.source.json"), meta)
    assert G.download(pbf, G.URL) == meta
    with pytest.raises(ValueError, match="different URL"):
        G.download(pbf, "https://download.geofabrik.de/asia/thailand-261024.osm.pbf")


@pytest.mark.parametrize("declared_size", [7, 100])
def test_download_records_redirect_and_preserves_cache_on_short_read(tmp_path, monkeypatch, declared_size):
    response = io.BytesIO(b"new PBF")
    response.url = "https://download.geofabrik.de/asia/thailand-261024.osm.pbf"
    response.headers = {"Content-Length": str(declared_size), "Last-Modified": "Sat, 24 Oct 2026 23:00:29 GMT"}
    monkeypatch.setattr(G.urllib.request, "urlopen", lambda *args, **kwargs: response)
    pbf = tmp_path / "download.osm.pbf"
    pbf.write_bytes(b"old cache")
    if declared_size == 7:
        meta = G.download(pbf, G.URL, refresh=True)
        assert pbf.read_bytes() == b"new PBF"
        assert meta["requested_url"] == G.URL
        assert meta["resolved_url"].endswith("thailand-261024.osm.pbf")
        assert meta["last_modified"] == response.headers["Last-Modified"]
        assert meta["bytes"] == 7 and meta["sha256"] == G.sha256(pbf)
        assert G.provenance(pbf) == meta
    else:
        with pytest.raises(ValueError, match="Short PBF download"):
            G.download(pbf, G.URL, refresh=True)
        assert pbf.read_bytes() == b"old cache"
    assert not pbf.with_name(pbf.name + ".part").exists()
