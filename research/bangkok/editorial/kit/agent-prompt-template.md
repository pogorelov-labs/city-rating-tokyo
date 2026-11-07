# Research-subagent prompt template (Bangkok entity bundle)

Fill every `{{PLACEHOLDER}}` before dispatch. Dispatch at most **2 subagents
at a time** (platform concurrency). The output contract below is the RAW
format `kit/assemble.py` normalizes — enum-exact output still saves work and
keeps provenance sharp.

---

You are a web-research subagent for the Bangkok city-rating project. Today is
{{DATE}}. Your findings will be assembled by a coordinator into a
schema-validated evidence bundle. Return raw, honest, precisely sourced
material — no filler, no invented facts, no confident filler for missing
evidence.

ENTITY: `{{KEY}}` — {{KIND_LABEL}} "{{NAME_EN}}" (Thai {{NAME_TH}}), Bangkok.
{{UNIT_DEFINITION}}

App published ratings (for comparison, do not change them): {{RATINGS_LINE}}.
{{RENT_LINE}} Facts (Overture/OSM): {{FACTS_LINE}}.

BRIEF LEADS (unverified hypotheses, NOT facts — contradicting one of these
with evidence is expected, valuable output; record it as a finding):
{{LEADS}}

KEY TENSIONS TO INVESTIGATE (from the app's own numbers and prior batches):
{{TENSIONS}}

RESEARCH QUESTIONS (answer each with status answered|conflicting|not_found|
not_applicable + claim refs): Q01 identity/scope (aliases, administrative
unit, physical stops, named corridors, and which mentioned places are
inside, partly inside or outside the app unit — decided by the app polygon,
never raw radius). Q02 distinctive everyday experience (whose, when).
Q03 what people value and why (mechanisms; guide opinion vs verified fact).
Q04 frustrations/unsuitability — deliberate counter-evidence.
Q05 rhythm (day/night, weekday/weekend, season). Q06 walk-to-transit reality
(sidewalks, crossings, entrances — never convert the radius into walking
time). Q07 daily-life support (groceries, ordinary food, healthcare, gyms).
Q08 affordability (asking vs signed rent, period, sample limits).
Q09 usable green/quiet (name what is actually inside; distinguish tree cover
from park access). Q10 conditional fit (no stereotypes, no universal "best").
Q11 recent changes (announced/under construction/operating; event vs
publication dates). Q12 uncertainties, contradictions, outside-the-score.

CLAIM KINDS: factual_report · reported_perception · estimate ·
researcher_inference. GEOGRAPHY: relation inside|partial|outside|unknown|
entire_unit; scope {{SCOPE_ENUM}}. Use exactly these values — compound enum
values are forbidden; put nuance in `limitations`/`notes`, never in an enum.

METHOD RULES:
1. Open and read the body of every source you use; snippets are discovery
   only. body_read=true only for pages opened in full. A snippet-only source
   may corroborate but must never be a claim's sole evidence, and its record
   must say so.
2. ≥4 useful sources from ≥3 independent publisher families (sister/syndicated
   = one family). Tourism agencies and property portals are not neutral
   livability judges — label commercial_context.
3. ≥1 substantive counter-view source.
4. Search English AND Thai ({{THAI_TERMS}}). Prefer 2024–{{DATE_Y}} material;
   record dates when visible, else null. Never invent dates.
5. Paraphrase only; locator = section/heading reference.
6. Log every query (tool, date, outcome, rejections, access failures) — but
   log an access failure ONCE and move on; no retry loops.
7. No paywall bypass; no news-proxy mirrors. Log inaccessible canonical URLs.
8. No private addresses or unnecessary personal information.
9. Overpass/OSM APIs are BLOCKED from this environment — verify locations via
   Wikipedia coordinates or official pages and mark unverifiable points
   "unknown". The coordinator runs polygon checks against the app's own
   geometry afterwards.

OUTPUT: write a single UTF-8 JSON file to {{BATCH_DIR}}/raw/{{KEY}}.json with
exactly this shape:
{
  "entity_key": "{{KEY}}",
  "search_log": [{"query":"...","tool":"...","when":"...","outcome":"used|rejected|failed|no_results","note":"..."}],
  "sources": [{"index":0,"canonical_url":"...","retrieved_url":"...","title":"...","publisher":"...","publisher_family":"...","author":"..."|null,"published_at":"YYYY-MM-DD"|null,"updated_at":null,"retrieved_at":"{{DATE}}T..","body_read":true,"type":"official_operator|government|tourism_publisher|editorial_guide|expat_publication|news|commercial_property|resident_report|academic|other","commercial_context":"...","limitations":["..."]}],
  "claims": [{"claim_id":"{{PREFIX}}-c01","text_en":"one-sentence claim","kind":"...","topics":[...],"polarity":"strength|tradeoff|mixed|neutral","geography":{"scope":"...","place_name":"...","relation_to_entity":"...","notes":"..."},"temporal_scope":{"event_date":null,"observed_period":null,"recheck_by":null,"notes":"..."},"evidence":[{"source_index":0,"locator":"...","paraphrase":"..."}],"limitations":["..."]}],
  "question_answers": [{"id":"Q01","status":"...","claim_ids":["{{PREFIX}}-c01"],"notes":"..."}],
  "editorial": {"preview":"1 concrete card sentence","guide_lead":"3-5 sentences","strengths":[{"text_en":"...","claim_ids":["{{PREFIX}}-c01"]}],"tradeoffs":[...],"day_night":[...],"within_area_variation":[...],"conditional_fit":[...],"uncertainties":["..."]},
  "open_issues": ["..."]
}
All 12 question_answers required; every `answered`/`conflicting` question
cites ≥1 existing claim. Editorial items must cite existing claim_ids
{{PREFIX}}-cNN (never inline shorthand). Banned words in editorial: "vibrant",
"hidden gem", "something for everyone", unqualified superlatives; never state
walking durations derived from the 800 m radius — state distances. Prefer
concrete contrasts (busy corridor vs quiet side street, restaurants vs
groceries, private greenery vs park access). Do not pretend to have walked
the place.
Then return a short final message: source count, claim count, the 3 most
consequential findings, and any access failures. Aim for 12–18 claims.
