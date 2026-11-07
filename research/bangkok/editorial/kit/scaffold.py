#!/usr/bin/env python3
"""Create a new batch skeleton under research/bangkok/editorial/batches/.

Run with: python3 scaffold.py --batch-id 2026-11-07-batch3-zcode-main [--seed <priority-seed.json>]

Refuses to overwrite an existing batch. Creates raw/, profiles/, briefs/,
review/ and a batch.json template. If --seed is given (the handoff package's
priority-seed.json), pre-fills model scores and cohort ranks for the entity
keys listed in --entities (comma-separated).
"""
import argparse
import json
import os
import sys

def repo_root(start):
    d = os.path.abspath(start)
    while d != os.path.dirname(d):
        if os.path.isdir(os.path.join(d, ".git")):
            return d
        d = os.path.dirname(d)
    raise SystemExit("repo root not found (no .git above %s)" % start)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch-id", required=True)
    ap.add_argument("--entities", default="", help="comma-separated entity keys, e.g. st.nana,pom-prap-sattru-phai")
    ap.add_argument("--seed", default=None, help="path to priority-seed.json to prefill scores/ranks")
    args = ap.parse_args()

    root = repo_root(__file__)
    batches = os.path.join(root, "research/bangkok/editorial/batches")
    path = os.path.join(batches, args.batch_id)
    if os.path.exists(path):
        sys.exit(f"REFUSING: batch dir already exists: {path}")
    for sub in ("raw", "profiles", "briefs", "review"):
        os.makedirs(os.path.join(path, sub))

    entities = []
    keys = [k.strip() for k in args.entities.split(",") if k.strip()]
    seed_by_key = {}
    if args.seed and os.path.exists(args.seed):
        seed = json.load(open(args.seed, encoding="utf-8"))
        seed_by_key = {e["entity_key"]: e for e in seed["all_entities"]}
    for k in keys:
        s = seed_by_key.get(k)
        if s is None and args.seed:
            print(f"NOTE: {k} not found in seed; fill batch.json manually")
        entities.append({
            "key": k,
            "kind": s["kind"] if s else None,
            "name_en": s["name_en"] if s else None,
            "name_th": s["name_th"] if s else None,
            "aliases": [],
            "scope_notes": "",
            "selection_rationale": "",
            "model_score_default": s["model_score_default"] if s else None,
            "cohort_rank": s["cohort_rank"] if s else None,
            "cohort_size": s["cohort_size"] if s else None,
        })
    batch = {
        "batch_id": args.batch_id,
        "created_at_note": "fill after creation",
        "task": "Bangkok editorial research batch (research only; no live app data changed)",
        "handoff": "research/bangkok/editorial/2026-11-05-handoff/HANDOFF.md",
        "app_snapshot_id": "bkk-d6499618507e7561",
        "weights": {"transport": 18, "rent": 18, "daily_essentials": 14, "safety": 10,
                    "food": 12, "green": 8, "gym_sports": 4, "vibe": 4, "nightlife": 8, "crowd": 4},
        "popularity_method": ("No citywide popularity measure has been collected. Coverage breadth "
                              "is measured for batch selection only (windowed, publisher-family-deduped "
                              "scan); it is a research-selection signal, never a popularity score."),
        "researcher": "",
        "parent_batch": None,
        "selection": {"method": "three separate axes per HANDOFF.md; see selection.md",
                      "window": None, "selected": keys, "deferred": []},
        "tool_and_access_limits": [
            "Overpass API blocked from this environment — verify locations via Wikipedia coordinates and app polygons (kit/check_geometry.py)",
            "Reddit/TripAdvisor/ExpatForum 403 — resident-voice evidence thinner than ideal",
            "Bangkok Post paywall-gateway redirects not bypassed; no news-proxy mirrors",
            "Dispatch research subagents at most 2 at a time",
        ],
        "qa_status_overrides": {},
        "entities": entities,
    }
    with open(os.path.join(path, "batch.json"), "w", encoding="utf-8") as f:
        json.dump(batch, f, ensure_ascii=False, indent=1)
    with open(os.path.join(path, "selection.md"), "w", encoding="utf-8") as f:
        f.write("# Batch selection memo — %s\n\nThree selection axes kept separate "
                "(no combined priority score). Axis-1 data from raw/coverage-scan.json.\n\n"
                "## Scanned candidates\n\n| Entity | Kind | Score (rank) | Coverage band |\n"
                "| --- | --- | --- | --- |\n\n## Selected\n\n1. \n\n## Deferred (with reasons)\n\n" % args.batch_id)
    print(f"created {path}")
    print("next: fill batch.json (aliases, scope_notes, rationales), then dispatch agents with kit/agent-prompt-template.md")

if __name__ == "__main__":
    main()
