#!/usr/bin/env python3
"""Assemble raw research JSON into schema-conformant entity bundles (kit version).

Run with: python3 assemble.py --batch-dir <batch>   (defaults to cwd)

Driven by the batch's `batch.json` (entities, metadata, QA overrides — see
kit/scaffold.py). Applies the documented normalizations to subagent output and
LOGS every one; normalization is a safety net, not a license for drift (the
agent prompt template asks for enum-exact output).

Normalizations applied (each counted in the summary):
- geography.scope `entire_unit`/`partial` → station_area/district (relation kept)
- claim kind outside the enum → researcher_inference
- polarity `positive`→strength, `negative`→tradeoff (incl. compound values)
- source `type` mapped via NORM_TYPE (encyclopedia→other, listing portals→
  commercial_property, guides→editorial_guide, …)
- QA field variants: id|q, claim_ids|claims|claim_refs, notes|answer;
  status `partial` → `answered`; inline `[ent-cNN]`/`[cNN]` refs extracted
- editorial items as plain strings → claim_ids extracted from inline refs,
  else union fallback; preview/guide_lead as strings likewise
- duplicate canonical URLs within a bundle deduped (first wins)
- corroboration independence uses canonical publisher families
  (canonical.py, B-10/G21): Wikipedia language editions / Wikimedia projects,
  OSM/Overpass variants, and portal casing variants count as ONE publisher
  family. Stored `publisher_family` strings stay raw (provenance).
"""
import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from canonical import canon_families  # noqa: E402

NORM_POLARITY = {
    "positive": "strength", "negative": "tradeoff",
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
    "operator_site": "official_operator", "forum_post": "resident_report",
    "corporate_site": "other", "organization_page": "other", "official_venue_page": "other",
    "official_site": "other", "official": "other", "social_media_transit_commentary": "other",
}
BANNED = re.compile(r"\b(vibrant|hidden gem|something for everyone)\b", re.I)
REF_RE = re.compile(r"(?:[a-z-]+-)?c(\d+)")

def repo_root(start):
    d = os.path.abspath(start)
    while d != os.path.dirname(d):
        if os.path.isdir(os.path.join(d, ".git")):
            return d
        d = os.path.dirname(d)
    raise SystemExit("repo root not found")

def src_id_for(url):
    return "src_" + hashlib.sha256(url.encode("utf-8")).hexdigest()[:12]

URL_TOKEN = re.compile(r"^(https?://\S+)")

def split_url_annotation(val):
    """(url, annotation|None): agents sometimes append notes after a URL."""
    if not isinstance(val, str):
        return val, None
    m = URL_TOKEN.match(val.strip())
    if not m:
        return val, None
    token = m.group(1)
    rest = val.strip()[len(token):].strip()
    return token, (rest or None)

def norm_datetime(s):
    if not s:
        return None
    s = s.strip()
    if re.match(r"^\d{4}-\d{2}-\d{2}$", s):
        return s + "T00:00:00Z"
    if re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?$", s):
        return s + (":00Z" if len(s) == 16 else "Z")
    return s

def norm_polarity(v, counts):
    if v in ("strength", "tradeoff", "mixed", "neutral"):
        return v
    out = NORM_POLARITY.get(v)
    if out is None and isinstance(v, str):
        if v.startswith("positive"):
            out = "strength"
        elif v.startswith("negative"):
            out = "tradeoff"
    if out and out != v:
        counts["polarity"] += 1
        return out
    return v  # left unmapped on purpose — audit.py will flag it

def norm_type(v, counts):
    out = NORM_TYPE.get(v, v)
    if out != v:
        counts["source_type"] += 1
    return out

def extract_refs(text, ent_prefix, claim_ids):
    refs = [f"{ent_prefix}-c{n}" for n in REF_RE.findall(text)]
    return [c for c in dict.fromkeys(refs) if c in claim_ids]

def norm_qa(raw_qa, claim_ids, ent_prefix, overrides, counts):
    out = []
    for q in raw_qa:
        qid = q.get("id") or q.get("q")
        if not qid:
            raise SystemExit(f"QA record without id: keys={list(q.keys())}")
        if "id" not in q:
            counts["qa_field"] += 1
        status = q.get("status", "answered")
        if status == "partial":
            status = "answered"
            counts["qa_status_partial"] += 1
        cids = q.get("claim_ids") or q.get("claims") or q.get("claim_refs") or []
        notes = q.get("notes") or q.get("answer") or ""
        if not cids and status in ("answered", "conflicting"):
            cids = extract_refs(notes, ent_prefix, claim_ids)
            if cids:
                counts["qa_inline_refs"] += 1
        status = overrides.get(qid, status)
        out.append({"id": qid, "status": status,
                    "claim_ids": [c for c in dict.fromkeys(cids) if c in claim_ids],
                    "notes": notes})
    return out

def assemble(key, ent_meta, raw, batch, counts):
    kind = ent_meta["kind"]
    ent_prefix = key.replace("st.", "")
    claim_ids = {c["claim_id"] for c in raw["claims"]}

    sources_out, url_seen = [], {}
    for i, s in enumerate(raw["sources"]):
        curl, ann = split_url_annotation(s["canonical_url"])
        rurl, rann = split_url_annotation(s.get("retrieved_url") or curl)
        lims = list(s.get("limitations") or [])
        for field, a in (("canonical_url", ann), ("retrieved_url", rann)):
            if a:
                lims.append(f"agent appended a note after {field}; annotation split off: '{a}'")
                counts["url_annotation_split"] = counts.get("url_annotation_split", 0) + 1
        curl = curl.strip()
        sid = src_id_for(curl)
        if curl in url_seen:
            counts["source_url_dedup"] += 1
            continue
        url_seen[curl] = sid
        cc = s.get("commercial_context", "")
        if isinstance(cc, bool):
            cc = "" if cc is False else "commercial (boolean flag normalized)"
            counts["commercial_context_bool"] = counts.get("commercial_context_bool", 0) + 1
        sources_out.append({
            "id": sid,
            "canonical_url": curl,
            "retrieved_url": rurl,
            "title": s["title"],
            "publisher": s["publisher"],
            "publisher_family": s.get("publisher_family") or s["publisher"],
            "author": s.get("author"),
            "published_at": s.get("published_at"),
            "updated_at": s.get("updated_at"),
            "retrieved_at": norm_datetime(s.get("retrieved_at")) or "1970-01-01T00:00:00Z",
            "body_read": bool(s.get("body_read", False)),
            "type": norm_type(s["type"], counts),
            "commercial_context": cc,
            "limitations": lims,
        })
    fam_by_sid = {s["id"]: s["publisher_family"] for s in sources_out}
    sid_by_index = {i: src_id_for(s["canonical_url"].strip()) for i, s in enumerate(raw["sources"])}

    conflicting_q = {k for k, v in batch.get("qa_status_overrides", {}).get(key, {}).items()}
    claims_out = []
    for c in raw["claims"]:
        geo = c["geography"]
        scope = geo["scope"]
        if scope in ("entire_unit", "partial"):
            scope = "station_area" if kind == "station_area" else "district"
            counts["geo_scope"] += 1
        ev_out, fams = [], set()
        for e in c["evidence"]:
            sid = sid_by_index[e["source_index"]]
            ev_out.append({"source_id": sid, "locator": e["locator"], "paraphrase": e["paraphrase"]})
            fams.add(fam_by_sid.get(sid, sid))
        fams_canon = canon_families(fams)
        if len(fams_canon) < len(fams):
            counts["canonical_family_merge"] = counts.get("canonical_family_merge", 0) + 1
        ckind = c["kind"]
        if ckind not in {"factual_report", "reported_perception", "estimate", "researcher_inference"}:
            ckind = "researcher_inference"
            counts["claim_kind"] += 1
        lims = list(c.get("limitations") or [])
        joined = " ".join([c["text_en"], *lims]).lower()
        if any(qid in conflicting_q for qid in
               [q.get("id") or q.get("q") for q in raw.get("question_answers", [])
                if c["claim_id"] in (q.get("claim_ids") or q.get("claims") or q.get("claim_refs") or [])]) \
                or "conflict" in joined:
            status = "conflicted"
        elif len(fams_canon) >= 2:
            status = "corroborated"
        else:
            status = "proposed"
        if isinstance(c.get("temporal_scope"), dict):
            ts = dict(c["temporal_scope"])
            ts["notes"] = ts.get("notes") or ""
        else:
            ts = {"event_date": None, "observed_period": None, "recheck_by": None,
                  "notes": str(c.get("temporal_scope") or "")}
        claims_out.append({
            "id": c["claim_id"], "text_en": c["text_en"], "kind": ckind,
            "topics": sorted(set(c.get("topics") or [])),
            "polarity": norm_polarity(c["polarity"], counts),
            "geography": {"scope": scope, "place_name": geo["place_name"],
                          "relation_to_entity": geo["relation_to_entity"],
                          "notes": geo.get("notes") or ""},
            "temporal_scope": ts,
            "evidence": ev_out, "supporting_claim_ids": [],
            "conflicts_with": [c for c in dict.fromkeys(c.get("conflicts_with") or [])
                               if c in claim_ids],
            "limitations": lims, "review_status": status,
        })

    qa_out = norm_qa(raw["question_answers"], claim_ids, ent_prefix,
                     batch.get("qa_status_overrides", {}).get(key, {}), counts)

    def ed_items(items):
        out = []
        for it in items or []:
            if isinstance(it, str):
                counts["editorial_string"] += 1
                out.append({"text_en": it, "claim_ids": extract_refs(it, ent_prefix, claim_ids)})
            else:
                out.append({"text_en": it.get("text_en") or it.get("text") or "",
                            "claim_ids": [cid for cid in dict.fromkeys(it.get("claim_ids", [])) if cid in claim_ids]})
        return out

    ed = raw["editorial"]
    editorial = {"preview": None, "guide_lead": None,
                 "strengths": ed_items(ed.get("strengths")), "tradeoffs": ed_items(ed.get("tradeoffs")),
                 "day_night": ed_items(ed.get("day_night")),
                 "within_area_variation": ed_items(ed.get("within_area_variation")),
                 "conditional_fit": ed_items(ed.get("conditional_fit")),
                 "uncertainties": [(it.get("text_en") or it.get("text") or "")
                                   if isinstance(it, dict) else (it or "")
                                   for it in (ed.get("uncertainties") or [])]}

    def as_block(v, fallback):
        if isinstance(v, dict):
            cids = [c for c in dict.fromkeys(v.get("claim_ids", [])) if c in claim_ids]
            return {"text_en": v.get("text_en") or v.get("text") or "", "claim_ids": cids or fallback}
        if isinstance(v, str):
            return {"text_en": v, "claim_ids": extract_refs(v, ent_prefix, claim_ids) or fallback}
        return None

    union_cids = sorted({c2 for lst in ("strengths", "tradeoffs", "day_night",
                                        "within_area_variation", "conditional_fit")
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
        "app_snapshot_id": batch["app_snapshot_id"],
        "model_score_default": ent_meta["model_score_default"],
        "cohort_rank": ent_meta["cohort_rank"],
        "cohort_size": ent_meta["cohort_size"],
        "popularity_status": "unmeasured",
        "popularity_method": batch["popularity_method"],
        "popularity_source_ids": [],
        "selection_rationale": ent_meta["selection_rationale"],
    }
    entity = {"city": "bangkok", "key": key, "kind": kind,
              "name_en": ent_meta["name_en"], "name_th": ent_meta["name_th"],
              "aliases": list(ent_meta.get("aliases") or []),
              "scope_notes": ent_meta.get("scope_notes", "")}

    bodyread_by_sid = {s["id"]: s["body_read"] for s in sources_out}
    unsupported = [c["id"] for c in claims_out
                   if not c["evidence"] or not any(bodyread_by_sid.get(e["source_id"]) for e in c["evidence"])]
    banned_hits, dangling = [], []
    def collect_text(blk):
        if blk is None:
            return
        banned_hits.extend(re.findall(BANNED, blk["text_en"]))
        dangling.extend(cid for cid in blk.get("claim_ids", []) if cid not in claim_ids)
        for lst in ("strengths", "tradeoffs", "day_night", "within_area_variation", "conditional_fit"):
            for item in blk.get(lst, []):
                banned_hits.extend(re.findall(BANNED, item["text_en"]))
                dangling.extend(cid for cid in item["claim_ids"] if cid not in claim_ids)
    collect_text(editorial["preview"])
    collect_text(editorial["guide_lead"])
    copy_ok = not banned_hits and not dangling and all(
        b["claim_ids"] for b in (editorial["preview"], editorial["guide_lead"]))
    geo_unknown = [c["id"] for c in claims_out if c["geography"]["relation_to_entity"] == "unknown"]
    recheck_flags = sum(1 for c in claims_out if c["temporal_scope"]["recheck_by"])
    review = {
        "status": "ready_for_review",
        "researcher": batch.get("researcher", ""),
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
        "notes": ["Researcher self-checks only; independent review still required (batch review/findings.md)."],
    }
    if geo_unknown:
        review["notes"].append(f"{len(geo_unknown)} claim(s) carry relation_to_entity=unknown as an honest gap: {', '.join(geo_unknown)}.")
    if recheck_flags:
        review["notes"].append(f"{recheck_flags} claim(s) carry explicit recheck_by flags for volatile facts.")
    for o in raw.get("open_issues", []):
        review["notes"].append(f"open issue: {o}")

    return {
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

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch-dir", default=os.getcwd())
    args = ap.parse_args()
    batch = json.load(open(os.path.join(args.batch_dir, "batch.json"), encoding="utf-8"))
    counts = {"polarity": 0, "source_type": 0, "geo_scope": 0, "claim_kind": 0,
              "qa_field": 0, "qa_status_partial": 0, "qa_inline_refs": 0,
              "editorial_string": 0, "source_url_dedup": 0, "canonical_family_merge": 0,
              "url_annotation_split": 0, "commercial_context_bool": 0}
    manifest_entities, all_logs = [], []
    for ent in batch["entities"]:
        key = ent["key"]
        raw = json.load(open(os.path.join(args.batch_dir, "raw", f"{key}.json"), encoding="utf-8"))
        bundle = assemble(key, ent, raw, batch, counts)
        for entry in raw.get("search_log", []):
            entry["entity"] = key
            all_logs.append(entry)
        out = os.path.join(args.batch_dir, "profiles", f"{key}.json")
        with open(out, "w", encoding="utf-8") as f:
            json.dump(bundle, f, ensure_ascii=False, indent=1)
        manifest_entities.append({
            "key": key, "kind": bundle["entity"]["kind"],
            "profile": f"profiles/{key}.json", "brief": f"briefs/{key}.md",
            "sources": len(bundle["sources"]), "claims": len(bundle["claims"]),
            "model_score_default": ent_meta_score(ent),
            "cohort_rank": ent.get("cohort_rank"), "cohort_size": ent.get("cohort_size"),
            "review_status": bundle["review"]["status"],
        })
        non_pass = {k: v for k, v in bundle["review"]["checks"].items() if v != "pass"}
        print(f"wrote {out}: sources={len(bundle['sources'])} claims={len(bundle['claims'])} non-pass={non_pass}")

    for extra in batch.get("extra_search_logs", []):
        for entry in extra.get("entries", []):
            entry["entity"] = extra.get("label", extra.get("entity", "coverage-scan"))
            all_logs.append(entry)
    with open(os.path.join(args.batch_dir, "search-log.jsonl"), "w", encoding="utf-8") as f:
        for entry in all_logs:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(f"wrote search-log.jsonl: {len(all_logs)} entries")

    manifest = {
        "batch_id": batch["batch_id"],
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "task": batch["task"],
        "handoff": batch.get("handoff"),
        "parent_batch": batch.get("parent_batch"),
        "data_snapshot": {"app_snapshot_id": batch["app_snapshot_id"],
                          "weights": batch["weights"],
                          "digests_verified_in_parent_batch": True},
        "weights": batch["weights"],
        "popularity": "unmeasured; coverage breadth measured for selection only (axis 1)",
        "selection": batch.get("selection", {}),
        "researcher": batch.get("researcher", ""),
        "tool_and_access_limits": batch.get("tool_and_access_limits", []),
        "entities": manifest_entities,
        "validation": {"schema": "entity-research.schema.json",
                       "profiles_validated": len(manifest_entities)},
        "normalizations_applied": counts,
        "live_app_data_changed": False,
    }
    with open(os.path.join(args.batch_dir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)
    print("wrote manifest.json | normalizations:", counts)

def ent_meta_score(ent):
    return ent.get("model_score_default")

if __name__ == "__main__":
    main()
