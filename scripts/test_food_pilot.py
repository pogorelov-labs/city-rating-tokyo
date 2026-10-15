"""Synthetic integrity regressions; never call a live provider."""
from copy import deepcopy
import gzip
import hashlib
import json
import io
import sys

import pytest

from food_pilot.stage0 import census, distance, freeze_sample, tile_plan, validate_osm
from food_pilot.freeze import load_census
from food_pilot import acquire_osm

NOW = "2026-10-15T15:00:00Z"
STATION = {"slug": "synthetic", "lat": 35.7, "lng": 139.7, "prefecture": "13"}


def payload(elements=None):
    return {"osm3s": {"timestamp_osm_base": NOW}, "elements": elements or []}


def node(identity=1, **kwargs):
    return {"type": "node", "id": identity, "lat": 35.7, "lon": 139.7,
            "tags": {"amenity": "restaurant"}, **kwargs}


def tiles(stations=None):
    return [{**t, "response": payload()} for t in tile_plan(stations or [STATION])["tiles"]]


def run_census(ts):
    return census([STATION], ts, [t["id"] for t in tile_plan([STATION])["tiles"]], NOW)


def test_coverage_plan_outward_padding_and_shared_boundaries():
    p = tile_plan([STATION])
    s, w, n, e = p["bbox"]
    assert distance(STATION, {"lat": s, "lng": STATION["lng"]}) >= 800
    assert distance(STATION, {"lat": STATION["lat"], "lng": w}) >= 800
    assert len(p["tiles"]) == 8
    assert sum((t["bbox"][2] - t["bbox"][0]) * (t["bbox"][3] - t["bbox"][1])
               for t in p["tiles"]) == pytest.approx((n - s) * (e - w))
    assert p["tiles"][0]["bbox"][3] == p["tiles"][1]["bbox"][1]
    assert p["tiles"][0]["bbox"][2] == p["tiles"][4]["bbox"][0]


def test_complete_empty_is_zero_but_missing_tile_is_not():
    ts = tiles()
    assert run_census(ts)[0]["status"] == "complete_zero"
    with pytest.raises(ValueError, match="tile set"):
        run_census(ts[:-1])


def test_query_or_bbox_tampering_cannot_establish_coverage():
    for key, bad in [("query_sha256", "unknown"), ("bbox", [0, 0, 1, 1])]:
        ts = tiles(); ts[0][key] = bad
        with pytest.raises(ValueError, match="geometry/query"):
            run_census(ts)


@pytest.mark.parametrize("doc", [{"elements": []}, {"osm3s": {"timestamp_osm_base": NOW}},
    {**payload(), "remark": "runtime error: out of memory"}, {**payload(), "elements": None}])
def test_incomplete_response_never_zero_filled(doc):
    with pytest.raises((ValueError, TypeError)):
        validate_osm(doc)


@pytest.mark.parametrize("coordinates", [{"lat": None}, {"lat": float("nan")},
                                        {"lon": 181}, {"lat": True}])
def test_invalid_coordinates_block_zero_inference(coordinates):
    with pytest.raises(ValueError, match="coordinates"):
        validate_osm(payload([node(**coordinates)]))


def test_boundary_tile_provider_duplicates_count_once_but_types_distinct():
    ts = tiles()
    ts[0]["response"] = payload([node()])
    ts[1]["response"] = payload([node()])
    assert run_census(ts)[0]["count"] == 1
    ts[2]["response"] = payload([{"type": "way", "id": 1,
        "center": {"lat": 35.7, "lon": 139.7}, "tags": {"amenity": "restaurant"}}])
    assert run_census(ts)[0]["count"] == 2  # physical duplicates are explicitly unverified


def test_conflicting_duplicates_and_stale_sources_rejected():
    ts = tiles(); ts[0]["response"] = payload([node()]); ts[1]["response"] = payload([node(lat=35.701)])
    with pytest.raises(ValueError, match="Conflicting"):
        run_census(ts)
    ts = tiles(); ts[0]["response"]["osm3s"]["timestamp_osm_base"] = "2026-04-03T00:00:00Z"
    with pytest.raises(ValueError, match="seven-day"):
        run_census(ts)


def synthetic_frame():
    stations, rows = [], []
    for pref_index, prefecture in enumerate(["13", "14", "11", "12"]):
        for count in range(4):
            for i in range(4):
                slug = f"synthetic-{prefecture}-{count}-{i}"
                stations.append({"slug": slug, "lat": 34.5 + pref_index * .5 + count * .06,
                                 "lng": 139 + i * .06, "prefecture": prefecture})
                rows.append({"slug": slug, "count": count, "radius_m": 800,
                             "status": "complete_positive" if count else "complete_zero"})
    return stations, rows


def test_freeze_reproducible_and_disjoint_with_32_32_split():
    stations, rows = synthetic_frame()
    result = freeze_sample(stations, rows, [])
    assert result["status"] == "frozen"
    assert result == freeze_sample(list(reversed(stations)), list(reversed(rows)), [])
    assert sum(s["split"] == "holdout" for s in result["stations"]) == 32
    assert sum(s["split"] == "development" for s in result["stations"]) == 32
    for i, a in enumerate(result["stations"]):
        assert all(distance(a, b) > 1600 for b in result["stations"][i + 1:])


def test_missing_cell_and_old_center_do_not_relax_design():
    stations, rows = synthetic_frame()
    rows[0]["status"] = "missing"
    assert freeze_sample(stations, rows, [])["status"] == "insufficient"
    stations, rows = synthetic_frame()
    assert freeze_sample(stations, rows, [stations[0]])["status"] == "insufficient"


def test_tied_positive_counts_cannot_manufacture_tertiles():
    stations, rows = synthetic_frame()
    for row in rows:
        if row["count"]:
            row["count"] = 1
    assert freeze_sample(stations, rows, [])["reason"] == "ties prevent three positive strata"


def test_inconsistent_zero_and_radius_fail_closed():
    stations, rows = synthetic_frame()
    bad = deepcopy(rows); bad[0]["count"] = 1
    with pytest.raises(ValueError, match="zero status"):
        freeze_sample(stations, bad, [])
    bad = deepcopy(rows); bad[0]["radius_m"] = 1000
    with pytest.raises(ValueError, match="radius"):
        freeze_sample(stations, bad, [])


def test_replay_checks_raw_hash_ledger_and_station_frame(tmp_path):
    stations_raw = json.dumps([STATION]).encode()
    plan = tile_plan([STATION]); plan["station_sha256"] = hashlib.sha256(stations_raw).hexdigest()
    (tmp_path / "query-plan.json").write_text(json.dumps(plan))
    raw = json.dumps(payload()).encode()
    ledger = {"status": "complete", "finished_at": NOW,
              "tiles_completed": [t["id"] for t in plan["tiles"]],
              "attempts": [{"tile": t["id"], "status": "complete",
                            "response_sha256": hashlib.sha256(raw).hexdigest()} for t in plan["tiles"]]}
    (tmp_path / "attempts.json").write_text(json.dumps(ledger))
    for t in plan["tiles"]:
        (tmp_path / f'tile-{t["id"]}.json.gz').write_bytes(gzip.compress(raw))
    assert load_census(stations_raw, tmp_path)[0][0]["count"] == 0
    with pytest.raises(ValueError, match="Station frame"):
        load_census(stations_raw + b" ", tmp_path)
    first = tmp_path / f'tile-{plan["tiles"][0]["id"]}.json.gz'
    first.write_bytes(gzip.compress(json.dumps(payload([node()])).encode()))
    with pytest.raises(ValueError, match="hash mismatch"):
        load_census(stations_raw, tmp_path)
    ledger["status"] = "in_progress"
    (tmp_path / "attempts.json").write_text(json.dumps(ledger))
    with pytest.raises(ValueError, match="Incomplete"):
        load_census(stations_raw, tmp_path)


@pytest.mark.parametrize("response", [
    {**payload(), "remark": "runtime error: timeout"},
    {"osm3s": {"timestamp_osm_base": "2020-01-01T00:00:00Z"}, "elements": []},
])
def test_adapter_rejects_http200_partial_or_stale_and_preserves_budget(tmp_path, monkeypatch, response):
    frame = tmp_path / "stations.json"; frame.write_text(json.dumps([STATION]))
    output = tmp_path / "internal"
    argv = ["acquire_osm.py", "--stations", str(frame), "--output", str(output)]
    monkeypatch.setattr(sys, "argv", argv + ["--plan-only"])
    monkeypatch.setitem(acquire_osm.LIMITS, "attempts", 2)
    acquire_osm.main()
    monkeypatch.setattr(sys, "argv", argv + ["--acquire"])
    monkeypatch.setattr(acquire_osm.urllib.request, "urlopen", lambda *a, **k: io.BytesIO(json.dumps(response).encode()))
    monkeypatch.setattr(acquire_osm.time, "sleep", lambda _: None)
    with pytest.raises(SystemExit, match="incomplete"):
        acquire_osm.main()
    ledger = json.loads((output / "attempts.json").read_text())
    assert ledger["status"] == "incomplete"
    assert len(ledger["attempts"]) == 2
    assert ledger["tiles_completed"] == []
    assert not list(output.glob("tile-*.json.gz"))
    with pytest.raises(ValueError, match="no silent budget reset"):
        acquire_osm.main()
    monkeypatch.setattr(sys, "argv", argv + ["--acquire", "--resume"])
    with pytest.raises(ValueError, match="budget exhausted"):
        acquire_osm.main()
