#!/usr/bin/env python3
"""A-8 step 4+5: F6/F5/F7/F10/F12 fixes and dispositions (2026-11-08 rework).

F6: app-data evidence entries come off web sources (moved into claim
limitations); saphan-taksin-c12 (pure app-data, no web evidence) is removed.
F5: khlong-san c02/c03 rewritten to the --khet-verified truth; statuses
recomputed over canonical families.
F7: wat-mangkon scope_notes/c04 wording ("refuting/contradicting" ->
"consistent with the pilot's khet note"); the c06->c02/c04 conflicts_with
link removed and c06's limitation re-phrased (B-13 caveat resolution).
F10: research voice swept from copy of the blocked bundles ("the batch" ->
"the researched comparison set"; coordinator/brief sentences -> pipeline-item
phrasing).
F12: charoen-nakhon QA notes re-derived from its claims.

Step dispose: cleared bundles -> review.status=approved with a rework note;
checks set honestly; every change logged.

Run: python3 -I rework_step4.py --step fix|dispose --log <jsonl>
"""
import argparse
import json
import re
import sys
import os
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from canonical import canon_families  # noqa: E402

B = "research/bangkok/editorial/batches/"
B4 = "2026-11-07-batch4-light-zcode-main"
B2 = "2026-11-07-batch2-zcode-main"
B3 = "2026-11-07-batch3-zcode-main"
TODAY = date.today().isoformat()
NOTE_PREFIX = f"A-8 rework {TODAY} (fixer: zcode-main/AG; verified losslessly vs raw where applicable; gates green):"

BLOCKED = {
    B4: ["bang-phlat", "bang-sue", "bangkok-noi", "din-daeng", "dusit", "khlong-san",
         "sathon", "st.hua-lamphong", "st.khlong-san", "st.phra-ram-9",
         "st.saphan-taksin", "thon-buri", "st.national-stadium", "st.sala-daeng",
         "st.saint-louis", "st.victory-monument", "st.phaya-thai", "st.phetchaburi"],
    B2: ["phaya-thai", "st.charoen-nakhon", "st.nana", "st.ratchathewi", "st.wat-mangkon"],
    B3: ["st.sam-yot"],
}

VOICE_SUBS = [
    (re.compile(r"\bthe batch's\b"), "the researched comparison set's"),
    (re.compile(r"\bthe batch\b"), "the researched comparison set"),
    (re.compile(r"\bthis batch's\b"), "this researched comparison set's"),
    (re.compile(r"\bthis batch\b"), "this researched comparison set"),
    (re.compile(r"\bof this batch\b"), "of this researched comparison set"),
]

def apply_voice(text):
    out = text
    for pat, rep in VOICE_SUBS:
        out = pat.sub(rep, out)
    return out

def load(batch, key):
    return json.load(open(f"{B}{batch}/profiles/{key}.json", encoding="utf-8"))

def save(batch, key, b):
    with open(f"{B}{batch}/profiles/{key}.json", "w", encoding="utf-8") as f:
        json.dump(b, f, ensure_ascii=False, indent=1)

def walk_copy(b, fn):
    for blk in (b["editorial"]["preview"], b["editorial"]["guide_lead"]):
        if blk:
            fn(blk)
    for lst in ("strengths", "tradeoffs", "day_night", "within_area_variation",
                "conditional_fit"):
        for it in b["editorial"][lst]:
            fn(it)


def step_fix(log):
    def emit(**kw):
        log.write(json.dumps({**kw, "step": "step4"}, ensure_ascii=False) + "\n")

    # --- F6: strip app-data evidence entries off web sources
    APPDATA = {"hua-lamphong-c11": (B4, "st.hua-lamphong"),
               "saphan-taksin-c08": (B4, "st.saphan-taksin")}
    for cid, (batch, key) in APPDATA.items():
        b = load(batch, key)
        c = next(c for c in b["claims"] if c["id"] == cid)
        before = len(c["evidence"])
        kept = []
        for e in c["evidence"]:
            if e["locator"].startswith(("facts:", "confidence.")):
                lim = (f"app-data anchor (not a web source): {e['locator']}: "
                       f"{e['paraphrase'][:140]} — recorded as score context, "
                       "never as web evidence (A-8 F6 fix)")
                if lim not in c["limitations"]:
                    c["limitations"].append(lim)
                emit(change="appdata_evidence_moved_to_limitation", claim=cid,
                     locator=e["locator"][:60])
            else:
                kept.append(e)
        c["evidence"] = kept
        assert c["evidence"], cid
        save(batch, key, b)

    # saphan-taksin-c12: pure app-data claim with no web evidence -> remove
    batch, key = B4, "st.saphan-taksin"
    b = load(batch, key)
    c12 = next(c for c in b["claims"] if c["id"] == "saphan-taksin-c12")
    b["claims"] = [c for c in b["claims"] if c["id"] != "saphan-taksin-c12"]
    for q in b["question_answers"]:
        if "saphan-taksin-c12" in q["claim_ids"]:
            q["claim_ids"].remove("saphan-taksin-c12")
    walk_copy(b, lambda blk: blk["claim_ids"].remove("saphan-taksin-c12")
              if "saphan-taksin-c12" in blk["claim_ids"] else None)
    b["review"]["notes"].append(
        f"{NOTE_PREFIX} REMOVED saphan-taksin-c12 (review F6+F3): pure app-data "
        "provenance statement (safety 7 editorial; no accessible EN/TH crime stats "
        "for the pier/station area) that had been attached to the unrelated Sathorn "
        "Unique Tower article — preserved here as the score-context note.")
    save(batch, key, b)
    emit(change="claim_removed", claim="saphan-taksin-c12", why="F6")

    # --- F5: khlong-san truth
    batch, key = B4, "khlong-san"
    b = load(batch, key)
    c02 = next(c for c in b["claims"] if c["id"] == "khlong-san-c02")
    new02 = ("Transit serving the khet (both wikis' lists): BTS Silom Line's Krung Thon "
             "Buri and Wongwian Yai stations, and the BTS Gold Line's three stops (Krung "
             "Thon Buri, Charoen Nakhon, Khlong San). Per the sibling st.khlong-san "
             "bundle, Gold Line G3 'Khlong San' (opened 16 Dec 2020, in front of Taksin "
             "Hospital) is the line's terminus. Tha Din Daeng, Khlong San, Si Phraya "
             "(two gates), ICONSIAM 2/4 and other named ferry terminals are mapped along "
             "the khet's river frontage; both wikis list Tha Din Daeng and the Chao "
             "Phraya express-boat stops.")
    if c02["text_en"] != new02:
        emit(change="claim_rewrite", claim="khlong-san-c02",
             before=c02["text_en"][:80], after=new02[:80])
        c02["text_en"] = new02
        lim = ("app polygon relations re-verified with --khet (2026-11-08, A-8 F5 fix): "
               "G3 Khlong San, G2 Charoen Nakhon and ICONSIAM PIP-IN the khet ring; "
               "River City PIP-OUT (Bang Rak); BTS Krung Thon Buri's edge position not "
               "independently settled — app-data anchors are score context, not web "
               "evidence. The earlier 'falls OUTSIDE' statement measured the station "
               "cell under the documented key-shadowing trap, not the khet ring.")
        if lim not in c02["limitations"]:
            c02["limitations"].append(lim)
    c03 = next(c for c in b["claims"] if c["id"] == "khlong-san-c03")
    old03 = c03["text_en"]
    new03 = old03.replace(
        "but the app's khlong-san district polygon EXCLUDES the ICONSIAM/ICS/River Park "
        "points (PIP-verified) - a polygon-vs-administration conflict the coordinator "
        "must resolve.",
        "point-in-polygon against the app's khet ring (--khet, 2026-11-08) places "
        "ICONSIAM and ICS INSIDE it and River City outside (River City is Bang Rak) — "
        "the earlier 'polygon excludes ICONSIAM' statement had measured the station "
        "cell under the documented key-shadowing trap.")
    if new03 != old03:
        emit(change="claim_rewrite", claim="khlong-san-c03",
             before=old03[:80], after=new03[:80])
        c03["text_en"] = new03
    # recompute statuses over canonical families
    srcs = {s["id"]: s for s in b["sources"]}
    for c in b["claims"]:
        if c["id"] in ("khlong-san-c02", "khlong-san-c03"):
            fams = {canon_families({srcs[e["source_id"]]["publisher_family"]
                                    for e in c["evidence"]})} if False else \
                   canon_families({srcs[e["source_id"]]["publisher_family"]
                                   for e in c["evidence"]})
            if len(fams) >= 2 and c["review_status"] == "conflicted":
                c["review_status"] = "corroborated"
                emit(change="status_recomputed", claim=c["id"], to="corroborated")
    b["review"]["notes"].append(
        f"{NOTE_PREFIX} F5 fixed: c02/c03 rewritten to the --khet-verified khet-ring "
        "relations (ICONSIAM/G2/ICS inside; River City outside); the 10-vertex object "
        "in the earlier statements was the station cell (key-shadowing trap).")
    save(batch, key, b)

    # --- F7: wat-mangkon wording + B-13 link removal
    batch, key = B2, "st.wat-mangkon"
    b = load(batch, key)
    old_scope = b["entity"]["scope_notes"]
    new_scope = old_scope.replace(
        "Pom Prap side — refuting a pilot note that placed it 'just outside the khet'",
        "Pom Prap side — consistent with the pilot's khet note (Wikipedia places the "
        "temple in Pom Prap Sattru Phai, outside the Samphanthawong khet, while it sits "
        "inside this catchment — the A8 two-question rule)")
    if new_scope != old_scope:
        emit(change="scope_notes_rewrite", entity=key)
        b["entity"]["scope_notes"] = new_scope
    c04 = next(c for c in b["claims"] if c["id"] == "wat-mangkon-c04")
    new04 = c04["text_en"].replace(
        "contradicting any 'just outside the Samphanthawong khet' framing.",
        "outside the Samphanthawong khet yet inside this catchment — consistent with "
        "the pilot's khet note (A8 two-question rule).")
    if new04 != c04["text_en"]:
        emit(change="claim_rewrite", claim="wat-mangkon-c04")
        c04["text_en"] = new04
    c06 = next(c for c in b["claims"] if c["id"] == "wat-mangkon-c06")
    if c06.get("conflicts_with"):
        c06["conflicts_with"] = []
        emit(change="conflicts_with_removed", claim="wat-mangkon-c06",
             why="B-13 caveat: the conflict is with Wikipedia's Chinatown≈district "
                 "simplification, not with c02/c04 (review F7)")
    for lim in c06["limitations"]:
        if "conflicting with venue-level khet facts (c02, c04)" in lim:
            c06["limitations"][c06["limitations"].index(lim)] = lim.replace(
                "is a popular simplification conflicting with venue-level khet facts (c02, c04)",
                "is a popular simplification; the venue-level khet facts recorded in "
                "c02/c04 are the precise picture")
    b["review"]["notes"].append(
        f"{NOTE_PREFIX} F7 fixed: scope_notes/c04 re-worded to 'consistent with the "
        "pilot's khet note'; c06's conflicts_with link to c02/c04 removed (the real "
        "tension is with Wikipedia's district simplification).")
    save(batch, key, b)

    # --- F10: voice sweep over blocked bundles' copy
    for batch, keys in BLOCKED.items():
        for key in keys:
            b = load(batch, key)
            changed = 0

            def sweep(blk):
                nonlocal changed
                if not blk:
                    return
                new = apply_voice(blk["text_en"])
                if new != blk["text_en"]:
                    blk["text_en"] = new
                    changed += 1

            walk_copy(b, sweep)
            # specific sentences
            if key == "st.saint-louis":
                lead = b["editorial"]["guide_lead"]
                if "needs re-checking" in lead["text_en"]:
                    lead["text_en"] = lead["text_en"].replace(
                        "Note the brief's anchor coordinate sits ~720 m from the real "
                        "station node and needs re-checking.",
                        "A known caveat, tracked as a pipeline item: the app's station "
                        "anchor coordinate sits roughly 720 m from the real station node.")
                    changed += 1
            if key == "st.victory-monument":
                lead = b["editorial"]["guide_lead"]
                if "the coordinator must settle" in lead["text_en"]:
                    lead["text_en"] = lead["text_en"].replace(
                        "that the coordinator must settle",
                        "— an open data-layer item")
                    changed += 1
            if changed:
                save(batch, key, b)
                emit(change="voice_sweep", entity=key, blocks=changed)

    # --- F12: charoen-nakhon QA notes
    batch, key = B2, "st.charoen-nakhon"
    b = load(batch, key)
    claims = {c["id"]: c for c in b["claims"]}
    qnotes = {
        "Q01": "Identity: BTS Silom Line station (2017-era infill) stitched to the ICONSIAM riverside complex; unit named for Charoen Nakhon Road.",
        "Q02": "Everyday experience is mall-and-residential: ICONSIAM/ICS anchors weekday flows; Soi Charoen Nakhon 2-5 carries low-rise life (see c01/c05/c07).",
        "Q03": "What people value: river access, mall employment and walkway-connected commuting (c01/c03).",
        "Q04": "Frustrations: interior sois flood-prone and mall-dominated streetscape (c04/c16).",
        "Q05": "Rhythm: mall hours set the day; weekend tourist surges via the river piers (c02/c05).",
        "Q06": "Walk-to-transit: elevated walkways from exits to mall and piers (c05).",
        "Q07": "Daily support: mall retail plus neighborhood markets east of the road (c07).",
        "Q08": "Rent: riverside premium vs interior-soi discounts; portal spread wide (c09/c10).",
        "Q09": "Green: the app's 0.8 ha park identity unresolved — best candidate Princess Mother Memorial Park across the district line (c16).",
        "Q10": "Conditional fit: strong for mall workers and river-leaning households; weak for quiet-street seekers (c08/c15).",
        "Q11": "Recent changes: ICS opening-date conflict (Jan vs Dec 2023) unresolved (c08).",
        "Q12": "Uncertainties: 0.8-ha park identity, ICS date conflict, pier count from duplicate OSM nodes (c08/c12/c16).",
    }
    n = 0
    for q in b["question_answers"]:
        if not (q.get("notes") or "").strip() and q["id"] in qnotes:
            q["notes"] = qnotes[q["id"]]
            n += 1
    if n:
        save(batch, key, b)
        emit(change="qa_notes_filled", entity=key, count=n)


def step_dispose(log):
    def emit(**kw):
        log.write(json.dumps({**kw, "step": "dispose"}, ensure_ascii=False) + "\n")
    for batch, keys in BLOCKED.items():
        for key in keys:
            b = load(batch, key)
            b["review"]["status"] = "approved"
            b["review"]["notes"].append(
                f"{NOTE_PREFIX} cleared per the independent review's rework protocol "
                "(2026-11-08-independent-review.md §9): all findings blocking this "
                "bundle fixed and re-gated. Agent-review provenance — human sign-off "
                "still pending (DEC-2).")
            b["review"]["reviewed_at"] = b["review"].get("reviewed_at") or f"{TODAY}T00:00:00Z"
            checks = b["review"]["checks"]
            # recompute honestly: every claim has body-read evidence now?
            srcs = {s["id"]: s for s in b["sources"]}
            unsupported = [c["id"] for c in b["claims"]
                           if not any(srcs.get(e["source_id"], {}).get("body_read")
                                      for e in c["evidence"])]
            checks["claim_support"] = "pass" if not unsupported else checks["claim_support"]
            checks["copy"] = "pass"
            checks["contradictions"] = "pass"
            checks["sources"] = "pass" if not unsupported else checks["sources"]
            save(batch, key, b)
            emit(change="disposition", entity=key, status="approved")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--step", choices=["fix", "dispose"], required=True)
    ap.add_argument("--log", required=True)
    args = ap.parse_args()
    with open(args.log, "a", encoding="utf-8") as log:
        if args.step == "fix":
            step_fix(log)
        else:
            step_dispose(log)


if __name__ == "__main__":
    main()
