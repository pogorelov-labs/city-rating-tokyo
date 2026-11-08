#!/usr/bin/env python3
"""A-1 enablement: record the human reviewer's sign-off decisions en masse.

The A-1 gate needs review.reviewer / review.reviewed_at / review.status set
per researched bundle. Doing that by hand for 55 bundles is error-prone;
this tool mechanizes the bookkeeping while the *judgment* stays human:

1. --emit-template  writes aone CSV row per researched (non-data-only)
   bundle: entity_key, batch, current_status, decision(empty), review_notes.
   The reviewer fills `decision` = approved|blocked (and notes where blocked).
2. --apply FILE     applies a filled CSV. E-5 semantics enforced:
   - `approved` requires the reviewer name (via --reviewer) and sets
     review.status=approved with a human signatory marker;
   - `blocked` bundles keep an explicit blocked status + notes (route to A-4);
   - data-only (tier C) bundles are refused — A-2 covers those separately;
   - rows already carrying `agent-review:` reviewers get overwritten (that is
     the point: human sign-off supersedes the agent pass) and the overwrite is
     logged;
   - `skip` rows are left untouched.

Safety: dry-run by default; writes only with --write, via tmp+rename.
"""
import argparse
import csv
import glob
import json
import os
import sys
from datetime import datetime, timezone

# file lives at research/bangkok/editorial/kit/tools/ -> editorial root is 3 up
EDITORIAL = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BATCHES = os.path.join(EDITORIAL, "batches")
VALID = {"approved", "blocked", "skip"}


def is_data_only(bundle):
    return any("data-only" in str(n).lower()
               for n in bundle.get("review", {}).get("notes", []))


def researched_bundles():
    """[(key, batch, profile_path, bundle)] for all researched bundles."""
    out = []
    for path in sorted(glob.glob(os.path.join(BATCHES, "*", "profiles", "*.json"))):
        b = json.load(open(path, encoding="utf-8"))
        if is_data_only(b):
            continue
        batch = os.path.basename(os.path.dirname(os.path.dirname(path)))
        out.append((b["entity"]["key"], batch, path, b))
    return out


def emit_template(rows):
    out = os.path.join(EDITORIAL, "a1-signoff-template.csv")
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["entity_key", "batch", "current_status", "decision", "review_notes"])
        for key, batch, _p, b in rows:
            w.writerow([key, batch, b.get("review", {}).get("status", ""), "", ""])
    print(f"template: {out} ({len(rows)} rows) — fill `decision` = approved|blocked|skip")


def load_decisions(path):
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    bad = [r for r in rows if r.get("decision") not in VALID]
    if bad:
        sys.exit(f"invalid/empty decision in rows: {[r.get('entity_key') for r in bad]} — use {sorted(VALID)}")
    return rows


def apply(rows, decisions, reviewer, write, logf):
    by_key = {key: (batch, path, b) for key, batch, path, b in rows}
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    planned = []
    for d in decisions:
        key, decision, notes = d["entity_key"], d["decision"], (d.get("review_notes") or "").strip()
        if key not in by_key:
            sys.exit(f"unknown entity key in decisions: {key}")
        batch, path, b = by_key[key]
        if is_data_only(b):
            sys.exit(f"{key}: data-only bundles are covered by A-2, not A-1")
        if decision == "skip":
            planned.append((path, b, None, notes))
            continue
        prev = b.get("review", {}).get("reviewer")
        rec_note = (f"A-1 human sign-off {now} by {reviewer}: {decision}."
                    + (f" Notes: {notes}" if notes else "")
                    + (f" (supersedes prior reviewer: {prev})" if prev else ""))
        planned.append((path, b, {"status": decision,
                                  "reviewer": reviewer,
                                  "reviewed_at": now,
                                  "note": rec_note}, notes))
    for path, b, rec, notes in planned:
        key = b["entity"]["key"]
        if rec is None:
            print(f"[skip] {key}")
            continue
        print(f"[{rec['status']:8s}] {key}" + (f" — {notes[:60]}" if notes else ""))
        if write:
            b["review"]["status"] = rec["status"]
            b["review"]["reviewer"] = rec["reviewer"]
            b["review"]["reviewed_at"] = rec["reviewed_at"]
            b["review"].setdefault("notes", []).append(rec["note"])
    if not write:
        print("\nDRY-RUN — rerun with --write to apply")
        return
    tmp = path + ".tmp"
    for path, b, rec, _n in planned:
        if rec is None:
            continue
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(b, f, ensure_ascii=False, indent=1)
        os.replace(tmp, path)
    print(f"\nAPPLIED to {sum(1 for _p, _b, r, _n in planned if r)} bundle(s)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--emit-template", action="store_true")
    ap.add_argument("--apply")
    ap.add_argument("--reviewer", default="")
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    rows = researched_bundles()
    if args.emit_template:
        emit_template(rows)
        return
    if args.apply:
        if not args.reviewer:
            sys.exit("--reviewer is required with --apply (the human signatory's name)")
        apply(rows, load_decisions(args.apply), args.reviewer, args.write, None)
        return
    ap.print_help()


if __name__ == "__main__":
    main()
