#!/usr/bin/env python3
"""B-10/G21 pass: canonicalize corroboration labels in EXISTING bundles.

NEVER re-run kit/assemble.py over closed batches — raw/ predates the
coordinator corrections applied to profiles/ after assembly. This tool edits
profiles in place, idempotently:

1. corroborated claims whose canonical publisher-family set (canonical.py)
   has <2 members -> proposed (never the reverse; `conflicted` untouched);
2. repairs limitations arrays exploded into single characters (normalize bug
   found by the re-gate: khlong-san-c03, saphan-taksin-c07);
3. appends a dated review note once (marker-checked);
4. stamps manifest.json with a `canonical_family_relabel` block.

Every change is logged to --log (JSONL) and summarized to stdout.

Run: python3 -I relabel_canonical.py --batch-dir <b1> [--batch-dir <b2> ...]
     --log ../../2026-11-08-canonical-relabel-log.jsonl
"""
import argparse
import json
import os
import sys
from datetime import date

KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KIT)
from canonical import canon_families  # noqa: E402

TODAY = date.today().isoformat()
NOTE_MARKER = "B-10/G21 canonical relabel applied"
NOTE = (f"{NOTE_MARKER} {TODAY}: corroboration labels recomputed under canonical "
        "publisher families (kit/canonical.py) — Wikipedia language editions/"
        "Wikimedia projects and OSM/Overpass variants count as ONE family; "
        "HipFlat casing/snippet variants likewise. See "
        "2026-11-08-canonical-relabel-log.jsonl for the per-claim ledger.")


def is_data_only(bundle):
    return any("data-only" in str(n).lower() for n in bundle.get("review", {}).get("notes", []))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch-dir", action="append", required=True)
    ap.add_argument("--log", required=True)
    args = ap.parse_args()

    log = open(args.log, "a", encoding="utf-8")
    total_relabel, total_repair, seen = 0, 0, set()
    for bd in args.batch_dir:
        profiles = sorted(os.listdir(os.path.join(bd, "profiles")))
        batch_relabel, batch_repair = 0, 0
        for fn in [f for f in profiles if f.endswith(".json")]:
            path = os.path.join(bd, "profiles", fn)
            bundle = json.load(open(path, encoding="utf-8"))
            if is_data_only(bundle):
                continue
            ent = bundle["entity"]["key"]
            bysid = {s["id"]: s for s in bundle["sources"]}
            changes = []
            for c in bundle["claims"]:
                raw_fams = {bysid[e["source_id"]]["publisher_family"]
                            for e in c["evidence"] if e["source_id"] in bysid}
                canon = canon_families(raw_fams)
                if c["review_status"] == "corroborated":
                    assert len(raw_fams) >= 2, f"{c['id']}: corroborated without 2 raw families?"
                    if len(canon) < 2:
                        c["review_status"] = "proposed"
                        changes.append({"entity": ent, "claim_id": c["id"], "change": "relabel",
                                        "before": "corroborated", "after": "proposed",
                                        "raw_families": sorted(raw_fams), "canonical_families": sorted(canon)})
                        batch_relabel += 1
                elif c["review_status"] == "proposed":
                    assert not (len(raw_fams) >= 2 and len(canon) >= 2), \
                        f"{c['id']}: proposed but 2+ canonical families — would need an upgrade, not a relabel"
                # repair exploded limitations arrays
                lims = c.get("limitations") or []
                if len(lims) > 5 and all(isinstance(x, str) and len(x) <= 1 for x in lims):
                    joined = "".join(lims)
                    c["limitations"] = [joined]
                    changes.append({"entity": ent, "claim_id": c["id"], "change": "limitations_repair",
                                    "before": f"{len(lims)} single-char entries",
                                    "after": joined})
                    batch_repair += 1
            notes = bundle.setdefault("review", {}).setdefault("notes", [])
            if changes or not any(NOTE_MARKER in n for n in notes):
                notes.append(NOTE)
            if changes:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(bundle, f, ensure_ascii=False, indent=1)
            for ch in changes:
                log.write(json.dumps({**ch, "date": TODAY}, ensure_ascii=False) + "\n")
            seen.add(ent)

        # manifest stamp
        mpath = os.path.join(bd, "manifest.json")
        if os.path.exists(mpath):
            manifest = json.load(open(mpath, encoding="utf-8"))
            manifest["canonical_family_relabel"] = {
                "date": TODAY,
                "rule": "kit/canonical.py v1 (B-10/G21)",
                "relabeled": batch_relabel,
                "limitations_repairs": batch_repair,
                "note": "corroboration recomputed over canonical publisher families; "
                        "per-claim ledger in 2026-11-08-canonical-relabel-log.jsonl",
            }
            manifest["updated_at"] = TODAY + "T00:00:00Z"
            with open(mpath, "w", encoding="utf-8") as f:
                json.dump(manifest, f, ensure_ascii=False, indent=1)

        total_relabel += batch_relabel
        total_repair += batch_repair
        print(f"{os.path.basename(bd)}: relabels={batch_relabel} limitations_repairs={batch_repair}")

    log.close()
    print(f"TOTAL: {total_relabel} claims corroborated->proposed, "
          f"{total_repair} limitations repairs; log={args.log}")


if __name__ == "__main__":
    main()
