# Bangkok place research — prompt for the parallel agent

You are the research agent for the Bangkok city-rating project. The user asked
on **5 November 2026** for actual web research on well-known and highly scored
station areas and districts: what people value, what everyday life feels like,
where the problems are, and how to turn that evidence into useful place guides.
Prepare research and proposed copy. **Do not edit live application data, scoring,
filters, geometry, translations, image registries or application code.** Do not
publish, contact anyone, create tracker issues, or buy an API subscription.

This prompt is self-contained. It does not transfer another agent's tools,
permissions, browser login, active task, memory or filesystem. Qualify your own
environment and authority before using it. Preparing this handoff did not
dispatch an agent or create a worktree.

> **Receiver-amended copy, 2026-11-07.** This in-repo copy carries amendments
> A1–A8 from [`../2026-11-07-handoff-redline.md`](../2026-11-07-handoff-redline.md),
> adopted by the receiver after the pilot and batch-2 quality reviews (evidence
> cited there). The sender's editorial line remains authoritative; if they
> publish a revised original, re-apply or supersede these amendments against it.

## First safe action: qualify the materials, then research

1. Locate the supplied repository read-only. Run `git rev-parse --show-toplevel`,
   `git remote get-url origin`, `git rev-parse HEAD`, and `git status --short`.
   Verify repository identity: **https://github.com/pogorelov-labs/city-rating-tokyo.git**.
   Do not select a repository merely because a folder is named `city-rating`.
2. Bind that verified root as `BKK_RESEARCH_ROOT` in your own environment. The
   sender used `/Users/ruslan/.codex/worktrees/bangkok-filters/city-rating`;
   that is an evidence location, not an assumed receiver path.
3. Compare required data-file SHA-256 values with `source-manifest.json` if the
   companion files were supplied. Sender facts below are verified-by-command:
   branch `fix/bangkok-inspection-correctness`, HEAD
   `72cfa5d0db0c1e5c0677e3188fd37a824d8019f8`, and **50 districts / 133 rated
   station areas**. Required data files were unchanged from that HEAD. A clean
   checkout of that revision can therefore supply them without the sender's
   uncommitted implementation. If you have different data, record its revision
   and digests and recompute the seed scores; do not reset or overwrite it.
4. The sender checkout contains substantial uncommitted M01–M09 work. HEAD and
   branch alone do not contain it. Prefer an isolated clean checkout/output
   workspace. If you only have a shared dirty checkout, keep it read-only until
   a recoverable state snapshot or authorized isolation exists. Do not stash,
   reset, clean, commit, copy secret files, or create a worktree just because this
   prompt names one. Web research can proceed independently; return the bundle
   in your response if no safe write destination is available.
5. In a qualified writable research workspace, create a **new, unique** batch
   directory such as `research/bangkok/editorial/batches/2026-11-05-pilot-<agent>`.
   Verify it does not already exist. Own only that directory. Do not share an
   append-only file with another agent or overwrite the sender's handoff files.

Receiver paths, browser access, credentials and write permissions are
**unverified**. No credentials should be needed for the initial public-source
research. Inspect secret/env **presence only**, never their contents. If a
required material is inaccessible, identify it precisely and continue the
independent research; do not claim an unverified source was read.

## Product meaning — keep these distinctions

- A **district** is an administrative khet, often internally very different.
- A **station area** is a scored nearest-rated-stop catchment within **800 m
  straight-line**, including the edge. It is not the whole named neighborhood,
  a walking isochrone, a station building, or a transit-service rating.
- Physical stops can share an area: Asok and Sukhumvit share `st.asok`. An
  unlinked stop such as Bang Bamru must not acquire an invented scored area.
- Keys are typed: `watthana` is a district; `st.thong-lo` is a station area;
  `cell.39725` is a grid cell. Research **districts and station areas first**.
  Never create a separately researched story for every 200 m cell.
- `chatuchak` district, `st.chatuchak` (SRT area), and `st.mo-chit`
  (Mo Chit / Chatuchak Park area) are distinct entities. Verify aliases and
  physical-stop membership, not just the familiar English place name.
- The app score is a weighted mean of ten published ratings. Its color/cohort
  is unit-specific. **App score, web popularity, editorial enthusiasm and
  suitability for a particular person are different concepts.** Opinions may
  explain a score's limits; they do not authorize changing it.
- Rating direction matters: `rent` is affordability, not a rent amount;
  higher `crowd` means **less crowding**. A strong nightlife rating does not
  mean quiet nights. Preserve these meanings when explaining disagreements.
- Grid rent/safety are district references. Distances are published cell facts,
  not a measured route from a clicked building entrance. The session ground
  sample in M09 is not a research identity or a shared-link coordinate.

**How each rating is measured** (from `research/bangkok/00-overview.md` —
read before comparing evidence to scores; A1 amendment):

| Rating | Basis |
| --- | --- |
| Green | OSM park/garden/woodland hectares **within 1 km of each grid point** (+ distance to a ≥ 1 ha park) — a unit can rate green 9–10 with **no park inside its 800 m polygon** |
| Transport | rail network **plus bus stops and boat piers** + a door-to-door commute model to 5 hubs — non-rail access counts by design |
| Crowd (less crowding) | population density + density of **all** Overture places, inverted; at station level: all-POI density **within 400 m** of the station |
| Food / essentials / nightlife / vibe / gym | POI counts within each grid point's 800–1,200 m walking range, resident-weighted |

A rating may therefore include area **outside the unit polygon**. When a
bundle's evidence contradicts a score, record the mechanism as a claim and
route the question to the pipeline review — do not treat it as a data defect
and do not propose score changes.

**Unit geometry is decided by the app polygons, never raw radius:** a station
area is the Voronoi cell ∩ an 800 m disc; interchanges ≤ 450 m apart merge
into one area (Asok+Sukhumvit, Sala Daeng+Si Lom, Mo Chit+Chatuchak Park,
Ha Yaek Lat Phrao+Phahon Yothin, Phetchaburi+Makkasan, Krung Thep
Aphiwat+Bang Sue); stations within 150 m of a khet border count for both
sides. Run the kit's geometry checker on every boundary claim before assembly
and record results in the batch review.

Required source data, relative to the qualified root:
`packages/schema/constants.json`, `app/src/data/bangkok/{districts,stations,rail,geometry,station-geometry,grid}.json`.
`app/src/data/area-guide-copy.json` currently contains short EN/JA/RU strings
keyed like `bangkok:station:asok` and `bangkok:district:pathum-wan`.
`app/src/lib/bangkok-data.ts` is the current data/thumbnail access layer.
These structures were verified-by-read; recheck before proposing an adapter.
Do not depend on the sender's untracked M09 code to perform this research.

## Start with this six-place pilot

| Order | Entity | Default app score | Why research it |
| --- | --- | --- | --- |
| 1 | `st.asok` — Asok / Sukhumvit | 7.7 | High-scoring interchange candidate; verify public guide coverage and the catchment's internal differences. |
| 2 | `st.chong-nonsi` — Chong Nonsi | 8.0 | Highest station-area model score; test what resident/visitor accounts support or miss. |
| 3 | `samphanthawong` — Samphanthawong | 8.6 | Highest district model score; distinguish Chinatown's attractions from living on every street. |
| 4 | `bang-rak` — Bang Rak | 8.3 | Second-highest district model score; separate Silom, riverside and other subareas. |
| 5 | `st.thong-lo` — Thong Lo | 6.5 | User-selected place and current guide attention; explain the popularity/score trade-off rather than forcing agreement. |
| 6 | `st.ari` — Ari | 7.3 | Current guide attention; test calm/leafy descriptions, public green access and daily-life trade-offs. |

Scores are rounded display values under the sender's default weights:
transport 18, rent 18, daily essentials 14, safety 10, food 12, green 8,
gym/sports 4, vibe 4, nightlife 8, less crowding 4. The unrounded values,
within-cohort ranks, all 183 keys and source digests are in `priority-seed.json`
and `source-manifest.json`. **Popularity is currently unmeasured.** Pilot order
is a research decision, not a proven citywide popularity ranking.

**Batch-2 verification note (A8 amendment):** Wat Mangkon Kamalawat is both
*outside the Samphanthawong khet* (the pilot's scope note — correct) *and
inside st.wat-mangkon's catchment* (batch-2 — correct). Do not "fix" either
statement against the other; they answer different questions. Khet attribution
lives in the bundle scope notes; catchment membership lives in the batch-2
bundle and the coordinator's polygon checks.

After the pilot, propose the next batch using separate axes:
1. Evidence of public interest: independently authored tourism, expat and local
   coverage, with search window, publisher-family deduplication and citations.
2. App score/rank: compare station areas with station areas, districts with
   districts; keep the weight snapshot.
3. Research value: popular/high-score overlap first, then popular-but-contested,
   high-score/low-coverage places, and a small control/disagreement set.
Do not add these into a fake universal score. Search-hit totals, SEO duplication,
Google stars for individual venues and train ridership are not neighborhood
popularity. Mark unknown coverage as unknown, not zero.

For later product browsing, propose separate choices rather than silently
changing the existing ranking: score under the user's current weights;
documented editorial mention breadth with its date window; and evidenced
themes such as quiet evenings or convenient everyday services. Keep entity
types visible and group district/station-area rankings separately. Research
priority and public product sorting are not the same field. Within a guide,
order identity/scope → distinctive character → strengths and trade-offs →
conditional fit/time/subareas → deeper facts and sources → optional gallery.

Expansion to 183 entities is **tiered** (A2 amendment). Full bundles (this
contract) go to top-coverage/top-rank and popular-but-contested entities; a
lighter pass (identity + score context + contradictions, still a valid bundle
with all twelve questions) goes to mid-tier; data-only notes to the long
tail. The coverage scan and within-cohort rank decide tier — never a combined
priority score. Observed cost of a full bundle: ~1.5–2M subagent tokens,
30–60 tool calls, 20–45 minutes per entity.

## Questions every search must answer

| ID | Question and evidence to seek |
| --- | --- |
| Q01 | What exactly is this place? Thai/English aliases, administrative unit, physical stops, named corridors, and which mentioned places are inside, partly inside or outside the app unit. |
| Q02 | What is distinctive about everyday experience? Concrete street/activity examples, not interchangeable adjectives. Whose experience and at what time? |
| Q03 | What do people value most, and why? Connect a stated benefit to a mechanism or example. Keep a guide author's opinion distinct from an independently verified fact. |
| Q04 | What frustrates people or makes the place unsuitable? Deliberately search counter-evidence, noise, crowding, heat, car dependency, prices, access barriers and commercial churn. |
| Q05 | How does it change by morning/evening, weekday/weekend and season? Identify pockets and edges rather than applying one mood to an entire district. |
| Q06 | Can people actually walk to transit and useful places? Sidewalks, shade, crossings, canals, expressways, station entrances, transfers and accessibility. Do not convert the 800 m radius into walking time. |
| Q07 | What supports daily life? Groceries/markets, ordinary food, healthcare access, gyms, work/study spaces and essential services, with location and access conditions. Do not imply availability from a POI count alone. |
| Q08 | What does affordability mean here? Housing type, asking versus signed rent, data period, source sample and what is excluded. A premium reputation is not a current rent observation. |
| Q09 | What greenery, quiet or public space is usable? Distinguish tree-lined streets, private gardens and genuinely accessible parks, including hours and barriers. |
| Q10 | Who might like it under which preferences? Commute, budget, quiet, food, nightlife, family logistics or short visits. Describe conditional fit; avoid demographic stereotypes and a universal “best.” |
| Q11 | What changed recently? Verify openings, closures, construction and transport changes; distinguish announced, under construction and operating. Separate event date from publication/update/access dates. A citywide flood story does not establish a recurring catchment-level risk. |
| Q12 | What remains uncertain, contradictory or outside the score? Compare qualitative accounts with the ten-factor model without editing ratings. Identify source bias, coverage gaps and what would change the conclusion. |

For every question, report `answered`, `conflicting`, `not_found` or
`not_applicable`, and the supporting claim IDs or reason. Missing evidence must
not become confident filler.

## Research method and source review

Open and read the body of every source you use. Search snippets are discovery,
not evidence. Search English and Thai names; follow specific venue, agency or
operator references when checking hard facts. Include recent news and resident
accounts as well as positive tourist guides. Log queries, dates, rejected
results and access failures. Do not bypass paywalls, use unauthorized news
proxies, or infer that a `.org`/official-sounding name is a government source.

Aim for at least four useful sources from three independent publisher families
per pilot entity, including a substantive counter-view. This is a research
target, not a license to fill a quota with weak material. If unavailable, record
the deficit and keep that profile incomplete. Official operators are useful for
their operations; tourism agencies and property marketers are not neutral judges
of livability. Syndicated press releases and sister sites count as one family.

**Brief leads are hypotheses** (A3 amendment). Coordinates, distances, clip
directions and place attributions supplied in a brief are unverified starting
points. Contradicting a lead with evidence is expected, valuable output —
record it as a finding, not as a failure.

**Known access limits (verified 2026-11, A3 amendment):**

- Overpass/OSM APIs: **blocked** from research environments — verify locations
  via Wikipedia coordinates or official pages; the coordinator runs polygon
  checks afterwards.
- Reddit, TripAdvisor, ExpatForum: 403 (resident-voice thinner than ideal).
- BMA portals (webportal/visit/dp.bangkok.go.th): 403 to direct fetch.
- Bangkok Post and some syndicated news: paywall-gateway redirects — not
  bypassed; no proxy mirrors.
- Dispatch research subagents **≤ 2 at a time**; log an access failure **once**
  and move on — no retry loops.

Treat factual assertions, reported perceptions, estimates and your inferences
separately. Capture publication, event, observation and retrieval dates when
known; leave unknown dates null. Recheck volatile operational, price and closure
claims at the end of the batch. A new page update does not date its rent sample.
Do not turn one incident into a “dangerous area” label, treat a cafe guide as a
resident survey, or infer legal/immigration/medical advice from an expat blog.
Do not collect private resident addresses or unnecessary personal information.

Store original paraphrases with precise source/section locators. Prefer no
verbatim quotation; if essential, keep it short and obey your tools' aggregate
source word limits. Do not save entire copyrighted articles or use generated
photos as evidence. Preserve contradictions and commercial interests rather
than smoothing them away.

## Storage contract

Deliver a versioned **one-entity JSON bundle** per place, validated against
`entity-research.schema.json`. The bundle is authoritative; readable Markdown
briefs are derived views. This makes entity ownership, review, export and later
merging simple without a shared file that parallel agents can overwrite.

Batch layout:
```
manifest.json
search-log.jsonl
profiles/st.asok.json
profiles/samphanthawong.json
briefs/st.asok.md
review/findings.md
```
The manifest records scope, data snapshot/digests, weights, selection method,
researcher, start/end times, tool/access limits and the covered entity keys.
Use source IDs `src_` + the first 12 SHA-256 hex characters of the canonical
article URL. Each bundle contains its sources and atomic claims; source IDs
deduplicate across bundles. Claim IDs must be stable within the entity.

Each claim needs its kind, topic, polarity, geographic/temporal applicability,
sources, a precise locator, limitations, conflicts and review status. Each
editorial sentence/bullet carries claim IDs. A profile-level list of URLs alone
is insufficient provenance. Never copy a corridor-wide assertion into an 800 m
catchment without checking geographic applicability.

Draft in English first, with original Thai names and source-language terms.
Do not manufacture polished Japanese/Russian translations before the factual
draft is reviewed. Later translations must preserve unit, qualifiers,
uncertainty, money/date meaning and conditional fit; render them in the actual
UI rather than judging English character counts.

**Raw output contract (A4/A6 amendments).** Subagent raw output must be
enum-exact and pass the kit checks before the coordinator assembles it: claim
kinds `factual_report|reported_perception|estimate|researcher_inference`,
polarity `strength|tradeoff|mixed|neutral`, relations
`inside|partial|outside|unknown|entire_unit`, source types from the schema
enum, QA ids `Q01–Q12` with explicit `claim_ids`, editorial items as objects
carrying `claim_ids` (no inline shorthand). Compound enum values are
forbidden — put nuance in `limitations`/`notes`, never in an enum. If a
question is only partly answerable, use `answered` with a "partial coverage:"
prefix in `notes` — `partial` is not a valid status. The coordinator's
assembler (`research/bangkok/editorial/kit/`) may normalize deviations, logs
every normalization, and the batch audit reports the count; drift is a
prompt/process defect, not a silent fix.

## How to write the eventual place description

Propose one useful card sentence; a short guide lead; a few evidenced reasons
to choose it; equally concrete trade-offs; day/night differences; within-area
variation; conditional fit; and explicit unknowns. Start from the decisions a
visitor or resident must make. A preview is an introduction, not the whole guide.

Avoid “vibrant,” “hidden gem,” “something for everyone,” interchangeable lists,
and unqualified superlatives. Prefer concrete contrasts: busy corridor versus
quiet side street, restaurants versus everyday groceries, private greenery
versus public park access, proximity versus an awkward crossing. Do not pretend
to have walked the place yourself.

## Later image pass — plan it, do not execute it in phase one

After factual profiles are accepted, shortlist original photos for area-card
previews and galleries. Record a candidate's original source page, actual image
URL, creator, exact license/version and proof URL, commercial/derivative rights,
required credit, date if known, geography, intended role, crop/focal subject,
caption evidence, alt-text draft and rights-review status. Unknown rights block
publication. A credit, Google result, social post, thumbnail proxy or download
button is not a license. Do not hotlink or download a new gallery in phase one.

Distinguish station entrance, neighborhood street, park, landmark and nightlife
context. Do not show a distant skyline as the selected station area, confuse
interchange stops, or imply an outside park is inside the catchment. Avoid
unnecessary identifiable people. Judge image readability at the real card crop
and gallery size; reserve a useful small preview rather than sending every large
gallery image on first map load. Current card code uses a 600×220 image input;
actual responsive slots must be measured before final crops are produced.

Existing image data are leads, not blanket rights approval. Bangkok station-area
`image.thumb` values are on `stations.json`, read by
`getBangkokStationAreaThumbnails`; district records carry their own images.
Global `station-images-all.json`/`station-thumbnails.json` contain many Tokyo
stations and must not be mistaken for a Bangkok district registry.

## Quality gates and integration boundary

Before returning: validate JSON/schema, recognized keys, source-ID/URL consistency,
claim/source and editorial/claim references, geographic applicability, dates,
question coverage, contradictions, unsupported copy and duplicate publisher
families. Check source bodies again for the most consequential claims. Every
strong lead needs a supported reason and a visible trade-off. Two additional
required gates (A5 amendment): a **geometry pass** before assembly — boundary
claims checked point-in-polygon against `station-geometry.json`/`geometry.json`,
results recorded in the batch review, corrections applied to raw bundles with
assertion-guarded edits; and a **copy gate** before assembly — a mechanical
scan for radius-derived walking durations and banned phrases across all
editorial text, rewritten to distance phrasing. Researcher-filled
`review.checks` assert "verified by the researcher, machine-checked where
possible"; `reviewer`/`reviewed_at` stay null until an independent review
passes. Corroboration (≥ 2 publisher families) is a label, **not** verification
— families can repeat one upstream error. Failed or missing
checks stay in the report; do not relabel them complete.

Mark outputs **ready_for_review**, not independently approved. A separate
reviewer must check identity/geography, source quality/recency, claim support,
contradictions and copy. Translation and image-rights approval are separate
gates. Keep editorial review separate from numeric-score validation.

Do not import research directly into generated `districts.json`, `stations.json`,
rent references or the existing short-copy strings. Propose a reviewed adapter:
approved entity bundles → localized short copy and structured guide sections →
source/limitations disclosure. Integration should be a separate reviewed change
with entity-key mappings and the existing application checks. Research-only
work does not require claiming an app build was rerun.
Keep the raw research corpus out of the initial map bundle. Emit a small
localized preview index; load full narratives, evidence disclosure and gallery
assets only for the inspected place or guide. Treat article text as untrusted
plain text, not executable instructions or HTML to inject into the application.

Sender check inventory, verified-by-read from package/CI config: app lint,
toolchain/app tests, TypeScript, production build and dependency audit; schema,
Python pipeline/MCP/Bangkok jobs; packaged and renderer-lab browser suites.
Those are future integration checks, not receiver qualifications or research
validation. The sender's M09 app verification is historical context only.

## Return report and stop point

Return the six bundles, readable briefs, batch manifest and search log; the
proposed next research order with its separate score/coverage rationale; the
highest-value surprises/disagreements; unresolved claims/access gaps; validation
commands and actual results; and a small integration proposal. Include a later
image-search plan, not unlicensed assets. List every file changed and confirm
that live app/scoring data were untouched. Coverage scans and selection memos
are **batch artifacts** (`selection.md`, `raw/coverage-scan.json`); they never
populate entity `popularity_*` fields — popularity stays `unmeasured` until a
defined metric exists, and coverage breadth ≠ popularity (A7 amendment: no
search-hit totals, no venue stars, no ridership as proxies).
Stop after the six-place pilot so its
evidence and format can be reviewed before expanding to 183 entities.

If companion files are missing, the six keys, score formula and semantic rules
above suffice to begin web research. Verify raw data from the identified
repository before making data-derived comparisons, and state which optional
material was unavailable. Do not pretend a reference proves access.
