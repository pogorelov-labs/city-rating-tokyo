#!/usr/bin/env python3
"""Apply coordinator geometry-verification corrections to batch-2 raw bundles.

Every replacement is assertion-guarded; the script fails loudly if an expected
string is missing. Runs before assembly so profiles and briefs inherit the
corrections.
"""
import json

BASE = "/Users/ruslan/msc_1/git/city-rating/research/bangkok/editorial/batches/2026-11-07-batch2-zcode-main/raw"

def load(key):
    return json.load(open(f"{BASE}/{key}.json", encoding="utf-8"))

def save(key, b):
    with open(f"{BASE}/{key}.json", "w", encoding="utf-8") as f:
        json.dump(b, f, ensure_ascii=False, indent=1)

# ---------- st.nana ----------
b = load("st.nana")
c09 = next(c for c in b["claims"] if c["claim_id"] == "nana-c09")
old = "sits at 33 Sukhumvit Soi 3 (Soi Nana Nuea) within the unit, roughly 350-500 m up the soi from BTS Nana by public-source estimates"
assert old in c09["text_en"]
c09["text_en"] = c09["text_en"].replace(old,
    "sits at 33 Sukhumvit Soi 3 (Soi Nana Nuea) with its campus straddling the unit's northwest "
    "edge: the hospital frontage begins roughly 415-450 m up the soi from BTS Nana (inside the "
    "mapped catchment), while its geotagged center (~13.7463, 100.5526, ~710 m straight-line) "
    "falls outside the mapped polygon, clipped toward st.phloen-chit (app-polygon check 2026-11-07)")
c09["geography"]["relation_to_entity"] = "partial"
c09["geography"]["notes"] = ("Campus spans the catchment boundary: frontage ~415-450 m from the station "
                             "inside the app polygon; geotagged center ~710 m outside it.")
c14 = next(c for c in b["claims"] if c["claim_id"] == "nana-c14")
old = "Benchasiri Park (4.7 ha, between Soi 22-24 next to Emporium/Emsphere, at Phrom Phong BTS) is ~1.1-1.3 km east"
assert old in c14["text_en"]
c14["text_en"] = c14["text_en"].replace(old,
    "Benchasiri Park (4.7 ha, between Soi 22-24 next to Emporium/Emsphere, at Phrom Phong BTS) is ~1.7 km east by straight-line from the station")
old = "Lumphini Park (57.6 ha, Pathum Wan) lies ~0.7-0.8 km from the station anchor at its nearest (northeastern) edge, a boundary case that is mostly st.lumphini's catchment"
assert old in c14["text_en"]
c14["text_en"] = c14["text_en"].replace(old,
    "Lumphini Park (57.6 ha, Pathum Wan) lies ~1.6-1.7 km from the station at its nearest edge - outside the unit, not a boundary case (app-polygon check 2026-11-07)")
qa = {q.get("q", q.get("id")): q for q in b["question_answers"]}
n = qa["Q07"]["notes"]
assert "Bumrungrad inside (official)" in n
qa["Q07"]["notes"] = n.replace("Bumrungrad inside (official)",
    "Bumrungrad straddles the unit's NW edge (frontage ~415-450 m inside; geotagged center ~710 m outside the polygon)")
n = qa["Q09"]["notes"]
assert "NE edge a boundary case" in n
qa["Q09"]["notes"] = n.replace("Lumphini 57.6 ha: majority outside, NE edge a boundary case.",
    "Lumphini 57.6 ha: outside (~1.6-1.7 km to nearest edge, polygon-verified 2026-11-07).")
save("st.nana", b)
print("st.nana: c09/c14/Q07/Q09 corrected")

# ---------- st.wat-mangkon ----------
b = load("st.wat-mangkon")
c17 = next(c for c in b["claims"] if c["claim_id"] == "wat-mangkon-c17")
assert "Wat Saket/Golden Mount about 1.3 km north" in c17["text_en"]
c17["text_en"] = c17["text_en"].replace("Wat Saket/Golden Mount about 1.3 km north",
    "Wat Saket/Golden Mount about 0.9 km north-northwest (914 m straight-line from the station, app-polygon check 2026-11-07)")
c18 = next(c for c in b["claims"] if c["claim_id"] == "wat-mangkon-c18")
assert "1.3 km out" in c18["text_en"]
c18["text_en"] = c18["text_en"].replace("1.3 km out", "~0.9 km out")
qa = {q.get("id", q.get("q")): q for q in b["question_answers"]}
n = qa["Q09"]["notes"]
assert "Golden Mount 1.3 km" in n
qa["Q09"]["notes"] = n.replace("Golden Mount 1.3 km", "Golden Mount ~0.9 km")
c07 = next(c for c in b["claims"] if c["claim_id"] == "wat-mangkon-c07")
c07["limitations"].append(
    "Polygon check 2026-11-07: the lane's northwestern (Maitrichit-side) end falls inside the "
    "mapped catchment (~414-447 m from the station) while its midpoint falls outside - the strip "
    "does straddle the boundary.")
save("st.wat-mangkon", b)
print("st.wat-mangkon: c17/c18/Q09 distances corrected, c07 polygon note added")

# ---------- phaya-thai ----------
b = load("phaya-thai")
c05 = next(c for c in b["claims"] if c["claim_id"] == "phaya-thai-c05")
c05["limitations"].append(
    "Conflict noted 2026-11-07: a point-in-polygon test against the app's own khet polygon "
    "(geometry.json) places the Victory Monument roundabout (~13.7699, 100.5350) INSIDE the "
    "phaya-thai khet, while the source attributes it to Ratchathewi - the monument sits at the "
    "boundary; treat its attribution as conflicting.")
save("phaya-thai", b)
print("phaya-thai: c05 Victory Monument conflict documented")

print("ALL RAW FIXES APPLIED")
