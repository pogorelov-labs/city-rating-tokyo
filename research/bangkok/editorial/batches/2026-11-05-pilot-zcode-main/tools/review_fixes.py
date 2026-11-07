#!/usr/bin/env python3
"""Apply confirmed quality-review fixes to the assembled bundles (2026-11-07).

Every replacement is assertion-guarded: the script fails loudly if an expected
source string is missing, so no fix is silently skipped.
"""
import json

BASE = "/Users/ruslan/msc_1/git/city-rating/research/bangkok/editorial/batches/2026-11-05-pilot-zcode-main"

def load(key):
    return json.load(open(f"{BASE}/profiles/{key}.json", encoding="utf-8"))

def save(key, b):
    with open(f"{BASE}/profiles/{key}.json", "w", encoding="utf-8") as f:
        json.dump(b, f, ensure_ascii=False, indent=1)

def replace_exact(obj_path_fn, old, new, label):
    """obj_path_fn(bundle) -> mutable container holding the string; hard-fail if old not present."""
    b = load(label[0])
    container = obj_path_fn(b)
    text = label[2] if False else None
    if old not in container:
        raise AssertionError(f"expected string not found for {label}: {old[:60]}…")
    return b, container, old, new

# ---------- st.chong-nonsi ----------
b = load("st.chong-nonsi")

# 1) claim c03: corrected two-layer framing (raw circle vs app nearest-stop catchment)
c03 = next(c for c in b["claims"] if c["id"] == "chong-nonsi-c03")
old_text = c03["text_en"]
assert "inside the 800 m circle" in old_text and "reaches into the catchment" in old_text
c03["text_en"] = (
    "Sala Daeng BTS station lies about 730 m and Wikipedia's Patpong block geotag about 657 m from "
    "Chong Nonsi station by straight-line — within a bare 800 m radius of the stop — but both fall "
    "outside the app's mapped st.chong-nonsi catchment, which ends at the nearest-stop boundary with "
    "the separately rated st.sala-daeng area; the app's nightlife 10 therefore does not rest on "
    "Patpong membership."
)
c03["geography"]["scope"] = "corridor"
c03["geography"]["place_name"] = "Silom / Sala Daeng / Patpong entertainment cluster"
c03["geography"]["relation_to_entity"] = "outside"
c03["geography"]["notes"] = (
    "Wikipedia coordinates: Sala Daeng BTS 13.7285083,100.5341333 (~730 m from the stop); "
    "Patpong 13.72833,100.53333 (~657 m). Point-in-polygon against the app's own "
    "station-geometry.json polygon (checked 2026-11-07): both outside; st.sala-daeng is itself "
    "a rated area and takes the Silom/Patpong block in the nearest-stop model."
)
c03["limitations"].append(
    "Corrected in the 2026-11-07 quality review: the original text said the fringe 'reaches into "
    "the catchment'; the app's nearest-stop model excludes it (verified against the app polygon). "
    "Bare-radius distances retained because a plain reading of '800 m circle' would suggest inclusion."
)
c03["review_status"] = "conflicted"  # conflicts with the original claim; correction documented

# 2) editorial within_area_variation[1]
wv1 = b["editorial"]["within_area_variation"][1]
old_wv = "The northern fringe behaves differently from the rest: around 660–740 m out, Sala Daeng and the southern edge of the Patpong/Silom entertainment streets fall inside the geometric circle, putting late-opening bars and tourist foot traffic at the unit's boundary rather than in its center."
assert old_wv in wv1["text_en"]
wv1["text_en"] = (
    "The northern edge differs from the rest: Sala Daeng BTS (~730 m) and the Patpong/Silom "
    "entertainment streets (~657 m geotag) sit within a bare 800 m straight-line of the stop but "
    "outside the app's mapped catchment — the separately rated st.sala-daeng area takes them — so "
    "the unit's own nightlife density, not Patpong, carries its nightlife score."
)

# 3) Q01 notes
qa01 = next(q for q in b["question_answers"] if q["id"] == "Q01")
old_q1 = "Partial: Patpong/Silom entertainment streets (geotag ~660 m; strip extends toward the 800 m edge) and the Sathorn Rd/Silom Rd spines."
assert old_q1 in qa01["notes"]
qa01["notes"] = qa01["notes"].replace(
    old_q1,
    "Within a bare 800 m of the stop but outside the app catchment: Patpong/Silom entertainment "
    "streets (geotag ~657 m; separately rated st.sala-daeng takes them); Sathorn Rd/Silom Rd spines "
    "remain partial corridor context."
)

# 4) Q12 notes point (5)
qa12 = next(q for q in b["question_answers"] if q["id"] == "Q12")
old_q12 = "(5) nightlife=10 depends on the Patpong fringe sitting inside the geometric circle — a boundary artifact more than a neighborhood trait."
assert old_q12 in qa12["notes"]
qa12["notes"] = qa12["notes"].replace(
    old_q12,
    "(5) nightlife=10 is not explained by Patpong membership: the Patpong/Sala Daeng cluster "
    "(~657–730 m) lies outside the app's nearest-stop catchment and is rated separately as "
    "st.sala-daeng, so the score rests on the unit's own ~34 mapped nightlife venues — a boundary "
    "question a reviewer should confirm against the POI layer."
)

# 5) scope_notes
sn = b["entity"]["scope_notes"]
old_sn = "Boundary caveat from coordinate checks: Sala Daeng BTS (~730–737 m) and the Patpong block geotag (~657–664 m) fall inside the circle by straight-line distance, with the strip extending toward Surawong beyond the edge — the nightlife rating is a fringe effect, not a core identity."
assert old_sn in sn
b["entity"]["scope_notes"] = sn.replace(old_sn,
    "Boundary caveat (verified 2026-11-07 against the app polygon and Wikipedia coordinates): "
    "Sala Daeng BTS (~730 m) and the Patpong block (~657 m) lie within a bare 800 m straight-line "
    "of the stop but OUTSIDE the app's mapped catchment, because st.sala-daeng is itself a rated "
    "area whose nearest-stop catchment takes the Silom/Patpong block; the nightlife rating rests "
    "on the unit's own venue density, not Patpong. MahaNakhon (~122 m from the stop, Wikipedia "
    "coordinates) is inside."
)
save("st.chong-nonsi", b)
print("st.chong-nonsi: 5 fixes applied")

# ---------- st.asok ----------
b = load("st.asok")
cf2 = b["editorial"]["conditional_fit"][2]
old_cf = "anyone prioritizing park life should treat Benjakitti as a 15-minute-walk park, not a doorstep one."
assert old_cf in cf2["text_en"]
cf2["text_en"] = cf2["text_en"].replace(old_cf,
    "anyone prioritizing park life should treat Benjakitti as a park whose nearest edge is about "
    "460 m away and whose main entrances lie beyond the catchment, not a doorstep one.")
save("st.asok", b)
print("st.asok: 1 fix applied")

# ---------- st.thong-lo ----------
b = load("st.thong-lo")
fixed = 0
for s in b["sources"]:
    if not s["body_read"]:
        lim = "Content used only via search-engine highlight excerpts, not a full page read (exa); corroboration only — every claim citing it also cites at least one fully read source."
        if lim not in s["limitations"]:
            s["limitations"].append(lim)
            fixed += 1
assert fixed == 3, f"expected 3 body_read=false sources, fixed {fixed}"
save("st.thong-lo", b)
print("st.thong-lo: 3 source limitations added")

print("ALL FIXES APPLIED")
