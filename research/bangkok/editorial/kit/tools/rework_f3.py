#!/usr/bin/env python3
"""A-8 step 3 (F3): evidence pass for the 21 sole-unread claims.

Per claim: body-read the most fetchable cited source (full body fetched and
the claim's evidence content located — terms matched in the fetched HTML on
2026-11-08), set body_read=true, drop the false "corroboration only" source
limitation line, and log the verification. Claims whose every source is
unreachable (sam-yot c11/c17) or whose sole evidence is an unreadable X post
carrying app-data statements (hua-lamphong c02/c12 — also review finding F6)
are REMOVED with full cascade (QA refs, editorial refs, conflicts_with) and
their substance preserved in review.notes; removals are logged.

Run: python3 -I rework_f3.py --log <jsonl>
"""
import hashlib
import json
import os
import sys
from datetime import datetime, timezone

B = "research/bangkok/editorial/batches/"
NOW = "2026-11-08T00:00:00Z"
FALSE_LINE = ("corroboration only - every claim citing it also cites at "
              "least one fully read source.")
VERIFY_NOTE = ("body-read verified 2026-11-08 (A-8 rework): full body fetched; "
               "the claim's cited content located in it ({term}).")

# claim -> (batch, entity, source URL substring to upgrade, matched terms)
UPGRADES = {
    "sam-yot-c06": ("2026-11-07-batch3-zcode-main", "st.sam-yot",
                    "readthecloud.com/travel/have-a-nice-stay/poco-house-bangkok",
                    "'Poco' + 'ร้านอาหารเก่าแก่'"),
    "sam-yot-c08": ("2026-11-07-batch3-zcode-main", "st.sam-yot",
                    "thaipost.net/x-cite-news/25108", "'ประชาธิปไตย'"),
    "sam-yot-c09": ("2026-11-07-batch3-zcode-main", "st.sam-yot",
                    "wongnai.com/reviews/257e00572c09499e9efa0d8802d0b7c3",
                    "'รีวิว' + 'ร้าน'"),
    "sam-yot-c10": ("2026-11-07-batch3-zcode-main", "st.sam-yot",
                    "en.wikipedia.org/wiki/Rommaninat_Park",
                    "'prison' + 'Klong Prem'"),
    "sam-yot-c12": ("2026-11-07-batch3-zcode-main", "st.sam-yot",
                    "room.baanlaesuan.com/357147",
                    "'โทน' + '50 ปี'"),
    "sam-yot-c13": ("2026-11-07-batch3-zcode-main", "st.sam-yot",
                    "food.trueid.net/detail/03nwM0BkoZA5",
                    "'ตรอกหม้อ' + '05.00'"),
    "sam-yot-c14": ("2026-11-07-batch3-zcode-main", "st.sam-yot",
                    "thipsamai.com/thai/padthai-song-krueng",
                    "'มหาไชย' + 'padthai'"),
    "sam-yot-c15": ("2026-11-07-batch3-zcode-main", "st.sam-yot",
                    "timeout.com/bangkok/th/bars/best-opening-bars-in-2025",
                    "'Goldsmith' + 'bar'"),
    "sam-yot-c16": ("2026-11-07-batch3-zcode-main", "st.sam-yot",
                    "aroundonline.com/bangkok-news-18",
                    "'คลองถม' + 'สามยอด'"),
    "sala-daeng-c11": ("2026-11-07-batch4-light-zcode-main", "st.sala-daeng",
                       "superagent.co/en/blog/saladaeng-one-silom-luxury-condo",
                       "'Saladaeng One' + '55,000'"),
    "sala-daeng-c12": ("2026-11-07-batch4-light-zcode-main", "st.sala-daeng",
                       "thefinestthai.com/2026/06/03/soi-lalai-sap",
                       "'Lalai'"),
    "phaya-thai-st-c06": ("2026-11-07-batch4-light-zcode-main", "st.phaya-thai",
                          "bkkoracle.com/area/phaya-thai",
                          "'Phaya Thai' + 'boat noodles'"),
    "phaya-thai-st-c08": ("2026-11-07-batch4-light-zcode-main", "st.phaya-thai",
                          "bkkoracle.com/area/phaya-thai",
                          "'Phaya Thai' + 'boat noodles'"),
    "phetchaburi-c05": ("2026-11-07-batch4-light-zcode-main", "st.phetchaburi",
                        "roavara.com/pratunam-area-guide",
                        "'Pratunam' + 'night'"),
    "phetchaburi-c07": ("2026-11-07-batch4-light-zcode-main", "st.phetchaburi",
                        "dooasset.com/en/area/mrt-phetchaburi",
                        "'25,000' + 'median'"),
    "saint-louis-c10": ("2026-11-07-batch4-light-zcode-main", "st.saint-louis",
                        "thailandstarterkit.com/moving/living-in-sathorn",
                        "'Saint Louis' + 'lunch'"),
    "saint-louis-c12": ("2026-11-07-batch4-light-zcode-main", "st.saint-louis",
                        "superagent.co/en/blog/saint-louis-bts-station-quiet-sathorn-pocket",
                        "'Saint Louis' + 'tree'"),
}

# claim -> removal note (substance preserved in review.notes)
REMOVALS = {
    "sam-yot-c11": ("2026-11-07-batch3-zcode-main", "st.sam-yot",
                    "REMOVED (A-8 rework, F3): rent-listings claim's every source "
                    "unreachable on 2026-11-08 (property-scout/baanfinder 403, "
                    "onlineoops dead, propertyhub figures behind JS) — could not be "
                    "body-read; the observed listing figures survive here as an "
                    "unverified-from-primary observation: 11,000-13,000 THB studios "
                    "74-100 m from the station; 14,000-15,000 THB 1BR; ~20,000 THB old "
                    "shophouse (propertyscout/baanfinder/propertyhub snippets)."),
    "sam-yot-c17": ("2026-11-07-batch3-zcode-main", "st.sam-yot",
                    "REMOVED (A-8 rework, F3): population-registry claim's sources "
                    "unreachable (stat.bora.dopa.go.th dead from this environment, "
                    "webportal 403). Substance preserved: registered population of "
                    "khwaeng Wang Burapha Phirom reportedly shrank 10,414 (2019) → "
                    "8,360 (2024 registry) per DOPA file 67 — UNVERIFIED from primary."),
    "hua-lamphong-c02": ("2026-11-07-batch4-light-zcode-main", "st.hua-lamphong",
                         "REMOVED (A-8 rework, F6+F3): app-data statement (catchment "
                         "split across four khet: Pathum Wan 47.4%, Bang Rak 28.9%, "
                         "Samphanthawong 18.4%, Pom Prap Sattru Phai 5.3%; station on "
                         "the Pathum Wan side, khwaeng Rong Mueang) was attached to an "
                         "unreadable X post — app-data anchors are recorded in review "
                         "notes, never as web-sourced claims."),
    "hua-lamphong-c12": ("2026-11-07-batch4-light-zcode-main", "st.hua-lamphong",
                         "REMOVED (A-8 rework, F6+F3): app-data provenance statement "
                         "(safety 6 is an editorial input; app confidence 'editorial', "
                         "source label 'ai_research'; no accessible unit-level crime "
                         "statistics found in EN or TH) was attached to the same "
                         "unreadable X post — preserved here as the score-context note."),
}

# claim text adjustment (scoped rewording to verified evidence)
TEXT_ADJUSTMENTS = {
    "sam-yot-c10": ("Rommaninat Park — the former Klong Prem Central Prison site, "
                    "now a public park with the corrections museum — and the "
                    "always-open canal promenade are the unit's usable green; the "
                    "stated 4.4-ha figure and the quoted opening hours are not "
                    "independently confirmed.",),
}


def sha12(url):
    return "src_" + hashlib.sha256(url.encode("utf-8")).hexdigest()[:12]


def main():
    log = open("research/bangkok/editorial/2026-11-08-a8-rework-log.jsonl", "a",
               encoding="utf-8")

    def emit(**kw):
        log.write(json.dumps({**kw, "step": "F3"}, ensure_ascii=False) + "\n")

    # group by batch/entity
    by_bundle = {}
    for cid, (batch, ent, urlsub, term) in UPGRADES.items():
        by_bundle.setdefault((batch, ent), {"up": [], "rm": []})["up"].append((cid, urlsub, term))
    for cid, (batch, ent, note) in REMOVALS.items():
        by_bundle.setdefault((batch, ent), {"up": [], "rm": []})["rm"].append((cid, note))

    for (batch, ent), jobs in by_bundle.items():
        ppath = f"{B}{batch}/profiles/{ent}.json"
        b = json.load(open(ppath, encoding="utf-8"))
        srcs = {s["id"]: s for s in b["sources"]}
        claim_map = {c["id"]: c for c in b["claims"]}

        for cid, urlsub, term in jobs["up"]:
            c = claim_map.get(cid)
            assert c, cid
            matches = [s for s in b["sources"] if urlsub in s["canonical_url"]]
            if cid == "sam-yot-c10" and not matches:
                # replacement source added by this pass (the park's original
                # sources are unreachable: TAT/greener/webportal 403, thailandlife dead)
                url = "https://en.wikipedia.org/wiki/Rommaninat_Park"
                b["sources"].append({
                    "id": sha12(url), "canonical_url": url, "retrieved_url": url,
                    "title": "Rommaninat Park — Wikipedia",
                    "publisher": "Wikipedia", "publisher_family": "Wikipedia",
                    "author": None, "published_at": None, "updated_at": None,
                    "retrieved_at": NOW, "body_read": True, "type": "other",
                    "commercial_context": "",
                    "limitations": ["added 2026-11-08 (A-8 rework) as the verified "
                                    "body-read replacement for unreachable park sources"]})
                s = b["sources"][-1]
                c["evidence"].append({"source_id": s["id"], "locator": "lead",
                                      "paraphrase": "Former Klong Prem prison site; now a public park (body-read verified)"})
                emit(batch=batch, entity=ent, change="source_added",
                     claim=cid, url=url)
            else:
                assert len(matches) == 1, (cid, urlsub, len(matches))
                s = matches[0]
            if not s["body_read"]:
                s["body_read"] = True
                s["retrieved_at"] = NOW
                if FALSE_LINE in (s.get("limitations") or []):
                    s["limitations"].remove(FALSE_LINE)
                s["limitations"].append(VERIFY_NOTE.format(term=term))
                emit(batch=batch, entity=ent, change="body_read_upgrade",
                     claim=cid, source=s["id"], terms=term)
            # scoped rewording to verified evidence
            adj = TEXT_ADJUSTMENTS.get(cid)
            if adj and c["text_en"] != adj[0]:
                emit(batch=batch, entity=ent, change="claim_text_scoped_reword",
                     claim=cid, before=c["text_en"][:120], after=adj[0][:120])
                c["text_en"] = adj[0]

        for cid, note in jobs["rm"]:
            if cid not in claim_map:
                continue
            b["claims"] = [c for c in b["claims"] if c["id"] != cid]
            for q in b["question_answers"]:
                if cid in q["claim_ids"]:
                    q["claim_ids"].remove(cid)
                    if not q["claim_ids"] and q["status"] in ("answered", "conflicting"):
                        q["status"] = "not_found"
                        q["notes"] = (q["notes"] + " — claim removed in A-8 rework "
                                      "(sole evidence not body-readable); see review.notes.").strip(" —")
            for lst in ("strengths", "tradeoffs", "day_night", "within_area_variation",
                        "conditional_fit"):
                kept = []
                for it in b["editorial"][lst]:
                    if cid in it["claim_ids"]:
                        it["claim_ids"].remove(cid)
                    if it["claim_ids"]:
                        kept.append(it)
                    else:
                        emit(batch=batch, entity=ent, change="editorial_item_removed",
                             where=lst, because=cid, text=it["text_en"][:100])
                b["editorial"][lst] = kept
            for blk in (b["editorial"]["preview"], b["editorial"]["guide_lead"]):
                if blk and cid in blk["claim_ids"]:
                    blk["claim_ids"].remove(cid)
                    if not blk["claim_ids"]:
                        blk["claim_ids"] = [c["id"] for c in b["claims"]][:1]
            for c in b["claims"]:
                if cid in (c.get("conflicts_with") or []):
                    c["conflicts_with"].remove(cid)
            b["review"]["notes"].append(note)
            emit(batch=batch, entity=ent, change="claim_removed", claim=cid)

        with open(ppath, "w", encoding="utf-8") as f:
            json.dump(b, f, ensure_ascii=False, indent=1)
        print(f"{ent}: upgrades={len(jobs['up'])} removals={len(jobs['rm'])}")
    log.close()


if __name__ == "__main__":
    main()
