#!/usr/bin/env python3
"""Contract repair pass (2026-11-08): make every bundle conform to the REAL
schema validation that was silently skipped before (kit/validate.py discarded
schema errors until 2026-11-08 — see 2026-11-08-gate-verification.md).

Repairs, each logged to --log:
1. claim.temporal_scope.notes: null -> "" (schema: string).
2. sources[].commercial_context: bool -> "" / "commercial (boolean normalized)".
3. editorial.uncertainties: {text|text_en, claim_ids} dicts -> text strings
   (schema: array of strings).
4. canonical_url / retrieved_url annotations ("url (annotation)" compounds):
   split to the leading URL token, annotation preserved verbatim in the
   source record's limitations. canonical_url changes recompute source ids
   and remap every evidence reference; identical normalized canonical_urls
   within a bundle are merged into the first record (limitations carry each
   query annotation, e.g. the sam-yan Overpass session ×4).

Idempotent; never touches claim text, statuses, or app data.

Run: python3 -I contract_repair.py --batch-dir <dir> [...] --log <jsonl>
"""
import argparse
import hashlib
import json
import os
import re
import sys

KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KIT)

URL_TOKEN = re.compile(r"^(https?://\S+)")

def sha12(url):
    return "src_" + hashlib.sha256(url.encode("utf-8")).hexdigest()[:12]


def norm_url_field(val):
    """Return (new_value, annotation_or_None). No-op for clean URLs."""
    if not isinstance(val, str):
        return val, None
    m = URL_TOKEN.match(val.strip())
    if not m:
        return val, None  # leave truly broken values for the gates to flag
    token = m.group(1)
    rest = val.strip()[len(token):].strip()
    if not rest:
        return val, None
    return token, rest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch-dir", action="append", required=True)
    ap.add_argument("--log", required=True)
    args = ap.parse_args()
    log = open(args.log, "a", encoding="utf-8")

    def emit(**kw):
        log.write(json.dumps(kw, ensure_ascii=False) + "\n")

    for bd in args.batch_dir:
        batch_name = os.path.basename(bd.rstrip("/"))
        stats = {"notes_null": 0, "commercial_bool": 0, "uncertainties_flat": 0,
                 "url_split": 0, "src_remap": 0, "merged_sources": 0}
        for fn in sorted(os.listdir(os.path.join(bd, "profiles"))):
            if not fn.endswith(".json"):
                continue
            path = os.path.join(bd, "profiles", fn)
            b = json.load(open(path, encoding="utf-8"))
            ent = b["entity"]["key"]
            changed = False

            # 1. temporal_scope.notes / geography.notes null -> ""
            for c in b.get("claims") or []:
                for field in ("temporal_scope", "geography"):
                    node = c.get(field)
                    if isinstance(node, dict) and node.get("notes") is None:
                        node["notes"] = ""
                        stats["notes_null"] += 1
                        changed = True

            # 2. commercial_context bool -> string
            for s in b.get("sources") or []:
                cc = s.get("commercial_context")
                if isinstance(cc, bool):
                    s["commercial_context"] = "" if cc is False else \
                        "commercial (boolean flag normalized 2026-11-08)"
                    stats["commercial_bool"] += 1
                    changed = True

            # 3. uncertainties dict -> string
            u = (b.get("editorial") or {}).get("uncertainties")
            if isinstance(u, list):
                new_u, touched = [], False
                for item in u:
                    if isinstance(item, dict):
                        new_u.append(item.get("text_en") or item.get("text") or "")
                        touched = True
                    else:
                        new_u.append(item)
                if touched:
                    b["editorial"]["uncertainties"] = new_u
                    stats["uncertainties_flat"] += len(new_u)
                    changed = True

            # 4. URL field annotations
            for s in b.get("sources") or []:
                for field in ("canonical_url", "retrieved_url"):
                    new, ann = norm_url_field(s.get(field))
                    if ann is not None:
                        s[field] = new
                        lim = (f"2026-11-08 contract repair: {field} carried a verbatim "
                               f"annotation after the URL and was split off: '{ann}'")
                        if lim not in (s.get("limitations") or []):
                            s.setdefault("limitations", []).append(lim)
                        stats["url_split"] += 1
                        changed = True

            # 5. recompute ids where canonical_url changed; merge collisions
            remap = {}
            kept, dropped = [], []
            for s in b.get("sources") or []:
                old = s["id"]
                expect = sha12(s["canonical_url"])
                if expect != old:
                    remap[old] = expect
                s["id"] = expect
                survivor = next((k for k in kept if k["id"] == expect), None)
                if survivor is None:
                    kept.append(s)
                else:
                    ann = [l for l in (s.get("limitations") or [])
                           if l not in (survivor.get("limitations") or [])]
                    survivor.setdefault("limitations", []).extend(ann)
                    survivor["limitations"].append(
                        f"2026-11-08 contract repair: duplicate record (identical canonical "
                        f"URL) merged into this one; its title was '{s.get('title')}'")
                    dropped.append(s)
                    stats["merged_sources"] += 1

            if remap or dropped:
                for c in b.get("claims") or []:
                    for e in c.get("evidence") or []:
                        sid = e["source_id"]
                        if sid in remap:
                            e["source_id"] = remap[sid]
                            stats["src_remap"] += 1
                if dropped:
                    b["sources"] = kept
                    changed = True

            if changed:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(b, f, ensure_ascii=False, indent=1)
                emit(batch=batch_name, entity=ent, **stats)
                print(f"{batch_name}/{fn}: repaired")

        print(f"{batch_name}: {stats}")

    log.close()


if __name__ == "__main__":
    main()
