# HANDOFF.md redline — proposed amendments (2026-11-07)

**Status: proposal for the sender's editorial line.** This file does not edit
`HANDOFF.md` or `entity-research.schema.json`. Each amendment cites the
evidence that motivates it (batches 1–2 + quality reviews). Wording is
ready to paste; owners may tighten it.

Grounding documents the amendments rely on:
`research/bangkok/00-overview.md` (measurement definitions, honesty notes),
`research/bangkok/editorial/kit/README.md` (kit conventions),
`research/bangkok/editorial/batches/*/review/findings.md`.

---

## A1 — "Product meaning — keep these distinctions": append a measurement table and geometry rules

**After** the existing bullet list, **insert**:

> **How each rating is measured (from `research/bangkok/00-overview.md` —
> read before comparing evidence to scores):**
>
> | Rating | Basis |
> |---|---|
> | Green | OSM park/garden/woodland hectares **within 1 km of each grid point** (+ distance to a ≥1 ha park) — a unit can rate green 9–10 with **no park inside its 800 m polygon** |
> | Transport | rail network **plus bus stops and boat piers** + a door-to-door commute model to 5 hubs — non-rail access counts by design |
> | Crowd (less crowding) | population density + density of **all** Overture places, inverted; at station level: all-POI density **within 400 m** of the station |
> | Food / essentials / nightlife / vibe / gym | POI counts within each grid point's 800–1,200 m walking range, resident-weighted |
>
> A rating may therefore include area **outside the unit polygon**. When a
> bundle's evidence contradicts a score, record the mechanism as a claim and
> route the question to the pipeline review — do not treat it as a data
> defect and do not propose score changes.
>
> **Unit geometry is decided by the app polygons, never raw radius:** a
> station area is the Voronoi cell ∩ an 800 m disc; interchanges ≤ 450 m
> apart merge into one area (Asok+Sukhumvit, Sala Daeng+Si Lom, Mo
> Chit+Chatuchak Park, …); stations within 150 m of a khet border count for
> both sides. Run the geometry checker on every boundary claim before
> assembly and record results in the batch review.

**Evidence:** pilot F1 (Sala Daeng/Patpong "inside the circle" — `chong-nonsi-c03`); batch-2 green findings across 4 entities; charoen-nakhon transport-10 investigation; chong-nonsi crowd-1 interpretation.

## A2 — "Start with this six-place pilot" / next-batch section: add tiering

**Append** to the next-batch section:

> Expansion to 183 entities is **tiered**. Full bundles (this contract) go to
> top-coverage/top-rank and popular-but-contested entities; a lighter pass
> (identity + score context + contradictions, still a valid bundle with all
> twelve questions) goes to mid-tier; data-only notes to the long tail. The
> coverage scan and within-cohort rank decide tier — never a combined
> priority score. Observed cost of a full bundle: ~1.5–2M subagent tokens,
> 30–60 tool calls, 20–45 minutes per entity.

**Evidence:** two batches' usage; the handoff's own batching cadence.

## A3 — "Research method and source review": two insertions

**Insert** after the publisher-family paragraph:

> **Brief leads are hypotheses.** Coordinates, distances, clip directions and
> place attributions supplied in a brief are unverified starting points.
> Contradicting a lead with evidence is expected, valuable output — record it
> as a finding, not as a failure.

**Insert** a "Known access limits (verified 2026-11)" list:

> - Overpass/OSM APIs: **blocked** from research environments — verify
>   locations via Wikipedia coordinates or official pages; the coordinator
>   runs polygon checks afterwards.
> - Reddit, TripAdvisor, ExpatForum: 403 (resident-voice thinner than ideal).
> - BMA portals (webportal/visit/dp.bangkok.go.th): 403 to direct fetch.
> - Bangkok Post and some syndicated news: paywall-gateway redirects — not
>   bypassed; no proxy mirrors.
> - Dispatch research subagents **≤ 2 at a time**; log an access failure
>   **once** and move on — no retry loops.

**Evidence:** Overpass failures in all 13 agent sessions; 403s logged in both search logs; concurrency-limit failures at dispatch.

## A4 — "Storage contract": require the machine-checkable raw contract

**Append**:

> Subagent raw output must be **enum-exact** and must pass the kit's checks
> before the coordinator assembles it: kinds
> `factual_report|reported_perception|estimate|researcher_inference`,
> polarity `strength|tradeoff|mixed|neutral`, relations
> `inside|partial|outside|unknown|entire_unit`, source types from the schema
> enum, QA ids `Q01–Q12` with explicit `claim_ids`, editorial items as
> objects with `claim_ids` (no inline shorthand). Compound enum values are
> forbidden — put nuance in `limitations`/`notes`. The coordinator's
> assembler may normalize deviations, **logs every normalization**, and the
> batch audit reports the count; drift is a prompt/process defect, not a
> silent fix. (`research/bangkok/editorial/kit/` — scaffold, prompt
> template, geometry checker, assembler, validator, audit, briefs.)

**Evidence:** 2/2 batches needed normalization (38 polarity + 70 source-type + 12 QA-field corrections in batch 2 alone); assembler equivalence check against the reviewed batch reproduced bodies identically.

## A5 — "Quality gates and integration boundary": add the geometry + copy gates

**Insert** into the gate list:

> - **Geometry pass** (before assembly): boundary claims checked
>   point-in-polygon against `station-geometry.json`/`geometry.json`; results
>   recorded in the batch review; corrections applied to raw bundles with
>   assertion-guarded edits and documented in the review findings.
> - **Copy gate** (before assembly): mechanical scan for radius-derived
>   walking durations and banned phrases across all editorial text; rewrite
>   to distance phrasing.
> - Researcher-filled `review.checks` assert "verified by the researcher,
>   machine-checked where possible"; `reviewer`/`reviewed_at` stay null
>   until an independent review passes. Corroboration (≥2 publisher
>   families) is a label, **not** verification — families can repeat one
>   upstream error.

**Evidence:** 4 walk-time conversions caught by the audit regex rather than authors; 14 PIP checks catching one P1 and six numeric corrections; batch-2 "corroborated" geometry claims still needing polygon checks.

## A6 — QA status enum: no schema change; rule instead

**Insert** under Storage contract (schema unchanged — sender may optionally
add `partial` later):

> If a question is only partly answerable, use `answered` with a
> "partial coverage:" prefix in `notes` — `partial` is not a valid status.

**Evidence:** two agents invented status `partial` in batch 2.

## A7 — "Return report and stop point": codify where selection data lives

**Insert**:

> Coverage scans and selection memos are **batch artifacts**
> (`selection.md`, `raw/coverage-scan.json`). They never populate entity
> `popularity_*` fields: popularity stays `unmeasured` until a defined
> metric exists. Coverage breadth ≠ popularity — no search-hit totals, no
> venue stars, no ridership as proxies.

**Evidence:** batch-2 kept the separation correctly but nothing in the handoff required it.

## A8 — Pilot-bundle note carried forward

**Append** to the six-place pilot section:

> Batch-2 verification note: Wat Mangkon Kamalawat is both *outside the
> Samphanthawong khet* (pilot scope note — correct) *and inside
> st.wat-mangkon's catchment* (batch-2 — correct). Do not "fix" either
> statement against the other; they answer different questions. The
> bundle's scope_notes carry the khet attribution; catchment membership
> lives in the batch-2 bundle and the coordinator's polygon checks.

**Evidence:** batch-2 agent's "refutes the pilot" phrasing overstates a complementary finding.

---

### Not changed (deliberately)

- `entity-research.schema.json` — no schema change required for anything
  above; the raw contract + kit handle drift without schema churn. If the
  sender later wants a first-class `partial` QA status or a
  `geometry_verification` block, those are separate schema-versioned changes.
- The one-entity bundle rule, per-batch directories, stop-per-batch cadence,
  publisher-family rule, and rating-direction warnings: kept as-is (they
  worked; see the review's "keep unchanged" table).
