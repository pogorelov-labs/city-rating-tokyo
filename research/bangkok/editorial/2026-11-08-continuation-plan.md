# Continuation plan & detailed backlog — Bangkok editorial research (v2.4, 2026-11-08)

**v2.4 — A-8 executed and integrated: all 24 blocked bundles cleared (F1: 72 editorial rebuilds from raw · F2: 49 limitation joins · F4: 95 profile-level strips · F3: 17 body-read upgrades + 1 replacement source + 4 removals with substance preserved · F5/F6/F7/F10/F12 fixed); 46/46 researched bundles `approved` (agent-review provenance); main report's Result/table/addendum updated; ledger [`2026-11-08-a8-rework-log.jsonl`](2026-11-08-a8-rework-log.jsonl). B-13 caveat resolved (c06→c02/c04 link removed per F7); B-13/B-9/G6 rows refreshed; A-7 covered by the review; F8 findings-files remain owed (A-9). **The only open A-gate is the human signature (DEC-2) over the 46 approved bundles.**

**v2.3 — integrates the independent agent review (A-1 executed: 22 approved / 24 blocked; tier C 137/137) and the third critical pass. New/changed: A-8 rework queue (24 blocked bundles, dependency-ordered); B-4 khlong-san claim corrected (station cell ≠ khet — verified by own PIP probes; final-review §2.4 and pipeline notes corrected too); B-13 conflict-link caveat; B-15 contract-derived audit checklist; E-5 amended (copy eligibility keys on HUMAN sign-off — `agent-review:*` reviewer ≠ copy-eligible); gate-count convention (audit findings are rule-relative — always report the rule version); F-4-fix must NOT re-assemble batch 2; D-6 Telegram corpus in the workflow; C-6 wave 1 done; PR #177 live.**

**v2.2 — the agent-executable lane is DONE (2026-11-08, commits 28805ad…): B-8, B-10, B-11, B-13, B-14 executed; G20/G21/G24 live in the kit; F-2 standing rules in the prompt template; kit unit tests green (B-9 local part). Corroboration relabel landed at the deterministic 23 (→ 399/228/40), superseding the deep review's 27; 71 batch-4 limitations arrays repaired (new audit rule); tail-batch manifest gap fixed. Remaining: owner decisions (DEC-1…10), human review gates (A-1/A-2), pipeline-team items (B-1..B-7, B-9 CI wiring), WS-C/D/E/F/G.**

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
- **Independent agent review executed (A-1 agent pass, 2026-11-08)**:
  **22 approved / 24 blocked**; tier C **137/137 PASS** independently
  reproduced. Recorded in `review.reviewer` as `agent-review:*` — **not a
  human signatory**; DEC-2/G10 (human sign-off) remains open. Report:
  [`2026-11-08-independent-review.md`](2026-11-08-independent-review.md).
  All 24 blocks were cleared by the A-8 rework the same day (46/46 `approved`,
  agent-review provenance).
- All 5 batches pass `kit/validate.py` — **genuinely as of 2026-11-08**: the
  schema half of the validator had been silently discarding errors
  ([`2026-11-08-gate-verification.md`](2026-11-08-gate-verification.md));
  after the fix + a logged contract-repair pass, ALL OK ×5 (schema +
  semantic) and audit zero-P1 ×5 stand for real.
- Program totals (tiers A+B): 668 sources (527 body-read, 547 distinct URLs as
  researched — 543 after the contract-repair merges, 299 publisher families),
  667 claims — 422 corroborated / 205 proposed /
  40 conflicted as researched; **399 / 228 / 40 after the executed B-10
  canonical relabel (2026-11-08; deterministic rule set, 23 relabels —
  [`2026-11-08-canonical-relabel.md`](2026-11-08-canonical-relabel.md))**.
- Snapshot `bkk-d6499618507e7561` throughout; **no live app data, scoring,
  filters, geometry, translations, image registries or application code were
  touched** (git-verified per commit).
- Branch `research/editorial-batches-1-2` — **pushed to origin + PR opened
  2026-11-08 (DEC-1 approved and executed)**.

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

**Decision record (2026-11-08, user approval):** **DEC-1 executed** — branch
pushed to `origin` and PR opened to `main` (§15). **DEC-5, DEC-6, DEC-7,
DEC-8, DEC-10 adopted at the recommended defaults as listed above.**
**DEC-2, DEC-3, DEC-4, DEC-9 remain open** — they need named people or a
budget figure and cannot be satisfied by a blanket approval; their stated
defaults apply (review gate stays open; calendar unowned; D-1 not started;
maintenance unassigned).

## 3. WS-A — Review & approval gates (P0 · blocks everything product-facing)

| ID | Item | Owner | Effort | Acceptance |
|---|---|---|---|---|
| A-1 | **Independent human review, tiers A+B (46 bundles).** 🟡 **Agent review DONE 2026-11-08: 22 approved / 24 blocked** ([`2026-11-08-independent-review.md`](2026-11-08-independent-review.md); reviewer recorded as `agent-review:DeepSeek Harness/deepseek-flash`, explicitly not a human signatory). ⏳ **Human sign-off remains (DEC-2)** — after the A-8 rework, all 46 bundles carry `review.status = approved` with rework notes; the human signs them in one pass. Packet: `batches/REVIEWER-PACKET.md`. | HR (DEC-2) | M | every researched bundle human-signed |
| A-2 | **Tier-C bulk check (137 placeholders).** ✅ **DONE pending signature**: script half 137/137 PASS ([`2026-11-08-tier-c-bulk-check.md`](2026-11-08-tier-c-bulk-check.md), `kit/tools/tier_c_bulk_check.py`) + independently reproduced by the agent review; human/owner signature is the remaining act (DEC-2). | HR (script-assisted) | S | owner signature recorded |
| A-3 | **Sender adoption of amendments A1–A8** (in-repo amended `2026-11-05-handoff/HANDOFF.md`; redline with receipts). | SL | S | amended copy accepted, or superseding revision reconciled |
| A-9 | **Batch findings files owed (review F8 — not part of the A-8 fix scope):** batch 3 and batch 4 have no `review/findings.md` (batch 4 also lacks `selection.md`); the reviewer re-derived stakes from bundles/notes. Write the researcher findings records retroactively (documented as such — dated, marked 'reconstructed 2026-11-08 from bundle notes, search logs and the review'), so the batch DoD (G7) closes. | AG | S | findings.md ×2 + selection.md present, marked reconstructed |
| A-4 | **Review rework/quarantine path (C2):** `blocked` bundles get a named fixer, scoped rework, re-review; blocked bundles are excluded from any integration slice until approved. Findings tracked per bundle. → **ACTIVE: A-8 below.** | HR + AG | M | no blocked bundle outside the quarantine list |
| A-8 | ✅ **DONE 2026-11-08** — all 24 blocks cleared; 46/46 researched bundles `approved` (agent-review provenance; human sign-off pending). Executed: F1 (72 editorial rebuilds from raw) · F2 (49 limitation joins) · F4 (95 blocks stripped, profile-level) · F3 (17 body-read upgrades incl. 1 replacement source + scoped reword; 4 claims removed: sam-yot c11/c17, hua-lamphong c02/c12 — substance preserved in review.notes) · F5 (khlong-san c02/c03 rewritten from `--khet` truth, statuses recomputed) · F6 (app-data entries moved to limitations / claims removed) · F7 (wat-mangkon wording + B-13 link removed) · F10 (voice swept, zero leftovers) · F12 (12 QA notes). Ledger: [`2026-11-08-a8-rework-log.jsonl`](2026-11-08-a8-rework-log.jsonl). Original queue for the record —
 1. **F1+F2 (lossless, from `raw/`):** rebuild corrupted `day_night`/`within_area_variation`/`uncertainties` (60 placeholder entries, 12 batch-4 bundles) + repair mixed/source limitations arrays (49 more, 7 bundles). Kit rule extended to their ≥10-single-char form; byte-checkable vs raw.
 2. **F4 (batch 2, 4 bundles):** strip inline `[ent-cNN]` refs from copy; per-block claim_ids from the block's own text. **Profile-level logged strip — NEVER re-assemble** (raw/ predates coordinator corrections; amended from the reviewer's §9.2).
 3. **F3 (6 bundles, 21 claims):** body-read or replace sole evidence, or drop the claim + the copy citing it. Real re-research; token cost — DEC-4-adjacent. sam-yot (11 claims) is the sharp end; the "post-hoc pass" its commit message claims is NOT in the delivered bundle.
 4. **F5 (khlong-san):** rewrite c02/c03/scope_notes from `--khet` truth (khet ring CONTAINS ICONSIAM/G2, excludes River City); correct final-review §2.4 (done) + pipeline notes (done).
 5. **F6/F7/F10/F12:** app-data locators off web sources (4 claims); wat-mangkon "refutes the pilot" → "consistent with" wording (and re-examine the B-13 conflicts_with link target); internal/research voice out of copy; charoen-nakhon QA notes re-derived.
 Re-run validate+audit after each step; re-review per A-4. | AG (fixer) + HR (re-review) | M | 24 blocked → 0 blocked; re-gates green under the current rule version |
| A-5 | **Legal/defamation/privacy gate (G11/G17):** before any user-visible copy — negative nameable claims (scam environments, shootings, displacement narratives, venue labels) reviewed for defamation risk; bundle audit for personal data (resident quotes, addresses); redact or attribute. | HR + legal | M | sign-off for every copy-bearing unit |
| A-6 | **Thai-source verification (G13):** Thai-language claims that surface in copy get a Thai-capable check against the cited section (~⅓ of sources are Thai-language), or the claim is flagged and excluded from copy. | HR/AG | S | Thai-sourced copy verified or excluded |
| A-7 | ✅ **Covered** — the independent review examined every focus item (QA normalizations, sam-yot provenance — and found its post-hoc pass unevidenced, now re-done in A-8; coordinator-drafted editorial sets; cross-batch facts). Human reviewer works from the post-rework tree. | HR | S | covered in review notes |

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
| B-4 | **Polygon quality pass (P1).** 🔄 **CORRECTED v2.3 (review F5 + own PIP probes):** the earlier khlong-san claim here and in the final review conflated the **station cell** with the **khet** — the 50-vertex `geometry.json` khlong-san ring **CONTAINS** ICONSIAM and G2 Charoen Nakhon and excludes River City; the 10-vertex object is `station-geometry.json["khlong-san"]` (the documented B-8 key-shadowing trap). Remaining genuine items: sathon boundary is metres-sensitive (app anchors for Surasak/Saint Louis sit on the line — "all three BTS nodes outside" holds for app anchors, phrase as boundary-sensitive); thon-buri does not contain BTS Wongwian Yai; Victory Monument khet conflict. Re-source coarse district polygons or document the 150 m border rule per case. | PL | M | PIP audit table for affected khets; polygons corrected or cases documented |
| B-5 | **Rent semantics cleanup (P1).** Dual "Pathum Wan blends" (phloen-chit record 33,500/74,000 vs district record 38,000/85,000); chit-lom 120,000 2-bed override is top-decile luxury, not a median (FazWaz Pathum Wan 2-bed avg 99,600, n=1,114; corridor median ~40k); pom-prap 2-bed 24,000 sits below all 14 observed asks (25,000–32,000) → recalibrate via CRTKY-141. Keep `blend`/`override`/`median` labels visible in ComparePanel. | PL | M | one blend per district; labels verified; pom-prap recalibrated |
| B-6 | **Fact corrections (P1, quick).** ratchathewi "1 Michelin star" → two one-star venues verify in-khet (Signature at VIE, Wana Yook); chit-lom "5 piers" → 2 distinct (4 duplicate OSM nodes); ratchathewi "0 piers" vs Pratunam pier nodes PIP-in-khet; hua-lamphong "2 piers" = canal (Khlong Phadung Krung Kasem), not river; Four Seasons Bangkok = 2015 rebrand, not 2024; OTK "CNN 4th best" rank unverifiable (URL 404) — already excluded from claims. | PL | S | corrections via fail-closed build replay |
| B-7 | **Counter-evidence → labeling policy (P2; DEC-7).** Dated events with receipts: Or Tor Kor shooting 2025-07-28 (5 dead); din-daeng = noisiest PCD station (71.6–81.6 dB(A), 182/182 days over) + Rocket Media rank 50/50; BTS Asok rush failure 2025-09-25; 529-stallholder clock-tower eviction 2025; Jodd Fairs Rama 9 demolished 2025-01; Khlong San Plaza closed 2021. Decide product visibility; **never** let a single incident become a persistent area label (handoff rule). | product (DEC-7) | S | policy recorded |
| B-8 | ✅ **DONE 2026-11-08** — `check_geometry.py --khet` flag (station-geometry `chatuchak` key shadows the district key); verified station catchment (33-vertex) vs khet ring (143-vertex). | AG | S | flag added + tested |
| B-9 | **Kit unit tests + CI (G16).** ✅ Tests DONE 2026-11-08: `kit/tests/` (33 green: canonical rules incl. TG-exclusion, assemble corroboration + normalizations, audit gate behavior incl. the review's six rules, tg_corpus parser). ⏳ Remaining: wire into CI beside the repo's existing checks; jsonschema cross-check when available. | PL | S | kit tests green in CI; validator cross-checked; changes fail closed |
| B-10 | ✅ **DONE 2026-11-08** — canonical family mapping (`kit/canonical.py`), relabel pass, re-gates: **23 of 422 corroborated → proposed (399/228/40)**; deterministic count supersedes the deep review's 27; 71 batch-4 limitations arrays repaired by the new audit rule (byte-exact vs raw). Ledger: [`2026-11-08-canonical-relabel.md`](2026-11-08-canonical-relabel.md). | AG | S | relabel applied; gates green; corrected counts in manifests |
| B-11 | ✅ **DONE 2026-11-08** — canonical source registry committed (`kit/registry/source-attributions.json`; deterministic stats: 54 family-inconsistent / 39 publisher-inconsistent / 32 title-inconsistent). Adapter to reference it in E-1/E-2. | PL/AG | S | registry committed; adapter uses it |
| B-12 | **Source-type taxonomy refinement.** 58% of sources sit in the collapsed `other` bucket (encyclopedia/OSM/datasets swallowed); refine the enum or add subtypes; report source-mix per bundle. 🟡 **Measured proposal ready 2026-11-08** ([`2026-11-08-source-taxonomy-v1.1-proposal.md`](2026-11-08-source-taxonomy-v1.1-proposal.md): additive enum + migration policy; adoption = SL decision). | SL/AG | S | taxonomy v1.1 or documented decision |
| B-13 | ✅ **DONE 2026-11-08** — validator + audit check `conflicts_with` integrity (dangling/self); reviewer-derived links applied (`wat-mangkon-c06`→c02/c04, the only intra-bundle claim-vs-claim contradiction). Honest corpus finding: source-level conflicts live inside single claims by design; going-forward agents declare claim-vs-claim conflicts via the prompt-template rule. 🔄 **Caveat RESOLVED in A-8 (2026-11-08):** the c06→c02/c04 link was REMOVED per F7 (c02/c04 are correct; the real tension is c06's framing vs Wikipedia's Chinatown≈district simplification — c06's limitation now says exactly that). | AG | S | conflicts_with populated where detectable; validator checks links |
| B-14 | ✅ **DONE 2026-11-08** — all 5 manifests carry `research_started_at`/`research_completed_at` (raw-write mtimes; profile-mtime fallback for the scripted tail) — and the tail batch, which had **no manifest at all** (batch-DoD gap), gained one. | AG | S | manifests carry start/end; batch DoD updated |
| B-15 | **Contract-derived audit checklist (third review, Angle F — top process item).** Every gate rule to date was added reactively after a defect class was *found*, never from the contract. Derive from HANDOFF.md: every "must" clause → a named audit rule or an explicit `not machine-checkable` note; commit the checklist beside the kit; fold the reviewer's six new rules + the placeholder/limitations/inline-ref/app-data-locator rules into it as the seed. | AG | M | checklist committed; every handoff must-clause mapped; kit README links it |

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
| C-6 | **Link-rot waves (G14):** quarterly checks over the canonical URLs (543 post-repair); wave 1 DONE 2026-11-08 — 485 OK, 4 dead flagged archived-citation, 33 access-limited; dead URLs flagged on the source record, affected claims downgraded to "archived citation" status — never deleted silently. | quarterly | wave 1 done |
| C-7 | **End-of-batch volatile recheck (handoff method rule — missed in all four batches).** Before closing any batch, re-open the volatile operational/price/closure sources it cites (rents, market schedules, opening hours, transport status) and confirm they still say what the claims say; append dated confirmation notes or corrections. | every batch close | Program DoD item 10; batch DoD amended |

## 6. WS-D — Tier upgrades & corpus maintenance (gated on A-1)

| ID | Item | Candidates | Effort |
|---|---|---|---|
| D-1 | **B → A (full bundles)** for contested/featured units: st.sala-daeng (nightlife 10 = the real heart, 108 venues; Lumphini Voronoi split), st.siam (flagship; 6 ha park unnamed; Paragon-event history), st.chit-lom (120k override), st.phetchaburi (merge resolved + CODI displacement), st.hua-lamphong (afterlife), st.saphan-taksin (river hub; cancelled rebuild), st.victory-monument (renovation + khet conflict), st.mo-chit (market reorg), st.phra-ram-9 (Jodd Fairs demolition + GR9 redevelopment). Budget: DEC-4. | 9 | L |
| D-2 | **C → B (light)** on triggers: product-surfaced entity; coverage/news event; user selection. | rolling | per-trigger |
| D-3 | **Tier-C regeneration** from each new app snapshot (identities/scores move; placeholders must not drift). | all 137 | S (scripted) |
| D-4 | **Bundle re-anchoring (G15) after any app-data change (C6):** B-1/B-2/B-3 change scores, ranks, cohort sizes — all 46 researched bundles' `selection_context` goes stale; a station-set change recomputes cohort ranks everywhere. Re-derive `selection_context` from the new snapshot (claims untouched). | AG (scripted) | S per change |
| D-5 | **Coverage battery in future light passes (C14) — and the handoff's second browsing choice.** Batch-4 skipped the dedicated axis-1 scan; fold the 3-query coverage battery into every new light bundle, and record per entity a structured **editorial mention breadth with its date window** (independent-family count + window) in the batch manifest — the handoff lists "documented editorial mention breadth with its date window" as a separate product-browsing choice alongside score and evidenced themes. Bundles keep `popularity_*` unmeasured; breadth lives in the manifest, not the bundle. | AG | S |
| D-6 | **Telegram corpus in the research workflow (2026-11-08; mitigates the resident-voice gap C-ep4 and independence concentration C-ep1).** Tool: `kit/tools/tg_corpus.py` (verify/pull/search/cite/restamp/status) + `kit/registry/telegram-channels.json`; rules in WS-H #8, template rule 12; corpus local-only (`research/bangkok/corpus/`), citations canonical `t.me` URLs. **Status: toolchain proven end-to-end (58-message smoke corpus); all 6 discoverable handles REJECTED after content inspection (masquerading/spam/promo) and official sites carry no t.me links — real Bangkok channel handles are the open work (user-provided or Thai-language search), then verify → pull → inspect → cite.** | AG | S per wave | channels registered with verdicts; any cited message carries its canonical URL + registry type |

## 7. WS-E — Product integration (P1 · separate reviewed change · gated on A-1)

| ID | Item | Owner | Effort | Acceptance |
|---|---|---|---|---|
| E-1 | **Adapter design spec** + two decisions from DEC-10: build-step location (`scripts/bangkok` export recommended) and a schema-migration policy (additive; `schema_version` bumps with migration notes). Localized preview index in the map bundle (locale keys with EN fallback until WS-F) → per-place guide narrative + evidence disclosure loaded on demand; entity-key mappings = existing `st.*`/district slugs; article text rendered as plain text only. **Guide section order follows the handoff**: identity/scope → distinctive character → strengths and trade-offs → conditional fit/time/subareas → deeper facts and sources → optional gallery. **Reconcile with the existing short-copy strings**: `app/src/data/area-guide-copy.json` currently holds exactly six `bangkok:station:*`/`bangkok:district:*` keys (the pilot set) — never silently overwrite; migrate/version them through review. | product+eng | M | spec reviewed and approved |
| E-2 | **Implementation** behind E-1, with the app's own checks (lint, toolchain tests, TS, production build, e2e). Research is **never** imported into `districts.json`/`stations.json`/rent references **or the existing `area-guide-copy.json` short-copy strings** (handoff boundary; reconcile via reviewed migration instead). | eng | L | app checks green; map bundle delta within budget |
| E-3 | **Score-context disclosures in UI (A4/C-ep4):** green buffer basis, transport mechanism, rent label semantics — placed **one tap from the score** (not buried in the guide); plus a corpus-skew disclosure (expat/tourist source skew, score-correlated selection, single-season observations). | product | S | disclosures live |
| E-4 | Raw research corpus stays out of the map bundle (hard rule); gallery/preview images only after WS-G. | eng | — | bundle audit |
| E-5 | **Copy evidence bar (G12) — the load-bearing new gate.** Card preview: **corroborated claims only** (canonical families, post-B-10). Guide narrative: corroborated + proposed with attribution. Conflicted claims: never in copy — evidence disclosure only. `researcher_inference`: never in copy. **Amended v2.3 (third review): copy eligibility also keys on HUMAN sign-off — a bundle whose `review.reviewer` starts with `agent-review:` is not copy-eligible until a human signatory records approval** (otherwise the agent review's `approved` statuses leak into product). Enforced by the adapter with a test case, not by convention. | eng+product | M | adapter rejects out-of-bar claims + un-signed bundles (tests in CI) |
| E-6 | **Tier-C card UX (DEC-8) — the two-speed seam is visible by design (A1).** 137 guide-less entities render an explicit data-only card (score+facts); the adapter must **never** synthesize guide-like prose from facts for unresearched units — that would launder tier C into fake tier A. | product | S | decision recorded + implemented |
| E-7 | **Corridor coherence pass (G22) + cross-bundle fact sweep.** Adjacent researched units narrate shared places with un-swept framing contradictions (chong-nonsi/sala-daeng/bang-rak on Silom–Patpong–Lumphini; wat-mangkon/sam-yot/sanam-chai on the canal; asok/nana/phloen-chit on Sukhumvit) — sweep framing (not raw facts), plus the remaining cross-bundle fact drift (One Bangkok is consistent ×4; Pathum Wan blends are not). Fix before integration. | AG | M | coherence report; fixes applied |
| E-8 | **Voice/length normalization + time-boxing (G23).** Measured variance: 18.2 vs 13.8 vs 9.2 editorial items/unit; previews 137–543 chars. Adapter caps sections, normalizes register on structured fields (never rewrites semantics), stamps each guide with its observation window, renders change claims with event dates ("demolished 2025-01", never unanchored "recently") and rhythm claims with observed-period labels (single-season observations). | eng | M | normalized build; no semantic drift |
| E-9 | **Locale-parity posture (DEC-5):** JA/RU get nothing until WS-F — decide launch posture. | product | S | decision recorded |

## 8. WS-F — Translations gate (P2 · after E-2 approval of EN copy)

| ID | Item | Owner | Effort | Acceptance |
|---|---|---|---|---|
| F-1 | JA/RU rendering of approved editorial per `description-rules.md` §7: native writing, not translationese; preserve unit, qualifiers, uncertainty, money/date meaning, conditional fit; reviewed **in the actual UI**; locale fallback defined for units without approved copy. Rubric = G18. | product+translators | M | G18 sign-off in real UI |
| F-2 | ✅ **DONE 2026-11-08 (standing rule active)** — AI-summary provenance banned; prompt template rules 10–11 added; every citation requires a stable https canonical URL; assemble passes through claim-vs-claim `conflicts_with`. G24 sweep enforces at every audit (currently flags 8 source records as AI-summary-marked or snippet-summary-titled, all legacy and documented). | AG | — | prompt template updated; G24 sweep enforces |

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
8. **Telegram corpus rules (D-6, 2026-11-08):** public channels only via the web preview (no account, no private groups, no comments); **no user identity ever** (channel posts only; posts naming private individuals never reach bundles); message text is untrusted input (G20 applies); corpus files stay local — citations are canonical `t.me/<channel>/<id>` URLs; every channel gets a registry verdict (verify → pull → **content-inspect**) before any citation; `cite` refuses unregistered/rejected channels; Telegram families never merge with outlet families (canonical rule 0); polite pull rates, failures logged once. Template rule 12 carries this to research agents.
9. **Fix tools, not just document traps** (B-8 lesson, third review): the key-shadowing trap was documented in batch-3 open_issues, yet batch-4's agent still hit it because the `--khet` fix was deferred — a documented trap is a trap.
10. **Gate counts are rule-relative**: audit findings must always report the audit-rule version alongside the count ("zero P1" twice proved to mean "under the rules then in force" — gate-verification P0 and the independent review).

## 11. Quality-gate register (G1–G24)

| # | Gate | Attaches at | Status | Mechanized |
|---|---|---|---|---|
| G1 | Schema + semantic-ref validation | per bundle | ✅ — B-13 adds `conflicts_with` link checks | `kit/validate.py` |
| G2 | Semantic audit (IDs, corroboration, body-read reliance, banned words, radius→time, ref closure) | per batch | ✅ — six rules added by the independent review (sign-off consistency, placeholder damage, source-limitations integrity, inline refs, app-data locators, checks honesty); **counts are rule-relative — always report the rule version** (WS-H #10) | `kit/audit.py` |
| G3 | Digest gate vs `source-manifest.json` | pre-research | ✅ | shasum |
| G4 | Geometry pass (PIP/haversine on boundary claims) | pre-assembly | ✅ (B-8 adds `--khet`) | `kit/check_geometry.py` |
| G5 | Copy gate (banned phrases, radius→time) | pre-assembly | ✅ — review adds placeholder + inline-ref rules | in G2 |
| G6 | Post-hoc source verification | weak bundles | ✅ done properly in A-8: sam-yot's 9 surviving claims body-read (terms matched in fetched bodies) + 2 removed; hua-lamphong/phaya-thai/phetchaburi/saint-louis/sala-daeng claims likewise | agent pass (ledger) |
| G7 | Batch-stop researcher review + findings | per batch | 🟡 batch-3/4 findings.md still owed (F8) — now A-9 (A-8 did not cover it) | manual |
| G8 | Live-data integrity | every commit | ✅ | `git status` |
| G9 | Data-only placeholder check | tier C | ✅ (audit handles + A-2 bulk check + reviewer reproduction) | audit handles |
| G10 | Independent human review | before product use | 🟡 agent review + A-8 rework complete (46/46 agent-approved) — human signatory pending (DEC-2) | packet + review record |
| G11 | Legal/defamation review | before publication | ❌ → A-5 | no |
| G12 | Copy evidence-bar enforcement | adapter | ❌ → E-5 (amended: human-sign-off key) | to build |
| G13 | Thai-source verification | copy-bearing Thai claims | ❌ → A-6 | no |
| G14 | Link-rot check | quarterly | 🟡 wave 1 DONE 2026-11-08 (485 OK / 4 dead flagged / 33 access-limited); quarterly schedule pending (C-6) | wave done |
| G15 | Bundle re-anchor after app-data change | every snapshot change | ❌ → D-4 | to build |
| G16 | Kit tests / CI | every kit change | 🟡 tests green locally (18); CI wiring pending (B-9) | tests done |
| G17 | Personal-data audit | before publication | ❌ → A-5 | no |
| G18 | Translation QA rubric | WS-F | ❌ rubric undefined → F-1 | no |
| G19 | Image rights per image | WS-G | ✅ defined | manual |
| G20 | Injection/HTML sweep over user-facing text | every assembly | ✅ in `kit/audit.py` (0 hits corpus-wide) | yes |
| G21 | Canonical family mapping in corroboration | assembly | ✅ `kit/canonical.py` in assemble+audit (B-10 done) | yes |
| G22 | Cross-bundle coherence pass | before integration | ❌ → E-7 | agent pass |
| G23 | Voice/length normalization + time-boxing | adapter build | ❌ → E-8 | to build |
| G24 | Citation URL-scheme + AI-summary ban | assembly | ✅ in `kit/audit.py` (1 http P2; AI-summary markers flagged) | yes |

## 12. Program Definition of Done (C1)

"Product-ready v1" holds when **all** of the following are true:

1. 183/183 bundles at their tier DoD (A/B human-approved via G10; C bulk-approved via A-2).
2. Zero open P1 audit findings across all batches **under the current audit-rule version** (rule version recorded with every count — WS-H #10).
3. Legal/privacy (A-5) signed for every copy-bearing unit; Thai verification (A-6) done or copy excluded.
4. Evidence bar (E-5/G12) implemented **and test-covered** in the adapter, including the human-sign-off eligibility key (v2.3).
5. Integration slice merged with the app's own checks green; disclosures (E-3) live; tier-C card UX decided (E-6/DEC-8).
6. Bundle re-anchoring current with the shipped app snapshot (D-4/G15).
7. Recheck calendar owned (DEC-3) and current; link-rot waves scheduled (C-6/G14).
8. Kit under tests in CI (B-9/G16 — tests exist and are green locally; CI wiring remains).
9. Honest status surface: which entities are copy-bearing (A/B approved) vs data-only (C) — no laundering.
10. End-of-batch volatile rechecks (C-7) performed and recorded for every researched batch (handoff method rule).

Per-artifact DoD (full checklists): [`2026-11-08-critique-gates-dod.md`](2026-11-08-critique-gates-dod.md) §3 — the batch DoD there additionally includes C-7 (end-of-batch volatile recheck) per the handoff-compliance sweep.

## 13. Sequencing (dependency-ordered)

```
Done       → DEC-1 (pushed, PR #177) · B-8/B-10/B-11/B-13/B-14 · G20/G21/G24 in kit
             · F-2 rules · C-6 wave 1 · D-6 TG corpus · A-1 agent review (22/24)
             · A-2 script half (137/137) · gate-verification P0 fix
Done       → A-8 rework complete (24 blocked → 0; ledger + report addendum)
Now        → A-2 signature + A-1 human sign-off (DEC-2) over the 46 approved bundles
           ∥ A-9 findings files (F8) ∥ packet §3b rework note for the reviewer
           → B-2 → B-1 → B-4-corrected (P0 data, fail-closed replay) ∥ B-15
             contract-derived checklist ∥ B-12 adoption (SL)
Next       → B-3/B-5/B-6/B-7 (product decisions + facts) ∥ B-9 CI wiring
           → D-4 re-anchor (after any landed data change) ∥ D-3 tail regen
Gated on   → D-1 batch 5 (B→A upgrades; DEC-4) ∥ C-1 recheck wave (Nov–Dec 2026)
A-8+A-1
Then       → E-1 spec (with E-5 human-sign-off key + DEC-10 defaults) → E-2
           → E-7 coherence pass ∥ E-3 disclosures ∥ E-6/DEC-8 tier-C card ∥ E-8
When live  → WS-F translations (F-1) ∥ WS-G images (G-1/G-2)
Per batch  → C-7 end-of-batch volatile recheck before close (handoff rule)
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
- Third review (verify-the-verifier): [`2026-11-08-third-review.md`](2026-11-08-third-review.md)
- Independent agent review (A-1 executed): [`2026-11-08-independent-review.md`](2026-11-08-independent-review.md)
- Kit: [`kit/`](kit/README.md) (scaffold · prompt template · canonical families · geometry checker · assembler · validator · audit · briefs · tools · tests · registry)

## 15. Progress log

- **2026-11-08 (AG lane executed, commits 28805ad…d40c83c + this one):**
  B-10 canonical relabel (23 claims; 399/228/40; 71 batch-4 limitations
  repairs caught by the new audit rule; deep-review 27 superseded) ·
  B-11 source-attribution registry (547 URLs; 54/39/32 inconsistent fields) ·
  B-13 conflicts_with (validator+audit checks; wat-mangkon-c06 link set) ·
  B-14 manifest research times (+ tail-batch manifest gap fixed) ·
  B-8 `--khet` · G20/G24 in `kit/audit.py` · F-2 prompt rules ·
  B-9 kit tests (18 green; CI wiring pending).
  All gates re-run green: `validate.py` ALL OK ×5, `audit.py` zero P1.
  Next unblocked: owner decisions DEC-1…10; A-1/A-2 review gates;
  pipeline-team B-1/B-2/B-4 (app-data, not agent-executable); CI wiring.
- **2026-11-08 (gate verification, same day later):** P0 found — validate.py
  discarded schema errors in every run (semantic-checks-only ALL OKs) +
  anyOf no-rollback; **both fixed**; contract repair pass over all bundles
  (18 URL annotations split incl. sam-yan Overpass ×4→1 merge with
  annotations preserved, 134 null notes, 32 bool commercial_context, 34 dict
  uncertainties); assemble normalizes all classes going forward; tests at 20
  green; **validate ALL OK ×5 + audit zero-P1 ×5 now genuine** ·
  C-6/G14 wave 1 run (543 URLs: 485 OK, 4 dead flagged archived-citation,
  33 access-limited, rest transient). Receipts:
  [`2026-11-08-gate-verification.md`](2026-11-08-gate-verification.md),
  [`2026-11-08-contract-repair-log.jsonl`](2026-11-08-contract-repair-log.jsonl),
  [`2026-11-08-link-health-wave1.json`](2026-11-08-link-health-wave1.json).
  B-12 taxonomy proposal and C-7 content-recheck for the closed batches
  remain open (C-7's first-content-recheck route: reviewer spot-checks +
  wave C-1).
- **2026-11-08 (decisions):** user approval recorded → DEC-1 executed (branch
  pushed to origin, **PR #177** opened to `main`); DEC-5/6/7/8/10 adopted at
  recommended defaults; DEC-2/3/4/9 remain open (need named people/budget).
  A-2 script half run: **137/137 placeholders PASS** against current app data
  ([`2026-11-08-tier-c-bulk-check.md`](2026-11-08-tier-c-bulk-check.md));
  reviewer sign-off still pending (DEC-2).
- **2026-11-08 (D-6):** Telegram corpus capability added to the workflow —
  `kit/tools/tg_corpus.py` + `kit/registry/telegram-channels.json` + WS-H #8
  rules + template rule 12; corpus local-only (git-ignored), citations are
  canonical `t.me/<channel>/<id>`. End-to-end smoke proven (verify → pull →
  search → cite → restamp; 58 records). Empirical finding: **all 6
  discoverable handles rejected after content inspection** (masquerading /
  spam / bot-promo channels) and official sites carry no `t.me` links —
  channel discovery is the open work; registry verdicts prevent any misuse.
- **2026-11-08 (independent review executed):** A-1 agent-review pass over all
  46 researched bundles + A-2 tier-C reviewer verification. **22 approved /
  24 blocked**; tier C **137/137 PASS** (independently reproduced). Six
  finding classes: batch-4 normalize damage in `day_night` /
  `within_area_variation` / `uncertainties` (12 bundles); incomplete
  limitations repair (49 claim + source arrays in 7 bundles); 21 claims
  resting solely on snippet-only sources (6 bundles); batch-2 inline claim
  refs in user copy (4 bundles); the khlong-san **station cell mistaken for
  the khet** polygon error (also in the final review §2.4); app-data locators
  attached to unrelated web sources (4 claims). `kit/audit.py` gained six gate
  rules + 9 tests (suite 32 green); every approved bundle has zero P1 under
  the new rules. Report:
  [`2026-11-08-independent-review.md`](2026-11-08-independent-review.md).
  **DEC-2 (human signatory) remains open** — this is an agent review.
  Next: fix F1/F2 mechanically from `raw/`, re-assemble batch 2 (F4), run the
  F3 evidence pass, then human sign-off. — **Amended (third review): F4 must
  NOT re-assemble batch 2** (raw/ predates coordinator corrections; kit rule
  "never re-assemble closed batches") — the fix is a logged profile-level
  strip of inline refs, contract-repair style.
- **2026-11-08 (third review, parallel):** the agent reviewer's work was
  **verified before acceptance** (F1/F2/F3/F5/F8 all reproduce; their commits,
  records and audit diff check out) and then audited from new angles —
  findings: my limitations repair was partial (F2 stands), my "zero P1" claims
  were rule-relative, my sam-yot verification-pass record is not evidenced in
  the delivered bundle (harshest correction), my khlong-san correction was
  wrong (station cell vs khet — verified by own PIP probes), and my B-13
  conflict link needs re-examination in rework. New fixes landed: canonical
  rule 0 (Telegram-channel families never merge with outlets — latent bug
  found), tg_corpus verdict guard + argparse + stall-break fixes, packet
  retraction of the false "machine-verified" residual, URL-count 547→543
  corrections. E-5 amendment recorded: copy eligibility keys on *human*
  sign-off (`agent-review:*` reviewer ≠ copy-eligible). Process items opened:
  contract-derived audit-rule checklist (Angle F); two-writers-one-tree
  hazard. Receipt: [`2026-11-08-third-review.md`](2026-11-08-third-review.md).
- **2026-11-08 (A-8 rework executed):** all 24 blocked bundles cleared per the
  review's §9 protocol (with the recorded F4 amendment: profile-strip, never
  re-assemble). Counts: 72 editorial rebuilds from raw · 49 limitation joins ·
  95 copy blocks stripped of inline refs · 17 claims' sole evidence body-read
  (browser-UA fetches, matched terms logged) · 1 replacement source added
  (Wikipedia Rommaninat Park) with a scoped claim reword · 4 claims removed
  with substance preserved (sam-yot c11/c17 unreachable sources; hua-lamphong
  c02/c12 app-data-on-X-post) · khlong-san c02/c03 rewritten from --khet truth
  · wat-mangkon wording + B-13 link removed · voice swept (zero leftovers) ·
  charoen-nakhon 12 QA notes filled. **Post-rework gates: validate ALL OK ×5,
  audit zero-P1 ×5 under the review's rules, 33 kit tests green.** Report
  updated (Result + §5 table + addendum). Ledger:
  [`2026-11-08-a8-rework-log.jsonl`](2026-11-08-a8-rework-log.jsonl). Human
  sign-off (DEC-2) over the 46 approved bundles is now the only open A-gate.
- **2026-11-08 (plan v2.4):** header + rows refreshed to the post-rework state — A-7 covered by the review; A-9 added (F8 findings files owed — A-8 did not include them); B-13 caveat resolved; B-9 test count 33; G6 closed properly; G7/A-9 split; sequencing: human sign-off ∥ A-9.
- **2026-11-08 (plan v2.3):** integrates the agent review + third review into
  the workstreams — A-8 rework queue added (dependency-ordered; F4 amended to
  profile-strip, never re-assemble); B-4 khlong-san claim corrected (station
  cell ≠ khet; final review + pipeline notes corrected); B-13 link caveat;
  B-15 contract-derived checklist added; E-5 human-sign-off key; WS-H #9/#10;
  gate register + DoD + sequencing updated to the post-review state
  (Done/Now/Next re-anchored on A-8 → human sign-off).
