#!/usr/bin/env python3
"""B-11: build the canonical source-attribution registry.

49 of 547 canonical URLs are cited with inconsistent publisher/title across
bundles ("Wikipedia" vs "Wikipedia (English)"; per-claim Overpass titles), so
any merged citation view would show conflicting attribution for one source.
This tool groups every bundle source record by canonical URL and emits one
canonical attribution per URL (most frequent exact string; ties resolved
lexicographically) plus the observed variants and the citing entities.

Output: kit/registry/source-attributions.json (full mapping — the adapter
references it for merged citation views; never rewrites bundle provenance).

Run: python3 -I build_source_registry.py --batch-dir <b1> [...]
     --out ../registry/source-attributions.json
"""
import argparse
import collections
import json
import os
from datetime import date, timezone, datetime


def canonical_variant(values):
    counts = collections.Counter(v for v in values if v)
    if not counts:
        return None
    best = max(counts.values())
    return sorted(v for v, n in counts.items() if n == best)[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch-dir", action="append", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    per_url = collections.defaultdict(lambda: {
        "publisher": [], "publisher_family": [], "title": [], "cited_by": set()})
    for bd in args.batch_dir:
        batch_name = os.path.basename(bd.rstrip("/"))
        for fn in sorted(os.listdir(os.path.join(bd, "profiles"))):
            if not fn.endswith(".json"):
                continue
            bundle = json.load(open(os.path.join(bd, "profiles", fn), encoding="utf-8"))
            ent = bundle["entity"]["key"]
            for s in bundle.get("sources") or []:
                rec = per_url[s["canonical_url"]]
                rec["publisher"].append(s.get("publisher") or "")
                rec["publisher_family"].append(s.get("publisher_family") or "")
                rec["title"].append(s.get("title") or "")
                rec["cited_by"].add(ent)
                rec.setdefault("batches", set()).add(batch_name)

    attributions, stats = {}, collections.Counter()
    for url, rec in per_url.items():
        variants = {k: sorted({v for v in rec[k] if v})
                    for k in ("publisher", "publisher_family", "title")}
        entry = {
            "publisher": canonical_variant(rec["publisher"]),
            "publisher_family": canonical_variant(rec["publisher_family"]),
            "title": canonical_variant(rec["title"]),
            "variants": variants,
            "cited_by": sorted(rec["cited_by"]),
        }
        attributions[url] = entry
        for k in variants:
            if len(variants[k]) > 1:
                stats[f"{k}_inconsistent"] += 1

    out = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "date": date.today().isoformat(),
        "generator": "kit/tools/build_source_registry.py v1 (B-11)",
        "rule": "canonical attribution = most frequent exact string per field; ties lexicographic",
        "url_count": len(attributions),
        "stats": dict(stats),
        "note": ("Reference registry for merged citation views. Bundle provenance is "
                 "never rewritten; the adapter consults this file at build time."),
        "attributions": attributions,
    }
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1, sort_keys=True)
    print(f"wrote {args.out}: {len(attributions)} URLs | inconsistent: {dict(stats)}")


if __name__ == "__main__":
    main()
