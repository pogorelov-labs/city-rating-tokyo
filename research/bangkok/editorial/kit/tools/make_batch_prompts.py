#!/usr/bin/env python3
"""Fill kit/agent-prompt-template.md per entity from batch.json + app data +
the prior bundle's stakes, writing briefs/<key>.md (the full agent prompt).

Usage: python3 -I make_batch_prompts.py --batch-dir <dir> [--keys k1,k2]
"""
import argparse
import json
import os
import re
import sys

KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
E = os.path.dirname(KIT)
TEMPLATE = open(os.path.join(KIT, "agent-prompt-template.md"), encoding="utf-8").read()


def repo_root(start):
    d = os.path.abspath(start)
    while d != os.path.dirname(d):
        if os.path.isdir(os.path.join(d, ".git")):
            return d
        d = os.path.dirname(d)
    raise SystemExit("repo root not found")


ROOT = repo_root(__file__)

STAKES = {
 "st.sala-daeng": {
   "unit": "Merged interchange unit: BTS Sala Daeng (S2) + MRT Si Lom (BL26) are 330 m apart — the app merges stops ≤450 m apart into one unit; the 800 m nearest-stop catchment covers Silom Soi 5 (Lalai Sap), Patpong and most of Lumphini Park's western edge.",
   "leads": "1) Nightlife 10's engine is Patpong (market + go-go strip 90-200 m) AND the scam-strip externality the light bundle flagged. 2) Food 10 rests on Lalai Sap weekday lunches + Silom evenings. 3) Green 10 = Lumphini west edge INSIDE the catchment (verify against station-geometry, not radius). 4) Rent 38,000/60,000 exceeds guide medians (~22-28k) — station-adjacent stock or larger units.",
   "tensions": "scam reports vs nightlife 10; rent blend vs portal medians; Lumphini inside catchment vs bang-rak khet green-thin; Duangtawee/monkey-pool vs patron safety reporting.",
   "thai": "สาลีรัฐธรรมนูญ ปาต้อง ลุมพินี ลไลษณ สีลม"},
 "st.siam": {
   "unit": "BTS Siam (CEN) — the Sukhumvit/Silom junction plus the Siam Paragon/CentralWorld mega-block; 800 m nearest-stop catchment spans Rama I frontage and the Ratchaprasong corners.",
   "leads": "1) The ~6 ha green the app maps is unnamed — candidates: Srapathum Palace grounds? Green 8 needs decomposition. 2) Paragon event history (parade closures, concert-capacity disputes). 3) Nightlife 6 with no obvious venue base. 4) Rent 45,000/95,000 — top-of-market; verify against listings.",
   "tensions": "unnamed park_ha vs named candidates; event-capacity vs crowd score; luxury rent blend vs observable asks; Pathum Wan dual-blend conflict (B-5).",
   "thai": "สยาม สยามพารากอน เซ็นทรัลเวิลด์ ราชประสงค์"},
 "st.chit-lom": {
   "unit": "BTS Chit Lom (E1) — Ratchaprasong skywalk node; 800 m catchment includes Erawan Shrine, CentralChidlom, Gaysorn, and the Platinum/Pratunam edge.",
   "leads": "1) The 120,000 2-bed override — top-decile luxury (Four Seasons/private residences), NOT a median. 2) Big bike-protest/temple-event history at Erawan. 3) Skywalk connectivity as transport 10 basis. 4) Green 4 with almost no named park.",
   "tensions": "override vs corridor median (~40k); shrine events vs crowd; skywalk reach vs walkability reports.",
   "thai": "ชิดลม ราชประสงค์ เอราวัณ แขวงลุมพินี"},
 "st.hua-lamphong": {
   "unit": "MRT Hua Lamphong (BL28, 2019) around the 1916 station; 800 m catchment covers Chinatown's southern edge, Bo Bae, and the Talat Noi fringe.",
   "leads": "1) Afterlife since the 2023-01-19 long-distance closure — station-museum/city-park plans, actual usage. 2) Krung Thep Aphiwat transition effects. 3) Rent = district blend (33,000/70,000?) vs old-stock reality. 4) Saen Saep pier vs river pier confusion (F6-adjacent).",
   "tensions": "heritage-station plans vs reality; tourist-fringe vs residential stock; rent blend vs observed listings.",
   "thai": "หัวลำโพง บางลำพู เยาวราช คลองถม"},
 "st.saphan-taksin": {
   "unit": "BTS Saphan Taksin (S6) + Sathorn/Central Pier — the river hub; 800 m catchment spans Charoen Krung south, State Tower, and the pier plaza.",
   "leads": "1) Green 8 rests on an unidentifiable 5.2 ha (post-F6 claim) — decompose. 2) Sathorn Unique tower: abandoned, rebuild cancelled — verify current status. 3) River-pier transport 10: piers + BTS overlap. 4) Rent 25,000/52,000 vs PropertyScout's missing aggregate.",
   "tensions": "ghost-tower status; pier-count duplication (OSM nodes); rent vs missing aggregates; Sathorn-road boundary sensitivity.",
   "thai": "สะพานตากสิน สาทร เจ้าพระยา คลองสาน"},
 "st.victory-monument": {
   "unit": "BTS Victory Monument (N3) + the bus-van interchange; 800 m catchment covers the monument islands, Rang Nam, and the Phahonyothin start.",
   "leads": "1) BMA 2025-2026 interchange reorganisation + Rajavithi skywalk phase 1 OPENED 1 Oct 2026 (C-1 recheck). 2) Khet attribution conflict: ratchathewi (encyclopedias/district portal) vs phaya-thai (app polygon) — report both, decide by app polygon. 3) Boat-noodle alleys as food anchor. 4) Santiphap Park 3.2 ha as the only real park.",
   "tensions": "renovation stall risk (half-funded islands); dangerous crossings; khet attribution; rents 20-42k vs app 18,000/38,000 blend.",
   "thai": "อนุสาวรีย์ชัยฯ ราชวิถี พหลโยธิน สันติภาพ"},
 "st.mo-chit": {
   "unit": "BTS Mo Chit (N8) + MRT Chatuchak Park — the park/market complex; 800 m catchment includes Chatuchak Weekend Market's southern sections and Queen Sirikit Park.",
   "leads": "1) Market reorganization (2025-2026 vendor/stall changes; the 529-stallholder clock-tower eviction was Or Tor Kor? — verify which market). 2) Mo Chit 2 terminal OUTSIDE the catchment (~2 km) — transport basis is BTS/MRT, not the bus terminal. 3) The four-park complex (Chatuchak/Queen Sirikit/Wachirabenchathat/Rot Fai) — areas per source conflict (149.2 OSM vs 167.1).",
   "tensions": "stall-count conflicts; park-area conflicts; market reorganization vs vendor stability; MRT-name confusion (Chatuchak Park vs Kamphaeng Phet).",
   "thai": "หมอชิต จตุจักร สวนจตุจักร ตลาดนัดจตุจักร"},
 "st.phra-ram-9": {
   "unit": "MRT Phra Ram 9 (BL23?, eastern Blue Line) — the new-CBD node; 800 m catchment covers the G/Tower office cluster and the Rama 9-soi fringes.",
   "leads": "1) Jodd Fairs Rama 9 DEMOLISHED 2025-01 — what replaced it (GR9 redevelopment). 2) The unit's food/nightlife ratings post-demolition. 3) Uniqlo/Chinese-community daily-life layer. 4) Rent 30,000/60,000 vs new-supply listings.",
   "tensions": "demolition aftermath vs ratings computed earlier; office-daytime vs evening population; new-supply rents.",
   "thai": "พระราม 9 จ็อดแฟร์ กรีด 9 รามคำแหง"},
 "st.phetchaburi": {
   "unit": "MRT Phetchaburi (BL?/Blue Line) + ARL Makkasan adjacency — batch 4 resolved the merge; the 800 m catchment straddles Ratchathewi/Phaya Thai/Huai Khwang edges and the CODI flats.",
   "leads": "1) Nightlife 9 with only 11 mapped venues (borrowed from hotel bars/Pratunam?) — independent guides deny a nightlife district. 2) CODI displacement (Nimit Lang Ruea?) status 2025-2026. 3) Rent 21,000/45,500 = ratchathewi blend, not unit-level. 4) Orange Line works on Phetchaburi Rd.",
   "tensions": "nightlife rating vs venue reality; CODI relocation progress; blend-vs-unit rents; Orange Line construction disruption.",
   "thai": "เพชรบุรี มักกะสัน พระราม 9 กอดี้"},
}


def ratings_line(area):
    r = area.get("ratings") or {}
    order = ["transport", "rent", "daily_essentials", "safety", "food",
             "green", "gym_sports", "vibe", "nightlife", "crowd"]
    return ", ".join(f"{k} {r[k]}" for k in order if k in r)


def rent_line(area):
    refs = area.get("rent_references") or area.get("rent") or {}
    if isinstance(refs, dict):
        parts = []
        for k, v in refs.items():
            if isinstance(v, (int, float)):
                parts.append(f"{k}={v}")
            elif isinstance(v, dict):
                parts.append(f"{k}={v.get('value', v)}")
        return "App rent references: " + ", ".join(parts[:6]) if parts else ""
    return ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch-dir", required=True)
    ap.add_argument("--keys")
    ap.add_argument("--date", default="2026-11-08")
    args = ap.parse_args()
    bd = args.batch_dir
    batch = json.load(open(os.path.join(bd, "batch.json"), encoding="utf-8"))
    app = json.load(open(os.path.join(ROOT, "app/src/data/bangkok/stations.json"), encoding="utf-8"))
    areas = {a["id"]: a for a in app["areas"]}

    keys = args.keys.split(",") if args.keys else [e["key"] for e in batch["entities"]]
    for key in keys:
        e = next(x for x in batch["entities"] if x["key"] == key)
        unpref = key.replace("st.", "")
        area = areas.get(unpref) or {}
        stakes = STAKES.get(key, {})
        prefix = unpref + "-"
        prompt = (TEMPLATE
                  .replace("{{KEY}}", key)
                  .replace("{{KIND_LABEL}}", "station area" if e["kind"] == "station_area" else "district")
                  .replace("{{NAME_EN}}", e["name_en"])
                  .replace("{{NAME_TH}}", e.get("name_th") or "")
                  .replace("{{UNIT_DEFINITION}}", stakes.get("unit", "800 m nearest-stop catchment around the station; interchanges ≤450 m are merged into one unit."))
                  .replace("{{RATINGS_LINE}}", ratings_line(area) or "n/a")
                  .replace("{{RENT_LINE}}", rent_line(area))
                  .replace("{{FACTS_LINE}}", "the app's mapped park hectares, venue counts and transit stops are in its data layer; verify against sources, do not copy")
                  .replace("{{LEADS}}", stakes.get("leads", "none recorded"))
                  .replace("{{TENSIONS}}", stakes.get("tensions", "none recorded"))
                  .replace("{{THAI_TERMS}}", stakes.get("thai", e.get("name_th") or ""))
                  .replace("{{SCOPE_ENUM}}", "station_area")
                  .replace("{{DATE}}", args.date)
                  .replace("{{DATE_Y}}", args.date[:4])
                  .replace("{{BATCH_DIR}}", os.path.relpath(bd))
                  .replace("{{PREFIX}}", prefix))
        out = os.path.join(bd, "briefs", f"{key}.md")
        open(out, "w", encoding="utf-8").write(prompt)
        print("wrote", out)


if __name__ == "__main__":
    main()
