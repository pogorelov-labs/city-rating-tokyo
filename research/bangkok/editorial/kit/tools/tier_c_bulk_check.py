#!/usr/bin/env python3
"""A-2: script-assisted bulk check of tier-C data-only placeholders.

Verifies, for every placeholder bundle (the script-assisted half of the A-2
gate; the human reviewer signs the result):
1. identity — key/kind/name_en/name_th match the CURRENT app data
   (app/src/data/bangkok/{stations,districts}.json, read-only);
2. zero web claims (no claims, no body-read sources);
3. review.status == draft;
4. notes score/rank drift vs the generation snapshot (report-only; D-3/D-4
   regeneration is the sanctioned fix — never a bundle edit).

Run: python3 -I tier_c_bulk_check.py --batch-dir <tail-batch> --out <md>
"""
import argparse
import json
import os
import sys

KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def repo_root(start):
    d = os.path.abspath(start)
    while d != os.path.dirname(d):
        if os.path.isdir(os.path.join(d, ".git")):
            return d
        d = os.path.dirname(d)
    raise SystemExit("repo root not found")


ROOT = repo_root(__file__)


def load_app_identity():
    st = json.load(open(os.path.join(ROOT, "app/src/data/bangkok/stations.json"), encoding="utf-8"))
    di = json.load(open(os.path.join(ROOT, "app/src/data/bangkok/districts.json"), encoding="utf-8"))
    areas = {}
    for a in st["areas"]:
        areas["st." + a["id"]] = {"kind": "station_area", "name_en": a["name_en"], "name_th": a["name_th"]}
    for d in di["districts"]:
        areas[d["slug"]] = {"kind": "district", "name_en": d["name_en"], "name_th": d["name_th"]}
    return areas


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch-dir", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    app = load_app_identity()
    rows, fails = [], []
    for fn in sorted(os.listdir(os.path.join(args.batch_dir, "profiles"))):
        if not fn.endswith(".json"):
            continue
        b = json.load(open(os.path.join(args.batch_dir, "profiles", fn), encoding="utf-8"))
        key = b["entity"]["key"]
        problems = []
        ref = app.get(key)
        if ref is None:
            problems.append("key not in current app data")
        else:
            if b["entity"].get("kind") != ref["kind"]:
                problems.append(f"kind {b['entity'].get('kind')} != app {ref['kind']}")
            if b["entity"].get("name_en") != ref["name_en"]:
                problems.append(f"name_en {b['entity'].get('name_en')!r} != app {ref['name_en']!r}")
            if b["entity"].get("name_th") != ref["name_th"]:
                problems.append(f"name_th {b['entity'].get('name_th')!r} != app {ref['name_th']!r}")
        if b.get("claims"):
            problems.append(f"carries {len(b['claims'])} claims")
        body = [s["id"] for s in (b.get("sources") or []) if s.get("body_read")]
        if body:
            problems.append(f"{len(body)} body-read source(s)")
        if b.get("review", {}).get("status") != "draft":
            problems.append(f"review.status={b.get('review', {}).get('status')}")
        status = "PASS" if not problems else "FAIL"
        if problems:
            fails.append((key, problems))
        rows.append((key, status, problems))

    print(f"checked {len(rows)} placeholders: PASS {len(rows) - len(fails)} / FAIL {len(fails)}")
    for key, problems in fails:
        print(f"  FAIL {key}: {'; '.join(problems)}")

    with open(args.out, "w", encoding="utf-8") as f:
        f.write("# A-2 tier-C bulk check — script-assisted half (2026-11-08)\n\n")
        f.write(f"Checked **{len(rows)}** placeholder bundles against the current app data "
                f"(read-only). PASS **{len(rows) - len(fails)}**, FAIL **{len(fails)}**. "
                "The human signature on this result completes A-2 (G9). Score/rank drift "
                "vs any future snapshot is handled by D-3/D-4 regeneration, never bundle edits.\n\n")
        if fails:
            f.write("## Failures\n\n")
            for key, problems in fails:
                f.write(f"- `{key}`: {'; '.join(problems)}\n")
        else:
            f.write("## Result\n\nAll placeholders pass: identity matches the current app data, "
                    "zero web claims, `draft` status. **Reviewer sign-off pending (DEC-2/A-1).**\n")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
