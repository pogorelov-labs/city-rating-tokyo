"""Bounded GET-equivalent Overpass census; outputs are internal research artifacts.

Run --plan-only first, inspect the immutable plan, then --acquire using the same
output directory. No production imports, database clients, or credential access.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import tempfile
import signal
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

if __package__:
    from .stage0 import tile_plan, validate_osm
else:
    from stage0 import tile_plan, validate_osm

ROOT = Path(__file__).resolve().parents[2]
ENDPOINTS = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
)
LIMITS = {"attempts": 24, "response_bytes": 16 * 1024**2,
          "wire_bytes": 128 * 1024**2, "retained_bytes": 256 * 1024**2,
          "wall_seconds": 900, "socket_seconds": 110}


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()


def write_new(path, value):
    with path.open("xb") as stream:
        stream.write(encoded(value))


def save_ledger(path, ledger):
    """Commit a complete receipt durably before any external request begins."""
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".ledger-", delete=False) as stream:
        temporary = Path(stream.name)
        stream.write(encoded(ledger))
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    directory = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def settle_interrupted(ledger, output):
    """Never refund an interrupted request whose consumed bytes are unknown."""
    for attempt in ledger["attempts"]:
        if attempt.get("status") not in (None, "pending", "interrupted") or attempt.get("reconciled"):
            continue
        if "reserved_bytes" not in attempt:
            # Legacy Ctrl-C receipts had no status/reservation. Additional full
            # charging may overcount, but cannot silently restore their budget.
            attempt["reserved_bytes"] = LIMITS["response_bytes"]
            ledger["wire_bytes"] += attempt["reserved_bytes"]
        attempt.update(status="interrupted", accounting="conservative_reservation")
        path = output / f"tile-{attempt['tile']}.json.gz"
        if attempt["tile"] in ledger["tiles_completed"]:
            ledger["tiles_completed"].remove(attempt["tile"])
        if path.exists():
            retained = f"tile-{attempt['tile']}-interrupted-{ledger['attempts'].index(attempt)}.json.gz"
            path.rename(output / retained)
            attempt["retained_artifact"] = retained
        attempt["reconciled"] = True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stations", type=Path, default=ROOT / "data/stations.json")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--plan-only", action="store_true")
    parser.add_argument("--acquire", action="store_true")
    parser.add_argument("--resume", action="store_true", help="Continue the original ledger/deadline without resetting its budget")
    args = parser.parse_args()
    if args.plan_only == args.acquire:
        parser.error("Choose exactly one of --plan-only or --acquire")
    if args.resume and not args.acquire:
        parser.error("--resume requires --acquire")
    output = args.output.resolve()
    if output.is_relative_to(ROOT):
        parser.error("Research snapshots must be outside the repository")
    output.mkdir(parents=True, exist_ok=True)
    station_raw = args.stations.read_bytes()
    stations = json.loads(station_raw)
    plan = {**tile_plan(stations), "station_sha256": hashlib.sha256(station_raw).hexdigest(),
            "limits": LIMITS, "endpoints": list(ENDPOINTS),
            "coordinate_contract": "node coordinates; way bounding-box center; inclusive haversine<=800m; provider type/id dedup; no physical-venue dedup claim"}
    plan_path = output / "query-plan.json"
    if args.plan_only:
        write_new(plan_path, plan)
        print(json.dumps({"status": "planned", "plan_sha256": hashlib.sha256(encoded(plan)).hexdigest(),
                          "bbox": plan["bbox"], "covered_catchments": plan["covered_catchments"],
                          "tile_query_hashes": [t["query_sha256"] for t in plan["tiles"]]}), flush=True)
        return
    if plan_path.read_bytes() != encoded(plan):
        raise ValueError("Plan changed; do not acquire against a different frame/contract")
    ledger_path = output / "attempts.json"
    if ledger_path.exists() and not args.resume:
        raise ValueError("Attempt ledger already exists; no silent budget reset")
    if args.resume:
        ledger = json.loads(ledger_path.read_text())
        resume_clock = time.monotonic()
        elapsed = (datetime.now(timezone.utc) - datetime.fromisoformat(ledger["started_at"])).total_seconds()
        started = resume_clock - elapsed
        if elapsed >= LIMITS["wall_seconds"] or len(ledger["attempts"]) >= LIMITS["attempts"]:
            raise ValueError("Original acquisition budget exhausted; resume cannot reset it")
        write_new(output / f'attempts-before-resume-{len(ledger["attempts"])}.json', ledger)
        settle_interrupted(ledger, output)
        save_ledger(ledger_path, ledger)
        # Preserve rejected bytes and the original ledger; re-query only the same tile.
        for tile_id in list(ledger["tiles_completed"]):
            successful = [a for a in ledger["attempts"] if a["tile"] == tile_id and a["status"] == "complete"]
            if len(successful) != 1:
                raise ValueError("Ambiguous tile receipt")
            path = output / f"tile-{tile_id}.json.gz"
            raw = gzip.decompress(path.read_bytes())
            if hashlib.sha256(raw).hexdigest() != successful[0]["response_sha256"]:
                raise ValueError("Existing tile hash mismatch")
            stamp, _ = validate_osm(json.loads(raw))
            if not 0 <= (datetime.now(timezone.utc) - stamp).total_seconds() <= 7 * 86400:
                rejected = f"tile-{tile_id}-rejected-{len(ledger['attempts'])}.json.gz"
                path.rename(output / rejected)
                successful[0].update(status="rejected_stale", transport_status="complete", retained_artifact=rejected)
                ledger["tiles_completed"].remove(tile_id)
        ledger["status"] = "in_progress"
        save_ledger(ledger_path, ledger)
    else:
        started = time.monotonic()
        ledger = {"started_at": datetime.now(timezone.utc).isoformat(), "attempts": [],
                  "wire_bytes": 0, "tiles_completed": [], "status": "in_progress"}
        save_ledger(ledger_path, ledger)
    def remaining_budget():
        remaining = LIMITS["wall_seconds"] - (time.monotonic() - started)
        if remaining <= 0:
            raise TimeoutError("Original acquisition wall deadline")
        return remaining

    def deadline(_signum, _frame):
        raise TimeoutError("Acquisition wall deadline")
    previous_handler = signal.signal(signal.SIGALRM, deadline)
    try:
        remaining_time = LIMITS["wall_seconds"] - (time.monotonic() - started)
        if remaining_time <= 0:
            raise ValueError("Original wall budget exhausted during recovery")
        signal.setitimer(signal.ITIMER_REAL, remaining_time)
        for tile in plan["tiles"]:
            if tile["id"] in ledger["tiles_completed"]:
                continue
            for endpoint in ENDPOINTS:
                remaining_time = LIMITS["wall_seconds"] - (time.monotonic() - started)
                if len(ledger["attempts"]) >= LIMITS["attempts"] or remaining_time <= 0:
                    raise ValueError("Request/wall budget exhausted")
                remaining = min(LIMITS["response_bytes"], LIMITS["wire_bytes"] - ledger["wire_bytes"])
                if remaining <= 0:
                    raise ValueError("Wire-byte budget exhausted")
                attempt = {"tile": tile["id"], "endpoint": endpoint,
                           "at": datetime.now(timezone.utc).isoformat(),
                           "status": "pending", "reserved_bytes": remaining,
                           "accounting": "conservative_reservation"}
                ledger["attempts"].append(attempt)
                # Charge the maximum before I/O. A killed process leaves this
                # pending receipt and its entire reservation on disk.
                ledger["wire_bytes"] += remaining
                save_ledger(ledger_path, ledger)
                received = 0
                eof = False
                raw = b""
                try:
                    req = urllib.request.Request(endpoint,
                        data=urllib.parse.urlencode({"data": tile["query"]}).encode(),
                        headers={"User-Agent": "city-rating-food-shadow/1.0", "Content-Type": "application/x-www-form-urlencoded"})
                    # Receipt fsync time is also part of the original deadline.
                    remaining_time = remaining_budget()
                    with urllib.request.urlopen(req, timeout=min(LIMITS["socket_seconds"], remaining_time)) as response:
                        # Never consume beyond the durably reserved allowance.
                        chunks = []
                        while True:
                            if remaining <= 0:
                                raise ValueError("Response/wire-byte limit")
                            chunk = response.read(min(65536, remaining))
                            received += len(chunk)
                            remaining -= len(chunk)
                            if remaining < 0:
                                raise ValueError("Response/wire-byte limit")
                            if time.monotonic() - started > LIMITS["wall_seconds"]:
                                raise ValueError("Wall budget exhausted")
                            if not chunk:
                                eof = True
                                break
                            chunks.append(chunk)
                        raw = b"".join(chunks)
                    doc = json.loads(raw)
                    stamp, features = validate_osm(doc)
                    remaining_budget()
                    if not 0 <= (datetime.now(timezone.utc) - stamp).total_seconds() <= 7 * 86400:
                        raise ValueError("OSM timestamp outside seven-day acquisition window")
                    packed = gzip.compress(raw, mtime=0)
                    used = sum(p.stat().st_size for p in output.iterdir() if p.is_file())
                    if used + len(packed) > LIMITS["retained_bytes"]:
                        raise ValueError("Retained-byte budget exhausted")
                    path = output / f'tile-{tile["id"]}.json.gz'
                    with path.open("xb") as stream:
                        stream.write(packed)
                    remaining_budget()
                    attempt.update(status="complete", source_base=stamp.isoformat(), features=len(features),
                                   response_sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))
                    ledger["tiles_completed"].append(tile["id"])
                except Exception as exc:
                    attempt.update(status="failed", error_type=type(exc).__name__,
                                   http_status=getattr(exc, "code", None))
                except BaseException as exc:
                    attempt.update(status="interrupted", error_type=type(exc).__name__)
                    ledger.update(status="incomplete", reason=type(exc).__name__)
                    raise
                finally:
                    attempt["observed_bytes"] = received
                    if eof and attempt["status"] != "interrupted":
                        ledger["wire_bytes"] -= attempt["reserved_bytes"] - received
                        attempt["accounting"] = "observed_complete_body"
                    save_ledger(ledger_path, ledger)
                    print(json.dumps(attempt), flush=True)
                if attempt["status"] == "complete":
                    break
                time.sleep(min(2, max(0, LIMITS["wall_seconds"] - (time.monotonic() - started))))
            else:
                raise ValueError("All established mirrors failed a required tile")
        remaining_budget()
        ledger["status"] = "complete"
    except Exception as exc:
        ledger.update(status="incomplete", reason=type(exc).__name__)
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous_handler)
        ledger["finished_at"] = datetime.now(timezone.utc).isoformat()
        save_ledger(ledger_path, ledger)
    if ledger["status"] != "complete":
        raise SystemExit("Census incomplete; no zero inference or sample freeze permitted")


if __name__ == "__main__":
    main()
