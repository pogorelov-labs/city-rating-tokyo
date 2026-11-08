# Critical review — updating the handoff rules and research guides

**2026-11-07.** Evidence base: two completed research batches
(`2026-11-05-pilot-zcode-main`, `2026-11-07-batch2-zcode-main` — 12 entities,
104 claims, 111 sources, ~470 logged searches, two coordinator verification
passes, validator/audit outputs), read against the governing docs:
`HANDOFF.md`, `research/bangkok/00-overview.md`, `description-rules.md`,
`backlog.md`, `entity-research.schema.json`.

**Verdict.** The contract's *integrity architecture* worked: no fabrication
reached a bundle, provenance held everywhere, the stop-per-batch cadence caught
a real P1 both times. The *information architecture* failed in specific,
fixable ways: the handoff under-carried the app's own measurement definitions,
the agent output contract existed only as prose, and coordinator-authored
"leads" were consumed as facts. Roughly half the batch-2 coordinator
verification pass was spent re-deriving things `00-overview.md` already knew.

---

## 1. What worked — keep unchanged

| Rule | Evidence it worked |
|---|---|
| One-entity bundles + per-batch dirs | 14 subagent runs, zero overwrite conflicts; the only 2 URLs shared across bundles resolved to identical source IDs |
| Stop after each batch | Batch-1 review caught F1 (a factual error that had propagated into scope notes); batch-2 inherited the lesson and agents corrected three wrong coordinator leads |
| "Snippets are discovery, not evidence" + locators | 19/19 re-reads of consequential sources found no paraphrase distortion; snippet-only sources were corroboration-only and flaggable |
| Rating-direction warnings (rent = affordability, crowd = less crowding) | No direction errors in 104 claims |
| Publisher-family rule + `src_` hashing | Corroboration labels mechanically recomputable; dedup worked |
| Copy bans | 0 banned-word hits across 12 bundles; the one recurring copy fault (radius→time) is a *rule-placement* problem, see §2-H7 |
| `ready_for_review` + `reviewer: null` | Approval discipline never blurred |

---

## 2. Handoff amendments (observation → concrete change)

### H1. Bind the per-rating measurement geometry — the biggest gap
**Observation.** Batch 2 spent researcher and coordinator effort flagging
"score-vs-unit" mismatches that `00-overview.md` documents as design:
green = park hectares **within 1 km** of each grid point (points count
800–1,200 m) — so a station unit can rate green 10 with no park inside its
800 m polygon (nana, pom-prap, phaya-thai, ratchathewi, ari); transport
**counts bus stops and boat piers** (explaining charoen-nakhon's 10);
station-level quietness/crowd = density of *all* Overture places within
**400 m**, inverted (explaining chong-nonsi's weekday-only crowd 1).
**Change.** Add to "Product meaning" a short table — *what each rating
measures and at what radius* — or bind `00-overview.md` §"Sources and
confidence" + honesty notes 3–7 as required reading. Add one rule:
*"A rating may legitimately include area outside the unit polygon; when a
bundle's evidence contradicts a score, record the mechanism as a claim and
route the question to the pipeline review — do not treat it as a data defect
and do not propose score changes."*

### H2. Make unit membership operational, not definitional
**Observation.** The handoff *did* say "nearest-rated-stop catchment" —
correct but inert. Agents (and the coordinator's first prompt pass) still
reasoned from raw radius: the batch-1 F1 error (Sala Daeng/Patpong "inside
the circle"), wrong clip directions, wrong distances. What actually fixed
it was point-in-polygon against `station-geometry.json` / `geometry.json`
(rings are `[lat, lng]`; districts in `geometry.json`).
**Change.** Add: *"Unit membership is decided by the app polygons, never by
raw radius: run the geometry checker (§kit) on every boundary claim before
assembly and record results in the batch review. Interchanges ≤ 450 m merge
into one area (Asok+Sukhumvit, Sala Daeng+Si Lom, …); stations within 150 m
of a khet border count for both sides."*

### H3. Promote the verification kit from batch-local to shared
**Observation.** Everything that caught real errors — `validate.py`
(schema subset), `audit.py` (ref closure, corroboration recompute, banned
words, radius→time scan, body-read reliance), the polygon checker, the
normalizing assembler — lives in batch directories and was re-derived/adapted
each time (one copy drifted: a hardcoded batch id leaked into briefs).
**Change.** Check the kit in once (suggested: `scripts/bangkok/research-kit/`
or `research/bangkok/editorial/kit/`), parameterized by `--batch-dir`, plus a
one-command batch skeleton (unique-name check, correct cwd, subdirs). Apply
as a separate reviewed change.

### H4. Machine-check the agent output contract
**Observation.** In both batches, subagents drifted from the prose JSON
contract: invalid geography scopes (`entire_unit` as scope), claim kind
`mixed`, polarity `positive`/`negative`/`negative_for_green_score`, ~25
source-type variants (`encyclopedia`, `reference`, `official`,
`property_portal_data`…), QA field variants (`q`/`claims`/`claim_refs`,
`answer` vs `notes`, status `partial`), editorial items as bare strings with
inline refs. The assembler absorbed all of it (~60 normalizations), but the
cost was silent until audited.
**Change.** (a) Publish a **raw-output schema + one-file checker** that every
research subagent must run before finishing (same pattern as the pilot's
"validated" self-checks, which did reduce drift). (b) Keep the normalizer as
a safety net and make it *log every normalization* (already done — keep).
(c) Prompt rule: *"Compound enum values are forbidden (`negative_for_green_score`);
put nuance in `limitations`/`notes`, never in an enum."*

### H5. Coordinator leads are hypotheses
**Observation.** Three of my authored leads were wrong and the agents
corrected them (Gold Line "crosses the river" — it doesn't; "itsaraphap
clips chong-nonsi" — 2.7 km away; "Suan Mali community" unverifiable; and
the app's own alias list places Woeng Nakhon Kasem in the wrong khet).
**Change.** Add to the handoff: *"Brief leads are unverified starting
points. Contradicting a lead with evidence is expected, valuable output —
record it as a finding, not as a failure."* This matters because the current
text implies leads are task inputs, and a compliant agent could have
"verified" them.

### H6. Publish known environment limits
**Observation.** Overpass was blocked in *every* session (each agent burned
multiple retries); Reddit/TripAdvisor 403; BMA portals 403; Bangkok Post
tollbit redirects; one webReader rejected Thai-language URLs (MCP -400);
platform concurrency capped parallel agents (6-at-once dispatch failed).
**Change.** Add a "Known access limits (verified 2026-11)" list + two rules:
*"log an access failure once and move on — no retry loops"* and *"dispatch
research subagents ≤ 2 at a time."* This converts wasted retries into
documented gaps.

### H7. Move the walk-time ban from prose to mechanics
**Observation.** The ban was stated, yet four editorial strings converted
radius into walking time (asok preview + conditional_fit, thong-lo, bang-rak,
charoen-nakhon) across two batches; all were caught by the audit regex, not
by authors.
**Change.** Keep the rule, add the mechanical gate to the kit (`audit.py`
already has it), and make the copy-check a *required* pre-assembly step
rather than a review-phase find. Add a sanctioned device to
`description-rules.md`: "prefer distance contrasts over duration claims."

### H8. Codify where selection/coverage data lives
**Observation.** Batch 2 measured coverage breadth for selection (axis 1)
while `selection_context.popularity_status` correctly stayed `unmeasured` —
the right call, but nothing in the handoff says so, and a future agent could
conflate the two.
**Change.** One paragraph: *"Coverage scans and selection memos are batch
artifacts (`selection.md`, `raw/coverage-scan.json`); they never populate
entity `popularity_*` fields. Popularity stays unmeasured until a defined
metric exists. Coverage breadth ≠ popularity: no hit counts, no venue stars."*

### H9. Clarify `review.checks` semantics
**Observation.** Researcher-filled `checks` could read as independent
verification; the handoff wants a separate reviewer but doesn't say what
researcher-filled checks mean.
**Change.** One line: *"Researcher-filled `checks` assert 'verified by the
researcher, machine-checked where possible'; `reviewer`/`reviewed_at` stay
null until an independent review passes."*

### H10. Tier the expansion to 183 entities
**Observation.** Cost profile: ~1.5–2M subagent tokens, 30–60 tool calls and
20–45 minutes per entity. Full coverage at pilot quality implies several
hundred million tokens.
**Change.** Add a tiering rule: full bundles for top-coverage/top-rank and
contested entities; a lighter "identity + score-context + contradictions"
pass for mid-tier; data-only notes for the long tail — with the coverage
scan and within-cohort rank deciding tier, and every tier still producing a
valid bundle (schema allows short bundles; minimum is the 12 questions).

---

## 3. Research-guide updates

### `00-overview.md` — no substantive change needed
Its measurement documentation is correct and was *sufficient to explain every
batch-2 "score anomaly"* — the failure was that the handoff didn't carry it
(§2-H1). Optional: add one honesty-note sentence making the station-area
unit-vs-buffer distinction explicit for readers ("green includes parks up to
1 km from a cell's centre — a station area can rate high on green with no
park inside its 800 m polygon").

### `description-rules.md` — small, evidence-backed additions
1. **Named-place confusion guard** (from batch 2): *Chinatown Soi Nana
   (Pom Prap) is not Sukhumvit Soi Nana (Watthana)* — a real LLM confusion
   observed in the wild; a "Wat Mangkon" description must not absorb
   Pom Prap's Golden Mount just because the MRT station straddles.
2. **Distance-not-duration**: prefer "400 m to the park edge, gates beyond
   the catchment" over "15-minute walk" (four batch incidents).
3. **Cross-khet landmarks get named as such** ("just across the boundary in
   <khet>") — the Woeng Nakhon Kasem misattribution in the app's own alias
   list shows the failure mode.
4. Optionally adopt the handoff's "concrete contrasts" device as a sanctioned
   pattern ("busy corridor vs quiet side street"), which the two batches
   produced naturally and reviewers praised.

### `backlog.md` — link findings to existing tickets, don't duplicate
- **CRTKY-153** (red-light zones): batch evidence — Nana Plaza inside nana's
  catchment (~255–300 m, consolidation 39→24 bars), Soi Cowboy ~121 m,
  Patpong boundary behavior across two catchments.
- **CRTKY-147** (walkability): dated BMA items — Asok Montri footpath
  rebuild (announced 2025-03-16/18), Soi Thong Lo 26.3M THB rebuild
  (contracted 2025-07-04, 0% progress at 2025-09-23), Ratchathewi flyover
  closure (2025-01-15 → due 2028-04).
- **CRTKY-141** (rent anchors): two batches confirm asking-vs-signed gap is
  universal in public sources; one anomaly for review — pom-prap 2-bed
  editorial 24,000 sits below *all* observed asks (25,000–32,000, n=14).
- **CRTKY-139** (flood): agents' catchment-specificity method worked (2011
  tide-driven riverside edge vs dry core; citywide 2026 stories never naming
  the unit) — reusable protocol for that ticket.
- **CRTKY-152** (tourist load): the coverage-breadth method (windowed,
  family-deduped) is a candidate instrument — explicitly *not* popularity.
- **New candidate item**: *green-rating basis audit* (1 km buffer vs 800 m
  unit; state-land contributions like the Army compound) — a pipeline
  question spanning ≥6 entities; belongs as a ticket, not per-entity
  research.

---

## 4. Route to pipeline/integration review (explicitly not research work)

1. Green-basis alignment question (§2-H1, §3 backlog item).
2. Transport-mechanism weighting (piers/buses count by design; lived-experience
   weighting is a model question — charoen-nakhon, ratchathewi evidence).
3. Rent floor anomaly (pom-prap 2-bed).
4. App-record inconsistencies for the data layer's own checks: wat-mangkon's
   `district` field vs its 51.4/48.6 split; phaya-thai description text vs
   its khet polygon (Victory Monument); pom-prap alias list (Woeng Nakhon
   Kasem). Research documented these; fixing them is a data change with the
   repo's existing build/replay gates.

---

## 5. Anti-overcorrection — what NOT to change

- **Don't loosen one-entity bundles.** They prevented every failure mode the
  handoff feared (overwrites, shared append-only files).
- **Don't treat "corroborated" as verified.** Two publisher families can
  repeat one upstream error (Wikipedia coordinates flowed into several
  families); the polygon pass was still required. Corroboration is a label,
  not a proof.
- **Don't adopt popularity from coverage counts.** The axis-1 method is a
  selection instrument; adopting it as a product ranking would recreate the
  SEO distortion the handoff bans.
- **Don't soften the walk-time ban** because agents keep testing it — that's
  the rule working.
- **Don't normalize silently.** Every enum mapping the assembler performs must
  stay visible in audit output (it is; keep it).
- **Keep the stop-per-batch cadence** even when it feels bureaucratic — it is
  the only stage that caught cross-cutting errors in both batches.

---

## 6. Draft lesson candidates (DRAFT_ONLY)

No candidate store is configured in this repo (`.agent-workflow/config.json`
absent), so per the extraction contract these are drafts for later persistence,
not saved records. Shape follows the candidate schema; evidence locators point
at real session artifacts.

1. **scope:** city-rating research pipeline. **trigger:** composing research
   subagent prompts for rating entities. **action:** state each rating's
   measurement radius/basis (green 1 km buffer, transport includes
   piers/bus stops, crowd = all-POI density 400 m inverted) and classify
   unit-vs-buffer mismatches as pipeline questions. **exceptions:** none
   known. **evidence:** `research/bangkok/00-overview.md` (Sources table);
   batch-2 profiles nana/ratchathewi/pom-prap/phaya-thai green claims;
   `manifest.json` findings.
2. **trigger:** assembling subagent research JSON. **action:** validate raw
   output against a raw-format schema + run a normalizing assembler that logs
   every enum/field normalization; keep the semantic audit (ref closure,
   corroboration recompute, copy bans, radius→time scan) as a required gate.
   **exceptions:** none. **evidence:** batch-1 audit (6 findings) and batch-2
   audit (224 → 15 after normalization); `tools/assemble.py` mapping tables.
3. **trigger:** boundary/membership claims about 800 m catchments.
   **action:** point-in-polygon against `station-geometry.json`/
   `geometry.json` before asserting membership; treat brief leads as
   hypotheses. **exceptions:** polygon near-boundary points carry ±ring-
   precision; say so. **evidence:** batch-1 REVIEW F1; batch-2
   `tools/raw_fixes.py` corrections; 14 PIP checks.
4. **trigger:** dispatching parallel research subagents here. **action:**
   ≤2 concurrent; log access failures once (Overpass unavailable, Reddit/
   TripAdvisor 403); no retry loops. **evidence:** concurrency-limit errors
   in both batches; agents' Overpass failure logs.
5. **trigger:** editorial copy for place cards. **action:** mechanical
   radius→duration scan before assembly; rewrite to distance phrasing.
   **exceptions:** resident-reported durations with sources are allowed.
   **evidence:** 4 conversions found and rewritten across batches.

---

## 7. If you want the edits applied

Ownership: `HANDOFF.md` and `entity-research.schema.json` belong to the
sender's editorial line (untracked; I would produce a redline, not edit it);
`00-overview.md`, `description-rules.md`, `backlog.md` are tracked repo files
(patchable after approval); the kit promotion is a normal reviewed change.
Say the word and I'll draft the concrete diffs for any subset.

## Appendix — incident ledger (evidence index)

| Incident | Batch / location | Proves |
|---|---|---|
| Sala Daeng/Patpong "inside catchment" | pilot F1, `chong-nonsi-c03` | raw-radius reasoning fails; polygon checks required |
| Green 10 with no in-unit park (nana) | batch-2 `nana-c14` + PIP | unit ≠ measurement buffer (1 km by design) |
| Transport 10 for a 1.8 km monorail | batch-2 `charoen-nakhon` | transport model counts piers/buses by design |
| Lumphini "0.7–0.8 km" (actual 1.6–1.7) | batch-2 raw fix | agent distance estimates need machine checks |
| "15-minute walk" ×4 | pilot + batch-2 | prose bans need mechanical gates |
| Gold Line "crosses the river" (coordinator lead) | batch-2 prompt → agent correction | leads are hypotheses |
| Polarity `positive/negative` (38 claims) | batch-2 audit | prose-only contract drifts |
| QA `partial` / `claim_refs` variants | batch-2 | raw-output schema needed |
| Overpass blocked, 13 sessions | both batches | environment limits table needed |
| Nested mkdir from wrong cwd | batch-2 setup | kit scripts need `--batch-dir`, skeleton command |
