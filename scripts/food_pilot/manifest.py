"""Build the owner-amended sample/contract without reading target outcomes."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from .freeze import load_census
from .stage0 import distance, freeze_sample, hash_order

RELEASE = "2026-09-23.1"
MIB = 1024**2


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def historical_empty_labels(raw, stations):
    """Read only source labels from the fixed export; never interpret them as HP zeros."""
    entries = re.findall(r'^  (?:(?:[\"\']([^\"\']+)[\"\'])|([\w-]+)): \{\n(.*?)^  \},',
                         raw.decode(), re.M | re.S)
    labels = {}
    for quoted, plain, body in entries:
        slug = quoted or plain
        match = re.search(r'sources:\s*\{[^\n]*\bfood:\s*\[([^\]]*)\]', body)
        if slug in labels or not match:
            raise ValueError("Ambiguous or missing historical food label")
        labels[slug] = not match.group(1).strip()
    if set(labels) != {s["slug"] for s in stations}:
        raise ValueError("Historical labels differ from station frame")
    return labels


def challenge_order(stations, rows, core, old, empty_labels):
    counts = {r["slug"]: r for r in rows}
    groups, excluded, selected = {}, [], []
    for group in ("rich", "sparse"):
        pool = []
        for station in stations:
            row = counts[station["slug"]]
            if row["status"] not in {"complete_zero", "complete_positive"}:
                continue
            low, high = core["boundaries"][station["prefecture"]]
            count = row["count"]
            if not (count > high if group == "rich" else count <= low):
                continue
            pool.append({**station, "osm_food_count": count, "challenge_group": group,
                         "historical_empty_food_label": empty_labels[station["slug"]],
                         "hp_zero_status": "not_acquired"})
        pool.sort(key=lambda s: (not s["historical_empty_food_label"], hash_order(s["slug"])))
        chosen = []
        for station in pool:
            if any(distance(station, other) <= 1600 for other in core["stations"] + old + selected):
                excluded.append(station["slug"])
                continue
            chosen.append(station)
            selected.append(station)
            if len(chosen) == 32:
                break
        groups[group] = {"candidates": chosen, "eligible_before_spatial": len(pool),
                         "reserve_order": [s["slug"] for s in pool if s not in chosen]}
    order = []
    for i in range(32):
        for group in ("rich", "sparse"):
            candidates = groups[group]["candidates"]
            if i < len(candidates):
                order.append(candidates[i])
    return {"maximum_prescreens": 64, "confirmed_goal_per_group": 8,
            "order": order, "groups": groups, "spatially_excluded": sorted(set(excluded)),
            "selection": "historical empty label first, then original seed hash; alternate rich/sparse",
            "stop": "first eight twice-confirmed zeros per group; never exceed frozen candidates",
            "spatial_rule": "all candidates >1600m from core, old16 and other challenge candidates"}


def budgets():
    hp = {"attempts": 400, "successful_pages": 320, "pages_per_station": 50,
          "response_bytes": MIB, "response_body_bytes": 128*MIB, "retained_bytes": 128*MIB,
          "wall_seconds": 1800, "socket_seconds": 20, "concurrency": 1,
          "minimum_request_interval_seconds": .6, "maximum_attempts_per_page": 2}
    ov = {"attempts": 2048, "row_groups": 256, "response_bytes": 8*MIB,
          "response_body_bytes": 512*MIB, "retained_bytes": 512*MIB, "wall_seconds": 1800,
          "socket_seconds": 20, "concurrency": 1, "minimum_request_interval_seconds": .1,
          "maximum_attempts_per_range": 2}
    return {"hp_development": hp, "hp_prescreen": dict(hp), "hp_holdout": dict(hp),
            "hp_confirmation": {**hp, "attempts": 200, "successful_pages": 160,
                                "response_body_bytes": 64*MIB, "retained_bytes": 64*MIB},
            "overture_metadata": {**ov, "attempts": 80, "response_body_bytes": 64*MIB,
                                  "retained_bytes": 64*MIB, "wall_seconds": 600},
            "overture_development": ov, "overture_holdout": dict(ov),
            "overture_challenge": {**ov, "attempts": 1024, "response_body_bytes": 256*MIB,
                                   "retained_bytes": 256*MIB},
            "total_retained_bytes": 2*1024**3,
            "accounting": "response bodies, not HTTP/TLS overhead; durable full reservation before I/O; unknown bytes never refunded",
            "continuation": "same original phase deadline and counters; no reset or automatic budget transfer",
            "retries": "one retry of same page/range for transient transport/5xx, after 2 seconds; all attempts charged; stop on auth/429/schema/object-change",
            "zero_confirmation": "per candidate start between 24 and 72 hours after first complete result; new separately capped phase, no immediate repeat"}


def build_manifest(stations_raw, ratings_raw, prior_raw, old_raw, objects_raw, raw_dir):
    stations = json.loads(stations_raw)
    prior, old = json.loads(prior_raw), json.loads(old_raw)["stations"]
    if len(old) != 16 or len({s["slug"] for s in old}) != 16:
        raise ValueError("Expected preserved old16 diagnostic frame")
    rows, tile_hashes = load_census(stations_raw, raw_dir)
    if rows != prior["census"] or tile_hashes != prior["tile_sha256"]:
        raise ValueError("Original census evidence changed")
    if freeze_sample(stations, rows, old) != prior["core_design"]:
        raise ValueError("Original design no longer reproduces")
    core = freeze_sample(stations, rows, old, allocation="owner_2026_10_15")
    if core["status"] != "frozen" or len(core["stations"]) != 64:
        raise ValueError("Owner-amended design remains insufficient")
    if sum(s["split"] == "holdout" for s in core["stations"]) != 32:
        raise ValueError("Expected exactly 32 holdout sites")
    empty = historical_empty_labels(ratings_raw, stations)
    challenge = challenge_order(stations, rows, core, old, empty)
    objects = json.loads(objects_raw)
    prefix = f"https://overturemaps-us-west-2.s3.us-west-2.amazonaws.com/release/{RELEASE}/theme=places/type=place/"
    if len(objects) != 16 or len(set(objects)) != 16 or any(not u.startswith(prefix) or not u.endswith('.parquet') for u in objects):
        raise ValueError("Expected the pinned 16-object Overture release listing")
    sites = core["stations"]
    return {
        "version": "crtky194-owner-amendment-2026-10-15-v1",
        "owner_amendment": "Tokyo zero 1/1, low 3/3, middle/high 2/2; other prefectures 2/2; total64=32+32",
        "target_acquisition_gate": "root manifest check AND reviewed acquisition/analysis code; manifest alone grants no execution",
        "inputs": {"stations_sha256": digest(stations_raw), "historical_labels_sha256": digest(ratings_raw),
                   "original_insufficient_sha256": digest(prior_raw), "old16_sha256": digest(old_raw),
                   "overture_listing_sha256": digest(objects_raw), "tile_sha256": tile_hashes},
        "core": core, "challenge": challenge,
        "historical_empty_label_count": sum(empty.values()),
        "spatial_proof": {"minimum_core_distance_m": min(distance(a,b) for i,a in enumerate(sites) for b in sites[i+1:]),
                          "minimum_core_old16_distance_m": min(distance(a,b) for a in sites for b in old),
                          "core_blocks": 64, "rule": "all core 800m circles disjoint; not a claim of statistical/provider independence"},
        "source_window": {"osm_acquired_date": "2026-10-15", "core_hp_complete_before": "2026-10-22T00:00:00Z",
                          "meaning": "seven UTC calendar dates Oct15–21; release/ingestion/venue observation dates separate"},
        "overture": {"release": RELEASE, "objects": objects, "identity": "verify listing then ETag/size per object; If-Match for ranges; fail on change",
                     "geometry": "WKB Point coordinates required; bbox used only for conservative row-group selection; invalid coordinates block completeness",
                     "confidence_min": .6, "operating_status_included": ["open", None],
                     "unknown_operation": "included candidate, never counted as audit-confirmed valid without independent evidence",
                     "food": {"hierarchy_prefix": "food_and_drink", "second_level": ["restaurant", "casual_eatery", "non_alcoholic_beverage_venue"],
                              "any_hierarchy_level": ["bakery", "dessert_shop", "food_court", "food_truck_stand"]},
                     "dedup": "exact provider ID; conflicting duplicate fails; physical duplicates remain for independent audit; no provider union"},
        "hotpepper": {"query_radius_m": 1000, "range": 3, "page_size": 100, "order": 1,
                      "analysis_radius_m": 800, "genre_filter": "none: primary comparator is total HP gourmet count",
                      "completeness": "stable declared total/start/returned counts; every page; unique IDs equal total; conflicting/duplicate/missing IDs or bad coordinates block; provider errors never zero",
                      "zero_states": ["complete_provider_zero", "complete_800m_zero", "complete_positive", "missing", "error", "truncated", "bad_coordinates", "unstable"]},
        "primary_comparison": "unweighted raw HP800m total vs Overture800m food count, no fitted calibration; secondary log1p/rank summaries declared",
        "holdout": {"acquire_only_after": "immutable primary candidate code/rules/manifest hashes recorded after development",
                    "isolation": "no holdout counts/rows/audit labels exposed before candidate freeze; raw row groups are internal and summaries filter development circles only",
                    "audit": "200 random distinct holdout provider IDs; hash-seed crtky194-audit-v1|id; if fewer, audit all and report limitation",
                    "targeted": "up to80 separate cases, predeclared risk ordering; never pooled with random denominator",
                    "quality": {"confirmed_joint_valid_min": .95, "redundant_physical_records_max": .02, "known_closed_max": .02},
                    "screening": {"pearson_min": .85, "spearman_min": .80},
                    "unresolved": "not confirmed valid, not automatically closed; intervals and bounds required; no correlation-only adoption"},
        "budgets": budgets(), "production_effects": "none; confidence/nightlife/ratings unchanged; full1493 dryrun and owner rollout remain separate"
    }


def finalize(candidate, *, audit_spec, audit_schema, auditor_rubric, selected_seed, unused_seed):
    result = json.loads(json.dumps(candidate))
    artifacts = {"audit_spec":audit_spec, "audit_schema":audit_schema,
                 "auditor_rubric":auditor_rubric, "selected_seed_receipt":selected_seed,
                 "unused_seed_receipt":unused_seed}
    result["audit_artifacts"] = {name:{"sha256":digest(path.read_bytes()), "path":str(path)} for name,path in artifacts.items()}
    seed = json.loads(selected_seed.read_text())["seed_hex"]
    if len(bytes.fromhex(seed)) != 32:
        raise ValueError("Expected one-time 256-bit audit seed")
    result["audit_contract"] = {"spec_markdown":audit_spec.read_text(), "record_schema":json.loads(audit_schema.read_text()),
        "seed_hex":seed, "seed_selection_basis":"B designated manifest owner before targets; C unused draw disclosed; no redraw",
        "retrievals":1200, "active_seconds":8*3600, "retained_bytes":128*MIB,
        "random":{"retrievals":800,"active_seconds":5*3600},
        "targeted":{"retrievals":240,"active_seconds":2*3600},
        "second_review":{"retrievals":160,"active_seconds":3600,"cases":40},
        "deadline":"2026-10-22T00:00:00Z", "unused_budget_transfer":False}
    result["holdout"]["audit"] = "200 distinct holdout IDs using selected random seed and exact HMAC/Fisher-Yates rejection algorithm in bound audit spec; no redraw"
    result["holdout"]["targeted"] = "up to80 separate cases; exact frozen12/12/12/12/16/8/8 buckets, precedence, ties and overlaps in bound audit spec"
    result["challenge"]["initial_stop"] = "screen all frozen64 candidates once in order unless phase budget/provider/schema failure stops; no reserve substitution"
    result["challenge"]["confirmation_stop"] = "repeat every initially complete zero (at most64) once inside each24–72h window in original order; no initial positives/errors substituted; select first8 twice-complete stable zeros per group; shortages insufficient"
    result["budgets"]["zero_confirmation"] = "at most64 initially complete zeros, separate200-attempt/160-page phase, per-case24–72h timestamps; no compressed time or immediate repeat"
    result["code_sha256"] = {str(p.relative_to(Path(__file__).resolve().parents[2])):digest(p.read_bytes())
                              for p in sorted(Path(__file__).parent.glob('*.py'))}
    result["state"] = "frozen"
    result["reviewed_execution_scope"] = ["overture_metadata","hp_development","overture_development","hp_prescreen"]
    result["later_phase_gate"] = "primary freeze after development; analysis/audit release review before holdout; real zero-confirmation window"
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('stations', 'ratings', 'original', 'old-sample', 'overture-objects', 'raw-dir', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--final',action='store_true')
    for name in ('audit-spec','audit-schema','auditor-rubric','selected-seed','unused-seed'):
        parser.add_argument('--'+name,type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.is_relative_to(Path(__file__).resolve().parents[2]):
        parser.error('Internal manifest must stay outside git')
    result = build_manifest(args.stations.read_bytes(), args.ratings.read_bytes(), args.original.read_bytes(),
                            args.old_sample.read_bytes(), args.overture_objects.read_bytes(), args.raw_dir)
    if args.final:
        required=(args.audit_spec,args.audit_schema,args.auditor_rubric,args.selected_seed,args.unused_seed)
        if any(p is None for p in required):
            parser.error('Final freeze requires audit/spec/schema/seed receipts')
        result=finalize(result,audit_spec=args.audit_spec,audit_schema=args.audit_schema,
                        auditor_rubric=args.auditor_rubric,selected_seed=args.selected_seed,unused_seed=args.unused_seed)
    raw = (json.dumps(result, sort_keys=True, indent=2, ensure_ascii=False)+'\n').encode()
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('xb') as stream:
        stream.write(raw)
    print(json.dumps({'sha256': digest(raw), 'core': len(result['core']['stations']),
                      'prescreens':len(result['challenge']['order']), 'spatial':result['spatial_proof']}))


if __name__ == '__main__':
    main()
