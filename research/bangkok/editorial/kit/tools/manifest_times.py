#!/usr/bin/env python3
"""B-14: stamp manifests with research start/end times (handoff: the manifest
records start and end).

Derivation: first/last raw-write mtimes per batch (raw/<key>.json, excluding
`original-*` correction backups). For scripted batches with no raw files (the
tier-C tail), profiles/ mtimes are used instead. Values are filesystem mtimes
— they reflect when the research files were written, not when the batch was
committed.

Run: python3 -I manifest_times.py --batch-dir <dir> [...]
"""
import argparse
import glob
import json
import os
from datetime import datetime, timezone


def iso(ts):
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def window(bd):
    raw = [f for f in glob.glob(os.path.join(bd, "raw", "*.json"))
           if not os.path.basename(f).startswith("original-")]
    src = raw or glob.glob(os.path.join(bd, "profiles", "*.json"))
    if not src:
        return None, None, "no-files"
    times = [os.path.getmtime(f) for f in src]
    basis = "raw-write-mtimes" if raw else "profile-write-mtimes (scripted batch)"
    return min(times), max(times), basis


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch-dir", action="append", required=True)
    args = ap.parse_args()
    for bd in args.batch_dir:
        lo, hi, basis = window(bd)
        mpath = os.path.join(bd, "manifest.json")
        if lo is None:
            print(f"{os.path.basename(bd.rstrip('/'))}: no files — skipped")
            continue
        manifest = json.load(open(mpath, encoding="utf-8"))
        manifest["research_started_at"] = iso(lo)
        manifest["research_completed_at"] = iso(hi)
        manifest["research_time_basis"] = basis
        with open(mpath, "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=1)
        print(f"{os.path.basename(bd.rstrip('/')):38s} {manifest['research_started_at']} → "
              f"{manifest['research_completed_at']}  ({basis})")


if __name__ == "__main__":
    main()
