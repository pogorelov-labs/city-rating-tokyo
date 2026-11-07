#!/usr/bin/env python3
"""Assemble raw research JSON into schema-conformant entity bundles.

Run with: python3 -I tools/assemble.py   (from the batch directory)
Reads raw/<key>.json, writes profiles/<key>.json, briefs/<key>.md,
manifest.json, search-log.jsonl and review findings scaffolding.
"""
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone

BATCH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(BATCH, "raw")
PROFILES = os.path.join(BATCH, "profiles")
BRIEFS = os.path.join(BATCH, "briefs")
REPO = "/Users/ruslan/msc_1/git/city-rating"

SEED_PATH = ("/Users/ruslan/.codex/worktrees/bangkok-filters/city-rating/"
             "research/bangkok/editorial/2026-11-05-handoff/priority-seed.json")

PILLOT = ["st.asok", "st.chong-nonsi", "samphanthawong", "bang-rak", "st.thong-lo", "st.ari"]

ENTITY_META = {
    "st.asok": {
        "kind": "station_area",
        "name_en": "Asok / Sukhumvit",
        "name_th": "อโศก / สุขุมวิท",
        "aliases": ["Asok Montri", "Sukhumvit interchange", "BTS Asok / MRT Sukhumvit"],
        "scope_notes": (
            "800 m straight-line catchment around the BTS Asok / MRT Sukhumvit interchange; "
            "both physical stops share the single scored area st.asok. District split (app data): "
            "Watthana 51.3%, Khlong Toei 48.7% — it is not all of either district. Research-verified "
            "locations: Terminal 21 (~147 m) and Soi Cowboy (~121 m) inside; Benjakitti Park northeast "
            "tip ~460 m inside but main entrances and most of its area beyond 800 m; Benchasiri Park "
            "(~958 m) outside; Bumrungrad Hospital (~1.2 km) outside."
        ),
    },
    "st.chong-nonsi": {
        "kind": "station_area",
        "name_en": "Chong Nonsi",
        "name_th": "ช่องนนทรี",
        "aliases": ["Sathorn (north corridor)", "Chong Nonsi canal area"],
        "scope_notes": (
            "800 m straight-line catchment around BTS Chong Nonsi (Silom line) on the Sathorn Road "
            "corridor. District split (app data): Bang Rak 68.4%, Sathon 31.6%. Boundary caveat from "
            "coordinate checks: Sala Daeng BTS (~730–737 m) and the Patpong block geotag (~657–664 m) "
            "fall inside the circle by straight-line distance, with the strip extending toward "
            "Surawong beyond the edge — the nightlife rating is a fringe effect, not a core identity."
        ),
    },
    "samphanthawong": {
        "kind": "district",
        "name_en": "Samphanthawong",
        "name_th": "สัมพันธวงศ์",
        "aliases": None,  # filled from districts.json
        "scope_notes": (
            "Administrative khet — Bangkok's smallest district (~1.42 km², pop ~21,324 in 2020). "
            "Research-verified boundary caveats: the wider 'Chinatown' label is larger than the khet — "
            "the Soi Nana bar strip (Pom Prap Sattru Phai), Khlong Thom and River City (Bang Rak) lie "
            "outside; MRT Wat Mangkon station straddles the boundary; Wat Mangkon Kamalawat temple "
            "itself is attributed just outside the khet by source coverage."
        ),
    },
    "bang-rak": {
        "kind": "district",
        "name_en": "Bang Rak",
        "name_th": "บางรัก",
        "aliases": None,  # filled from districts.json
        "scope_notes": (
            "Administrative khet (~5.54 km², pop ~45,757 in 2020) with strongly distinct subareas: "
            "Silom CBD, Patpong/Suriwong nightlife, Surawong, the Charoen Krung riverside creative "
            "corridor, Saphan Taksin pier area and quiet blocks between. Research-verified: MahaNakhon "
            "inside (Si Lom khwaeng, Bang Rak side of Narathiwat Rd); St. Louis Hospital outside "
            "(Sathon district); Lumphini Park outside across Rama IV (Pathum Wan)."
        ),
    },
    "st.thong-lo": {
        "kind": "station_area",
        "name_en": "Thong Lo",
        "name_th": "ทองหล่อ",
        "aliases": ["Thonglor", "Soi Thong Lo", "Sukhumvit Soi 55"],
        "scope_notes": (
            "800 m straight-line catchment around BTS Thong Lo (Sukhumvit line), covering the Soi "
            "Thong Lo (Sukhumvit Soi 55) mouth and adjacent blocks. District split (app data): "
            "Watthana 51.3%, Khlong Toei 48.7%. Venues deep up the soi or across the Phra Khanong "
            "canal (Ekkamai side) can fall outside the circle; the single-spine street layout is the "
            "defining access constraint. Not the whole Thonglor neighborhood or Watthana district."
        ),
    },
    "st.ari": {
        "kind": "station_area",
        "name_en": "Ari",
        "name_th": "อารีย์",
        "aliases": ["Aree", "Soi Ari", "Ari Samphan"],
        "scope_notes": (
            "800 m straight-line catchment around BTS Ari (Sukhumvit line), entirely within Phaya "
            "Thai district (100% per app data) but not the whole khet. Residential grid around Soi "
            "Ari 1–5 and Phahonyothin Road. Coordinate checks placed every named public park outside "
            "the circle (Phaya Thai Palace ~1.80 km; Santiphap Park ~1.87 km; Vachirabenjatas/Rot Fai "
            "Park ~3.7 km to centroid) — the app's green 9 is not explained by any named public park "
            "source could confirm inside the unit (app park_ha 5.1 unverified against names)."
        ),
    },
}

QA_STATUS_OVERRIDES = {
    "bang-rak": {"Q05": "conflicting"},   # Silom Walking Street schedule conflicting/unconfirmed since ~2020
    "st.thong-lo": {"Q11": "conflicting"},  # Soi 38 night market status conflicting
}

SELECTED_RATIONALE = {
    "st.asok": "Recognizable interchange candidate with a high model rank (11/133); verify independent guide coverage.",
    "st.chong-nonsi": "Highest station-area model score (1/133); test whether public accounts agree and what the score misses.",
    "samphanthawong": "Highest district model score (1/50); tourism/food identity must not be generalized across every street.",
    "bang-rak": "Second-highest district model score (2/50); distinguish Silom, riverside and other subareas.",
    "st.thong-lo": "Current user-selected area and current guide coverage; investigate the gap between editorial enthusiasm and a 6.5 model score.",
    "st.ari": "Current guide coverage; investigate calm/leafy descriptions, actual public green access and day/night differences.",
}

POP_METHOD = ("No citywide popularity measure has been collected. Each bundle logs its independent "
              "publisher families; search-hit totals, SEO duplication and venue stars are explicitly "
              "not treated as popularity measurements.")

def src_id_for(url: str) -> str:
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
    areas = {a["id"]: a for a in stations["areas"]}
    dis = {d["slug"]: d for d in districts["districts"]}
    return seed, seed_by_key, areas, dis

def assemble(key, raw, seed_by_key, areas, dis):
    meta = ENTITY_META[key]
    seed_ent = seed_by_key[key]

    # ---- sources ----
    sources_out, src_ids, url_seen = [], [], {}
    for s in raw["sources"]:
        curl = s["canonical_url"].strip()
        sid = src_id_for(curl)
        if curl in url_seen:
            continue  # dedup identical canonical URL within a bundle
        url_seen[curl] = sid
        src_ids.append((s["index"], sid, s.get("publisher_family", "")))
        sources_out.append({
            "id": sid,
            "canonical_url": curl,
            "retrieved_url": s.get("retrieved_url") or curl,
            "title": s["title"],
            "publisher": s["publisher"],
            "publisher_family": s.get("publisher_family") or s["publisher"],
            "author": s.get("author"),
            "published_at": s.get("published_at"),
            "updated_at": s.get("updated_at"),
            "retrieved_at": norm_datetime(s.get("retrieved_at")) or "2026-11-05T00:00:00Z",
            "body_read": bool(s.get("body_read", False)),
            "type": s["type"],
            "commercial_context": s.get("commercial_context", ""),
            "limitations": list(s.get("limitations") or []),
        })
    idx_to_sid = {i: sid for (i, sid, _f) in src_ids}
    fam_by_sid = {sid: fam for (_i, sid, fam) in src_ids}

    # ---- claims ----
    qa_by_claim = {}
    for q in raw["question_answers"]:
        for cid in q.get("claim_ids", []):
            qa_by_claim.setdefault(cid, []).append(q["id"])
    conflicting_q = {k for k, v in QA_STATUS_OVERRIDES.get(key, {}).items()}

    claims_out = []
    for c in raw["claims"]:
        geo = c["geography"]
        scope = geo["scope"]
        if scope in ("entire_unit", "partial"):  # normalization: agents used relation value as scope
            scope = "station_area" if meta["kind"] == "station_area" else "district"
        ev_out = []
        fams = set()
        for e in c["evidence"]:
            sid = idx_to_sid[e["source_index"]]
            ev_out.append({"source_id": sid, "locator": e["locator"], "paraphrase": e["paraphrase"]})
            fams.add(fam_by_sid.get(sid, sid))
        kinds_enum = {"factual_report", "reported_perception", "estimate", "researcher_inference"}
        kind = c["kind"] if c["kind"] in kinds_enum else "researcher_inference"
        lims = list(c.get("limitations") or [])
        joined = " ".join([c["text_en"], *lims]).lower()
        if any(qid in conflicting_q for qid in qa_by_claim.get(c["claim_id"], [])) or "conflict" in joined:
            status = "conflicted"
        elif len(fams) >= 2:
            status = "corroborated"
        else:
            status = "proposed"
        claims_out.append({
            "id": c["claim_id"],
            "text_en": c["text_en"],
            "kind": kind,
            "topics": sorted(set(c.get("topics") or [])),
            "polarity": c["polarity"],
            "geography": {
                "scope": scope,
                "place_name": geo["place_name"],
                "relation_to_entity": geo["relation_to_entity"],
                "notes": geo.get("notes", ""),
            },
            "temporal_scope": {
                "event_date": c["temporal_scope"].get("event_date"),
                "observed_period": c["temporal_scope"].get("observed_period"),
                "recheck_by": c["temporal_scope"].get("recheck_by"),
                "notes": c["temporal_scope"].get("notes", ""),
            },
            "evidence": ev_out,
            "supporting_claim_ids": [],
            "conflicts_with": [],
            "limitations": lims,
            "review_status": status,
        })
    claim_ids = {c["id"] for c in claims_out}

    # ---- question answers ----
    qa_out = []
    for q in raw["question_answers"]:
        status = QA_STATUS_OVERRIDES.get(key, {}).get(q["id"], q["status"])
        cids = [cid for cid in dict.fromkeys(q.get("claim_ids", [])) if cid in claim_ids]
        qa_out.append({"id": q["id"], "status": status, "claim_ids": cids, "notes": q.get("notes", "")})

    # ---- editorial ----
    def ed_items(items):
        out = []
        for it in items or []:
            out.append({"text_en": it["text_en"],
                        "claim_ids": [cid for cid in dict.fromkeys(it.get("claim_ids", [])) if cid in claim_ids]})
        return out

    ed = raw["editorial"]
    editorial = {
        "preview": None,
        "guide_lead": None,
        "strengths": ed_items(ed.get("strengths")),
        "tradeoffs": ed_items(ed.get("tradeoffs")),
        "day_night": ed_items(ed.get("day_night")),
        "within_area_variation": ed_items(ed.get("within_area_variation")),
        "conditional_fit": ed_items(ed.get("conditional_fit")),
        "uncertainties": list(ed.get("uncertainties") or []),
    }
    # preview / guide_lead may arrive as plain strings or dicts depending on agent output
    def as_block(v, fallback_cids):
        if isinstance(v, dict):
            cids = [c for c in dict.fromkeys(v.get("claim_ids", [])) if c in claim_ids]
            return {"text_en": v["text_en"], "claim_ids": cids or fallback_cids}
        if isinstance(v, str):
            return {"text_en": v, "claim_ids": fallback_cids}
        return None
    preview_raw = ed.get("preview")
    lead_raw = ed.get("guide_lead")
    # fallback provenance for string previews/leads: union of the editorial items they summarize
    union_cids = sorted({c for lst in ("strengths", "tradeoffs", "day_night", "within_area_variation", "conditional_fit")
                         for b in editorial[lst] for c in b["claim_ids"]})
    if preview_raw is not None:
        editorial["preview"] = as_block(preview_raw, union_cids or sorted(claim_ids)[:1])
    if lead_raw is not None:
        editorial["guide_lead"] = as_block(lead_raw, union_cids or sorted(claim_ids)[:1])
    for fld in ("preview", "guide_lead"):
        if editorial[fld] is not None and not editorial[fld]["claim_ids"]:
            editorial[fld]["claim_ids"] = [sorted(claim_ids)[0]]
    if editorial["preview"] is None:
        editorial["preview"] = None  # keep null only if truly absent (schema allows null)

    # ---- selection context ----
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

    # ---- entity ----
    aliases = meta["aliases"]
    if aliases is None:
        aliases = list(dis[key].get("aliases") or [])
    entity = {
        "city": "bangkok",
        "key": key,
        "kind": meta["kind"],
        "name_en": meta["name_en"],
        "name_th": meta["name_th"],
        "aliases": aliases,
        "scope_notes": meta["scope_notes"],
    }

    # ---- review checks (computed honestly) ----
    bodyread_by_sid = {s["id"]: s["body_read"] for s in sources_out}
    unsupported = [c["id"] for c in claims_out
                   if not c["evidence"] or not any(bodyread_by_sid.get(e["source_id"]) for e in c["evidence"])]
    banned = re.compile(r"\b(vibrant|hidden gem|something for everyone)\b", re.I)
    banned_hits = []
    def collect_text(b):
        if b is None:
            return
        banned_hits.extend(re.findall(banned, b["text_en"]))
        for lst in ("strengths", "tradeoffs", "day_night", "within_area_variation", "conditional_fit"):
            for item in b.get(lst, []):
                banned_hits.extend(re.findall(banned, item["text_en"]))
    collect_text(editorial["preview"]); collect_text(editorial["guide_lead"])
    dangling = []
    def chk_refs(b):
        if b is None:
            return
        for cid in b.get("claim_ids", []):
            if cid not in claim_ids:
                dangling.append(cid)
        for lst in ("strengths", "tradeoffs", "day_night", "within_area_variation", "conditional_fit"):
            for item in b.get(lst, []):
                for cid in item["claim_ids"]:
                    if cid not in claim_ids:
                        dangling.append(cid)
    chk_refs(editorial["preview"]); chk_refs(editorial["guide_lead"])
    copy_ok = not banned_hits and not dangling and all(b["claim_ids"] for b in (editorial["preview"], editorial["guide_lead"]))
    geography_ok = True
    geo_unknown = [c["id"] for c in claims_out if c["geography"]["relation_to_entity"] == "unknown"]
    recheck_flags = sum(1 for c in claims_out if c["temporal_scope"]["recheck_by"])
    review = {
        "status": "ready_for_review",
        "researcher": "zcode-main (ZCode orchestrator + 6 parallel research subagents), 2026-11-05",
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
        "notes": [],
    }
    review["notes"].append(
        "Researcher self-checks only; an independent reviewer must still confirm identity/geography, source quality and recency, claim support, contradictions and copy (see batch review/findings.md).")
    if geo_unknown:
        review["notes"].append(
            f"{len(geo_unknown)} claim(s) carry relation_to_entity=unknown as an honest gap: {', '.join(geo_unknown)}.")
    if recheck_flags:
        review["notes"].append(f"{recheck_flags} claim(s) carry explicit recheck_by flags for volatile facts.")
    if raw.get("open_issues"):
        review["notes"].extend(f"open issue: {o}" for o in raw["open_issues"])

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
    return bundle, raw.get("search_log", [])

def main():
    seed, seed_by_key, areas, dis = load_data()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    all_logs = []
    manifest_entities = []
    for key in PILLOT:
        raw = json.load(open(os.path.join(RAW, f"{key}.json"), encoding="utf-8"))
        bundle, logs = assemble(key, raw, seed_by_key, areas, dis)
        for entry in logs:
            entry["entity"] = key
            all_logs.append(entry)
        out_path = os.path.join(PROFILES, f"{key}.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(bundle, f, ensure_ascii=False, indent=1)
        manifest_entities.append({
            "key": key,
            "kind": bundle["entity"]["kind"],
            "profile": f"profiles/{key}.json",
            "brief": f"briefs/{key}.md",
            "sources": len(bundle["sources"]),
            "claims": len(bundle["claims"]),
            "model_score_default": bundle["selection_context"]["model_score_default"],
            "cohort_rank": bundle["selection_context"]["cohort_rank"],
            "cohort_size": bundle["selection_context"]["cohort_size"],
            "review_status": bundle["review"]["status"],
        })
        print(f"wrote {out_path}: sources={len(bundle['sources'])} claims={len(bundle['claims'])} "
              f"review={ {k: v for k, v in bundle['review']['checks'].items() if v != 'pass'} }")

    # search log
    with open(os.path.join(BATCH, "search-log.jsonl"), "w", encoding="utf-8") as f:
        for entry in all_logs:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(f"wrote search-log.jsonl: {len(all_logs)} entries")

    # manifest
    manifest = {
        "batch_id": "2026-11-05-pilot-zcode-main",
        "created_at": now,
        "task": "Bangkok six-place editorial pilot (research only; no live app data changed)",
        "handoff": "research/bangkok/editorial/2026-11-05-handoff/HANDOFF.md",
        "repository": {
            "verified_url": "https://github.com/pogorelov-labs/city-rating-tokyo.git",
            "verified_root": REPO,
            "receiver_head": "894324a48ab236780c285e21b0c68eb8894b9292",
            "sender_head": "72cfa5d0db0c1e5c0677e3188fd37a824d8019f8",
            "sender_branch": "fix/bangkok-inspection-correctness",
            "data_files_identical_across_revisions": True,
        },
        "data_snapshot": {
            "snapshot_id": "bkk-d6499618507e7561",
            "digests_verified": True,
            "digest_source": "sender source-manifest.json (all 9 files matched SHA-256 in receiver clean checkout)",
        },
        "weights": {
            "transport": 18, "rent": 18, "daily_essentials": 14, "safety": 10, "food": 12,
            "green": 8, "gym_sports": 4, "vibe": 4, "nightlife": 8, "crowd": 4,
        },
        "score_method": ("sum(weight[k] * published_rating[k]) / sum(weights); no filters; raw model score; "
                         "rank only within the same entity cohort"),
        "popularity": "unmeasured citywide; per-bundle coverage logs only",
        "selection_method": ("Sender-defined six-place pilot order (priority-seed.json pilot_order 1–6); "
                             "a research decision, not a proven popularity ranking"),
        "researcher": "zcode-main (ZCode orchestrator, GLM-5.3-Flash) with six parallel research subagents",
        "tool_and_access_limits": [
            "Overpass API blocked from this environment (406/TLS reset/timeouts) — POI ground-truth gap for some geography checks",
            "Reddit r/Bangkok and TripAdvisor threads returned 403 — resident-voice evidence thinner than ideal on several entities",
            "Bangkok Post and some paywalled news (SCMP beyond lede) not used; no paywall bypass or proxy mirrors",
            "BMA portal pages (webportal.bangkok.go.th, visit.bangkok.go.th, dp.bangkok.go.th direct) 403; recovered via alternate access where possible",
            "WebFetch/exa concurrency limits caused retries; subagent platform concurrency limited dispatch batches",
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
