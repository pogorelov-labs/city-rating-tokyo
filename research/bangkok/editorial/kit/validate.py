#!/usr/bin/env python3
"""Minimal Draft 2020-12 validator for the schema subset used by entity-research.schema.json.

Run with: python3 -I tools/validate.py   (from the batch directory)
"""
import json
import os
import re
import sys

SCHEMA_DEFAULT = ("/Users/ruslan/.codex/worktrees/bangkok-filters/city-rating/"
                  "research/bangkok/editorial/2026-11-05-handoff/entity-research.schema.json")
SCHEMA_FALLBACK = "research/bangkok/editorial/2026-11-05-handoff/entity-research.schema.json"

URI_RE = re.compile(r"^https?://\S+$")
DT_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(Z|[+-]\d{2}:?\d{2})$")

def is_type(v, t):
    if t == "object": return isinstance(v, dict)
    if t == "array": return isinstance(v, list)
    if t == "string": return isinstance(v, str)
    if t == "number": return isinstance(v, (int, float)) and not isinstance(v, bool)
    if t == "integer": return isinstance(v, int) and not isinstance(v, bool)
    if t == "boolean": return isinstance(v, bool)
    if t == "null": return v is None
    return True

def validate(v, schema, path, errors):
    if "anyOf" in schema:
        for opt in schema["anyOf"]:
            pre = len(errors)
            validate(v, opt, path, errors)
            if len(errors) == pre:
                return
        errors.append(f"{path}: does not match any allowed variant")
        return
    if "const" in schema and v != schema["const"]:
        errors.append(f"{path}: expected const {schema['const']!r}, got {v!r}")
        return
    if "enum" in schema and v not in schema["enum"]:
        errors.append(f"{path}: {v!r} not in enum {schema['enum']}")
        return
    t = schema.get("type")
    if t is not None:
        types = t if isinstance(t, list) else [t]
        if not any(is_type(v, tt) for tt in types):
            errors.append(f"{path}: expected type {t}, got {type(v).__name__} ({v!r})")
            return
    if isinstance(v, str):
        if "pattern" in schema and not re.search(schema["pattern"], v):
            errors.append(f"{path}: {v!r} fails pattern {schema['pattern']}")
        if schema.get("format") == "uri" and not URI_RE.match(v):
            errors.append(f"{path}: {v!r} not a valid http(s) URI")
        if schema.get("format") == "date-time" and not DT_RE.match(v):
            errors.append(f"{path}: {v!r} not an ISO date-time")
        if schema.get("minLength") is not None and len(v) < schema["minLength"]:
            errors.append(f"{path}: shorter than minLength {schema['minLength']}")
        if schema.get("maxLength") is not None and len(v) > schema["maxLength"]:
            errors.append(f"{path}: longer than maxLength {schema['maxLength']}")
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        if "minimum" in schema and v < schema["minimum"]:
            errors.append(f"{path}: {v} < minimum {schema['minimum']}")
        if "maximum" in schema and v > schema["maximum"]:
            errors.append(f"{path}: {v} > maximum {schema['maximum']}")
    if isinstance(v, list):
        if "minItems" in schema and len(v) < schema["minItems"]:
            errors.append(f"{path}: {len(v)} items < minItems {schema['minItems']}")
        if "maxItems" in schema and len(v) > schema["maxItems"]:
            errors.append(f"{path}: {len(v)} items > maxItems {schema['maxItems']}")
        if schema.get("uniqueItems"):
            seen = [json.dumps(x, sort_keys=True, ensure_ascii=False) for x in v]
            if len(seen) != len(set(seen)):
                dup = [x for i, x in enumerate(seen) if x in seen[:i]]
                errors.append(f"{path}: duplicate items {dup[:2]}")
        if "items" in schema:
            for i, item in enumerate(v):
                validate(item, schema["items"], f"{path}[{i}]", errors)
    if isinstance(v, dict):
        for req in schema.get("required", []):
            if req not in v:
                errors.append(f"{path}: missing required '{req}'")
        props = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            for k in v:
                if k not in props:
                    errors.append(f"{path}: unexpected property '{k}'")
        for k, sub in props.items():
            if k in v:
                validate(v[k], sub, f"{path}.{k}", errors)

def semantic_checks(b, path_prefix, errors):
    key = b["entity"]["key"]
    claim_ids = {c["id"] for c in b["claims"]}
    if len(claim_ids) != len(b["claims"]):
        errors.append(f"{path_prefix}: duplicate claim ids")
    src_ids = [s["id"] for s in b["sources"]]
    if len(set(src_ids)) != len(src_ids):
        errors.append(f"{path_prefix}: duplicate source ids")
    known_src = set(src_ids)
    for c in b["claims"]:
        for e in c["evidence"]:
            if e["source_id"] not in known_src:
                errors.append(f"{path_prefix}.{c['id']}: evidence source {e['source_id']} not in sources")
        for link in c.get("conflicts_with") or []:
            if link == c["id"]:
                errors.append(f"{path_prefix}.{c['id']}: conflicts_with self-reference")
            elif link not in claim_ids:
                errors.append(f"{path_prefix}.{c['id']}: conflicts_with dangling link {link}")
    for q in b["question_answers"]:
        for cid in q["claim_ids"]:
            if cid not in claim_ids:
                errors.append(f"{path_prefix}.{q['id']}: dangling claim ref {cid}")
    ed = b["editorial"]
    for blk in ("preview", "guide_lead"):
        if ed[blk] is not None:
            for cid in ed[blk]["claim_ids"]:
                if cid not in claim_ids:
                    errors.append(f"{path_prefix}.{blk}: dangling claim ref {cid}")
    for lst in ("strengths", "tradeoffs", "day_night", "within_area_variation", "conditional_fit"):
        for i, item in enumerate(ed[lst]):
            for cid in item["claim_ids"]:
                if cid not in claim_ids:
                    errors.append(f"{path_prefix}.{lst}[{i}]: dangling claim ref {cid}")

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch-dir", default=os.getcwd())
    ap.add_argument("--schema", default=None)
    args = ap.parse_args()
    schema_path = args.schema or (SCHEMA_DEFAULT if os.path.exists(SCHEMA_DEFAULT) else SCHEMA_FALLBACK)
    schema = json.load(open(schema_path, encoding="utf-8"))
    profiles_dir = os.path.join(args.batch_dir, "profiles")
    all_ok = True
    for fn in sorted(os.listdir(profiles_dir)):
        if not fn.endswith(".json"):
            continue
        p = os.path.join(profiles_dir, fn)
        b = json.load(open(p, encoding="utf-8"))
        errors = []
        validate(b, schema, fn, [])
        semantic_checks(b, fn, errors)
        status = "PASS" if not errors else "FAIL"
        n_claims = len(b["claims"]); n_src = len(b["sources"])
        statuses = {}
        for c in b["claims"]:
            statuses[c["review_status"]] = statuses.get(c["review_status"], 0) + 1
        qa_conf = [q["id"] for q in b["question_answers"] if q["status"] == "conflicting"]
        print(f"{fn}: {status} | sources={n_src} claims={n_claims} review_status={statuses} conflicting_q={qa_conf}")
        for e in errors:
            print("   -", e)
            all_ok = False
    print("ALL OK" if all_ok else "VALIDATION FAILURES PRESENT")
    sys.exit(0 if all_ok else 1)

if __name__ == "__main__":
    main()
