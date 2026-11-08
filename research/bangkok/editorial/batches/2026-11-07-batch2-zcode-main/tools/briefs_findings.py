#!/usr/bin/env python3
"""Generate derived briefs (markdown) from assembled profile bundles.

Run with: python3 -I tools/briefs_findings.py   (from the batch directory)
Briefs are derived views; profiles/*.json remain authoritative.
"""
import json
import os
from datetime import datetime, timezone

BATCH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROFILES = os.path.join(BATCH, "profiles")
BRIEFS = os.path.join(BATCH, "briefs")

ORDER = ["st.charoen-nakhon", "st.ratchathewi", "st.nana", "st.wat-mangkon", "pom-prap-sattru-phai", "phaya-thai"]

def fmt_date(s):
    return (s or "—")[:10]

def li_block(items, bullet="-"):
    out = []
    for it in items:
        cids = ", ".join(f"`{c}`" for c in it["claim_ids"])
        out.append(f"- {it['text_en']} *[{cids}]*")
    return "\n".join(out) or "_(none)_"

def brief(b):
    e = b["entity"]; sc = b["selection_context"]
    kind_label = "Station area (800 m straight-line catchment)" if e["kind"] == "station_area" else "District (administrative khet)"
    lines = []
    lines.append(f"# {e['name_en']} ({e['key']}) — research brief")
    lines.append("")
    lines.append(f"**Derived view** of `profiles/{e['key']}.json` (authoritative bundle), batch `2026-11-07-batch2-zcode-main`. "
                 f"Status: **{b['review']['status']}** — not independently approved. Drafted in English only; no translations manufactured.")
    lines.append("")
    lines.append(f"- **Unit:** {kind_label}. Aliases: {', '.join(e['aliases']) or '—'}")
    lines.append(f"- **Scope:** {e['scope_notes']}")
    lines.append(f"- **App score context:** model {sc['model_score_default']} (display rounded), cohort rank {sc['cohort_rank']} of {sc['cohort_size']} "
                 f"({'station areas' if e['kind'] == 'station_area' else 'districts'}), snapshot `{sc['app_snapshot_id']}`. "
                 f"Public popularity: **{sc['popularity_status']}** — {sc['popularity_method']}")
    lines.append(f"- **Selection rationale:** {sc['selection_rationale']}")
    lines.append("")
    lines.append("## Card preview (proposed)")
    lines.append(f"> {b['editorial']['preview']['text_en']}")
    lines.append("")
    lines.append("## Guide lead (proposed)")
    lines.append(b["editorial"]["guide_lead"]["text_en"])
    lines.append("")
    lines.append("## Strengths")
    lines.append(li_block(b["editorial"]["strengths"]))
    lines.append("")
    lines.append("## Trade-offs")
    lines.append(li_block(b["editorial"]["tradeoffs"]))
    lines.append("")
    lines.append("## Day / night")
    lines.append(li_block(b["editorial"]["day_night"]))
    lines.append("")
    lines.append("## Within-area variation")
    lines.append(li_block(b["editorial"]["within_area_variation"]))
    lines.append("")
    lines.append("## Conditional fit")
    lines.append(li_block(b["editorial"]["conditional_fit"]))
    lines.append("")
    lines.append("## Explicit unknowns")
    for u in b["editorial"]["uncertainties"]:
        lines.append(f"- {u}")
    lines.append("")
    lines.append("## Question coverage")
    for q in b["question_answers"]:
        lines.append(f"- **{q['id']} — {q['status']}**: {q['notes']}")
    lines.append("")
    lines.append("## Evidence base")
    lines.append("")
    lines.append("| Source | Publisher (family) | Type | Published | Read |")
    lines.append("| --- | --- | --- | --- | --- |")
    for s in b["sources"]:
        title = s["title"] if len(s["title"]) <= 90 else s["title"][:87] + "…"
        read = "yes" if s["body_read"] else "partial"
        lines.append(f"| [{title}]({s['canonical_url']}) | {s['publisher']} ({s['publisher_family']}) | {s['type']} | {fmt_date(s['published_at'])} | {read} |")
    lines.append("")
    lines.append("## Claim index")
    lines.append("")
    for c in b["claims"]:
        geo = c["geography"]
        lines.append(f"- `{c['id']}` **[{c['review_status']}·{c['polarity']}·{c['geography']['relation_to_entity']}]** {c['text_en']} "
                     f"_(scope: {geo['scope']} — {geo['place_name']})_")
    lines.append("")
    lines.append("## Reviewer notes from the researcher")
    for n in b["review"]["notes"]:
        lines.append(f"- {n}")
    lines.append("")
    return "\n".join(lines)

def main():
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    for key in ORDER:
        b = json.load(open(os.path.join(PROFILES, f"{key}.json"), encoding="utf-8"))
        path = os.path.join(BRIEFS, f"{key}.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write(brief(b))
        print("wrote", path)

if __name__ == "__main__":
    main()
