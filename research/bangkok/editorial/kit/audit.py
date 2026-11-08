#!/usr/bin/env python3
"""Independent quality audit over assembled profile bundles (kit version).

Run with: python3 audit.py --batch-dir <batch>   (defaults to cwd)

Recomputes what assembly asserted rather than trusting it: source-ID hashing,
corroboration labels (over canonical publisher families — canonical.py,
B-10/G21), body-read reliance, date sanity, banned phrases across ALL bundle
text, radius→walk-time patterns, claim-ID prefixes, question coverage,
editorial provenance, review.checks honesty, plus the standing G20 injection/
HTML sweep, the G24 URL-scheme + AI-summary-provenance checks, and
limitations-array integrity. Findings are advisory severities (P1 = fix
before review, P2 = document or accept).
"""
import argparse
import glob
import hashlib
import json
import os
import re
import sys
from datetime import date
from urllib.parse import urlparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from canonical import canon_family  # noqa: E402

TODAY = date.today()
ISSUES = []

KINDS = {"factual_report", "reported_perception", "estimate", "researcher_inference"}
POLAR = {"strength", "tradeoff", "mixed", "neutral"}
RELS = {"inside", "partial", "outside", "unknown", "entire_unit"}
SCOPES = {"station_area", "district", "corridor", "venue", "building", "citywide", "other"}
SRCTYPES = {"official_operator", "government", "tourism_publisher", "editorial_guide",
            "expat_publication", "news", "commercial_property", "resident_report", "academic", "other"}
QA_IDS = {f"Q{i:02d}" for i in range(1, 13)}
BANNED = re.compile(r"\b(vibrant|hidden gem|something for everyone)\b", re.I)
WALKTIME = re.compile(r"\b\d+\s*[- ]?(min(ute)?s?|hour)s?\b.{0,20}\b(walk|stroll)\b|\bwalk\b.{0,30}\b\d+\s*[- ]?min", re.I)
# 2026-11-08 independent review: normalize damage that no gate caught.
PLACEHOLDER_TEXT = {"text", "text_en", "claim_ids", "texts", "claims"}
INLINE_CLAIM_REF = re.compile(r"\b[a-z0-9][a-z0-9-]*-c\d{2}\b")
APP_LOCATOR = re.compile(
    r"\b(areas\[\]|districts\[\]|confidence\.[a-z_]+|sources\.[a-z_]+|ratings\b|"
    r"facts:\s*park_ha|rent_1br|rent_2br|app[- ]data)\b", re.I)

# G20 — injection/HTML sweep over user-facing text.
INJ_HTML = re.compile(r"<[a-zA-Z][a-zA-Z0-9]*[^>]*>")
INJ_MD_LINK = re.compile(r"\[[^\]\n]{1,80}\]\(https?://[^)\n]{1,200}\)")
INJ_TEMPLATE = re.compile(r"\{\{|\$\{")
INJ_PHRASES = re.compile(
    r"ignore (all |any )?(previous|prior|above) (instructions|rules|prompts?)"
    r"|disregard (all |any )?(previous|prior|above)"
    r"|system prompt"
    r"|you are an? (AI|assistant|language model)"
    r"|act as an? (AI|assistant)"
    r"|prompt injection|jailbreak"
    r"|instructions?:\s*(you must|do not|never|always)", re.I)
# G24 — AI-summary provenance markers (F-2 bans them in future bundles).
AI_SUMMARY = re.compile(
    r"ai[- ]?(summary|overview|generated|answer)|search summary|web search ai", re.I)

def injection_scan(text):
    """Return [(gate, match)] for structural (P1-grade) and phrase (P2-grade) hits."""
    hits = []
    for pat, gate in ((INJ_HTML, "G20-html"), (INJ_MD_LINK, "G20-md-link"),
                      (INJ_TEMPLATE, "G20-template")):
        m = pat.search(text)
        if m:
            hits.append((gate, m.group(0)[:60]))
    m = INJ_PHRASES.search(text)
    if m:
        hits.append(("G20-phrase", m.group(0)[:60]))
    return hits

def note(sev, entity, msg):
    ISSUES.append((sev, entity, msg))
    print(f"[{sev}] {entity}: {msg}")

def sha12(url):
    return "src_" + hashlib.sha256(url.encode("utf-8")).hexdigest()[:12]

def all_text(node):
    if isinstance(node, str):
        yield node
    elif isinstance(node, dict):
        for v in node.values():
            yield from all_text(v)
    elif isinstance(node, list):
        for v in node:
            yield from all_text(v)

def audit_bundle(path):
    b = json.load(open(path, encoding="utf-8"))
    ent = b["entity"]["key"]
    short = os.path.basename(path)
    data_only = any("data-only" in str(n).lower() for n in (b.get("review") or {}).get("notes", []))
    if data_only:
        # Data-only placeholders: identity is the only meaningful check; editorial/claims are by design empty.
        ok_identity = isinstance(b.get("entity"), dict) and b["entity"].get("key") and b["entity"].get("name_en")
        srcs = b.get("sources") or []
        no_web = (not b.get("claims")) and (not srcs or all(not s.get("body_read") for s in srcs))
        if ok_identity and no_web:
            print(f"[OK-data-only] {short}: identity verified, no web claims (tier C placeholder)")
            return
        note("P1", short, "data-only bundle carries web claims or broken identity — regenerate")
        return

    for s in b["sources"]:
        if s["id"] != sha12(s["canonical_url"]):
            note("P1", short, f"source id mismatch for {s['canonical_url']}")
        if s["type"] not in SRCTYPES:
            note("P1", short, f"bad source type {s['type']} on {s['id']}")
        m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", s.get("published_at") or "")
        if m and date(int(m.group(1)), int(m.group(2)), int(m.group(3))) > TODAY:
            note("P1", short, f"future published_at {s['published_at']} on {s['id']}")
        # 2026-11-08: the normalize bug also hit SOURCE limitations; the earlier
        # repair and rule only covered claim arrays (all-single-char case).
        slim = s.get("limitations") or []
        single = sum(1 for x in slim if isinstance(x, str) and len(x) <= 1)
        if single >= 10:
            note("P1", short, f"source {s['id']}: limitations array exploded "
                              f"({single}/{len(slim)} single-character entries)")
        # G24 — URL scheme + AI-summary provenance
        scheme = urlparse(s["canonical_url"]).scheme.lower()
        if scheme == "http":
            note("P2", short, f"G24: plain http:// citation {s['id']} — upgrade or drop")
        elif scheme not in ("https",):
            note("P1", short, f"G24: non-http(s) canonical URL on {s['id']}: {s['canonical_url'][:60]}")
        probe = " ".join(str(s.get(k) or "") for k in ("publisher", "publisher_family", "title"))
        if AI_SUMMARY.search(probe):
            note("P2", short, f"G24/F-2: AI-summary provenance on {s['id']} — banned in future bundles")

    urls = [s["canonical_url"] for s in b["sources"]]
    if len(urls) != len(set(urls)):
        note("P1", short, "duplicate canonical URLs within bundle")

    cids = set()
    provenance_bad = False
    for c in b["claims"]:
        cid = c["id"]
        cids.add(cid)
        expect = re.sub(r"[^a-z-]", "", ent.replace("st.", "")) + "-c"
        if not cid.startswith(expect):
            note("P2", short, f"claim id {cid} does not use entity prefix {expect}…")
        if c["kind"] not in KINDS:
            note("P1", short, f"{cid}: bad kind {c['kind']}")
        if c["polarity"] not in POLAR:
            note("P1", short, f"{cid}: bad polarity {c['polarity']}")
        g = c["geography"]
        if g["scope"] not in SCOPES or g["relation_to_entity"] not in RELS:
            note("P1", short, f"{cid}: bad geography {g['scope']}/{g['relation_to_entity']}")
        if not c["evidence"]:
            note("P1", short, f"{cid}: no evidence")
        for e in c["evidence"]:
            src = next((s for s in b["sources"] if s["id"] == e["source_id"]), None)
            if src is None:
                note("P1", short, f"{cid}: evidence points to missing source {e['source_id']}")
            elif not src["body_read"]:
                note("P2", short, f"{cid}: evidence uses body_read=false source {e['source_id']}")
            # 2026-11-08: app-data locators must not be attached to a web source.
            if APP_LOCATOR.search(e.get("locator") or ""):
                note("P1", short, f"{cid}: app-data locator on web source "
                                  f"{e['source_id']} — provenance mismatch")
                provenance_bad = True
        fams = {canon_family(s["publisher_family"]) for s in b["sources"]
                if s["id"] in {e["source_id"] for e in c["evidence"]}}
        expected = "corroborated" if len(fams) >= 2 else "proposed"
        if c["review_status"] not in (expected, "conflicted", "rejected", "approved"):
            note("P1", short, f"{cid}: review_status {c['review_status']} but canonical corroboration implies {expected}")
        if c["review_status"] == "corroborated" and len(fams) < 2:
            note("P1", short, f"{cid}: marked corroborated with only {len(fams)} canonical family(ies)")
        txt = " ".join([c["text_en"], *c["limitations"]])
        if BANNED.search(txt):
            note("P1", short, f"{cid}: banned phrase in claim text")
        for link in c.get("conflicts_with") or []:
            if link == cid:
                note("P1", short, f"{cid}: conflicts_with self-reference")
            elif link not in cids:
                note("P1", short, f"{cid}: conflicts_with dangling link {link}")
        lims = c.get("limitations") or []
        single = sum(1 for x in lims if isinstance(x, str) and len(x) <= 1)
        if single >= 10:
            note("P1", short, f"{cid}: limitations array exploded "
                              f"({single}/{len(lims)} single-character entries)")

    qmap = {q["id"]: q for q in b["question_answers"]}
    if set(qmap) != QA_IDS:
        note("P1", short, f"question set mismatch: {set(qmap) ^ QA_IDS}")
    for qid, q in qmap.items():
        if q["status"] in ("answered", "conflicting") and not q["claim_ids"]:
            note("P1", short, f"{qid}: {q['status']} but no claim refs")
        for cid in q["claim_ids"]:
            if cid not in cids:
                note("P1", short, f"{qid}: dangling claim ref {cid}")

    ed = b["editorial"]
    # G20 — injection/HTML sweep over all user-facing text
    user_text = []
    for blk in (ed["preview"], ed["guide_lead"]):
        if blk:
            user_text.append(blk["text_en"])
    for lst in ("strengths", "tradeoffs", "day_night", "within_area_variation",
                "conditional_fit", "uncertainties"):
        for item in ed.get(lst) or []:
            # uncertainties entries are strings (batches 1-2) or {text|text_en} dicts (batch 3)
            user_text.append((item.get("text_en") or item.get("text") or "")
                             if isinstance(item, dict) else str(item))
    for c in b["claims"]:
        user_text.append(c["text_en"])
        user_text.extend(c.get("limitations") or [])
    for q in b["question_answers"]:
        user_text.append(q.get("notes") or "")
    for t in user_text:
        for gate, frag in injection_scan(t or ""):
            sev = "P2" if gate == "G20-phrase" else "P1"
            note(sev, short, f"{gate}: {frag!r} in user-facing text")
    copy_bad = False
    for blk in ("preview", "guide_lead"):
        if ed[blk] is None:
            note("P1", short, f"{blk} is null — required card/lead copy missing")
            copy_bad = True
            continue
        if BANNED.search(ed[blk]["text_en"]):
            note("P1", short, f"{blk}: banned phrase")
            copy_bad = True
        if not ed[blk]["claim_ids"]:
            note("P1", short, f"{blk}: no claim provenance")
        t = (ed[blk].get("text_en") or "").strip()
        if t.lower() in PLACEHOLDER_TEXT:
            note("P1", short, f"{blk}: placeholder text {t!r} (normalize damage)")
            copy_bad = True
        if INLINE_CLAIM_REF.search(t):
            note("P1", short, f"{blk}: inline claim reference in user-facing copy")
            copy_bad = True
    for lst in ("strengths", "tradeoffs", "day_night", "within_area_variation", "conditional_fit"):
        if not ed[lst]:
            note("P2", short, f"editorial.{lst} empty")
        for i, it in enumerate(ed[lst]):
            if BANNED.search(it["text_en"]):
                note("P1", short, f"{lst}[{i}]: banned phrase")
                copy_bad = True
            if not it["claim_ids"]:
                note("P1", short, f"{lst}[{i}]: no claim provenance")
            for cid in it["claim_ids"]:
                if cid not in cids:
                    note("P1", short, f"{lst}[{i}]: dangling claim ref {cid}")
            t = (it.get("text_en") or "").strip()
            if t.lower() in PLACEHOLDER_TEXT:
                note("P1", short, f"{lst}[{i}]: placeholder text {t!r} (normalize damage)")
                copy_bad = True
            if INLINE_CLAIM_REF.search(t):
                note("P1", short, f"{lst}[{i}]: inline claim reference in user-facing copy")
                copy_bad = True
    unc = ed.get("uncertainties") or []
    unc_text = [(x.get("text_en") or x.get("text") or "") if isinstance(x, dict) else str(x)
                for x in unc]
    if any(v.strip().lower() in PLACEHOLDER_TEXT for v in unc_text):
        note("P1", short, "editorial.uncertainties contains placeholder text (normalize damage)")
        copy_bad = True
    if len(unc_text) > 3 and all(len(v) <= 1 for v in unc_text):
        note("P1", short, f"editorial.uncertainties exploded into {len(unc_text)} characters (normalize damage)")
        copy_bad = True

    for t in all_text(b["editorial"]):
        if WALKTIME.search(t):
            note("P2", short, f"possible radius->time conversion in editorial: …{WALKTIME.search(t).group(0)}…")

    src_by_id = {s["id"]: s for s in b["sources"]}
    unsupported = [c["id"] for c in b["claims"]
                   if not any(src_by_id.get(e["source_id"], {}).get("body_read") for e in c["evidence"])]
    if unsupported and b["review"]["checks"]["sources"] == "pass":
        note("P1", short, f"review.checks.sources=pass but unsupported claims: {unsupported}")
    if unsupported and b["review"]["checks"]["claim_support"] == "pass":
        note("P1", short, "review.checks.claim_support=pass despite unsupported claims")
    if provenance_bad and b["review"]["checks"].get("claim_support") == "pass":
        note("P1", short, "review.checks.claim_support=pass despite provenance mismatches")
    if copy_bad and b["review"]["checks"].get("copy") == "pass":
        note("P1", short, "review.checks.copy=pass despite copy defects")

    # 2026-11-08 independent review: sign-off consistency (replaces the old
    # "reviewer set -> P1" rule, which made a completed review fail the gate).
    rv = b["review"]
    status = rv.get("status")
    reviewer = rv.get("reviewer")
    reviewed_at = rv.get("reviewed_at")
    nonpass = [k for k, v in (rv.get("checks") or {}).items()
               if v not in ("pass", "not_applicable")]
    if status == "approved":
        if not reviewer:
            note("P1", short, "approved without a reviewer")
        if not reviewed_at:
            note("P1", short, "approved without reviewed_at")
        if nonpass:
            note("P1", short, f"approved with non-pass checks: {nonpass}")
    elif status == "blocked":
        if not reviewer:
            note("P2", short, "blocked bundle has no reviewer recorded")
    elif status != "ready_for_review":
        note("P2", short, f"review.status={status}")
    if reviewer and status == "ready_for_review":
        note("P2", short, "reviewer set but review.status is still ready_for_review")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch-dir", default=os.getcwd())
    args = ap.parse_args()
    for path in sorted(glob.glob(os.path.join(args.batch_dir, "profiles", "*.json"))):
        audit_bundle(path)
    print()
    counts = {}
    for sev, _e, _m in ISSUES:
        counts[sev] = counts.get(sev, 0) + 1
    print(f"AUDIT COMPLETE: {len(ISSUES)} findings — {counts or 'none'}")

if __name__ == "__main__":
    main()
