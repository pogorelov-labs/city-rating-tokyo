# Continuation plan & detailed backlog — Bangkok editorial research (v2.1, 2026-11-08)

**v2.1 — fully integrates both review passes AND the handoff-compliance sweep (2026-11-08): six misses against the original HANDOFF.md fixed — end-of-batch volatile recheck (C-7), structured conflicts_with links (B-13), manifest start/end times (B-14), validator cross-check (in B-9), guide section order + localized preview index + existing short-copy reconciliation (E-1/E-2), and mention-breadth with date window (D-5).**

**v2 — fully integrates both review passes.** The first version was amended
twice (critique pass → A-4/A-5/A-6, B-0/B-9, C-5/C-6, D-4/D-5, E-5/E-6, G-2,
program DoD; deep review → B-10/B-11/B-12, E-7/E-8/E-9, F-2, G20/G24, plus
E-1/E-3/B-2/A-1 amendments). This version folds every item into the
workstreams so nothing lives in an appendix. Review history:
[`2026-11-08-critique-gates-dod.md`](2026-11-08-critique-gates-dod.md) ·
[`2026-11-08-deep-review.md`](2026-11-08-deep-review.md).

## 0. State snapshot

- **183/183 entities** carry a schema-valid bundle: 22 tier A (full),
  24 tier B (light), 137 tier C (data-only placeholders, `draft` by design).
  Master index: [`2026-11-08-tier-plan.md`](2026-11-08-tier-plan.md).
- All 5 batches pass `kit/validate.py` (ALL OK); audits have zero open P1s;
  P2s are documented snippet-corroboration flags.
- Program totals (tiers A+B): 668 sources (527 body-read, 547 distinct URLs,
  299 publisher families), 667 claims — 422 corroborated / 205 proposed /
  40 conflicted **pre-canonicalization**; B-10 relabels 27 → **395/205/40**.
- Snapshot `bkk-d6499618507e7561` throughout; **no live app data, scoring,
  filters, geometry, translations, image registries or application code were
  touched** (git-verified per commit).
- Everything lives on local branch `research/editorial-batches-1-2`
  (7 commits) — push/PR is DEC-1.

## 1. How to read this plan

Owners: **HR** human reviewer · **SL** sender's editorial line · **PL**
pipeline/data team (build/replay gates) · **AG** research-agent workflow
(≤2 concurrent). Effort: **S** ≤ half a day · **M** 1–3 days · **L**
multi-week/multi-batch. Item IDs are stable across versions and referenced
from the two review documents.

## 2. Owner decision items (unblock the backlog — decide now)

| ID | Decision | Why it blocks | Default if un-decided |
|---|---|---|---|
| DEC-1 | Push/PR of branch `research/editorial-batches-1-2` (C13: single-copy risk) | all work is one local copy | none — work stays local and at risk |
| DEC-2 | Name the independent reviewer(s) for A-1 (A-1 now covers **four** batches — autonomous dispatch skipped inter-batch review, C19) | G10 blocks all product-facing use | gate stays open |
| DEC-3 | Name the recheck-calendar owner (C-5) | 201 dated flags with no maintainer | calendar decays |
| DEC-4 | D-1 budget envelope (≈9 full-bundle runs ≈ 20–50M subagent tokens; observed per-run 0.8–11.6M) | D-1 cannot start | not started |
| DEC-5 | Locale-parity posture (E-9): EN-only guides at launch vs delaying guides until JA/RU parity | WS-F scope | EN-only, flagged |
| DEC-6 | Green-basis decision (B-3): disclose the 1 km buffer vs add a catchment-interior sub-signal; exclude non-public state land | B-3 blocks | honesty-notes disclosure only |
| DEC-7 | Counter-evidence labeling policy (B-7): whether/where dated events (shootings, closures, evictions) are product-visible | B-7 blocks | not product-visible |
| DEC-8 | Tier-C card UX (E-6): what renders for 137 guide-less entities | E-6 blocks | score+facts card, explicit data-only label |
| DEC-9 | Corpus maintenance ownership + refresh SLO after this engagement (F-1, C-5) | every "AG" item beyond batch 5 | unassigned |
| DEC-10 | Adapter build-step location + schema-migration policy (E-1) | E-2 cannot start | recommended: `scripts/bangkok` export step; additive migrations only |

## 3. WS-A — Review & approval gates (P0 · blocks everything product-facing)

| ID | Item | Owner | Effort | Acceptance |
|---|---|---|---|---|
| A-1 | **Independent human review, tiers A+B (46 bundles; four batches in scope — C19).** Packet: `batches/REVIEWER-PACKET.md`. Spot pass 45–60 min; full pass 8–12 h. Reviewer sets `review.reviewer/reviewed_at/status` per bundle. Batch 3–4 stakes are in their findings docs; the five coordinator-drafted editorial sets (batch 3) and the batch-4 `partial`→`answered` QA normalizations are pre-flagged for attention (A-7). | HR (DEC-2) | M | every researched bundle `approved` or `blocked` with findings |
| A-2 | **Tier-C bulk check (137 placeholders):** identity vs current app snapshot, zero web claims, `draft` status — script-assisted. | HR (script-assisted) | S | tail batch approved or regeneration list produced |
| A-3 | **Sender adoption of amendments A1–A8** (in-repo amended `2026-11-05-handoff/HANDOFF.md`; redline with receipts). | SL | S | amended copy accepted, or superseding revision reconciled |
| A-4 | **Review rework/quarantine path (C2):** `blocked` bundles get a named fixer, scoped rework, re-review; blocked bundles are excluded from any integration slice until approved. Findings tracked per bundle. | HR + AG | M | no blocked bundle outside the quarantine list |
| A-5 | **Legal/defamation/privacy gate (G11/G17):** before any user-visible copy — negative nameable claims (scam environments, shootings, displacement narratives, venue labels) reviewed for defamation risk; bundle audit for personal data (resident quotes, addresses); redact or attribute. | HR + legal | M | sign-off for every copy-bearing unit |
| A-6 | **Thai-source verification (G13):** Thai-language claims that surface in copy get a Thai-capable check against the cited section (~⅓ of sources are Thai-language), or the claim is flagged and excluded from copy. | HR/AG | S | Thai-sourced copy verified or excluded |
| A-7 | **Reviewer focus list:** batch-4 QA `partial`→`answered` normalizations; sam-yot post-hoc verification pass; five coordinator-drafted editorial sets (batch 3); the corrected cross-batch facts (Rommaninat, Pathum Wan blends). | HR | S | covered in review notes |

## 4. WS-B — Data-layer fixes (P0/P1 · pipeline team · fail-closed replay gates)

**B-0 dependency order (C7):** B-2 (anchors) → B-1 (station set) → B-4
(polygons) → B-3/B-5 (product decisions) → B-6 (facts) — re-deriving
Voronoi/polygons before anchors are settled guarantees rework. **Every** B
change passes the CRTKY-197 fail-closed replay/signature process (generalized
from B-6, C8). Receipts: the 2026-11-07 + 2026-11-08 pipeline notes.

| ID | Item | Owner | Effort | Acceptance |
|---|---|---|---|---|
| B-1 | **Ghost-station audit (P0).** `st.sena-ruam` (rank #9/133) is a never-built BTS infill (N6) modeled as operating in `rail.json` (Prachachat 2026-11-05 council hearing is the live hook). Audit **all 139 stations** against operator publications; resolve sena-ruam (remove/reclassify — product decision; its catchment is a real gap cell between Ari and Saphan Khwai); add a build assertion: a modeled station must exist in a published operator source. | PL | M | 139-row audit table committed; sena-ruam resolved; build passes |
| B-2 | **Anchor-convention audit (P0) + distance-base rule.** App centers vs OSM/Wikipedia nodes differ 270–770 m on ≥8 units (saint-louis ≥720 m — the real infill station is 13.72082/100.52669), match to 5 decimals on others; Wikipedia/OSM themselves carry displaced coords for BTS Chit Lom and Victory Monument. Document the convention or correct coordinates; **add a distance-base rule** for bundles (app anchor vs verified station coordinate) and mark affected claims (saint-louis unit is the known case). | PL | M | convention documented in `00-overview.md`; offsets ≤ threshold or explained; geometry pass re-run; affected claims marked |
| B-3 | **Green-basis decision (P0; DEC-6).** Proven: green = park ha within 1 km of grid points. Decompositions: pathum-wan 102.7 ha = Lumphini 57.6 + Centenary 4.5 + One Bangkok ~8 + **RBSC 36.3 members-only** + royal 7.9 (~60–65% public); phra-nakhon ~19–20 public vs 38.5; chatuchak 149.2 OSM vs 167.1; ratchathewi 17.8 = 8.81 named public; din-daeng OSM ~3 vs app 15.5; **dusit 118.7 largely non-public** (zoo fenced since 2018; Sanam Suea Pa royal); kamphaeng-phet 0.1 ha in-unit. Decide: disclose the buffer basis in UI honesty notes, or add a catchment-interior green sub-signal; exclude non-public state land from public-green figures. | PL + product (DEC-6) | M | decision recorded; honesty update or pipeline change; re-derivation only via the build |
| B-4 | **Polygon quality pass (P1).** khlong-san district polygon (10 vertices, coarsest in set) PIP-OUTs ICONSIAM (in-khet per khwaeng Wat Kanlaya) and PIP-INS River City; sathon polygon hugs the south side of Sathorn Rd — all three BTS nodes PIP-OUT (the clean mechanism for transport 7); thon-buri does not contain BTS Wongwian Yai (khlong-san, per infobox + PIP); Victory Monument khet conflict (app polygon vs sources). Re-source coarse district polygons or document the 150 m border rule per case. | PL | M | PIP audit table for affected khets; polygons corrected or cases documented |
| B-5 | **Rent semantics cleanup (P1).** Dual "Pathum Wan blends" (phloen-chit record 33,500/74,000 vs district record 38,000/85,000); chit-lom 120,000 2-bed override is top-decile luxury, not a median (FazWaz Pathum Wan 2-bed avg 99,600, n=1,114; corridor median ~40k); pom-prap 2-bed 24,000 sits below all 14 observed asks (25,000–32,000) → recalibrate via CRTKY-141. Keep `blend`/`override`/`median` labels visible in ComparePanel. | PL | M | one blend per district; labels verified; pom-prap recalibrated |
| B-6 | **Fact corrections (P1, quick).** ratchathewi "1 Michelin star" → two one-star venues verify in-khet (Signature at VIE, Wana Yook); chit-lom "5 piers" → 2 distinct (4 duplicate OSM nodes); ratchathewi "0 piers" vs Pratunam pier nodes PIP-in-khet; hua-lamphong "2 piers" = canal (Khlong Phadung Krung Kasem), not river; Four Seasons Bangkok = 2015 rebrand, not 2024; OTK "CNN 4th best" rank unverifiable (URL 404) — already excluded from claims. | PL | S | corrections via fail-closed build replay |
| B-7 | **Counter-evidence → labeling policy (P2; DEC-7).** Dated events with receipts: Or Tor Kor shooting 2025-07-28 (5 dead); din-daeng = noisiest PCD station (71.6–81.6 dB(A), 182/182 days over) + Rocket Media rank 50/50; BTS Asok rush failure 2025-09-25; 529-stallholder clock-tower eviction 2025; Jodd Fairs Rama 9 demolished 2025-01; Khlong San Plaza closed 2021. Decide product visibility; **never** let a single incident become a persistent area label (handoff rule). | product (DEC-7) | S | policy recorded |
| B-8 | **Kit TODO (P2).** `check_geometry.py --khet` flag (station-geometry `chatuchak` key shadows the district key — found by the batch-3 chatuchak agent). | AG | S | flag added + tested |
| B-9 | **Kit unit tests + CI (G16).** assemble/validate/audit are load-bearing, patched ≥6 times under pressure. Fixture bundles + expected outputs, wired beside the repo's existing checks; when `jsonschema` is available, cross-check the kit validator against the real Draft-2020-12 validator on the fixture set (the handoff requires validation against `entity-research.schema.json` proper). | PL | S | kit tests green in CI; validator cross-checked; changes fail closed |
| B-10 | **Canonical family mapping + corroboration relabel (G21).** Exact family-string matching let "English Wikipedia"+"Thai Wikipedia" count as two families: canonical mapping relabels **27 of 422 corroborated claims to proposed (422→395)** — affected list produced (bang-sue, thon-buri, dusit, bang-phlat EN+TH pairs). Implement canon mapping in `kit/assemble.py`, re-label, re-gate. | AG | S | relabel applied; gates green; corrected counts in manifests |
| B-11 | **Canonical source registry (G21 companion).** 49 URLs are cited with inconsistent publisher/title across bundles ("Wikipedia" vs "Wikipedia (English)"; per-claim Overpass titles). Build URL → canonical publisher/title registry; adapter references it so merged citation views show one attribution. | PL/AG | S | registry committed; adapter uses it |
| B-12 | **Source-type taxonomy refinement.** 58% of sources sit in the collapsed `other` bucket (encyclopedia/OSM/datasets swallowed); refine the enum or add subtypes; report source-mix per bundle. | SL/AG | S | taxonomy v1.1 or documented decision |

| B-13 | **Populate `conflicts_with` (handoff: every claim needs its conflicts).** Conflicts are currently captured via `conflicted` status + limitations + QA notes, but the schema's structured claim-to-claim link field is empty everywhere. Where two claims in one bundle conflict (e.g. chit-lom opening dates, sala-daeng Lalai Sap schedule), link them; extend `kit/validate.py` to check link integrity. | AG | S | conflicts_with populated where detectable; validator checks links |
| B-14 | **Manifest completeness (handoff: manifest records start/end times).** Manifests currently stamp only `created_at`. Emit research start/end times (first/last raw-write mtimes per batch). | AG | S | manifests carry start/end; batch DoD updated |

## 5. WS-C — Re-verification calendar (P1 · AG · quarterly waves)

**201 dated recheck flags** extracted from the researched bundles — registry:
[`2026-11-08-recheck-calendar.csv`](2026-11-08-recheck-calendar.csv)
(16 due 2026 · 150 during 2027 · 2 later · 33 tied to named events).

| ID | Item | When | Notes |
|---|---|---|---|
| C-1 | Wave **2026-11/12** (≈11 items): Wat Saket temple fair (Nov 2026); Rajavithi Skywalk phase-1 opening; national-stadium concert calendar; Silom Walking Street; nana green/clip audits; phloen-chit green decomposition re-anchors | Nov–Dec 2026 | light-agent waves |
| C-2 | Wave **2027-01** (≈21 items): Central Phaholyothin completion (Q4 2026); rent re-audits (asok, ari, thong-lo, nana, chong-nonsi, phloen-chit); Hua Lamphong transition; market reorganizations; CODI relocation progress | Jan 2027 | |
| C-3 | Wave **2027-02 → 2027-06** (≈70 items — the spring cluster): One Bangkok phases; canal-park progress; Chula/RMU land dispute; vendor-crackdown effects; Charoen Chai status; Khlong Thom Center post-fire; rents across tier A/B | quarterly | |
| C-4 | Wave **2027-07 → 2029** (≈40 items): DOPA census releases; quarterly portal rent refresh; SRT/MRTA/BEM ridership; named milestones (Purple line Nov 2030, Orange line Jul 2030, Ratchathewi flyover Apr 2028, Central Ladprao renovation to 2058 lease) | as published | |
| C-5 | **Living registry (C9):** regenerate the calendar at every batch end via `kit/recheck-due.py`; fold bundle `open_issues` (~547 notes) in as verifiable items; **owner named via DEC-3**. | continuous | script to build |
| C-6 | **Link-rot waves (G14):** quarterly checks over the 547 canonical URLs; dead URLs flagged on the source record, affected claims downgraded to "archived citation" status — never deleted silently. | quarterly | script to build |

| C-7 | **End-of-batch volatile recheck (handoff method rule — missed in all four batches).** Before closing any batch, re-open the volatile operational/price/closure sources it cites (rents, market schedules, opening hours, transport status) and confirm they still say what the claims say; append dated confirmation notes or corrections. Batch DoD updated accordingly. | AG | S per batch | batch DoD item; no stale-at-close volatiles |

## 6. WS-D — Tier upgrades & corpus maintenance (gated on A-1)

| ID | Item | Candidates | Effort |
|---|---|---|---|
| D-1 | **B → A (full bundles)** for contested/featured units: st.sala-daeng (nightlife 10 = the real heart, 108 venues; Lumphini Voronoi split), st.siam (flagship; 6 ha park unnamed; Paragon-event history), st.chit-lom (120k override), st.phetchaburi (merge resolved + CODI displacement), st.hua-lamphong (afterlife), st.saphan-taksin (river hub; cancelled rebuild), st.victory-monument (renovation + khet conflict), st.mo-chit (market reorg), st.phra-ram-9 (Jodd Fairs demolition + GR9 redevelopment). Budget: DEC-4. | 9 | L |
| D-2 | **C → B (light)** on triggers: product-surfaced entity; coverage/news event; user selection. | rolling | per-trigger |
| D-3 | **Tier-C regeneration** from each new app snapshot (identities/scores move; placeholders must not drift). | all 137 | S (scripted) |
| D-4 | **Bundle re-anchoring (G15) after any app-data change (C6):** B-1/B-2/B-3 change scores, ranks, cohort sizes — all 46 researched bundles' `selection_context` goes stale; a station-set change recomputes cohort ranks everywhere. Re-derive `selection_context` from the new snapshot (claims untouched). | AG (scripted) | S per change |
| D-5 | **Coverage battery in future light passes (C14) — and the handoff's second browsing choice.** Batch-4 skipped the dedicated axis-1 scan; fold the 3-query coverage battery into every new light bundle, and record per entity a structured **editorial mention breadth with its date window** (independent-family count + window) in the batch manifest — the handoff lists "documented editorial mention breadth with its date window" as a separate product-browsing choice alongside score and evidenced themes. Bundles keep `popularity_*` unmeasured; breadth lives in the manifest, not the bundle. | AG | S |

## 7. WS-E — Product integration (P1 · separate reviewed change · gated on A-1)

| ID | Item | Owner | Effort | Acceptance |
|---|---|---|---|---|
| E-1 | **Adapter design spec** + two decisions from DEC-10: build-step location (`scripts/bangkok` export recommended) and a schema-migration policy (additive; `schema_version` bumps with migration notes). Localized preview index in the map bundle (locale keys with EN fallback until WS-F) → per-place guide narrative + evidence disclosure loaded on demand; entity-key mappings = existing `st.*`/district slugs; article text rendered as plain text only. **Guide section order follows the handoff**: identity/scope → distinctive character → strengths and trade-offs → conditional fit/time/subareas → deeper facts and sources → optional gallery. **Reconcile with the existing short-copy strings**: `app/src/data/area-guide-copy.json` currently holds exactly six `bangkok:station:*`/`bangkok:district:*` keys (the pilot set) — never silently overwrite; migrate/version them through review. | product+eng | M | spec reviewed and approved |
| E-2 | **Implementation** behind E-1, with the app's own checks (lint, toolchain tests, TS, production build, e2e). Research is **never** imported into `districts.json`/`stations.json`/rent references **or the existing `area-guide-copy.json` short-copy strings** (handoff boundary; reconcile via reviewed migration instead). | eng | L | app checks green; map bundle delta within budget |
| E-3 | **Score-context disclosures in UI (A4/C-ep4):** green buffer basis, transport mechanism, rent label semantics — placed **one tap from the score** (not buried in the guide); plus a corpus-skew disclosure (expat/tourist source skew, score-correlated selection, single-season observations). | product | S | disclosures live |
| E-4 | Raw research corpus stays out of the map bundle (hard rule); gallery/preview images only after WS-G. | eng | — | bundle audit |
| E-5 | **Copy evidence bar (G12) — the load-bearing new gate.** Card preview: **corroborated claims only** (canonical families, post-B-10). Guide narrative: corroborated + proposed with attribution. Conflicted claims: never in copy — evidence disclosure only. `researcher_inference`: never in copy. Enforced by the adapter with a test case, not by convention. | eng+product | M | adapter rejects out-of-bar claims (test in CI) |
| E-6 | **Tier-C card UX (DEC-8) — the two-speed seam is visible by design (A1).** 137 guide-less entities render an explicit data-only card (score+facts); the adapter must **never** synthesize guide-like prose from facts for unresearched units — that would launder tier C into fake tier A. | product | S | decision recorded + implemented |
| E-7 | **Corridor coherence pass (G22) + cross-bundle fact sweep.** Adjacent researched units narrate shared places with un-swept framing contradictions (chong-nonsi/sala-daeng/bang-rak on Silom–Patpong–Lumphini; wat-mangkon/sam-yot/sanam-chai on the canal; asok/nana/phloen-chit on Sukhumvit) — sweep framing (not raw facts), plus the remaining cross-bundle fact drift (One Bangkok is consistent ×4; Pathum Wan blends are not). Fix before integration. | AG | M | coherence report; fixes applied |
| E-8 | **Voice/length normalization + time-boxing (G23).** Measured variance: 18.2 vs 13.8 vs 9.2 editorial items/unit; previews 137–543 chars. Adapter caps sections, normalizes register on structured fields (never rewrites semantics), stamps each guide with its observation window, renders change claims with event dates ("demolished 2025-01", never unanchored "recently") and rhythm claims with observed-period labels (single-season observations). | eng | M | normalized build; no semantic drift |
| E-9 | **Locale-parity posture (DEC-5):** JA/RU get nothing until WS-F — decide launch posture. | product | S | decision recorded |

## 8. WS-F — Translations gate (P2 · after E-2 approval of EN copy)

| ID | Item | Owner | Effort | Acceptance |
|---|---|---|---|---|
| F-1 | JA/RU rendering of approved editorial per `description-rules.md` §7: native writing, not translationese; preserve unit, qualifiers, uncertainty, money/date meaning, conditional fit; reviewed **in the actual UI**; locale fallback defined for units without approved copy. Rubric = G18. | product+translators | M | G18 sign-off in real UI |
| F-2 | **Method amendment (standing rule): AI-summary provenance banned** in all future research (6 exist today — flagged, never sole evidence). Every citation requires a stable canonical URL; AI/search-summary sources may not be added even as corroboration. | AG | — | prompt template updated; G24 sweep enforces |

## 9. WS-G — Image rights pass (P2 · parallel-safe after A-1)

| ID | Item | Owner | Effort | Acceptance |
|---|---|---|---|---|
| G-1 | Candidate hunt per researched entity in role order (station entrance → neighborhood street → usable park → landmark → night context); per image: license name/version + proof URL + commercial/derivative rights + required credit + geography match + caption claim refs + alt text + crop measured at real slots (current input 600×220 — measure responsive slots first). `rights_status: unknown` blocks publication. Candidates registered in bundle `images` arrays only after the rights check. | AG + HR | M | per-image DoD met (G19) |
| G-2 | **Scope (C17):** re-verification covers **any entity whose card ships** (integration-driven), not only researched entities — existing Wikimedia thumbs on unresearched units get the same license/version re-check when their card goes live. | AG | S | scope recorded in E-1 spec |

## 10. WS-H — Standing guards & method rules (do NOT do)

1. **No score edits** proposed or made by research — disputes route to pipeline tickets with receipts.
2. **No popularity adoption** from coverage counts (selection signal only).
3. **No tier-C fabrication** — placeholders stay honest drafts; the adapter never synthesizes prose for unresearched units (pairs with E-6).
4. **The machine gates are the load-bearing control** — prompt prose drifted in every batch; validate/audit/injection-sweep run at every assembly. Inter-batch human review was skipped under autonomous dispatch (C19) — A-1 is the compensation control and covers four batches.
5. **No paywall bypass, no proxy mirrors, no personal data** — standing method rules; AI-summary provenance banned (F-2).
6. **Safety-5 routing (C18):** the five safety-5 entities stay perception-labeled until CRTKY-150 (BMA risk registry) provides evidence — connect there; do not invent unit-level claims.
7. **Corridor honesty:** adjacent-unit guides must not contradict each other's corrected facts (Rommaninat, Pathum Wan blends) — E-7 enforces before integration.

## 11. Quality-gate register (G1–G24)

| # | Gate | Attaches at | Status | Mechanized |
|---|---|---|---|---|
| G1 | Schema + semantic-ref validation | per bundle | ✅ | `kit/validate.py` |
| G2 | Semantic audit (IDs, corroboration, body-read reliance, banned words, radius→time, ref closure) | per batch | ✅ — B-10/B-11 refine canonicalization | `kit/audit.py` |
| G3 | Digest gate vs `source-manifest.json` | pre-research | ✅ | shasum |
| G4 | Geometry pass (PIP/haversine on boundary claims) | pre-assembly | ✅ (B-8 adds `--khet`) | `kit/check_geometry.py` |
| G5 | Copy gate (banned phrases, radius→time) | pre-assembly | ✅ | in G2 |
| G6 | Post-hoc source verification | weak bundles | ✅ (sam-yot precedent) | agent pass |
| G7 | Batch-stop researcher review + findings | per batch | ✅ | manual |
| G8 | Live-data integrity | every commit | ✅ | `git status` |
| G9 | Data-only placeholder check | tier C | ✅ | audit handles |
| G10 | Independent human review | before product use | ⏳ pending (DEC-2) | packet |
| G11 | Legal/defamation review | before publication | ❌ → A-5 | no |
| G12 | Copy evidence-bar enforcement | adapter | ❌ → E-5 | to build |
| G13 | Thai-source verification | copy-bearing Thai claims | ❌ → A-6 | no |
| G14 | Link-rot check | quarterly | ❌ → C-6 | to build |
| G15 | Bundle re-anchor after app-data change | every snapshot change | ❌ → D-4 | to build |
| G16 | Kit tests / CI | every kit change | ❌ → B-9 | to build |
| G17 | Personal-data audit | before publication | ❌ → A-5 | no |
| G18 | Translation QA rubric | WS-F | ❌ rubric undefined → F-1 | no |
| G19 | Image rights per image | WS-G | ✅ defined | manual |
| G20 | Injection/HTML sweep over user-facing text | every assembly | ✅ today (0 hits) — promote to kit | scripted |
| G21 | Canonical family mapping in corroboration | assembly | ❌ → B-10 | to build |
| G22 | Cross-bundle coherence pass | before integration | ❌ → E-7 | agent pass |
| G23 | Voice/length normalization + time-boxing | adapter build | ❌ → E-8 | to build |
| G24 | Citation URL-scheme + AI-summary ban | assembly | ❌ → F-2/G24 | trivial check |

## 12. Program Definition of Done (C1)

"Product-ready v1" holds when **all** of the following are true:

1. 183/183 bundles at their tier DoD (A/B human-approved via G10; C bulk-approved via A-2).
2. Zero open P1 audit findings across all batches.
3. Legal/privacy (A-5) signed for every copy-bearing unit; Thai verification (A-6) done or copy excluded.
4. Evidence bar (E-5/G12) implemented **and test-covered** in the adapter.
5. Integration slice merged with the app's own checks green; disclosures (E-3) live; tier-C card UX decided (E-6/DEC-8).
6. Bundle re-anchoring current with the shipped app snapshot (D-4/G15).
7. Recheck calendar owned (DEC-3) and current; link-rot waves scheduled (C-6/G14).
8. Kit under tests in CI (B-9/G16).
9. Honest status surface: which entities are copy-bearing (A/B approved) vs data-only (C) — no laundering.
10. End-of-batch volatile rechecks (C-7) performed and recorded for every researched batch (handoff method rule).

Per-artifact DoD (full checklists): [`2026-11-08-critique-gates-dod.md`](2026-11-08-critique-gates-dod.md) §3.

## 13. Sequencing (dependency-ordered)

```
Now        → DEC-1..DEC-10 owner decisions
           → A-1/A-2 review gates ∥ A-3 sender adoption
           → B-2 → B-1 → B-4 (P0 data, fail-closed replay) ∥ B-10/B-11 (kit canon)
Next       → B-3/B-5/B-6/B-7 (product decisions + facts) ∥ B-8/B-9/B-12 (kit/taxonomy)
           → D-4 re-anchor (after any landed data change) ∥ D-3 tail regen
Gated on   → D-1 batch 5 (B→A upgrades; DEC-4) ∥ C-1 recheck wave (Nov–Dec 2026)
A-1
Then       → E-1 spec → E-2 implementation ∥ E-7 coherence pass ∥ E-5 evidence bar
           → E-3 disclosures ∥ E-6/DEC-8 tier-C card ∥ E-8 normalization ∥ G20/G24 in kit
When live  → WS-F translations (F-1) ∥ WS-G images (G-1/G-2)
Always     → C-5/C-6 registry upkeep ∥ D-5 coverage battery ∥ WS-H guards
```

## 14. Registry & review history

- Master index + tiers: [`2026-11-08-tier-plan.md`](2026-11-08-tier-plan.md) (183 rows)
- Recheck calendar: [`2026-11-08-recheck-calendar.csv`](2026-11-08-recheck-calendar.csv) (201 items)
- Pipeline receipts: [`../notes/2026-11-07-editorial-batch-pipeline-followups-crtky130.md`](../notes/2026-11-07-editorial-batch-pipeline-followups-crtky130.md) (2026-11-08 update appended)
- Reviewer packet: [`batches/REVIEWER-PACKET.md`](batches/REVIEWER-PACKET.md) (covers batches 1–4 + tail)
- Final program review: [`2026-11-08-final-review.md`](2026-11-08-final-review.md)
- Critique + gates + DoD: [`2026-11-08-critique-gates-dod.md`](2026-11-08-critique-gates-dod.md)
- Deep review (five angles, empirical): [`2026-11-08-deep-review.md`](2026-11-08-deep-review.md)
- Kit: [`kit/`](kit/README.md) (scaffold · prompt template · geometry checker · assembler · validator · audit · briefs)
