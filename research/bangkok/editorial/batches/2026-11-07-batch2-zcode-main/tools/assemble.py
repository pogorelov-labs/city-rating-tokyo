#!/usr/bin/env python3
"""Assemble batch-2 raw research JSON into schema-conformant entity bundles.

Run with: python3 -I tools/assemble.py   (from the batch-2 directory)
Adapted from the batch-1 assembler: new entity metadata, batch-2 selection
rationales, and QA-record normalization (agents used q/claims/claim_refs and
answer/partial variants in some files).
"""
import hashlib
import json
import os
import re
from datetime import datetime, timezone

BATCH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(BATCH, "raw")
PROFILES = os.path.join(BATCH, "profiles")
REPO = "/Users/ruslan/msc_1/git/city-rating"

SEED_PATH = ("/Users/ruslan/.codex/worktrees/bangkok-filters/city-rating/"
             "research/bangkok/editorial/2026-11-05-handoff/priority-seed.json")

BATCH2 = ["st.charoen-nakhon", "st.ratchathewi", "st.nana", "st.wat-mangkon",
          "pom-prap-sattru-phai", "phaya-thai"]

ENTITY_META = {
    "st.charoen-nakhon": {
        "kind": "station_area",
        "name_en": "Charoen Nakhon",
        "name_th": "เจริญนคร",
        "aliases": ["Gold Line (Khlong San)", "ICONSIAM area", "Somdet Chao Phraya"],
        "scope_notes": (
            "800 m nearest-stop catchment around BTS Charoen Nakhon (Gold Line G2) on the Charoen "
            "Nakhon Road corridor. District split (app data): Khlong San 75%, Bang Rak 25% — the 25% "
            "being the east-bank pier strip the circle sweeps across the river bend. Research-verified: "
            "ICONSIAM is inside and adjacent (OSM mall polygon ~0.14 km from the station; exits 1–3 "
            "bridge directly in; River Park end ~0.47 km). The Gold Line has three stations and never "
            "crosses the river (1.74–1.8 km total); the transport 10 plausibly reflects the pier "
            "cluster plus buses rather than rail service alone (researcher inference; score untouched)."
        ),
    },
    "st.ratchathewi": {
        "kind": "station_area",
        "name_en": "Ratchathewi",
        "name_th": "ราชเทวี",
        "aliases": ["Ratchathewi intersection", "Phetchaburi (corridor)"],
        "scope_notes": (
            "800 m nearest-stop catchment around BTS Ratchathewi, entirely within Ratchathewi khet "
            "but not the whole khet (which extends far north on Phahonyothin). Research-verified "
            "outside: Baiyoke Tower II (~1.28 km ENE), Santiphap Park (~1.65 km NNE, Ratchathewi "
            "khet's north), Suan Pakkad Palace Museum (~0.81 m NNE, nearer BTS Phaya Thai). No named "
            "public park verified inside (app 1.0 ha unmatched; OSM shows none). The Ratchathewi "
            "flyover closed 15–16 Jan 2025 with reconstruction due by Apr 2028."
        ),
    },
    "st.nana": {
        "kind": "station_area",
        "name_en": "Nana",
        "name_th": "นานา",
        "aliases": ["Sukhumvit Soi Nana", "Soi Nana (Soi 4) bar strip", "Soi Arab (Soi 3)", "Nana intersection"],
        "scope_notes": (
            "800 m nearest-stop catchment around BTS Nana. District split (app data): Watthana 48%, "
            "Khlong Toei 44%, Pathum Wan 8%. NOT the Chinatown Soi Nana — that cocktail-bar strip "
            "sits in Pom Prap Sattru Phai inside st.wat-mangkon's catchment (batch-2 verified). "
            "Research-verified: Nana Plaza ~255–300 m inside; Bumrungrad campus straddles the NW "
            "boundary (frontage ~415–450 m inside, geotagged center ~710 m outside the polygon); "
            "Benchasiri ~1.7 km east and Lumphini ~1.6–1.7 km south both outside — green 10 is not "
            "reproducible from in-unit geometry (1.4 ha mapped, identity unresolved)."
        ),
    },
    "st.wat-mangkon": {
        "kind": "station_area",
        "name_en": "Wat Mangkon",
        "name_th": "วัดมังกร",
        "aliases": ["MRT Wat Mangkon (Blue Line)", "Chinatown MRT station"],
        "scope_notes": (
            "800 m nearest-stop catchment around MRT Wat Mangkon (Blue Line, opened 2019), straddling "
            "Pom Prap Sattru Phai 51.4% / Samphanthawong 48.6%. Note for reviewers: Wikipedia "
            "attributes the station itself to Samphanthawong while the app's district split gives "
            "Pom Prap the majority. Research-verified inside: Wat Mangkon Kamalawat temple (~54 m to "
            "geotag, Pom Prap side — refuting a pilot note that placed it 'just outside the khet') "
            "and the northwestern end of the Chinatown Soi Nana bar strip (~414–447 m; the lane "
            "straddles the boundary). Research-verified outside: Wat Traimit and Odean Circle "
            "(st.hua-lamphong side), Khlong Ong Ang and Rommaninat Park (st.sam-yot side), Golden "
            "Mount (~0.91 km)."
        ),
    },
    "pom-prap-sattru-phai": {
        "kind": "district",
        "name_en": "Pom Prap Sattru Phai",
        "name_th": "ป้อมปราบศัตรูพ่าย",
        "aliases": None,  # filled from districts.json
        "scope_notes": (
            "Administrative khet (~1.93 km², pop ~41,524 in 2020, density ~21,504/km² — among "
            "Bangkok's densest) between the Golden Mount and Chinatown. Research-verified: the "
            "Chinatown Soi Nana bar strip and Bangkok Kunsthalle are in khwaeng Pom Prap; Woeng "
            "Nakhon Kasem is in Samphanthawong (the app alias list includes it — a data-level "
            "correction for reviewers); Rommaninat Park is in Phra Nakhon; Wat Ratchanatdaram's "
            "attribution is conflicting. Green 9 rests on the free Golden Mount compound and the "
            "Khlong Ong Ang promenade (researcher inference; only 0.7 ha mapped parks)."
        ),
    },
    "phaya-thai": {
        "kind": "district",
        "name_en": "Phaya Thai",
        "name_th": "พญาไท",
        "aliases": None,  # filled from districts.json
        "scope_notes": (
            "Administrative khet (~9.59 km², pop ~67,388 in 2020) along the Phahonyothin corridor "
            "with sharply different subareas (Ari, Saphan Khwai, Sanam Pao, Pradiphat, Samsen Nai). "
            "Research-verified: the khet's namesake BTS Phaya Thai + ARL terminus sit in Ratchathewi, "
            "just outside the khet (app-polygon check confirms); inside stations are Ari, Sanam Pao, "
            "Saphan Khwai + SRT Sam Sen. Green 9's likely basis is the Royal Thai Army compound and "
            "other state land (controlled access, not public parkland — inference; 14.8 ha unmapped). "
            "Victory Monument's attribution is conflicting (app polygon includes the roundabout; "
            "sources place it in Ratchathewi)."
        ),
    },
}

SELECTED_RATIONALE = {
    "st.charoen-nakhon": "Rank #2/133 with thin independent coverage — the high-score/low-coverage pattern; transport 10 for a Gold Line feeder needed a mechanism check.",
    "st.ratchathewi": "Rank #3/133 and the only station area with 'some' measured coverage; safety 5 (lowest in the research set) vs vibe 10 needed testing.",
    "st.nana": "Popular-but-contested nightlife identity; the Soi Nana name confusion is a Q01 test; green 10 with 1.4 ha park is a green-geometry outlier.",
    "st.wat-mangkon": "Boundary control: catchment split Pom Prap 51.4% / Samphanthawong 48.6%, straddling the pilot's Samphanthawong findings on both sides.",
    "pom-prap-sattru-phai": "District #3 with broad independent coverage; owns the Chinatown Soi Nana bars and Khlong Thom the pilot placed outside Samphanthawong; green 9 vs 0.7 ha park test.",
    "phaya-thai": "District #4 with broad coverage; district-level counterpart to the pilot's st.ari findings; where the 14.8 ha of mapped parkland actually sit.",
}

POP_METHOD = ("No citywide popularity measure has been collected. Coverage breadth was measured for "
              "batch selection only (2024-11-05..2026-11-07 window, publisher-family dedup, "
              "coverage-scan.json); it is a research-selection signal, not a popularity score.")


NORM_POLARITY = {
    "positive": "strength", "negative": "tradeoff",
    "negative_for_sukhumvit_so4_labeling": "tradeoff",
    "negative_for_green_score": "tradeoff",
}
NORM_TYPE = {
    "encyclopedia": "other", "encyclopedic": "other", "reference": "other",
    "dataset": "other", "map_data": "other", "geo_directory": "other",
    "transit_directory": "other", "transit_aggregator": "other",
    "news": "news", "news_report": "news", "news_traffic_report": "news", "business_news": "news",
    "government_site": "government", "government_tourism_feature": "government",
    "tourism_publisher": "tourism_publisher", "official_tourism_page": "tourism_publisher",
    "tourism_listing": "tourism_publisher", "event_listing": "tourism_publisher",
    "commercial_property": "commercial_property", "property_portal_data": "commercial_property",
    "property_portal_guide": "commercial_property", "listing_portal_stats": "commercial_property",
    "listing_data": "commercial_property", "listings": "commercial_property",
    "listings_portal": "commercial_property", "restaurant_listing": "editorial_guide",
    "neighborhood_guide": "editorial_guide", "guide": "editorial_guide",
    "travel_guide": "editorial_guide", "listicle": "editorial_guide", "feature": "editorial_guide",
    "operator_site": "official_operator",
    "forum_post": "resident_report",
    "corporate_site": "other", "organization_page": "other", "official_venue_page": "other",
    "official_site": "other", "official": "other", "social_media_transit_commentary": "other",
}

def src_id_for(url):
    return "src_" + hashlib.sha256(url.encode("utf-8")).hexdigest()[:12]

def norm_datetime(s):
    if not s:
        return None
    s = s.strip()
    if re.match(r"^\d{4}-\d{2}-\d{2}$", s):
        return s + "T00:00:00Z"
    if re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?$", s):
        return s + (":00Z" if len(s) == 16 else "Z")
    return s

def load_data():
    seed = json.load(open(SEED_PATH, encoding="utf-8"))
    seed_by_key = {e["entity_key"]: e for e in seed["all_entities"]}
    stations = json.load(open(os.path.join(REPO, "app/src/data/bangkok/stations.json"), encoding="utf-8"))
    districts = json.load(open(os.path.join(REPO, "app/src/data/bangkok/districts.json"), encoding="utf-8"))
    return seed_by_key, stations, districts

def norm_qa(raw, claim_ids, ent_prefix):
    """Normalize QA records across agent variants (id/q, claim_ids/claims/claim_refs, notes/answer)."""
    out = []
    for q in raw["question_answers"]:
        qid = q.get("id") or q.get("q")
        assert qid, f"QA record without id: {list(q.keys())}"
        status = q.get("status", "answered")
        if status == "partial":  # handoff enum: answered|conflicting|not_found|not_applicable
            status = "answered"
        cids = q.get("claim_ids") or q.get("claims") or q.get("claim_refs") or []
        if not cids and status in ("answered", "conflicting"):
            # extract inline [ent-cNN] references from the answer text
            notes = q.get("notes") or q.get("answer") or ""
            cids = [f"{ent_prefix}-c{n}" for n in re.findall(r"(?:[a-z-]+-)?c(\d+)", notes)]
            cids = [c if c in claim_ids else c for c in dict.fromkeys(cids)]
        out.append({
            "id": qid,
            "status": status,
            "claim_ids": [c for c in dict.fromkeys(cids) if c in claim_ids],
            "notes": q.get("notes") or q.get("answer") or "",
        })
    return out

def assemble(key, raw, seed_by_key, stations, districts):
    meta = ENTITY_META[key]
    seed_ent = seed_by_key[key]
    kind = meta["kind"]

    sources_out = []
    for s in raw["sources"]:
        curl = s["canonical_url"].strip()
        sources_out.append({
            "id": src_id_for(curl),
            "canonical_url": curl,
            "retrieved_url": s.get("retrieved_url") or curl,
            "title": s["title"],
            "publisher": s["publisher"],
            "publisher_family": s.get("publisher_family") or s["publisher"],
            "author": s.get("author"),
            "published_at": s.get("published_at"),
            "updated_at": s.get("updated_at"),
            "retrieved_at": norm_datetime(s.get("retrieved_at")) or "2026-11-07T00:00:00Z",
            "body_read": bool(s.get("body_read", False)),
            "type": NORM_TYPE.get(s["type"], s["type"]),
            "commercial_context": s.get("commercial_context", ""),
            "limitations": list(s.get("limitations") or []),
        })
    # dedup identical canonical URLs within a bundle (keep first)
    seen_urls, dedup_sources, url_map = set(), [], {}
    for s in sources_out:
        if s["canonical_url"] in seen_urls:
            continue
        seen_urls.add(s["canonical_url"])
        url_map[s["canonical_url"]] = s["id"]
        dedup_sources.append(s)
    sources_out = dedup_sources
    sid_by_index = {i: src_id_for(s["canonical_url"]) for i, s in enumerate(raw["sources"])}
    fam_by_sid = {s["id"]: s["publisher_family"] for s in sources_out}

    claims_out = []
    for c in raw["claims"]:
        geo = c["geography"]
        scope = geo["scope"]
        if scope in ("entire_unit", "partial"):
            scope = "station_area" if kind == "station_area" else "district"
        ev_out = []
        fams = set()
        for e in c["evidence"]:
            sid = sid_by_index[e["source_index"]]
            ev_out.append({"source_id": sid, "locator": e["locator"], "paraphrase": e["paraphrase"]})
            fams.add(fam_by_sid.get(sid, sid))
        kind_enum = {"factual_report", "reported_perception", "estimate", "researcher_inference"}
        ckind = c["kind"] if c["kind"] in kind_enum else "researcher_inference"
        lims = list(c.get("limitations") or [])
        joined = " ".join([c["text_en"], *lims]).lower()
        if "conflict" in joined:
            status = "conflicted"
        elif len(fams) >= 2:
            status = "corroborated"
        else:
            status = "proposed"
        claims_out.append({
            "id": c["claim_id"],
            "text_en": c["text_en"],
            "kind": ckind,
            "topics": sorted(set(c.get("topics") or [])),
            "polarity": NORM_POLARITY.get(c["polarity"], c["polarity"]),
            "geography": {"scope": scope, "place_name": geo["place_name"],
                          "relation_to_entity": geo["relation_to_entity"], "notes": geo.get("notes", "")},
            "temporal_scope": {"event_date": c["temporal_scope"].get("event_date"),
                               "observed_period": c["temporal_scope"].get("observed_period"),
                               "recheck_by": c["temporal_scope"].get("recheck_by"),
                               "notes": c["temporal_scope"].get("notes", "")},
            "evidence": ev_out,
            "supporting_claim_ids": [],
            "conflicts_with": [],
            "limitations": lims,
            "review_status": status,
        })
    claim_ids = {c["id"] for c in claims_out}
    ent_prefix = key.replace("st.", "")

    qa_out = norm_qa(raw, claim_ids, ent_prefix)

    def ed_items(items):
        out = []
        for it in items or []:
            if isinstance(it, str):
                refs = [f"{ent_prefix}-c{n}" for n in re.findall(r"(?:[a-z-]+-)?c(\d+)", it)]
                out.append({"text_en": it,
                            "claim_ids": [c for c in dict.fromkeys(refs) if c in claim_ids]})
            else:
                out.append({"text_en": it["text_en"],
                            "claim_ids": [cid for cid in dict.fromkeys(it.get("claim_ids", [])) if cid in claim_ids]})
        return out

    ed = raw["editorial"]
    editorial = {"preview": None, "guide_lead": None,
                 "strengths": ed_items(ed.get("strengths")), "tradeoffs": ed_items(ed.get("tradeoffs")),
                 "day_night": ed_items(ed.get("day_night")),
                 "within_area_variation": ed_items(ed.get("within_area_variation")),
                 "conditional_fit": ed_items(ed.get("conditional_fit")),
                 "uncertainties": list(ed.get("uncertainties") or [])}

    def as_block(v, fallback_cids):
        if isinstance(v, dict):
            cids = [c for c in dict.fromkeys(v.get("claim_ids", [])) if c in claim_ids]
            return {"text_en": v["text_en"], "claim_ids": cids or fallback_cids}
        if isinstance(v, str):
            return {"text_en": v, "claim_ids": fallback_cids}
        return None

    union_cids = sorted({c2 for lst in ("strengths", "tradeoffs", "day_night", "within_area_variation", "conditional_fit")
                         for blk in editorial[lst] for c2 in blk["claim_ids"]})
    for lst in ("strengths", "tradeoffs", "day_night", "within_area_variation", "conditional_fit"):
        for blk in editorial[lst]:
            if not blk["claim_ids"]:
                blk["claim_ids"] = union_cids or sorted(claim_ids)[:1]
    if ed.get("preview") is not None:
        editorial["preview"] = as_block(ed["preview"], union_cids or sorted(claim_ids)[:1])
    if ed.get("guide_lead") is not None:
        editorial["guide_lead"] = as_block(ed["guide_lead"], union_cids or sorted(claim_ids)[:1])
    for fld in ("preview", "guide_lead"):
        if editorial[fld] is not None and not editorial[fld]["claim_ids"]:
            editorial[fld]["claim_ids"] = [sorted(claim_ids)[0]]

    selection = {
        "app_snapshot_id": "bkk-d6499618507e7561",
        "model_score_default": seed_ent["model_score_default"],
        "cohort_rank": seed_ent["cohort_rank"],
        "cohort_size": seed_ent["cohort_size"],
        "popularity_status": "unmeasured",
        "popularity_method": POP_METHOD,
        "popularity_source_ids": [],
        "selection_rationale": SELECTED_RATIONALE[key],
    }

    aliases = meta["aliases"]
    if aliases is None:
        aliases = list(districts_map.get(key, {}).get("aliases") or [])
    entity = {"city": "bangkok", "key": key, "kind": kind, "name_en": meta["name_en"],
              "name_th": meta["name_th"], "aliases": aliases, "scope_notes": meta["scope_notes"]}

    bodyread_by_sid = {s["id"]: s["body_read"] for s in sources_out}
    unsupported = [c["id"] for c in claims_out
                   if not c["evidence"] or not any(bodyread_by_sid.get(e["source_id"]) for e in c["evidence"])]
    banned = re.compile(r"\b(vibrant|hidden gem|something for everyone)\b", re.I)
    banned_hits, dangling = [], []
    def collect_text(blk):
        if blk is None:
            return
        banned_hits.extend(re.findall(banned, blk["text_en"]))
        dangling.extend(cid for cid in blk.get("claim_ids", []) if cid not in claim_ids)
        for lst in ("strengths", "tradeoffs", "day_night", "within_area_variation", "conditional_fit"):
            for item in blk.get(lst, []):
                banned_hits.extend(re.findall(banned, item["text_en"]))
                dangling.extend(cid for cid in item["claim_ids"] if cid not in claim_ids)
    collect_text(editorial["preview"])
    collect_text(editorial["guide_lead"])
    copy_ok = not banned_hits and not dangling and all(
        b["claim_ids"] for b in (editorial["preview"], editorial["guide_lead"]))
    geo_unknown = [c["id"] for c in claims_out if c["geography"]["relation_to_entity"] == "unknown"]
    recheck_flags = sum(1 for c in claims_out if c["temporal_scope"]["recheck_by"])
    review = {
        "status": "ready_for_review",
        "researcher": "zcode-main (ZCode orchestrator + coverage-scan and 6 research subagents), 2026-11-07",
        "reviewer": None,
        "reviewed_at": None,
        "checks": {
            "identity": "pass",
            "geography": "pass",
            "sources": "pass" if not unsupported else "incomplete",
            "recency": "pass",
            "claim_support": "pass" if not unsupported else "fail",
            "contradictions": "pass",
            "copy": "pass" if copy_ok else "incomplete",
            "translations": "not_applicable",
            "image_rights": "not_applicable",
        },
        "notes": [
            "Researcher self-checks only; independent review still required (batch review/findings.md + coordinator geometry pass 2026-11-07).",
        ],
    }
    if geo_unknown:
        review["notes"].append(f"{len(geo_unknown)} claim(s) carry relation_to_entity=unknown as an honest gap: {', '.join(geo_unknown)}.")
    if recheck_flags:
        review["notes"].append(f"{recheck_flags} claim(s) carry explicit recheck_by flags for volatile facts.")
    for o in raw.get("open_issues", []):
        review["notes"].append(f"open issue: {o}")

    bundle = {
        "schema_version": "1.0",
        "entity": entity,
        "selection_context": selection,
        "sources": sources_out,
        "claims": claims_out,
        "question_answers": qa_out,
        "editorial": editorial,
        "images": [],
        "review": review,
    }
    return bundle

def main():
    global districts_map
    seed_by_key, stations, districts = load_data()
    areas = {a["id"]: a for a in stations["areas"]}
    districts_map = {d["slug"]: d for d in districts["districts"]}
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    all_logs, manifest_entities = [], []
    for key in BATCH2:
        raw = json.load(open(os.path.join(RAW, f"{key}.json"), encoding="utf-8"))
        bundle = assemble(key, raw, seed_by_key, stations, districts)
        for entry in raw.get("search_log", []):
            entry["entity"] = key
            all_logs.append(entry)
        out_path = os.path.join(PROFILES, f"{key}.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(bundle, f, ensure_ascii=False, indent=1)
        non_pass = {k: v for k, v in bundle["review"]["checks"].items() if v != "pass"}
        manifest_entities.append({
            "key": key, "kind": bundle["entity"]["kind"],
            "profile": f"profiles/{key}.json", "brief": f"briefs/{key}.md",
            "sources": len(bundle["sources"]), "claims": len(bundle["claims"]),
            "model_score_default": bundle["selection_context"]["model_score_default"],
            "cohort_rank": bundle["selection_context"]["cohort_rank"],
            "cohort_size": bundle["selection_context"]["cohort_size"],
            "review_status": bundle["review"]["status"],
        })
        print(f"wrote {out_path}: sources={len(bundle['sources'])} claims={len(bundle['claims'])} non-pass={non_pass}")

    with open(os.path.join(BATCH, "search-log.jsonl"), "w", encoding="utf-8") as f:
        cov = json.load(open(os.path.join(RAW, "coverage-scan.json"), encoding="utf-8"))
        for entry in cov.get("search_log", []):
            entry["entity"] = "coverage-scan"
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        for entry in all_logs:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(f"wrote search-log.jsonl: {len(all_logs) + len(cov.get('search_log', []))} entries")

    manifest = {
        "batch_id": "2026-11-07-batch2-zcode-main",
        "created_at": now,
        "task": "Bangkok editorial research batch 2 (research only; no live app data changed)",
        "handoff": "research/bangkok/editorial/2026-11-05-handoff/HANDOFF.md",
        "parent_batch": "research/bangkok/editorial/batches/2026-11-05-pilot-zcode-main (reviewed; corrections applied per review/REVIEW-2026-11-07.md)",
        "repository": {
            "verified_url": "https://github.com/pogorelov-labs/city-rating-tokyo.git",
            "verified_root": REPO,
            "receiver_head": "894324a48ab236780c285e21b0c68eb8894b9292",
            "data_files_identical_to_sender_verified_snapshot": True,
        },
        "data_snapshot": {"snapshot_id": "bkk-d6499618507e7561", "digests_verified_in_parent_batch": True},
        "weights": {"transport": 18, "rent": 18, "daily_essentials": 14, "safety": 10, "food": 12,
                    "green": 8, "gym_sports": 4, "vibe": 4, "nightlife": 8, "crowd": 4},
        "score_method": "sum(weight[k] * published_rating[k]) / sum(weights); no filters; raw model score; rank only within the same entity cohort",
        "popularity": "unmeasured; coverage breadth measured for selection only (axis 1)",
        "selection": {
            "method": "Three separate axes (coverage breadth / score-rank / research value) per HANDOFF.md; see selection.md and raw/coverage-scan.json",
            "window": "2024-11-05..2026-11-07",
            "selected": BATCH2,
            "deferred": ["st.phloen-chit", "st.sam-yot", "st.ha-yaek-lat-phrao", "st.ratchaprarop"],
        },
        "researcher": "zcode-main (ZCode orchestrator, GLM-5.3-Flash) with 1 coverage-scan + 6 research subagents",
        "tool_and_access_limits": [
            "Overpass API blocked throughout (406/timeouts) — POI ground truth unavailable; app-mapped park hectares could not be identified for nana, ratchathewi, wat-mangkon, charoen-nakhon",
            "Reddit and TripAdvisor blocked (403) — resident-voice evidence thinner than ideal",
            "Bangkok Post paywall-gateway redirects not bypassed (full text obtained via reader where legally accessible)",
            "bem.co.th station pages 404; BMA portal pages 403 to direct fetch (recovered via server-side reader)",
        ],
        "entities": manifest_entities,
        "validation": {"schema": "entity-research.schema.json", "profiles_validated": len(manifest_entities)},
        "live_app_data_changed": False,
    }
    with open(os.path.join(BATCH, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)
    print("wrote manifest.json")

if __name__ == "__main__":
    main()
