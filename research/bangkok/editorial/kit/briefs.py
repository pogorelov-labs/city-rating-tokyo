#!/usr/bin/env python3
"""Generate derived briefs (markdown) from assembled profile bundles (kit version).

Run with: python3 briefs.py --batch-dir <batch>   (defaults to cwd)
Briefs are derived views; profiles/*.json remain authoritative.
"""
import argparse
import json
import os

def li_block(items):
    out = []
    for it in items:
        cids = ", ".join(f"`{c}`" for c in it["claim_ids"])
        out.append(f"- {it['text_en']} *[{cids}]*")
    return "\n".join(out) or "_(none)_"

def brief(b):
    e = b["entity"]
    sc = b["selection_context"]
    kind_label = ("Station area (nearest-stop catchment, Voronoi ∩ 800 m disc)"
                  if e["kind"] == "station_area" else "District (administrative khet)")
    lines = [f"# {e['name_en']} ({e['key']}) — research brief", "",
             f"**Derived view** of `profiles/{e['key']}.json` (authoritative bundle), "
             f"batch `{b['review']['researcher']}` era output. Status: **{b['review']['status']}** — "
             "not independently approved. Drafted in English only; no translations manufactured.", "",
             f"- **Unit:** {kind_label}. Aliases: {', '.join(e['aliases']) or '—'}",
             f"- **Scope:** {e['scope_notes']}",
             f"- **App score context:** model {sc['model_score_default']} (display rounded), "
             f"cohort rank {sc['cohort_rank']} of {sc['cohort_size']}, snapshot `{sc['app_snapshot_id']}`. "
             f"Public popularity: **{sc['popularity_status']}** — {sc['popularity_method']}",
             f"- **Selection rationale:** {sc['selection_rationale']}", "",
             "## Card preview (proposed)", f"> {b['editorial']['preview']['text_en']}", "",
             "## Guide lead (proposed)", b["editorial"]["guide_lead"]["text_en"], "",
             "## Strengths", li_block(b["editorial"]["strengths"]), "",
             "## Trade-offs", li_block(b["editorial"]["tradeoffs"]), "",
             "## Day / night", li_block(b["editorial"]["day_night"]), "",
             "## Within-area variation", li_block(b["editorial"]["within_area_variation"]), "",
             "## Conditional fit", li_block(b["editorial"]["conditional_fit"]), "",
             "## Explicit unknowns"]
    for u in b["editorial"]["uncertainties"]:
        lines.append(f"- {u}")
    lines += ["", "## Question coverage"]
    for q in b["question_answers"]:
        lines.append(f"- **{q['id']} — {q['status']}**: {q['notes']}")
    lines += ["", "## Evidence base", "",
              "| Source | Publisher (family) | Type | Published | Read |", "| --- | --- | --- | --- | --- |"]
    for s in b["sources"]:
        title = s["title"] if len(s["title"]) <= 90 else s["title"][:87] + "…"
        read = "yes" if s["body_read"] else "partial"
        pub = s.get("published_at") or "—"
        lines.append(f"| [{title}]({s['canonical_url']}) | {s['publisher']} ({s['publisher_family']}) | "
                     f"{s['type']} | {pub[:10]} | {read} |")
    lines += ["", "## Claim index", ""]
    for c in b["claims"]:
        geo = c["geography"]
        lines.append(f"- `{c['id']}` **[{c['review_status']}·{c['polarity']}·{geo['relation_to_entity']}]** "
                     f"{c['text_en']} _(scope: {geo['scope']} — {geo['place_name']})_")
    lines += ["", "## Reviewer notes from the researcher"]
    for n in b["review"]["notes"]:
        lines.append(f"- {n}")
    lines.append("")
    return "\n".join(lines)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch-dir", default=os.getcwd())
    args = ap.parse_args()
    profiles = os.path.join(args.batch_dir, "profiles")
    briefs = os.path.join(args.batch_dir, "briefs")
    os.makedirs(briefs, exist_ok=True)
    for fn in sorted(os.listdir(profiles)):
        if not fn.endswith(".json"):
            continue
        b = json.load(open(os.path.join(profiles, fn), encoding="utf-8"))
        out = os.path.join(briefs, fn)
        with open(out, "w", encoding="utf-8") as f:
            f.write(brief(b))
        print("wrote", out)

if __name__ == "__main__":
    main()
