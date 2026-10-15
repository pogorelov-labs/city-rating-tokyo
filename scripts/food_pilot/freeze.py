"""Replay pinned Stage 0 tiles and report sample feasibility, before target reads."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path

if __package__:
    from .stage0 import census, freeze_sample, tile_plan
else:
    from stage0 import census, freeze_sample, tile_plan

ROOT = Path(__file__).resolve().parents[2]


def load_census(stations_raw, raw_dir):
    stations = json.loads(stations_raw)
    plan = json.loads((raw_dir / "query-plan.json").read_text())
    if plan["station_sha256"] != hashlib.sha256(stations_raw).hexdigest():
        raise ValueError("Station frame changed after query-plan freeze")
    expected = tile_plan(stations)
    if plan["tiles"] != expected["tiles"]:
        raise ValueError("Frozen tile/query contract differs from replay")
    ledger = json.loads((raw_dir / "attempts.json").read_text())
    if ledger["status"] != "complete" or sorted(ledger["tiles_completed"]) != sorted(t["id"] for t in plan["tiles"]):
        raise ValueError("Incomplete attempt ledger; do not infer zeros")
    tiles, hashes = [], {}
    for tile in plan["tiles"]:
        records = [a for a in ledger["attempts"] if a["tile"] == tile["id"] and a["status"] == "complete"]
        if len(records) != 1:
            raise ValueError("Ambiguous successful tile attempt")
        raw = gzip.decompress((raw_dir / f'tile-{tile["id"]}.json.gz').read_bytes())
        digest = hashlib.sha256(raw).hexdigest()
        if digest != records[0]["response_sha256"]:
            raise ValueError("Pinned tile hash mismatch")
        hashes[tile["id"]] = digest
        tiles.append({**tile, "response": json.loads(raw)})
    rows = census(stations, tiles, [t["id"] for t in plan["tiles"]], ledger["finished_at"])
    return rows, hashes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stations", type=Path, default=ROOT / "data/stations.json")
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--old-sample", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.is_relative_to(ROOT):
        parser.error("Internal census/manifest outputs must be outside the repository")
    stations_raw = args.stations.read_bytes()
    old_raw = args.old_sample.read_bytes()
    old = json.loads(old_raw)["stations"]
    if len(old) != 16 or len({s["slug"] for s in old}) != 16:
        raise ValueError("Expected 16 distinct diagnostic centers")
    rows, hashes = load_census(stations_raw, args.raw_dir)
    sample = freeze_sample(json.loads(stations_raw), rows, old)
    result = {"station_sha256": hashlib.sha256(stations_raw).hexdigest(),
              "old_sample_sha256": hashlib.sha256(old_raw).hexdigest(),
              "tile_sha256": hashes, "census": rows, "core_design": sample,
              "target_acquisition_authorized_by_this_file": False,
              "challenge_design": "not frozen; must precede target acquisition",
              "target_category_status_budget_contract": "not frozen; must precede target acquisition"}
    output.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(result, sort_keys=True, indent=2) + "\n").encode()
    with output.open("xb") as stream:
        stream.write(raw)
    print(json.dumps({"status": sample["status"], "sha256": hashlib.sha256(raw).hexdigest(),
                      "census_rows": len(rows), "zero_rows": sum(r["count"] == 0 for r in rows),
                      "cells": sample.get("cells", []), "reason": sample.get("reason")}), flush=True)


if __name__ == "__main__":
    main()
