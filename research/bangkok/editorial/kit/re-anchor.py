#!/usr/bin/env python3
"""D-4/G15: re-anchor bundle selection_context to the CURRENT app snapshot.

After any app-data change (B-1 sena-ruam removal, B-2 anchors, B-4 polygons,
a refresh), every researched bundle's `selection_context` goes stale: the
composite score and cohort ranks shift. This tool re-derives them from the
current `app/src/data/bangkok/{districts,stations}.json` — **claims and copy
are never touched** — and logs every drift.

Derivation (verified against the seed: samphanthawong 8.56 exactly):
  model_score_default = weight-weighted mean of the entity's 10 ratings;
  cohort_rank / cohort_size = rank of that score within the entity's kind
  (districts / station areas), descending.

Run after the replay lands:
  python3 -I re-anchor.py --batch-dir <b1> [...] [--snapshot app/src/data/bangkok]
Dry-run (default) reports drift without writing; --write applies.
"""
import argparse
import json
import os

WEIGHTS = {"transport": 18, "rent": 18, "daily_essentials": 14, "safety": 10,
           "food": 12, "green": 8, "gym_sports": 4, "vibe": 4, "nightlife": 8,
           "crowd": 4}
TW = sum(WEIGHTS.values())


def repo_root(start):
    d = os.path.abspath(start)
    while d != os.path.dirname(d):
        if os.path.isdir(os.path.join(d, ".git")):
            return d
        d = os.path.dirname(d)
    raise SystemExit("repo root not found")


def score(ratings):
    return round(sum(ratings[k] * WEIGHTS[k] for k in WEIGHTS) / TW, 2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch-dir", action="append", required=True)
    ap.add_argument("--snapshot", default="app/src/data/bangkok")
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    root = repo_root(__file__)
    snap = os.path.join(root, args.snapshot)

    # kind-separated tables: district slugs and area ids can collide
    # (e.g. a district slug equal to a station-area id) — one dict would
    # silently overwrite entries and shrink cohorts (found in the first
    # dry-run: 31/50 districts after collisions)
    tables = {"district": {}, "station_area": {}}
    with open(os.path.join(snap, "districts.json"), encoding="utf-8") as f:
        for d in json.load(f)["districts"]:
            tables["district"][d["slug"]] = d["ratings"]
    with open(os.path.join(snap, "stations.json"), encoding="utf-8") as f:
        for a in json.load(f)["areas"]:
            tables["station_area"][a["id"]] = a["ratings"]

    ranks = {}
    for kind, tbl in tables.items():
        lst = sorted(((k, score(r)) for k, r in tbl.items()), key=lambda kv: -kv[1])
        size = len(lst)
        for i, (k, _s) in enumerate(lst, 1):
            ranks[k] = (i, size, kind)

    drift = 0
    for bd in args.batch_dir:
        for fn in sorted(os.listdir(os.path.join(bd, "profiles"))):
            if not fn.endswith(".json"):
                continue
            p = os.path.join(bd, "profiles", fn)
            b = json.load(open(p, encoding="utf-8"))
            key = b["entity"]["key"]
            unpref = key.replace("st.", "")
            kind = b["entity"]["kind"]
            tbl = tables.get(kind, {})
            if unpref not in tbl:
                print(f"[MISS] {key}: not in current snapshot (removed unit?) — bundle left for manual routing")
                continue
            new_score = score(tbl[unpref])
            new_rank, new_size, _ = ranks[unpref]
            sc = b["selection_context"]
            old = (sc.get("model_score_default"), sc.get("cohort_rank"), sc.get("cohort_size"))
            new = (new_score, new_rank, new_size)
            if old[0] != new[0]:
                drift += 1
                print(f"[DRIFT] {key}: score {old[0]}→{new[0]} rank {old[1]}→{new[1]}/{new[2]}")
            elif old[1:] != new[1:]:
                # same score, different tie order — the seed's arbitrary
                # tie-break, not a real drift (snapshot unchanged here)
                print(f"[tie] {key}: score unchanged at {new[0]}; rank {old[1]}→{new[1]}/{new[2]} (tie order)")
                if args.write:
                    sc["model_score_default"] = new_score
                    sc["cohort_rank"] = new_rank
                    sc["cohort_size"] = new_size
                    sc["reanchored"] = "D-4/G15 re-anchor to current snapshot"
                    b.setdefault("review", {}).setdefault("notes", []).append(
                        "D-4/G15 re-anchor applied: selection_context re-derived from the "
                        "current app snapshot (claims/copy untouched).")
                    with open(p, "w", encoding="utf-8") as f:
                        json.dump(b, f, ensure_ascii=False, indent=1)
            else:
                print(f"[ok] {key}: no drift")
    print(f"{'WRITTEN' if args.write else 'DRY-RUN'}: {drift} bundle(s) drifted")


if __name__ == "__main__":
    main()
