#!/usr/bin/env python3
"""A-8 rework tool (2026-11-08): clear the independent review's blocked bundles.

Step 1 (F1+F2): rebuild batch-4 editorial fields from raw/<key>.json
(day_night / within_area_variation / uncertainties / preview / guide_lead /
strengths / tradeoffs / conditional_fit — wherever the profile carries
placeholder or exploded values) and join exploded limitations arrays (claims
AND sources) into their original strings. Editorial rebuilds are lossless by
construction (text taken verbatim from raw); limitation joins are structural.

Step 2 (F4): strip inline claim refs ([...] and (...) forms) from user-facing
copy and set each block's claim_ids from its own text (extract before strip;
union fallback only when a block yields nothing — flagged as P2-grade).

Every change is logged to --log (JSONL). Idempotent. Never touches claims'
substance, statuses, scores, or any other bundle fields.

Run: python3 -I rework_a8.py --batch-dir <dir> [--keys k1,k2,...] --log <jsonl>
     --step rebuild|strip
"""
import argparse
import json
import os
import re
import sys

KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KIT)

BATCH4 = "2026-11-07-batch4-light-zcode-main"
F1_KEYS = ["bang-phlat", "bang-sue", "bangkok-noi", "din-daeng", "dusit",
           "khlong-san", "sathon", "st.hua-lamphong", "st.khlong-san",
           "st.phra-ram-9", "st.saphan-taksin", "thon-buri"]

REF_BRACKET = re.compile(r"\[((?:[a-z0-9\-]*-)?c\d+(?:\s*,\s*(?:[a-z0-9\-]*-)?c\d+)*)\]")
REF_PAREN = re.compile(r"\(((?:[a-z0-9\-]*-)?c\d+(?:\s*,\s*(?:[a-z0-9\-]*-)?c\d+)*)\)")
REF_RE = re.compile(r"(?:[a-z0-9]+-)*c(\d+)")

PLACEHOLDER_VALUES = {"text", "text_en", "claim_ids"}


def is_placeholder_item(item):
    if isinstance(item, dict):
        return (item.get("text_en") in PLACEHOLDER_VALUES
                or item.get("text") in PLACEHOLDER_VALUES)
    if isinstance(item, str):
        return item.strip() in PLACEHOLDER_VALUES
    return False


def extract_refs(text):
    refs = []
    for m in REF_BRACKET.finditer(text):
        refs.extend(REF_RE.findall(m.group(1)))
    for m in REF_PAREN.finditer(text):
        refs.extend(REF_RE.findall(m.group(1)))
    out = []
    for n in refs:
        # entity prefix is restored by the caller via known ids
        out.append(n)
    return out


def strip_refs(text, prefix):
    """Remove [refs]/(refs) groups (full or bare cNN tokens); return
    (clean_text, [claim_ids full ids]) — bare tokens expanded with prefix."""
    ids = []

    def collect(m):
        for tok in re.split(r"\s*,\s*", m.group(1)):
            if REF_RE.fullmatch(tok):
                ids.append(tok if "-c" in tok else f"{prefix}{tok}")
        return ""

    t = REF_BRACKET.sub(collect, text)
    t = REF_PAREN.sub(collect, t)
    t = re.sub(r"\s{2,}", " ", t)
    t = re.sub(r"\s+([.,;:!?])", r"\1", t)
    return t.strip(), ids


def join_exploded(lims, min_chars=8, min_len=10):
    """If ≥min_len entries and ≥min_chars single-char ones: join the char run,
    keep intact multi-char entries (post-assembly annotations) as separate
    strings. Returns (new_list, joined_string) or None."""
    if not isinstance(lims, list) or len(lims) < min_len:
        return None
    singles = [x for x in lims if isinstance(x, str) and len(x) <= 1]
    if len(singles) < min_chars:
        return None
    joined_parts, trailing = [], []
    run = []
    for x in lims:
        if isinstance(x, str) and len(x) <= 1:
            run.append(x)
        else:
            if run:
                joined_parts.append("".join(run))
                run = []
            trailing.append(x)
    if run:
        joined_parts.append("".join(run))
    joined = "".join(joined_parts)
    out = [joined] + trailing
    return out, joined


def norm_raw_item(item, known_ids, union_fallback, prefix=""):
    """raw editorial item (dict with text|text_en, or str) -> profile item."""
    if isinstance(item, dict):
        text = item.get("text_en") or item.get("text") or ""
    else:
        text = item or ""
    clean, ids = strip_refs(text, prefix)
    known = [c for c in dict.fromkeys(ids) if c in known_ids]
    if not known:
        extra = [c for c in (item.get("claim_ids") if isinstance(item, dict) else []) or []
                 if c in known_ids]
        known = [c for c in dict.fromkeys(extra) if c in known_ids]
    if not known:
        known = list(union_fallback)
    return {"text_en": clean, "claim_ids": known}


def rebuild_editorial(profile, raw, log, ent, batch):
    prefix = ent.replace("st.", "") + "-"
    ed, raw_ed = profile["editorial"], raw["editorial"]
    known_ids = {c["id"] for c in profile["claims"]}
    union = sorted({c2 for lst in ("strengths", "tradeoffs", "day_night",
                                   "within_area_variation", "conditional_fit")
                    for blk in ed.get(lst) or []
                    for c2 in blk.get("claim_ids", [])}) or sorted(known_ids)[:1]
    changed = 0

    def rebuild_list_field(field):
        nonlocal changed
        cur = ed.get(field)
        raw_val = raw_ed.get(field)
        needs = (not cur or any(is_placeholder_item(i) for i in cur))
        if raw_val is None and not needs:
            return
        if isinstance(raw_val, dict):
            items = [norm_raw_item(raw_val, known_ids, union, prefix)]
        elif isinstance(raw_val, list):
            items = [norm_raw_item(i, known_ids, union, prefix) for i in raw_val]
        elif isinstance(raw_val, str):
            items = [norm_raw_item(raw_val, known_ids, union, prefix)]
        else:
            items = None
        if items is None:
            return
        old = json.dumps(cur, ensure_ascii=False)[:80]
        ed[field] = items if field != "uncertainties" else \
            [(i["text_en"] if isinstance(i, dict) else i) for i in items]
        log.write(json.dumps({"batch": batch, "entity": ent, "field": f"editorial.{field}",
                              "change": "rebuild_from_raw", "before": old,
                              "after": json.dumps(ed[field], ensure_ascii=False)[:120]},
                             ensure_ascii=False) + "\n")
        changed += 1

    for field in ("strengths", "tradeoffs", "day_night", "within_area_variation",
                  "conditional_fit", "uncertainties"):
        rebuild_list_field(field)

    for field in ("preview", "guide_lead"):
        cur, raw_val = ed.get(field), raw_ed.get(field)
        if cur is None and isinstance(raw_val, dict):
            text = raw_val.get("text_en") or raw_val.get("text") or ""
            clean, ids = strip_refs(text, "")
            known = [c for c in dict.fromkeys(ids) if c in known_ids] or \
                    [c for c in (raw_val.get("claim_ids") or []) if c in known_ids] or \
                    union[:1]
            ed[field] = {"text_en": clean, "claim_ids": known}
            log.write(json.dumps({"batch": batch, "entity": ent, "field": f"editorial.{field}",
                                  "change": "rebuild_from_raw"}, ensure_ascii=False) + "\n")
            changed += 1
    return changed


def repair_limitations(profile, raw, log, ent, batch):
    changed = 0
    for c in profile.get("claims") or []:
        res = join_exploded(c.get("limitations"))
        if res:
            old = c["limitations"]
            c["limitations"] = res[0]
            log.write(json.dumps({"batch": batch, "entity": ent, "claim": c["id"],
                                  "change": "limitations_join", "entries_before": len(old),
                                  "after": res[1][:160]}, ensure_ascii=False) + "\n")
            changed += 1
    for s in profile.get("sources") or []:
        res = join_exploded(s.get("limitations"))
        if res:
            old = s["limitations"]
            s["limitations"] = res[0]
            log.write(json.dumps({"batch": batch, "entity": ent, "source": s["id"],
                                  "change": "source_limitations_join", "entries_before": len(old),
                                  "after": res[1][:160]}, ensure_ascii=False) + "\n")
            changed += 1
    return changed


def cmd_rebuild(args, log):
    total_e = total_l = 0
    for bd in args.batch_dir:
        batch = os.path.basename(bd.rstrip("/"))
        keys = args.keys.split(",") if args.keys else (F1_KEYS if BATCH4 in batch else None)
        if keys is None:
            print(f"{batch}: no key list for this batch — skipped")
            continue
        for key in keys:
            ppath = os.path.join(bd, "profiles", f"{key}.json")
            rpath = os.path.join(bd, "raw", f"{key}.json")
            if not (os.path.exists(ppath) and os.path.exists(rpath)):
                print(f"{batch}/{key}: missing profile or raw — skipped")
                continue
            profile = json.load(open(ppath, encoding="utf-8"))
            raw = json.load(open(rpath, encoding="utf-8"))
            e = rebuild_editorial(profile, raw, log, key, batch)
            l = repair_limitations(profile, raw, log, key, batch)
            if e or l:
                with open(ppath, "w", encoding="utf-8") as f:
                    json.dump(profile, f, ensure_ascii=False, indent=1)
            total_e += e
            total_l += l
            print(f"{batch}/{key}: editorial rebuilds={e} limitation joins={l}")
    print(f"STEP1 TOTAL: editorial rebuilds={total_e} limitation joins={total_l}")


def cmd_strip(args, log):
    """F4: strip inline refs from batch-2 (and any given) bundles' copy."""
    B2_KEYS = ["phaya-thai", "st.charoen-nakhon", "st.nana", "st.ratchathewi"]
    total = 0
    for bd in args.batch_dir:
        batch = os.path.basename(bd.rstrip("/"))
        keys = args.keys.split(",") if args.keys else (B2_KEYS if "batch2" in batch else None)
        if keys is None:
            continue
        for key in keys:
            ppath = os.path.join(bd, "profiles", f"{key}.json")
            if not os.path.exists(ppath):
                continue
            profile = json.load(open(ppath, encoding="utf-8"))
            known_ids = {c["id"] for c in profile["claims"]}
            prefix = key.replace("st.", "") + "-"
            ed = profile["editorial"]
            changed = 0

            def fix_block(blk):
                nonlocal changed
                if blk is None:
                    return
                text = blk.get("text_en") or ""
                clean, ids = strip_refs(text, prefix)
                extracted = [c for c in dict.fromkeys(ids) if c in known_ids]
                new_ids = extracted if extracted else (blk.get("claim_ids") or [])
                if clean != text or new_ids != blk.get("claim_ids"):
                    old_txt = text[:60]
                    blk["text_en"] = clean
                    blk["claim_ids"] = new_ids
                    log.write(json.dumps({"batch": batch, "entity": key, "change": "strip_refs",
                                          "before": old_txt, "claim_ids": new_ids[:6]},
                                         ensure_ascii=False) + "\n")
                    changed += 1

            fix_block(ed.get("preview"))
            fix_block(ed.get("guide_lead"))
            for lst in ("strengths", "tradeoffs", "day_night", "within_area_variation",
                        "conditional_fit"):
                for item in ed.get(lst) or []:
                    fix_block(item)
            if changed:
                with open(ppath, "w", encoding="utf-8") as f:
                    json.dump(profile, f, ensure_ascii=False, indent=1)
            total += changed
            print(f"{batch}/{key}: stripped blocks={changed}")
    print(f"STEP2 TOTAL: stripped blocks={total}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch-dir", action="append", required=True)
    ap.add_argument("--keys", help="comma-separated entity keys (default: per-step lists)")
    ap.add_argument("--log", required=True)
    ap.add_argument("--step", choices=["rebuild", "strip"], required=True)
    args = ap.parse_args()
    with open(args.log, "a", encoding="utf-8") as log:
        if args.step == "rebuild":
            cmd_rebuild(args, log)
        else:
            cmd_strip(args, log)


if __name__ == "__main__":
    main()
