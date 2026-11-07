# Continuation plan & detailed backlog — Bangkok editorial research (2026-11-08)

Where the program stands: **183/183 entities carry a schema-valid bundle**
(22 full tier A · 24 light tier B · 137 data-only tier C, all gated, master
index in [`2026-11-08-tier-plan.md`](2026-11-08-tier-plan.md)). This document
is the ordered backlog for everything that comes next. It complements
[`../backlog.md`](../backlog.md) (CRTKY-130 subtree, which owns the
data-pipeline tickets) and the two pipeline-notes
([2026-11-07](../notes/2026-11-07-editorial-batch-pipeline-followups-crtky130.md),
[2026-11-08 update appended](2026-11-08-recheck-calendar.csv)).

Effort codes: **S** ≤ half a day · **M** 1–3 days · **L** multi-week or
multi-batch. Owner codes: **HR** human reviewer · **SL** sender's editorial
line · **PL** pipeline/data team (via build/replay gates) · **AG** research
agent (this workflow, ≤2 concurrent).

---

## WS-A — Review & approval gates (P0 · blocks everything product-facing)

| ID | Item | Owner | Effort | Acceptance |
|---|---|---|---|---|
| A-1 | **Independent review, tiers A+B (46 bundles).** Packet ready (`batches/REVIEWER-PACKET.md`): spot pass 45–60 min, full pass 8–12 h. Reviewer signs `review.reviewer/reviewed_at/status` per bundle. | HR | M | every researched bundle `approved` or `blocked` with findings |
| A-2 | **Tier C bulk check (137 placeholders).** Script-assisted: identity vs app snapshot, zero web claims, `draft` status. One approval covers the batch. | HR (script-assisted) | S | tail batch approved or regeneration list produced |
| A-3 | **Sender adoption of amendments A1–A8** (in-repo amended copy at `2026-11-05-handoff/HANDOFF.md`; redline with evidence). | SL | S | amended copy accepted, or superseding revision published and diffs reconciled |

## WS-B — Data-layer fixes (P0/P1 · pipeline team, via build/replay gates)

Grounded in the 2026-11-07 + 2026-11-08 pipeline notes; every item has bundle
evidence with receipts. Order = priority.

| ID | Item | Owner | Effort | Acceptance |
|---|---|---|---|---|
| B-1 | **Ghost-station audit (P0).** `st.sena-ruam` is a never-built BTS infill (N6) modeled as operating — rank #9/133. Audit **all 139 stations** for operating status against operator publications; add a build assertion ("modeled station must exist in a published operator source"). Resolve sena-ruam (remove/reclassify — a product decision: its catchment is a real gap cell between Ari and Saphan Khwai). | PL | M | 139-row audit table committed; sena-ruam resolved; build passes |
| B-2 | **Anchor-convention audit (P0).** App centers vs OSM/Wikipedia nodes differ 270–770 m on ≥8 units (saint-louis ≥720 m — the real infill station is at 13.72082/100.52669), match to 5 decimals on others; Wikipedia/OSM themselves carry displaced coords for BTS Chit Lom and Victory Monument. Document the convention (unit-centroid?) or correct coordinates; then re-run the kit geometry pass. | PL | M | convention documented in `00-overview.md`; offsets ≤ documented threshold or explained; geometry pass re-run |
| B-3 | **Green-basis decision (P0, product decision).** Proven: green counts park ha within 1 km of grid points; dusit's 118.7 ha largely non-public; pathum-wan includes 36.3 ha members-only RBSC; ratchathewi 17.8 = 8.81 named public; din-daeng OSM ~3 ha vs app 15.5; kamphaeng-phet 9 = parks in other units. Decide: (a) disclose the buffer basis in UI honesty notes, or (b) add a catchment-interior green sub-signal. Either way: exclude non-public state land from the public-green figure. | PL + product | M | decision recorded; honesty-notes update or pipeline change; scores re-derived only through the build |
| B-4 | **Polygon quality pass (P1).** khlong-san district polygon (10 vertices) PIP-OUTs ICONSIAM (in-khet per khwaeng) and PIP-INS River City; sathon polygon PIP-OUTs all three BTS nodes (explains transport 7); thon-buri does not contain BTS Wongwian Yai; Victory Monument khet conflict. Re-source coarse district polygons or document the 150 m border rule per case. | PL | M | PIP audit table for the affected khets; polygons corrected or cases documented |
| B-5 | **Rent semantics cleanup (P1).** Two coexisting "Pathum Wan blends" (phloen-chit record 33,500/74,000 vs district record 38,000/85,000); chit-lom's 120,000 override is top-decile luxury, not a median; pom-prap 2-bed 24,000 sits below all 14 observed asks → recalibrate via the CRTKY-141 process. Keep `blend`/`override`/`median` labels visible in ComparePanel. | PL | M | one blend per district; label changes verified; pom-prap recalibrated |
| B-6 | **Fact corrections (P1, quick).** ratchathewi "1 Michelin star" → two one-star venues verify (Signature at VIE, Wana Yook); chit-lom "5 piers" → 2 distinct (4 duplicate OSM nodes); ratchathewi "0 piers" vs Pratunam pier nodes PIP-in-khet; hua-lamphong "2 piers" = canal (Khlong Phadung Krung Kasem), not river; Four Seasons Bangkok = 2015 rebrand, not 2024. | PL | S | corrections via build replay with snapshot signature checks (CRTKY-197 process) |
| B-7 | **Counter-evidence → labeling policy (P2, product decision).** Dated events with receipts: Or Tor Kor shooting 2025-07-28 (5 dead); din-daeng = noisiest PCD station + Rocket Media rank 50/50; BTS Asok rush failure 2025-09-25; 529-stallholder clock-tower eviction 2025; Jodd Fairs Rama 9 demolished 2025-01. Decide whether/where any of this is product-visible (connects CRTKY-150/151/152). Do **not** let single incidents become persistent area labels (handoff rule). | product | S | policy decision recorded |
| B-8 | **Kit TODO (P2).** `check_geometry.py --khet` flag (station-geometry `chatuchak` key shadows the district key — found by the batch-3 agent). | AG | S | flag added + tested |

## WS-C — Re-verification calendar (P1 · AG, quarterly waves)

**201 dated recheck flags** live in the bundles — registry:
[`2026-11-08-recheck-calendar.csv`](2026-11-08-recheck-calendar.csv)
(16 due 2026 · 150 during 2027 · 2 later · 33 tied to named events/milestones).
Run as quarterly waves; each wave is 2–3 light-agent runs over the due claims
(open the cited sources again, update or confirm, append a dated verification
note to the claim).

| ID | Wave | Items (examples) | When |
|---|---|---|---|
| C-1 | **2026-11/12** | Wat Saket temple fair (Nov 2026); Rajavithi Skywalk phase-1 opening (~Oct 2026 → recheck 2026-12); national-stadium concert calendar; Silom Walking Street; Nana green/clip audits | Nov–Dec 2026 |
| C-2 | **2027-01** | Central Phaholyothin completion (Q4 2026); rent re-audits (asok, ari, thong-lo, nana, chong-nonsi, phloen-chit…); Hua Lamphong transition; market reorganizations | Jan 2027 |
| C-3 | **2027-02 → 2027-06** | the big spring cluster (~70 items): One Bangkok phases, canal-park progress, rents, Chula/RMU land dispute, vendor-crackdown effects, Charoen Chai status | quarterly |
| C-4 | **Rolling** | DOPA census releases, quarterly portal refresh (rent corroborations), SRT/MRTA/BEM ridership and milestone publications, named-event triggers (Purple line, SRTA contracts, Samsen reopening) | as published |

Mechanization (S): extend the kit with `recheck-due.py` (regenerates the CSV
from profiles, emits wave task lists for light agents).

## WS-D — Tier upgrades (P1/P2 · AG · gated on A-1)

| ID | Item | Candidates | Effort |
|---|---|---|---|
| D-1 | **B → A (full bundles)** for contested/featured units. Shortlist from batch-4 tensions: st.sala-daeng (nightlife 10 = the real heart, 108 venues; Lumphini Voronoi split), st.siam (flagship; 6 ha park unnamed; Paragon-event history), st.chit-lom (120k override), st.phetchaburi (merge resolved + CODI displacement), st.hua-lamphong (afterlife), st.saphan-taksin (river hub, cancelled rebuild), st.victory-monument (renovation + khet conflict), st.mo-chit (market reorg), st.phra-ram-9 (Jodd Fairs demolition + GR9 redevelopment). | 9 | L (≈9 full-bundle runs; batch per the standard cadence) |
| D-2 | **C → B (light)** trigger rules: entity surfaced prominently by the product; coverage/news events; user selection. Regenerate the tail placeholder with a light bundle on trigger. | rolling | per-trigger |
| D-3 | **Tier C regeneration** from each new app snapshot (identities/scores move; placeholders must not drift). | all 137 | S (scripted) |

## WS-E — Product integration (P1 · separate reviewed change · gated on A-1)

| ID | Item | Owner | Effort | Acceptance |
|---|---|---|---|---|
| E-1 | **Adapter design spec:** localized preview index (small, in map bundle) → per-place guide narrative + evidence disclosure loaded on demand; entity-key mappings = existing `st.*`/district slugs; article text rendered as plain text only; sources/limitations disclosure on the guide page. | product+eng | M | spec reviewed and approved |
| E-2 | **Implementation** behind the spec, with the app's own checks (lint, toolchain tests, TS, production build, e2e). Do **not** import research into `districts.json`/`stations.json`/rent references. | eng | L | app checks green; map bundle size delta within budget |
| E-3 | **Score-context disclosures in UI** (green buffer basis, transport mechanism, rent label semantics) — the honesty-notes extension from B-3/B-5, wherever scores are shown. | product | S | disclosures live |
| E-4 | Keep the raw research corpus out of the map bundle (hard rule); gallery/preview images only after WS-G. | eng | — | bundle audit |

## WS-F — Translations gate (P2 · after E-2 approval of EN copy)

JA/RU rendering of approved editorial per `description-rules.md` §7 (native
writing, not translationese; preserve unit, qualifiers, uncertainty,
money/date meaning, conditional fit), reviewed in the actual UI. New
translation work is a separate gate from factual review.

## WS-G — Image rights pass (P2 · parallel-safe after A-1)

Candidate hunt per researched entity in role order (station entrance →
neighborhood street → usable park → landmark → night context); rights
verification with proof URLs (license name/version, commercial/derivative
rights, required credit); `rights_status: unknown` blocks publication; judge
readability at the real card crop (current input 600×220 — measure responsive
slots first); existing Wikimedia thumbs on station/district records are leads,
not approvals. Register candidates in bundle `images` arrays only after the
rights check.

## WS-H — Standing guards (do NOT do)

1. No score edits proposed or made by research — score disputes route to
   pipeline tickets with receipts.
2. No popularity adoption from coverage counts (selection signal only).
3. No fabricated copy for tier C placeholders — they stay honest drafts until
   upgraded.
4. Keep the stop-per-batch review cadence and the machine gates
   (`validate`/`audit`) as the load-bearing controls; prompt prose alone has
   drifted in every batch.
5. No paywall bypass, no proxy mirrors, no personal data — standing method
   rules.

## Suggested sequencing

```
Now            → A-1/A-2 review gates ∥ A-3 sender adoption ∥ B-1/B-2 (P0 data)
Then           → B-3..B-6 pipeline fixes ∥ D-1 batch 5 (B→A upgrades) gated on A-1
Next quarter   → C-1/C-2 recheck waves ∥ E-1/E-2 integration (after reviews)
When approved  → E-3 disclosures ∥ WS-F translations ∥ WS-G images
Always         → D-3 placeholder regeneration per app snapshot ∥ WS-H guards
```

## Registry files

- Master index + tiers: `2026-11-08-tier-plan.md` (183 rows)
- Recheck calendar: `2026-11-08-recheck-calendar.csv` (201 items)
- Pipeline receipts: `../notes/2026-11-07-editorial-batch-pipeline-followups-crtky130.md`
  (with 2026-11-08 update appended)
- Reviewer packet: `batches/REVIEWER-PACKET.md`
- Final program review: `2026-11-08-final-review.md`
