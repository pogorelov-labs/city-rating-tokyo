# Critical review of the continuation plan — gaps, quality gates, DoD (2026-11-08)

A self-critique of [`2026-11-08-continuation-plan.md`](2026-11-08-continuation-plan.md)
and the program it plans, written the day after that plan. The point is to find
what is wrong or missing **before** work starts, define the gates that should
have been in the plan, and state the DoD the plan never stated. Amendments
resulting from this critique are applied to the plan (§5).

---

## 1. What is wrong or missed

### C1 — The plan has no Definition of Done. (Sev: high — the user's question exposes it)
Per-item acceptance criteria exist, but there is no DoD for a bundle, a
batch, or the program. Without it, "done" is whatever the last gate said.
Fixed: §4 defines DoD per artifact type.

### C2 — No failure path for the review gate. (Sev: high)
WS-A says bundles end `approved` or `blocked` — then nothing. No rework
workflow (who fixes, how re-reviewed), no quarantine rule (a blocked bundle
must be excluded from any integration slice), no SLA. → plan A-4.

### C3 — No evidence bar for product copy. (Sev: high — biggest integration gap)
The claim pool is 422 corroborated / 205 proposed / 40 conflicted. The
adapter spec (E-1) never says **which confidence tiers may surface where**.
Without a rule, a single-source or conflicted claim can reach a card preview.
→ plan E-5 defines the evidence bar (card copy: corroborated only; guide
narrative: corroborated + proposed with attribution; conflicted: never in
copy, only in evidence disclosure; researcher_inference: never in copy).

### C4 — No legal/defamation/privacy gate before publication. (Sev: high)
The corpus contains negative, nameable claims — scam environments (Patpong,
Nana), a mass-shooting event (Siam Paragon 2023), displacement narratives
(Sam Yan, Charoen Chai), "seedy"-adjacent labels, OTK shooting fatalities.
The handoff's own rules banned personal data, but **no publication-legal
review exists in the plan** for a consumer-facing product. → plan A-5.

### C5 — Thai-language verification risk. (Sev: medium)
Roughly a third of the 547 sources are Thai-language; the named reviewer may
not read Thai. The plan has no Thai-capable verification step for
Thai-sourced claims that surface in copy. → plan A-6.

### C6 — No bundle re-anchoring process after app-data changes. (Sev: high)
Every bundle stores score/rank/cohort/rent from snapshot
`bkk-d6499618507e7561`. When B-1..B-6 land (or any data refresh), 46 researched
bundles go stale — and if B-1 removes a station, **ranks shift for the whole
cohort** (133→132). D-3 regenerates only tier C. → plan D-4 (re-anchor pass:
re-derive selection_context from the new snapshot, claims untouched).

### C7 — WS-B has no dependency graph. (Sev: medium)
B-2 (anchors) must precede B-4 (polygons) and any Voronoi-dependent work;
B-1 (station set) precedes rank-dependent re-anchoring (C6); B-3 decision
gates the green sub-signal build. The plan lists priority, not order. → §5
adds the order: B-2 → B-1 → B-4 → B-3/B-5 → B-6.

### C8 — All B-items must pass the CRTKY-197 replay gate. (Sev: medium)
The plan cites the fail-closed replay process only for B-6. Generalize: every
data-layer change goes through snapshot-signature verification. → §5.

### C9 — The recheck calendar is a snapshot, not a living registry. (Sev: medium)
201 flags extracted once. Future batches will add flags; bundle `open_issues`
(~547 researcher notes) are not in it; nothing assigns an owner. → plan C-5
(living registry + `kit/recheck-due.py` regeneration at every batch end).

### C10 — No link-rot monitoring. (Sev: medium)
547 canonical URLs will rot; claims cite them as evidence. No scheduled
link-health check exists. → plan C-6 (quarterly HEAD-check wave, dead URLs
flagged on sources, claims downgraded to archived-citation status).

### C11 — The kit has no tests and no CI. (Sev: medium)
`assemble/validate/audit` are load-bearing and were patched repeatedly under
pressure (≥6 bugs found by ad-hoc smoke tests). → plan B-9 (unit tests over
fixture bundles + CI hook alongside the repo's existing checks).

### C12 — Tier-C card UX is undefined. (Sev: medium)
137 entities have no editorial preview — the map must decide what a tier-C
card shows (score+facts only? "guide pending"? no card?). → plan E-6.

### C13 — The work is unpushed on one local branch. (Sev: medium, needs user)
Six commits exist only on this machine. Push/PR is a user decision; the plan
should not assume it silently. → listed in §5 as an explicit decision item.

### C14 — Tier-B coverage debt untracked. (Sev: low)
Batch-4 selection skipped the dedicated axis-1 coverage scan; 24 tier-B
entities have no measured coverage breadth, yet D-2 trigger rules reference
coverage. → plan D-5 (fold a coverage battery into each future light pass).

### C15 — Continuation cost envelope unstated. (Sev: low)
D-1 ≈ 9 full-bundle runs ≈ 20–50M subagent tokens. The plan gives effort
letters but no token/cost line. → §5 adds estimates per research item.

### C16 — QA `partial` → `answered` normalization may overstate completeness.
(Sev: low) Batch-4 normalization collapsed `partial` statuses (logged, but
reviewers should specifically check those QAs). → reviewer packet note.

### C17 — Image re-verification scope undefined. (Sev: low)
WS-G doesn't say whether existing Wikimedia thumbs are re-verified for all
183 entities or only researched ones. → plan G-2 (scope: any entity whose
card ships — i.e., integration-driven, not coverage-driven).

### C18 — Safety-5 has no resolution path. (Sev: low, honest gap)
Five entities carry safety 5 with no unit-specific evidence. The plan notes
the pattern but never routes it: connect to CRTKY-150 (BMA risk registry) as
the evidence source that could resolve it, or label it perception-based.
→ §5 amendment.

### C19 — Four batches landed without inter-batch human review. (Sev: honesty note)
The handoff's stop-per-batch cadence was superseded by the dispatch
instruction ("continue autonomously"). That makes the pending human review
**more** important, not less — A-1 is the compensation for skipped cadence.
Stated here so it is not forgotten.

## 2. Quality gates — register

| # | Gate | Attaches at | Status | Mechanized |
|---|---|---|---|---|
| G1 | Schema + semantic-ref validation (`kit/validate.py`) | per bundle | ✅ | yes |
| G2 | Semantic audit — source-ID hashing, corroboration recompute, body-read reliance, banned words, radius→time, ref closure (`kit/audit.py`) | per batch | ✅ | yes |
| G3 | Digest gate — data files vs `source-manifest.json` | per batch, pre-research | ✅ | yes (shasum) |
| G4 | Geometry pass — PIP/haversine on boundary claims | per batch, pre-assembly | ✅ | partially (`check_geometry.py`) |
| G5 | Copy gate — banned phrases, radius→time | per batch, pre-assembly | ✅ | yes (in G2) |
| G6 | Post-hoc source verification (re-read of load-bearing claims) | weak bundles | ✅ | no (agent pass) |
| G7 | Batch-stop researcher review + findings doc | per batch | ✅ | no |
| G8 | Live-data integrity (`git status` clean of app files) | every commit | ✅ | manual |
| G9 | Data-only placeholder check | tier C | ✅ (audit handles) | yes |
| G10 | **Independent human review** | before product use | ⏳ defined, pending | packet |
| G11 | **Legal/defamation/privacy review** | before publication | ❌ missing → A-5 | no |
| G12 | **Copy evidence-bar enforcement** (C3) | adapter | ❌ missing → E-5 | to build |
| G13 | **Thai-source verification** | claims surfacing in copy | ❌ missing → A-6 | no |
| G14 | **Link-rot check** | quarterly | ❌ missing → C-6 | to build |
| G15 | **Bundle re-anchor after app-data change** | every snapshot change | ❌ missing → D-4 | to build |
| G16 | **Kit unit tests / CI** | every kit change | ❌ missing → B-9 | to build |
| G17 | **Personal-data audit** | before publication | ❌ missing → A-5 | no |
| G18 | Translation QA rubric | WS-F | ❌ missing (rubric undefined) | no |
| G19 | Image rights DoD per image | WS-G | ✅ defined in handoff/plan | no |

## 3. Definition of Done

### DoD — tier A bundle
1. `validate.py` PASS; `audit.py` zero open P1, P2s documented.
2. ≥4 useful sources / ≥3 publisher families; every load-bearing citation body-read.
3. All 12 QAs with status + ≥1 claim ref where answered/conflicting.
4. Editorial fully claim-linked; banned-copy and radius→time gates clean.
5. Geometry pass run for boundary claims; corrections logged in findings.
6. Recheck flags present in the calendar registry.
7. **Human review: `approved`** (G10). Blocked ⇒ rework per A-4.

### DoD — tier B bundle
As tier A with: ≥3 sources / ≥2 families; 8–12 claims; coverage noted
opportunistically (D-5 battery once built).

### DoD — tier C bundle
1. Identity (key/kind/name/score/rank) matches the **current** app snapshot.
2. Zero web sources, zero claims; 12 × `not_applicable` QAs; `draft` status.
3. Regenerated after every app-data change (D-3/D-4); bulk-approved (A-2).

### DoD — batch
Every bundle at its tier DoD · manifest + merged search log · findings doc
with verification results and open issues · kit gates green · committed with
live-data integrity confirmed.

### DoD — program (v1 "product-ready")
1. 183/183 bundles at their tier DoD; zero open P1 audit findings anywhere.
2. G10 (human review) passed; G11 (legal/privacy) passed for all user-visible copy.
3. Evidence bar (G12) implemented in the adapter and enforced.
4. E-2 integrated with app checks green; E-3 disclosures live; G14 link-rot
   check scheduled; recheck calendar owned.
5. Kit version-controlled with tests (G16).
6. Honest status page: which entities are copy-bearing (A/B approved) vs
   data-only (C).

### DoD — integration slice (E)
Spec approved → adapter merged (app checks green; bundle-size delta within
budget; lazy-load verified; untrusted-text rendering verified; rollback plan
documented) → disclosures live → copy passes G12/G11/G17.

### DoD — translations (F)
JA/RU rendered in the actual UI for approved units; native-quality review
signed off; qualifiers/uncertainty/money/date meaning preserved; zero English
leakage; locale fallback defined for units without approved copy.

### DoD — images (G)
Per image: license name/version + proof URL + commercial/derivative rights
recorded; required credit; geography match labeled; caption claim refs; alt
text; crop measured at real slots. `rights_status: unknown` ⇒ blocked from
publication. Scope per G-2 amendment.

## 4. Honest gaps that remain even after DoD

- Resident voice stays thin (Reddit/TripAdvisor blocked) — bundles note it;
  no mitigation path in this environment.
- Safety 5 remains perception-labeled until CRTKY-150 data lands (C18).
- Overpass-dependent POI ground truth (park identities: ari 5.1 ha, nana
  1.4 ha, ratchaprarop 3.2 ha straddle) — resolved only by the pipeline audit.
- Tier C is a map of ignorance: 137 entities are intentionally not researched.

## 5. Plan amendments applied (this critique → plan)

Added to the continuation plan: **A-4** review rework/quarantine path ·
**A-5** legal/privacy gate · **A-6** Thai-source verification · **B-0** WS-B
dependency order + generalized replay gate · **B-9** kit tests/CI ·
**C-5** living recheck registry + `kit/recheck-due.py` · **C-6** link-rot
waves · **D-4** bundle re-anchoring after app-data changes · **D-5** coverage
battery in future light passes · **E-5** copy evidence bar (G12) ·
**E-6** tier-C card UX · **G-2** image re-verification scope · program DoD
section · push/PR decision item · safety-5 routing to CRTKY-150.
