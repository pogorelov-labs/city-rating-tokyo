#!/usr/bin/env python3
"""Batch-3 raw adapter: five agent output shapes -> the kit's contract shape.

Backs up each original to raw/original-<key>.json, applies the coordinator
geometry corrections (assertion-guarded), then normalizes:
- geography: nested {scope, relation|relation_to_entity, notes, place_name?}
  or top-level relation/scope fields -> contract shape (place_name defaulted)
- sources: top-level list (shape-1) or inline-per-claim (shape-2/3) -> registry
- file:// app-data anchors -> dropped from registry, recorded as limitations
- claims: text|text_en -> text_en; id|claim_id -> id; evidence built for
  inline-source shapes (paraphrase = claim title, per conversion note)
- QA: id|q, question_id, answer|summary|notes, status default answered
- editorial: contract dicts pass through; commentary lists ({id,topic,item})
  and rating-annotated lists ({rating,value,claim_ids,note}) move to
  uncertainties/review notes; coordinator-drafted editorial inserted for the
  five entities lacking contract editorial (claim refs validated, invalid
  refs dropped with a warning)
"""
import json, os, re, sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(BASE, "raw")

ENTITY_NAMES = {
    "st.ha-yaek-lat-phrao": "Ha Yaek Lat Phrao", "st.phloen-chit": "Phloen Chit",
    "st.sam-yan": "Sam Yan", "st.sam-yot": "Sam Yot", "st.sena-ruam": "Sena Ruam",
    "st.ratchaprarop": "Ratchaprarop", "ratchathewi": "Ratchathewi",
    "phra-nakhon": "Phra Nakhon", "chatuchak": "Chatuchak", "pathum-wan": "Pathum Wan",
}
PREFIX = {k: k.replace("st.", "") for k in ENTITY_NAMES}

import hashlib

def src_id_for(url):
    return "src_" + hashlib.sha256(url.encode('utf-8')).hexdigest()[:12]

def type_infer(publisher):
    p = (publisher or "").lower()
    if re.search(r"wikipedia|wiki|openstreetmap|osm|overpass|app facts|app data", p): return "other"
    if re.search(r"bma|bangkok\.go|district office|governmen|mrta|srt\b|state railway|corrections dept", p): return "government"
    if re.search(r"tat\b|tourism", p): return "tourism_publisher"
    if re.search(r"hipflat|fazwaz|property|listing|rental|dooasset|thailand-property|baanlyy", p): return "commercial_property"
    if re.search(r"time out|bk magazine|guide|wongnai|klook|tripadvisor", p): return "editorial_guide"
    if re.search(r"news|khaosod|nation|thairath|matichon|prachachat|thai pbs|posttoday|standard|the standard|fm91|mcot", p): return "news"
    if re.search(r"reddit|forum|blog", p): return "resident_report"
    return "other"

def load(key):
    return json.load(open(os.path.join(RAW, f"{key}.json"), encoding="utf-8"))

def save_raw(key, d):
    orig = os.path.join(RAW, f"original-{key}.json")
    if not os.path.exists(orig):
        cur = os.path.join(RAW, f"{key}.json")
        with open(orig, "w", encoding="utf-8") as f:
            json.dump(json.load(open(cur, encoding="utf-8")), f, ensure_ascii=False, indent=1)
    with open(os.path.join(RAW, f"{key}.json"), "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)

# ---------- geometry corrections (assertion-guarded, pre-conversion) ----------
def apply_geometry_corrections():
    # ha-yaek: Rot Fai north section computes inside; keep centroid facts, fix framing (idempotent)
    d = load("st.ha-yaek-lat-phrao")
    done = False
    for c in d["claims"]:
        cid = c.get("claim_id") or c.get("id")
        if cid == "ha-yaek-c09":
            txt = c.get("text_en") or c.get("text") or ""
            if "coordinator's polygon" in txt or "coordinator's polygon" in str(c.get("geography", {})):
                done = True
                break
            old = "lie OUTSIDE the unit's 800 m catchment"
            assert old in txt, "c09 anchor missing"
            c["text_en"] = txt.replace(old,
                "have their centroids outside the unit's 800 m catchment, but the coordinator's polygon "
                "check (2026-11-07) places Rot Fai Park's northern section INSIDE the catchment polygon")
            g = c.get("geography") or {}
            rel = g.get("relation") or g.get("relation_to_entity") or "outside"
            g["relation"] = "partial" if rel == "outside" else rel
            g["relation_to_entity"] = g["relation"]
            g["notes"] = (str(g.get("notes", "")) +
                          " | Coordinator polygon check 2026-11-07: Rot Fai north section inside "
                          "(~223-666 m from ring centroid); Chatuchak Park point ~862 m outside. "
                          "Centroids remain outside per source coordinates — the park straddles the edge.")
            done = True
    save_raw("st.ha-yaek-lat-phrao", d)
    print("ha-yaek: c09 straddle correction", "already applied" if done else "applied")

    # sam-yot: Rommaninat computes OUTSIDE sam-yot's polygon (sanam-chai side) (idempotent)
    d = load("st.sam-yot")
    done = False
    for c in d["claims"]:
        cid = c.get("id") or c.get("claim_id")
        if cid == "sam-yot-c10":
            lims = json.dumps(c.get("limitations") or [], ensure_ascii=False)
            if "sanam-chai side" in lims:
                done = True
                break
            txt = c.get("text_en") or c.get("text") or ""
            assert "Rommaninat Park" in txt, "c10 anchor missing"
            c["limitations"] = list(c.get("limitations") or []) + [
                "Coordinator polygon check 2026-11-07: the park's mapped point (~13.7546, 100.5048) falls "
                "OUTSIDE the st.sam-yot catchment polygon — it sits on the st.sanam-chai side of the "
                "boundary despite facing MRT Sam Yot Exit 1 across Mahachai Road. Khet attribution "
                "(Phra Nakhon) unchanged. An earlier batch-2 inference placed it 'in the Sam Yot unit' — "
                "superseded by this check."]
            c["relation"] = "outside"; c["scope"] = c.get("scope", "venue")
            done = True
    save_raw("st.sam-yot", d)
    print("sam-yot: Rommaninat correction", "already applied" if done else "applied")
    for it in d.get("editorial", []):
        if isinstance(it, dict) and str(it.get("topic", "")).startswith("green 9"):
            it["item"] = it["item"] + " | Coordinator correction 2026-11-07: Rommaninat Park computes OUTSIDE the catchment polygon (st.sanam-chai side); the in-unit green case rests on Khlong Ong Ang, temple and institutional grounds."
    save_raw("st.sam-yot", d)
    print("sam-yot: Rommaninat outside-polygon correction applied")

    # reviewed batch-2 wat-mangkon profile c17
    p = "/Users/ruslan/msc_1/git/city-rating/research/bangkok/editorial/batches/2026-11-07-batch2-zcode-main/profiles/st.wat-mangkon.json"
    b = json.load(open(p, encoding="utf-8"))
    for c in b["claims"]:
        if c["id"] == "wat-mangkon-c17":
            old = "lies about 1.0 km WNW in the Sam Yot unit"
            if old in c["text_en"]:
                c["text_en"] = c["text_en"].replace(old,
                    "lies about 1.36 km WNW in Phra Nakhon khet, on the st.sanam-chai side of the boundary "
                    "(coordinator polygon check 2026-11-07 — not in the sam-yot unit as earlier inferred)")
                c["limitations"].append("Unit-attribution corrected 2026-11-07: polygon check supersedes the earlier sam-yot-unit inference.")
                print("batch-2 wat-mangkon c17 corrected")
    json.dump(b, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

# ---------- coordinator-drafted editorial (validated claim refs) ----------
EDITORIAL_DRAFTS = {
    "chatuchak": {
        "preview": "A low-density family khet built around 167 ha of connected public parks and 18 rail stations — with the weekend storm of 15,000 JJ Market stalls one stop away, not at the door.",
        "lead": "Chatuchak is the large, calm northern district most people know for its weekend market and its parks. The Mo Chit park complex — Chatuchak, Queen Sirikit and Rot Fai — puts genuinely public, hours-posted green inside the khet, and eighteen rail stations across four lines make it unusually well connected for a mid-ring family area. Weekends transform the market zone into the city's biggest crowd while the rest of the district stays leafy and quiet. The trade-offs are distance between khwaeng, corridors built for cars, and a market economy whose rent disputes and occasional violence reach the news.",
        "strengths": [
            ("The four-park Mo Chit complex (~120.5 ha: Chatuchak 30.4, Queen Sirikit 22.4, Rot Fai 60, Chak Phupha 4, opened 2025) is genuinely public with posted hours — the honest green case.", ["chatuchak-c07"]),
            ("Eighteen rail stations across four lines, including the intercity hub at Krung Thep Aphiwat and Red Line service (~35,300 trips/day FY2025), make the district transit-rich for its density.", ["chatuchak-c02"]),
            ("Or Tor Kor market and the JJ Market food economy put produce and cooked food within reach of most khwaeng.", ["chatuchak-c11"]),
            ("Rent medians (1BR 16,000 / 2BR 31,500 THB paid-rent data) support the app's 16,000/33,000 blend.", ["chatuchak-c13"]),
        ],
        "tradeoffs": [
            ("The khet is 32.9 km²: daily-essentials coverage thins between khwaeng, and corridors like Phahonyothin and Vibhavadi favor cars — the model's daily_essentials 7 is the researched set's lowest.", ["chatuchak-c15"]),
            ("Weekend market crowds, the Jul 2025 Or Tor Kor shooting (5 dead) and the 2024-25 market rent/eviction dispute are the cost of living next to a national-scale market.", ["chatuchak-c16"]),
        ],
        "day_night": [
            ("Weekends belong to the market (200,000+ visitors); weekdays return the district to parks, universities and quiet residential sois — the sharpest weekend/weekday contrast of any researched entity.", ["chatuchak-c10"]),
        ],
        "within_area_variation": [
            ("The JJ Market / Mo Chit corner is a different city from Kasetsart and Sena Nikhom up Phahonyothin: market-economy bustle south, university calm north.", ["chatuchak-c01"]),
        ],
        "conditional_fit": [
            ("Strong fit: families and pet owners (Rot Fai's 2-rai dog park, registration and leash rules apply) who want park access and transit without core-city prices.", ["chatuchak-c08"]),
            ("Poor fit: late-night social life seekers — vibe 7 / nightlife 7 are the researched set's lowest and are largely unanchored by specific venues.", ["chatuchak-c12"]),
        ],
    },
    "phra-nakhon": {
        "preview": "Old Bangkok proper: royal parks with posted hours, a river pier on every corner and 171 temples — with Khao San's backpacker strip and a shrinking residential population an honest walk apart.",
        "lead": "Phra Nakhon is the heritage core: the Grand Palace, Wat Pho, Sanam Luang and the river piers, with Banglamphu's guesthouse economy and Khao San's nightlife inside the same khet as quiet old shophouse quarters. Its green is genuinely public — Sanam Luang, Saranrom and Santichaiprakan post daily hours — though about half the mapped 38.5 ha is temple and palace grounds rather than open park. Two MRT stations (Sam Yot, Sanam Chai) serve the southern half while Banglamphu relies on boats and buses. Registered population has fallen from 114,124 (1985) to 38,408 (2025), and the trade-offs are tourist monoculture, conservation-constrained housing and no full-service hospital inside the khet.",
        "strengths": [
            ("Sanam Luang (~11.9 ha, 05:00-22:00), Saranrom (~3.7 ha) and Santichaiprakan (~1.3 ha) are polygon-interior public parks with posted hours — the researched set's most defensible green 10.", ["phra-nakhon-c02"]),
            ("Fourteen named ferry terminals in-polygon plus two MRT stations give the southern khet genuine river-and-rail access.", ["phra-nakhon-c03"]),
            ("Cheap for the core: studios and shophouse rooms consistent with the 14,000/28,000 blend, especially in Wang Burapha's shrinking quarters.", ["phra-nakhon-c12"]),
        ],
        "tradeoffs": [
            ("No full-service hospital inside the polygon (Klang is just outside; Siriraj across the river) against an otherwise dense market layer.", ["phra-nakhon-c09"]),
            ("Tourist monoculture around Khao San and conservation-constrained old housing stock shape what living here is actually like.", ["phra-nakhon-c13"]),
        ],
        "day_night": [
            ("Ceremonial calendar and tourist high season set the rhythm; Khao San runs late while riverside and temple quarters empty early.", ["phra-nakhon-c10"]),
        ],
        "within_area_variation": [
            ("Banglamphu/Khao San, the royal-field and temple core, and the riverside piers are three different neighborhoods inside 5.5 km².", ["phra-nakhon-c01"]),
        ],
        "conditional_fit": [
            ("Strong fit: heritage-oriented residents and low-budget starters who accept old-building conditions and thin resident services.", ["phra-nakhon-c14"]),
            ("Poor fit: households needing hospitals, modern condos or quiet tourist-free streets.", ["phra-nakhon-c15"]),
        ],
    },
    "st.sam-yot": {
        "preview": "A three-khet heritage stop on Dinso Road: the always-open Khlong Ong Ang promenade at the door, 11,000-THB studios two minutes' walk from it, and Rommaninat Park across the boundary.",
        "lead": "Sam Yot is the old town's quiet rail corner — an underground Blue-line station beneath Charoen Krung at the Sam Yot junction, straddling Phra Nakhon, Pom Prap Sattru Phai and Samphanthawong. The Khlong Ong Ang promenade (Friday-Sunday walking street, kayaks, street art) runs beside the station, and listings put 11,000-13,000 THB studios and 14,000-15,000 THB 1-bedrooms at the door. The trade-offs: safety 5 has no visible unit-specific basis, evening life is event-driven rather than street-level, and the district's registered population is shrinking. Purple Line interchange targeted November 2030.",
        "strengths": [
            ("Khlong Ong Ang promenade — restored moat canal, verified inside the catchment — gives daily waterside walking plus a Fri-Sun 16:00-22:00 walking street.", ["sam-yot-c07"]),
            ("Rent 8 is backed by hard listings: 11,000-13,000 THB studios 74-100 m from the station and 14,000-15,000 THB 1-bedrooms.", ["sam-yot-c11"]),
            ("Market density (Trok Mo dawn market, Khlong Thom, Mega Plaza) supports daily_essentials 9 for a car-free household.", ["sam-yot-c13"]),
        ],
        "tradeoffs": [
            ("Safety 5 has no visible unit-specific evidence base — only generic old-town night emptiness after ~22:00 and the tourist-fringe scam genre.", ["sam-yot-c15"]),
            ("Vibe 10 / nightlife 9 are event- and heritage-driven: the 17 small bars and the Fri-Sun walking street carry it, and the canal's revival has stagnated between festivals.", ["sam-yot-c16"]),
        ],
        "day_night": [
            ("Daytime is a government-office and market quarter; evenings depend on the Fri-Sun walking street and small bars, with backstreets dim after ~22:00.", ["sam-yot-c14"]),
        ],
        "within_area_variation": [
            ("The station quarter (Wang Burapha, Dinso) differs from the canal-frontage blocks and from the Pom Prap and Samphanthawong fringes the catchment touches.", ["sam-yot-c02"]),
        ],
        "conditional_fit": [
            ("Strong fit: heritage-oriented renters on a budget who walk and use the canal promenade as their green.", ["sam-yot-c17"]),
            ("Poor fit: park-dependent households — Rommaninat Park computes outside the catchment (st.sanam-chai side) despite facing Exit 1.", ["sam-yot-c10"]),
        ],
    },
    "ratchathewi": {
        "preview": "A four-station khet stitched from Pratunam's market economy, pocket parks no bigger than 3.4 ha, and corridors that currently wear an Orange Line construction site.",
        "lead": "Ratchathewi packs four researched station areas (BTS Ratchathewi, ARL Ratchaprarop, BTS/ARL Phaya Thai, Victory Monument) into 7.1 km² with four khwaeng. Its green 9 rests on pocket parks — Phirom 3.38 ha, Santiphap 2.85 ha, Suan Rom 1.71 ha — plus institutional gardens; no public park above ~3.4 ha exists anywhere in the khet. Pratunam's wholesale economy and Baiyoke towers (khwaeng Thanon Phaya Thai) anchor the east, and the MRT Orange Line (three in-khet stations, opening ~July 2030) is reshaping its main corridors. Safety 5 repeats the pattern seen at station level: no per-khet statistics exist in any retrieved source.",
        "strengths": [
            ("District-level transit is structurally rich: three BTS stations, ARL and the under-construction Orange Line (OR08 Ratchathewi, OR09 Pratunam, OR10 Ratchaprarop).", ["ratchathewi-d-c03"]),
            ("Rent 7 is bracketed by live asking data (FazWaz 1,864 listings, 13,000-300,000 THB).", ["ratchathewi-d-c15"]),
        ],
        "tradeoffs": [
            ("Green 9 decomposes to 8.81 ha of named public parks plus small institutional/private garden stock — pocket-scale, not park-scale.", ["ratchathewi-d-c06"]),
            ("The Ratchathewi flyover is closed (since mid-Jan 2025) until 30 Apr 2028, and the Pratunam overpass demolition window is contested between sources.", ["ratchathewi-d-c12"]),
        ],
        "day_night": [
            ("Pratunam's wholesale day economy and the office corridors set weekday rhythm; Phetchaburi Road runs quieter at night.", ["ratchathewi-d-c09"]),
        ],
        "within_area_variation": [
            ("Pratunam/Makkasan market-and-tower blocks, Thanon Phaya Thai's towers, and the Rangnam/Thanon Phetchaburi mid-rise belt are distinct subareas.", ["ratchathewi-d-c01"]),
        ],
        "conditional_fit": [
            ("Strong fit: market traders, airport commuters and transit-first renters who accept pocket-park green and construction disruption.", ["ratchathewi-d-c16"]),
        ],
    },
    "st.ratchaprarop": {
        "preview": "The airport-rail control unit: ARL Ratchaprarop, Pratunam's garment economy at the door, a 1.7 ha pocket park — and an MRT Orange Line interchange arriving ~2030.",
        "lead": "Ratchaprarop is the app's ARL-only control: no BTS or MRT interchange, just City Line service (10-13 min headways) to Suvarnabhumi and a one-stop transfer at Phaya Thai. Its transport 9 is 'airport rail plus everything nearby' — Pratunam's wholesale blocks, Platinum Fashion Mall's economy and the Pratunam canal pier — not rail density. Suan Rom Ratchathewi (1.70 ha, 343-471 m) is the verifiable in-unit green; the mapped 3.2 ha figure matches Santiphap Park straddling the 800 m edge. Safety 5 repeats the dataset's unanchored pattern. The MRT Orange Line runs under Ratchaprarop Road with an ARL interchange targeted for July 2030.",
        "strengths": [
            ("Airport rail at the door: ARL City Line headways of 10-13 minutes and 70,887 daily riders (2026 Q1) make airport commuting the unit's defining convenience.", ["ratchaprarop-c06"]),
            ("Suan Rom Ratchathewi (1.70 ha, 343-471 m) is polygon-verified in-unit green.", ["ratchaprarop-c09"]),
        ],
        "tradeoffs": [
            ("Transport 9 has no interchange behind it: ARL headways trail BTS 2.4-6 minutes, and the unit depends on buses and walking for non-airport trips.", ["ratchaprarop-c07"]),
            ("Safety 5 is the third entity in a row with zero unit-level statistics; only alleged tourist-scam reports (bag-slicing, pickpocket alleys) exist.", ["ratchaprarop-c12"]),
        ],
        "day_night": [
            ("Wholesale-market hours set the day; the garment district's evenings thin earlier than the nearby hotel belt.", ["ratchaprarop-c10"]),
        ],
        "within_area_variation": [
            ("The ARL/Pratunam frontage differs from the quieter Ratchaprarop sois west toward Santiphap.", ["ratchaprarop-c01"]),
        ],
        "conditional_fit": [
            ("Strong fit: airport commuters and wholesale-market traders; the control condition expires when the Orange Line interchange opens (~July 2030).", ["ratchaprarop-c14"]),
        ],
    },
}

def norm_geo(c, ent_name):
    g = c.get("geography") or {}
    scope = g.get("scope") or c.get("scope") or "other"
    rel = g.get("relation_to_entity") or g.get("relation") or c.get("relation") or "unknown"
    notes = g.get("notes") or ""
    place = g.get("place_name") or ent_name
    if scope in ("entire_unit", "partial"):
        scope = "station_area"
    return {"scope": scope, "place_name": place,
            "relation_to_entity": rel if rel in ("inside","partial","outside","unknown","entire_unit") else "unknown",
            "notes": notes if isinstance(notes, str) else json.dumps(notes, ensure_ascii=False)}

def normalize(key, d):
    name = ENTITY_NAMES[key]
    prefix = PREFIX[key]
    notes_out, warnings = [], []
    src_registry, url_to_idx = [], {}
    claims = d.get("claims") or []
    ref_to_idx = {}
    top_sources = d.get("sources") or []
    if top_sources and isinstance(top_sources[0], dict) and "ref" in top_sources[0]:
        for i, s in enumerate(top_sources):
            url = s.get("url") or ""
            sid = src_id_for(url) if url.startswith("http") else None
            idx = i
            url_to_idx[url] = idx
            ref_to_idx[s["ref"]] = idx
            src_registry.append({
                "publisher": s.get("publisher") or "Unknown",
                "publisher_family": s.get("publisher_family") or s.get("publisher") or "Unknown",
                "title": s.get("title") or url,
                "url": url, "date": s.get("pub_date") or s.get("date") or s.get("published_at"),
                "body_read": bool(s.get("body_read", s.get("bod", False))),
                "retrieved_url": s.get("retrieved_url") or url,
            })
        src_by_ref = {s.get("ref"): s for s in top_sources}

    def reg_source(s):
        url = s.get("url") or s.get("canonical_url") or ""
        if not url.startswith("http"):
            if url.startswith("file://"):
                return None, True
            return None, False
        if url in url_to_idx:
            return url_to_idx[url], False
        idx = len(src_registry)
        url_to_idx[url] = idx
        src_registry.append({
            "publisher": s.get("publisher") or "Unknown",
            "publisher_family": s.get("publisher_family") or s.get("publisher") or "Unknown",
            "title": s.get("title") or s.get("publisher") or url,
            "url": url, "date": s.get("date") or s.get("published_at"),
            "body_read": bool(s.get("body_read", False)),
            "retrieved_url": s.get("retrieved_url") or url,
        })
        return idx, False

    claims_out = []
    for c in claims:
        cid = c.get("claim_id") or c.get("id")
        text = c.get("text_en") or c.get("text") or c.get("claim") or ""
        kind = c.get("kind") or "factual_report"
        if kind not in ("factual_report","reported_perception","estimate","researcher_inference"):
            kind = "researcher_inference"
        polarity = c.get("polarity") or "neutral"
        if polarity.startswith("positive"): polarity = "strength"
        elif polarity.startswith("negative"): polarity = "tradeoff"
        if polarity not in ("strength","tradeoff","mixed","neutral"): polarity = "neutral"
        ev_out, dropped_file = [], []
        inline = c.get("evidence")
        if isinstance(inline, list) and inline and isinstance(inline[0], dict) and ("source_index" in inline[0] or "source_id" in inline[0]):
            for e in inline:
                si = e.get("source_index")
                if si is not None and si < len(d.get("sources") or []):
                    src_registry_reg = d["sources"][si]
                    idx, is_file = reg_source(src_registry_reg)
                    if idx is None:
                        dropped_file.append(src_registry_reg.get("title") or src_registry_reg.get("url"))
                        continue
                    ev_out.append({"source_index": idx, "locator": e.get("locator") or "", "paraphrase": e.get("paraphrase") or c.get("title") or text[:80]})
        elif c.get("sources") and all(isinstance(x, str) for x in c["sources"]) and ref_to_idx:
            # shape-4: ref-keyed registry
            for ref in c["sources"]:
                idx = ref_to_idx.get(ref)
                s = src_by_ref.get(ref) or {}
                if idx is None:
                    dropped_file.append(ref); continue
                ev_out.append({"source_index": idx,
                               "locator": s.get("locator") or s.get("title", "")[:80],
                               "paraphrase": (c.get("title") or text[:100])})
        else:
            for s in (c.get("sources") or []):
                idx, is_file = reg_source(s)
                if idx is None:
                    dropped_file.append(s.get("title") or s.get("url"))
                    continue
                ev_out.append({"source_index": idx, "locator": s.get("locator") or "", "paraphrase": c.get("title") or text[:80]})
        lims = list(c.get("limitations") or [])
        for t in dropped_file:
            lims.append(f"app-data anchor (not a web source): {t}")
        claims_out.append({
            "claim_id": cid, "text_en": text, "kind": kind,
            "topics": sorted(set(c.get("topics") or [])) or ["identity"],
            "polarity": polarity, "geography": norm_geo(c, name),
            "temporal_scope": {"event_date": None, "observed_period": None, "recheck_by": None, "notes": ""},
            "evidence": ev_out, "limitations": lims,
        })
        if not ev_out:
            warnings.append(f"{key}/{cid}: no evidence after conversion")

    qa_out = []
    for q in (d.get("question_answers") or d.get("qa") or []):
        qid = q.get("id") or q.get("question_id") or q.get("q")
        status = q.get("status") or "answered"
        if status not in ("answered","conflicting","not_found","not_applicable"):
            status = "answered"
        notes = q.get("notes") or q.get("answer") or q.get("summary") or ""
        cids = [c for c in dict.fromkeys(q.get("claim_ids") or []) if c in {c["claim_id"] for c in claims_out}]
        qa_out.append({"id": qid, "status": status, "claim_ids": cids, "notes": notes})

    ed = d.get("editorial")
    editorial = None
    if isinstance(ed, dict):
        editorial = ed  # contract-ish; ed_items handled at assemble (strings ok)
    else:
        # commentary or rating-annotated list -> uncertainties + coordinator draft
        unc = []
        for it in (ed or []):
            if isinstance(it, dict):
                if "rating" in it:
                    unc.append(f"rating {it.get('rating')} ({it.get('value')}): {it.get('note','')}")
                else:
                    unc.append(f"{it.get('topic')}: {it.get('item','')}")
            elif isinstance(it, str):
                unc.append(it)
        draft = EDITORIAL_DRAFTS.get(key)
        valid_ids = {c["claim_id"] for c in claims_out}
        def vc(ids):
            ok = [i for i in ids if i in valid_ids]
            if not ok:
                warnings.append(f"{key}: draft refs {ids} all invalid; fallback to first claim")
                ok = [sorted(valid_ids)[0]] if valid_ids else []
            bad = [i for i in ids if i not in valid_ids]
            if bad:
                warnings.append(f"{key}: dropped invalid draft refs {bad}")
            return ok
        editorial = {
            "preview": {"text_en": draft["preview"], "claim_ids": vc(draft.get("preview_refs") or []) or vc(sorted(valid_ids)[:1])},
            "guide_lead": {"text_en": draft["lead"], "claim_ids": vc(draft.get("lead_refs") or draft.get("preview_refs") or []) or vc(sorted(valid_ids)[:1])},
            "strengths": [{"text_en": t, "claim_ids": vc(r)} for t, r in draft["strengths"]],
            "tradeoffs": [{"text_en": t, "claim_ids": vc(r)} for t, r in draft["tradeoffs"]],
            "day_night": [{"text_en": t, "claim_ids": vc(r)} for t, r in draft["day_night"]],
            "within_area_variation": [{"text_en": t, "claim_ids": vc(r)} for t, r in draft["within_area_variation"]],
            "conditional_fit": [{"text_en": t, "claim_ids": vc(r)} for t, r in draft["conditional_fit"]],
            "uncertainties": unc + list(draft.get("extra_uncertainties") or []),
        }
    out = {
        "entity_key": key,
        "search_log": d.get("search_log") or [],
        "sources": [{"index": i, "canonical_url": s["url"], "retrieved_url": s["retrieved_url"],
                     "title": s["title"], "publisher": s["publisher"],
                     "publisher_family": s["publisher_family"], "author": None,
                     "published_at": s["date"], "updated_at": None,
                     "retrieved_at": "2026-11-07T00:00:00Z", "body_read": s["body_read"],
                     "type": type_infer(s["publisher"]),
                     "commercial_context": "", "limitations": []} for i, s in enumerate(src_registry)],
        "claims": claims_out, "question_answers": qa_out, "editorial": editorial,
        "open_issues": list(d.get("open_issues") or []) + notes_out,
    }
    return out, warnings

def main():
    apply_geometry_corrections()
    total_warn = 0
    for key in ENTITY_NAMES:
        d = load(key)
        if "sources" in d and "question_answers" in d and isinstance(d.get("editorial"), dict) and all(
                isinstance(d["editorial"].get(x), list) for x in ("strengths","tradeoffs")):
            # already contract-ish (sam-yan); just normalize geography + QA keys
            name = ENTITY_NAMES[key]
            for c in d["claims"]:
                g = c.get("geography") or {}
                if "relation" in g and "relation_to_entity" not in g:
                    g["relation_to_entity"] = g.pop("relation")
                g.setdefault("place_name", name)
                g.setdefault("notes", "")
            for q in d["question_answers"]:
                q.setdefault("id", q.get("question_id") or q.get("q"))
                q.setdefault("notes", q.get("answer") or "")
            save_raw(key, d)
            print(f"{key}: contract-ish — geography/QA normalized in place")
            continue
        out, warnings = normalize(key, d)
        save_raw(key, out)
        total_warn += len(warnings)
        print(f"{key}: normalized — sources={len(out['sources'])} claims={len(out['claims'])} qa={len(out['question_answers'])}")
        for w in warnings:
            print("  WARN:", w)
    print(f"conversion complete, {total_warn} warnings")

if __name__ == "__main__":
    main()
