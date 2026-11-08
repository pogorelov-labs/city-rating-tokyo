#!/usr/bin/env python3
"""C-5/G14-support: regenerate the living recheck registry from the bundles.

Sources (the plan's C-5):
1. every claim with `temporal_scope.recheck_by` — the dated volatile flags;
2. every bundle `open_issues` note — folded in as verifiable items (dated
   `open`, sorted to the end; owners work them via the review/rework flow).

Output: a CSV compatible with the original calendar's columns plus
`source` (recheck|open_issue) and `kind`, sorted by due date. Run at every
batch close and after any rework; also prints the due-now count for the
current month.

Run: python3 -I recheck-due.py --batch-dir <b1> [...] --out <calendar.csv>
"""
import argparse
import csv
import glob
import json
import os
from datetime import date


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch-dir", action="append", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--supersede", action="append", default=[],
                    help="later_batch:earlier_batch — for entities present in the later "
                         "batch, drop registry rows sourced from the earlier (superseded) batch")
    args = ap.parse_args()

    superseded_entities = set()
    for pair in args.supersede:
        later_b, earlier_b = pair.split(":", 1)
        later_path = os.path.join(later_b, "profiles")
        for fn in os.listdir(later_path):
            if fn.endswith(".json"):
                superseded_entities.add(fn[:-5])

    rows, issues = [], 0
    for bd in args.batch_dir:
        batch = os.path.basename(bd.rstrip("/"))
        for p in sorted(glob.glob(os.path.join(bd, "profiles", "*.json"))):
            b = json.load(open(p, encoding="utf-8"))
            ent = b["entity"]["key"]
            name = b["entity"]["name_en"]
            for c in b.get("claims") or []:
                rb = (c.get("temporal_scope") or {}).get("recheck_by")
                if not rb:
                    continue
                topic = (c.get("temporal_scope") or {}).get("notes") or c["text_en"]
                rows.append({"recheck_by": str(rb), "entity": ent, "name": name,
                             "claim_id": c["id"], "topic": topic[:220],
                             "batch": batch, "profile": os.path.relpath(p),
                             "source": "recheck", "kind": "claim"})
            for note in (b.get("review", {}).get("notes") or []):
                if not str(note).startswith("open issue:"):
                    continue
                issues += 1
                rows.append({"recheck_by": "open", "entity": ent, "name": name,
                             "claim_id": "", "topic": str(note)[len("open issue: "):][:220],
                             "batch": batch, "profile": os.path.relpath(p),
                             "source": "open_issue", "kind": "note"})

    # drop superseded-batch rows (upgrade precedence: highest tier wins)
    dropped = 0
    kept = []
    earlier_names = {os.path.basename(p.split(":", 1)[1].rstrip("/")) for p in args.supersede}
    for r in rows:
        if r["entity"] in superseded_entities and r["batch"] in earlier_names:
            dropped += 1
            continue
        kept.append(r)
    rows = kept

    rows.sort(key=lambda r: (r["recheck_by"] == "open", r["recheck_by"], r["entity"]))
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["recheck_by", "entity", "name", "claim_id",
                                          "topic", "batch", "profile", "source", "kind"])
        w.writeheader()
        w.writerows(rows)

    today = date.today()
    ym = f"{today.year}-{today.month:02d}"
    due_now = sum(1 for r in rows if r["recheck_by"].startswith(ym)
                  or (len(r["recheck_by"]) == 4 and r["recheck_by"] == str(today.year)))
    print(f"registry: {len(rows)} items ({dropped} superseded rows dropped) ({sum(1 for r in rows if r['source']=='recheck')} "
          f"recheck flags + {issues} open issues) -> {args.out}; due this month ({ym}): {due_now}")


if __name__ == "__main__":
    main()
