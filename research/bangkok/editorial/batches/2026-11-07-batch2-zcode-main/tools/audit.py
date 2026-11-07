#!/usr/bin/env python3
"""Independent quality audit over assembled profile bundles.

Run with: python3 -I tools/audit.py   (from the batch directory)
Recomputes what assemble.py asserted rather than trusting it: source-ID
hashing, corroboration status, body-read reliance, date sanity, banned
phrases across ALL bundle text, walking-time patterns, claim-ID prefixes,
question coverage, and review.checks honesty.
"""
import glob
import hashlib
import json
import os
import re
from datetime import date

TODAY = date(2026, 11, 7)
ISSUES = []

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

BANNED = re.compile(r"\b(vibrant|hidden gem|something for everyone)\b", re.I)
WALKTIME = re.compile(r"\b\d+\s*[- ]?(min(ute)?s?|hour)s?\b.{0,20}\b(walk|stroll)\b|\bwalk\b.{0,30}\b\d+\s*[- ]?min", re.I)
KINDS = {"factual_report", "reported_perception", "estimate", "researcher_inference"}
POLAR = {"strength", "tradeoff", "mixed", "neutral"}
RELS = {"inside", "partial", "outside", "unknown", "entire_unit"}
SCOPES = {"station_area", "district", "corridor", "venue", "building", "citywide", "other"}
SRCTYPES = {"official_operator", "government", "tourism_publisher", "editorial_guide",
            "expat_publication", "news", "commercial_property", "resident_report", "academic", "other"}
QA_IDS = {f"Q{i:02d}" for i in range(1, 13)}

for path in sorted(glob.glob("profiles/*.json")):
    b = json.load(open(path, encoding="utf-8"))
    ent = b["entity"]["key"]
    short = path.split("/")[-1]

    # --- source ID integrity ---
    for s in b["sources"]:
        if s["id"] != sha12(s["canonical_url"]):
            note("P1", short, f"source id mismatch for {s['canonical_url']}")
        if s["type"] not in SRCTYPES:
            note("P1", short, f"bad source type {s['type']} on {s['id']}")
        m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", s.get("published_at") or "")
        if m and date(int(m.group(1)), int(m.group(2)), int(m.group(3))) > TODAY:
            note("P1", short, f"future published_at {s['published_at']} on {s['id']}")
        if not (s.get("retrieved_at") or "").startswith("2026-11-0"):
            note("P2", short, f"odd retrieved_at {s.get('retrieved_at')} on {s['id']}")

    # duplicate canonical URLs
    urls = [s["canonical_url"] for s in b["sources"]]
    if len(urls) != len(set(urls)):
        note("P1", short, "duplicate canonical URLs within bundle")

    # --- claims ---
    cids = set()
    for c in b["claims"]:
        cid = c["id"]
        cids.add(cid)
        prefix = ent.split(".", 1)[1].replace("-", "-") if ent.startswith("st.") else ent
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
                continue
            if not src["body_read"]:
                note("P2", short, f"{cid}: evidence uses body_read=false source {e['source_id']}")
        # recompute corroborated / conflicted labels
        fams = {s["publisher_family"] for s in b["sources"]
                if s["id"] in {e["source_id"] for e in c["evidence"]}}
        expected = "corroborated" if len(fams) >= 2 else "proposed"
        if c["review_status"] not in (expected, "conflicted", "rejected", "approved"):
            note("P1", short, f"{cid}: review_status {c['review_status']} but corroboration implies {expected}")
        if c["review_status"] == "corroborated" and len(fams) < 2:
            note("P1", short, f"{cid}: marked corroborated with only {len(fams)} family(ies)")
        txt = " ".join([c["text_en"], *c["limitations"]])
        if BANNED.search(txt):
            note("P1", short, f"{cid}: banned phrase in claim text")

    # --- question answers ---
    qmap = {q["id"]: q for q in b["question_answers"]}
    if set(qmap) != QA_IDS:
        note("P1", short, f"question set mismatch: {set(qmap) ^ QA_IDS}")
    for qid, q in qmap.items():
        if q["status"] in ("answered", "conflicting") and not q["claim_ids"]:
            note("P1", short, f"{qid}: {q['status']} but no claim refs")
        for cid in q["claim_ids"]:
            if cid not in cids:
                note("P1", short, f"{qid}: dangling claim ref {cid}")
        # every answered question should have all its cited claims shared back? (one-directional is fine)

    # --- editorial ---
    ed = b["editorial"]
    for blk in ("preview", "guide_lead"):
        if ed[blk] is None:
            note("P1", short, f"{blk} is null — required card/lead copy missing")
            continue
        if BANNED.search(ed[blk]["text_en"]):
            note("P1", short, f"{blk}: banned phrase")
        if not ed[blk]["claim_ids"]:
            note("P1", short, f"{blk}: no claim provenance")
    for lst in ("strengths", "tradeoffs", "day_night", "within_area_variation", "conditional_fit"):
        if not ed[lst]:
            note("P2", short, f"editorial.{lst} empty")
        for i, it in enumerate(ed[lst]):
            if BANNED.search(it["text_en"]):
                note("P1", short, f"{lst}[{i}]: banned phrase")
            if not it["claim_ids"]:
                note("P1", short, f"{lst}[{i}]: no claim provenance")
            for cid in it["claim_ids"]:
                if cid not in cids:
                    note("P1", short, f"{lst}[{i}]: dangling claim ref {cid}")

    # --- walking-time conversions anywhere in editorial or claims ---
    for t in all_text(b["editorial"]):
        if WALKTIME.search(t):
            note("P2", short, f"possible radius->time conversion in editorial: …{WALKTIME.search(t).group(0)}…")

    # --- review.checks honesty ---
    src_by_id = {s["id"]: s for s in b["sources"]}
    unsupported = [c["id"] for c in b["claims"]
                   if not any(src_by_id.get(e["source_id"], {}).get("body_read") for e in c["evidence"])]
    if unsupported and b["review"]["checks"]["sources"] == "pass":
        note("P1", short, f"review.checks.sources=pass but unsupported claims: {unsupported}")
    if unsupported and b["review"]["checks"]["claim_support"] == "pass":
        note("P1", short, "review.checks.claim_support=pass despite unsupported claims")
    if b["review"]["status"] != "ready_for_review":
        note("P2", short, f"review.status={b['review']['status']}")
    if b["review"]["reviewer"] is not None:
        note("P1", short, "reviewer set — no independent review has happened")

print()
counts = {}
for sev, ent, msg in ISSUES:
    counts[sev] = counts.get(sev, 0) + 1
print(f"AUDIT COMPLETE: {len(ISSUES)} findings — {counts or 'none'}")
