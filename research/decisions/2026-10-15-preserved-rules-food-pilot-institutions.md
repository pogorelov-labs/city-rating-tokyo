# ADR addendum: preserved rules, food shadow pilot, and institution facts

Date: 2026-10-15. Status: accepted scope; implementation and pilot outcomes are
tracked separately. This supplements, without rewriting, the
[2026-10-14 discovery ADR](2026-10-14-discovery-adoption.md).

## Acceptance source and precedence

The owner explicitly selected behavior-preserving shared normalization for
CRTKY-166 and a Tokyo food-only Overture 800 m shadow pilot for CRTKY-194. The
owner's subsequent “ok” to the coordinating session's proposal accepted the
CRTKY-190 institution scope below, the next wave, and the detailed pilot protocol.
The coordinating session relayed these
choices and the final protocol to the implementation lanes on 2026-10-15.
The earlier protocol artifact was titled “proposed”; that historical title is
not a claim that its accepted thresholds have already been measured or passed.

These decisions narrow the older ADR's automatic “two-source strong if passed”
language and the broader food/nightlife wording in CRTKY-194. Pilot acceptance
does not authorize production activation, confidence promotion, or nightlife
changes. The superseded original ticket wording is historical context, not the
authoritative scope of this wave; this addendum
records the subsequent owner choices, not a ticket-completion assertion.

## CRTKY-166: share implementation, preserve behavior

Extract common normalization primitives while preserving each city's existing
parameters, call-site semantics and results. Tokyo's HP-zero food behavior and
the Tokyo/Bangkok confidence divergence are deliberately retained for this
refactor, including existing missing/null behavior. Do not silently harmonize
them or change categories, weights, caps, rounding, or the percentile population.
Require characterization tests and offline output equivalence; a live refresh
is not an equivalence test and is not authorized by this decision.

Reconsider HP-zero behavior only after separate evidence and an explicit owner
decision defining zero versus missing/error, fallback provenance and score limits.

## CRTKY-194: bounded food-only shadow evaluation

“Tokyo” means the existing 1,493-station product frame across Tokyo, Kanagawa,
Saitama and Chiba. Stage 0 must establish a dated, status-bearing OSM food census
and sample feasibility before target HP/Overture outcomes. Historical empty food
source labels are not confirmed HP zeros; historical HP counts use 1 km, not the
pilot's matched 800 m universe.

- Core: 64 **new** sites, four prefectures × four OSM-density strata × four
  sites; two development and two locked holdout sites per cell (32 + 32).
  Strata are verified OSM zero and positive-count tertiles within prefecture;
  missing/errors are separate, and ties cannot create artificial density bins.
- Freeze census hashes, coordinates, stratum boundaries, seed
  `crtky194-food-v1|canonical_slug`, reserves, spatial blocks, category/status
  contracts, dates and request/storage budgets before target results. Require
  >1,600 m across development/holdout and between new and old diagnostic sites.
  Report unfilled cells as insufficient; do not silently shrink or redesign the
  sample after seeing outcomes.
- HP-zero challenge: up to 16 additional cases, eight OSM-rich and eight sparse,
  from at most 64 prescreen candidates in a frozen order. Rich is the upper
  positive tertile; sparse is verified zero or the lower positive tertile.
  Missing/error/partial data cannot supply a zero. Confirm genuine zeros with a
  second complete acquisition 24–72 hours later; an immediate repeat is invalid.
  A shortage explicitly leaves fallback evidence insufficient.
- The old 16-center experiment remains diagnostic only, outside the new core,
  fitting and holdout denominators. Development may refine the food candidate;
  freeze final code and rules before opening holdout. Tuning after holdout
  inspection consumes that holdout and requires new validation.
- Matched counts use identical centers and inclusive haversine distance ≤800 m.
  HP requires complete 1 km pagination followed by coordinate filtering.
  Preserve date, category, coordinate, filtering, deduplication and completeness
  evidence. Acquisition dates do not establish venue observation dates. Core
  HP/OSM acquisition must fit the protocol's seven-calendar-day window.

### Owner allocation amendment — 2026-10-15

After the complete Stage 0 census found only three Tokyo mapped-food zero
stations, the owner explicitly approved: “2 Tokyo zero + 6 low-positive sites,
keeping 64 total and 32/32 splits. Record the amendment, freeze revised
sample/acquisition budget, then run bounded shadow pilot. Keep production
rules unchanged.” The coordinating session relayed this approval on 2026-10-15.

This supersedes **only** Tokyo's cell allocation above: zero has one development
and one holdout site; low-positive has three of each; middle and high retain two
of each. Every other prefecture retains two of each per stratum. Preserve the
original insufficient 63-site artifact and census; it remains the evidence for
this pre-outcome amendment. Do not retroactively call it a complete sample.

The amended manifest must freeze exact IDs/centers, census and code hashes,
strata, reserve order, spatial exclusions, the separate HP-zero prescreen order,
category/status/dedup contracts and acquisition budgets before target outcomes.
Root checks that manifest and the acquisition/analysis code-review gates before
requests; this is coordination validation of the accepted pilot, not a new owner
policy decision. Holdout remains unopened until the primary candidate is frozen.
All quality, time-window, challenge, production and non-adoption gates below
remain unchanged. The executable manifest and staged acquisition contract are
documented in [the pilot protocol](../../scripts/food_pilot/PROTOCOL.md).

The final audit is **200 random distinct holdout Overture provider IDs**, not the
earlier 160-record proposal, plus up to 80 separately reported targeted cases.
Random sampling is over candidate-food IDs in the union of the 32 holdout
circles, without counting repeated station memberships as new records. It
estimates record precision in that frame, not citywide recall. Require ≥95%
jointly confirmed category/location/current-operation validity, ≤2% redundant
physical-venue records and ≤2% known-closed records. These are accepted
**observed-fraction** thresholds, with uncertainty and unresolved-case bounds
reported; they are not guarantees about confidence-interval limits. Unresolved
records are neither confirmed-valid nor automatically closed. Systematic
targeted failures can block a recommendation despite a passing average.

Locked-holdout Pearson ≥0.85 and Spearman ≥0.80 for HP total versus Overture food
are screening conditions, not standalone adoption evidence. Report paired
counts, raw/log behavior, calibration errors if applicable, ties, zeros,
geographic/density bias and block sensitivity. HP is not ground truth; shared
provider lineage does not establish independent evidence. Do not substitute a
better-performing food/nightlife union after seeing results.

Production remains a separate decision and execution gate. It requires a full
1,493-station, same-vintage offline baseline/candidate replay; separately identify
HP's radius change and the source change. Review food/rank/composite deltas,
8/9/10 cap crossings and zero/missing transitions. Median absolute percentile
shift >5 points, p95 >15 points, any food-score change >1, and any cap crossing
trigger explicit review, not an automatic claim of bad data. Other categories,
confidence and nightlife must remain unchanged with identical inputs. Define
the candidate's role and physical-venue identity/union contract before combining
providers; do not simply add overlapping catalog counts. Rights, attribution,
freshness SLA, source schema, upstream refresh, single-writer recovery and a
reviewed rollout remain prerequisites. Neither this ADR nor pilot success
authorizes production writes, schema changes or refresh.

## CRTKY-190: factual institutions within existing page scope

Retain Tokyo English-speaking medicine's **2 km straight-line** catchment and
label it precisely; do not silently replace it with the older proposed 800 m
radius. Bangkok district embassy counts use district polygon containment, not
an 800 m circle around a district center. Keep facts within the existing Tokyo
station, Bangkok station-area and Bangkok district page scopes; do not invent
Tokyo district pages as part of this work.

Bangkok English-service medicine remains gated on an appropriate verified,
publishable source. JNTO's Japan directory is not Thailand coverage. Preserve
counts-and-source-link publication limits, source QA exclusions and EN/JA/RU
labels. No institutions safety score, schools expansion, or unsupported service
availability/proximity claim follows from this decision.

## Completion boundaries

The accepted decisions unblock scoped implementation, not automatic closure.
CRTKY-194 can remain partial for census/sample feasibility, unavailable audit
evidence, the 24–72-hour zero confirmation, freshness and operator prerequisites.
CRTKY-190 can remain partial for Bangkok medicine's source gate. Record actual
results separately; retain negative and insufficient outcomes without weakening
the frozen protocol.
