# Deep review — second pass, different angles (2026-11-08)

A second critical pass over the completed program, deliberately from angles
the first critique (`2026-11-08-critique-gates-dod.md`) did not use: the end
user, the data architecture, research epistemics, security, and cross-bundle
coherence. Every claim below is backed by an empirical sweep run today over
the 46 researched bundles (547 URLs, 1,561 evidence citations, 667 claims).
New plan items from this pass are applied to the continuation plan (§6) and
committed.

---

## Angle A — the end user of the product

**A1. The corpus is two-speed, and the plan never designed the seam.** 46
units get rich, claim-linked guides; 137 get nothing. E-6 ("what renders on a
tier-C card") exists, but the deeper question is the *user's* mental model: a
browser walking the map sees detailed guides for the tourist core and silence
for Yan Nawa. Recommendation: the seam must be visible-by-design — tier-C
cards say data-only explicitly, and the adapter must never synthesize guide-
like prose from facts for unrresearched units (that would launder tier C into
fake tier A).

**A2. Voice inconsistency is measured, not hypothetical.** Editorial items per
unit: batches 1–2 average **18.2**, batch 3 **13.8** (five units are
coordinator-drafted), batch 4 **9.2**; preview lengths run 137–543 chars.
Guides will read like three different publications. → new plan item E-8:
voice/length normalization at adapter build time (caps per section, unified
register, "as of" date labels) — copy semantics must not drift when the
adapter reformats, so normalization happens on structured fields, not by
rewriting text.

**A3. Time-boxing is missing from the copy contract.** Bundles narrate
2024–2026 events ("Jodd Fairs demolished 2025-01", "One Bangkok opened
2024-10-25"). A user reading in 2028 gets stale "recent changes" presented as
news. → E-8 also adds: adapter stamps every guide with the bundle's
observation window and renders change claims with their event dates, never
as unanchored "recently".

**A4. Score-vs-guide juxtaposition is an ethics placement problem.** A card
shows "7.7" beside a guide whose finding is that the score's *basis* is
contested (five safety-5 units; kamphaeng-phet's transport 10; nana's green
10). E-3 disclosures help, but placement matters: the disclosure must be one
tap from the score, not buried in the guide. → E-3 amendment.

**A5. Locale parity degrades by design.** JA/RU users get nothing until WS-F
runs on approved EN copy — for all 46 units. The plan treats translations as
a late gate; the product decision (EN-only guides at launch vs delaying
guides until parity) is unmade. → E-9 decision item.

## Angle B — data architecture

**B-arc1. Global claim-ID uniqueness: PASS.** Zero collisions across all 46
bundles (the per-entity prefix discipline held, including the deliberate
`-d-`/`-st-` infixes). The adapter can key claims globally.

**B-arc2. Same-URL metadata variance: 49 URLs cited with inconsistent
publisher/title across bundles** (e.g. "Wikipedia" vs "Wikipedia (English)";
Overpass queries titled per-claim). Any merged citation view will show
conflicting attribution for one source. → new plan item B-11: canonical
source registry (URL → canonical publisher/title), built once and referenced
by the adapter.

**B-arc3. Adapter build-step location is undefined.** Bundles → preview index
is a build step; the plan doesn't say whether it lives in `scripts/bangkok`,
the app build, or a research export. → E-1 amendment.

**B-arc4. No schema-migration policy.** All bundles are `schema_version 1.0`;
if the amended handoff evolves the contract, old bundles need a migration
rule. → E-1 amendment.

## Angle C — research epistemics (measured, not impressionistic)

**C-ep1. Wikimedia provides 37% of all evidence citations** (577/1,561;
counting the six spelling variants of the family). OSM/Overpass adds ~10%.
The corpus's evidential spine is encyclopedia + map data — fine for identity/
geometry, thin for "what residents value". The type taxonomy makes it worse:
58% of sources sit in the collapsed `other` bucket. → new plan item B-12
(refine the type taxonomy in upgrades; report source-mix per bundle).

**C-ep2. Corroboration labels contain a measurable defect.** Family strings
were matched exactly, so "English Wikipedia" + "Thai Wikipedia" counted as
two independent families. Canonical mapping relabels **27 of 422
`corroborated` claims to `proposed`** (422 → 395; list produced today, e.g.
bang-sue-c01, thon-buri-c01/c04/c09/c12, dusit-c02/c05/c10 — mostly EN+TH
Wikipedia pairs). → new plan item B-10: canonical family mapping in the kit
+ relabel pass + re-gates. The adapter's evidence bar (E-5) must use
*canonical* families. **Reconciliation (B-10 executed 2026-11-08):** the
committed deterministic rule set ([`kit/canonical.py`](kit/canonical.py))
relabels **23** (→ 399/228/40) — this review's in-session 27 came from an
unrecorded broader mapping and is superseded;
[`2026-11-08-canonical-relabel.md`](2026-11-08-canonical-relabel.md) is
authoritative.

**C-ep3. Distance claims inherit anchor ambiguity.** Bundle distances were
measured from app anchors (per the research briefs). Where anchors are wrong
(saint-louis ≥720 m), the bundle's own distances inherit the error; where
anchors match, they're fine. B-2's resolution must include a decision rule
for which base distance claims use, and mark the affected claims (saint-louis
unit is the known case). → B-2 amendment.

**C-ep4. Language and population skew are structural.** Thai body-reads
improved over batches but webReader/URL-encoding issues suppressed several;
guides skew expat/tourist because that's what is published, while the
product's question is residential. Tier selection is score-correlated, so
the researched corpus over-covers the central city. These are limitations to
*carry*, not fix — but they belong on the guide page's disclosure, not in a
drawer. → E-3 amendment.

**C-ep5. Seasonal claims were never observed across seasons.** Flood, market,
and festival rhythms rest on single-observation sources. Bundles flag it;
the adapter should render rhythm claims with observed-period labels. → E-8.

## Angle D — security of the pipeline

**D-sec1. Injection sweep: clean.** Mechanical scan over all user-facing text
(preview, lead, claims, QA notes) for HTML, markdown links, template braces,
and instruction-injection patterns: **0 hits** in 46 bundles. The untrusted-
text surface is currently clean; make the sweep a standing gate (G20) run at
every assembly.

**D-sec2. AI-summary provenance: 6 sources** ("web search AI summaries" as
snippet-only corroboration). Flagged and never sole evidence, but they should
be **banned in future bundles** — no upgrade may cite an unattributable
AI-summary as even corroboration. → F-2 method amendment.

**D-sec3. Residual risk is behavioral, not textual.** Injection could have
shaped *search behavior* (what agents chose to read) without leaving text
traces; retroactive audit is impossible beyond the sweeps. Mitigation is the
standing sweep + the human review gate reading against sources.

**D-sec4. One plain `http://` URL** (the Atlantic 2011 flood photo essay in
bang-rak). Cosmetic; the adapter should upgrade or drop non-https citations.

## Angle E — cross-bundle coherence

**E-coh1. Adjacent units tell overlapping stories with different framings** —
chong-nonsi/sala-daeng/bang-rak all narrate Silom–Patpong–Lumphini; batch-3
corrections already fixed the cross-unit Rommaninat attribution. No sweep has
checked remaining adjacent pairs for contradictory framing (not raw facts —
*framing*: "quiet pocket" in one guide vs "part of the nightlife belt" in the
neighbor's). → new plan item E-7: corridor coherence pass over the
researched adjacency graph before integration.

**E-coh2. Cross-bundle fact consistency is un-swept beyond spot fixes** (One
Bangkok appears in four bundles with consistent facts; Pathum Wan blends do
not). → folded into E-7.

## Angle F — operations

**F-1. Maintenance ownership ends with this session.** The plan says "AG"
for future work but nobody is assigned after the engagement. The corpus is a
product asset with an annual refresh question (Bangkok churn) — ownership and
refresh SLO are unassigned. → decision item.

**F-2. Method amendment:** ban AI-summary provenance from all future bundles;
require a stable URL for every citation (see D-sec2).

**F-3. Push/PR remains an owner decision** (C13 from the first critique) —
six-plus commits live only on this machine.

---

## New gates (extending the register from the first critique)

| # | Gate | Attaches at | Mechanized |
|---|---|---|---|
| G20 | Injection/HTML sweep over all user-facing text | every assembly | yes (scripted today; promote to kit) |
| G21 | Canonical family mapping in corroboration | assembly | to build (B-10) |
| G22 | Cross-bundle coherence pass (adjacency graph + fact sweep) | before integration | no (agent pass) |
| G23 | Voice/length normalization + as-of time-boxing | adapter build | to build (E-8) |
| G24 | Citation URL scheme + AI-summary ban | assembly | yes (trivial check) |

## Plan items added by this pass

**B-10** canonical family mapping + corroboration relabel (27 claims) ·
**B-11** canonical source registry (49 inconsistent URLs) · **B-12** source-
type taxonomy refinement (58% `other`) · **E-7** corridor coherence + cross-
bundle fact sweep · **E-8** voice/length normalization + as-of time-boxing +
rhythm labels · **E-9** locale-parity decision · **F-2** AI-summary ban ·
**G20** standing injection sweep · **G24** URL-scheme check. Amendments to
existing items: E-1 (adapter build-step location + schema migration policy),
E-3 (disclosure placement; skew/limitations disclosure), B-2 (distance-base
rule + affected-claim marks), A-1 (review covers four batches).

## What survived the review untouched

The integrity architecture (provenance, gates, honest tiers), the empirical
corrections ledger, the ghost-station find, the tiering itself, and the
boundary discipline (no live-data edits). The corpus's weakest point is not
integrity — it is **independence concentration** (Wikipedia 37%) and
**voice fragmentation** across batches; both now have owners in the plan.
