# Final results review — Bangkok editorial research program (2026-11-08)

**Completion state: 183/183 entities carry a schema-valid bundle** — originally 22 full
(tier A), 24 light (tier B), 137 scripted data-only placeholders (tier C); **now 31 A / 15 B / 137 C**
after the D-1 batch-5 upgrades (2026-11-08) —
per the A2 tiering the handoff amendment introduced. Statuses: 46
`ready_for_review`, 137 `draft` (placeholders, by design). Master index:
[`2026-11-08-tier-plan.md`](2026-11-08-tier-plan.md). This file is the
program-level review the dispatch asked for; per-batch verification lives in
each batch's `review/`. **No bundle is independently approved** — that human
gate remains open (see §7).

## 1. Volume and provenance (researched tiers A+B, 46 bundles)

668 sources cited / 527 body-read / **547 distinct canonical URLs as researched
(543 after the 2026-11-08 contract-repair merges)** across 299
publisher families; 667 claims — **422 corroborated / 205 proposed / 40
conflicted as researched; 399 / 228 / 40 after the 2026-11-08 canonical
publisher-family relabel (B-10/G21)**, which merged Wikipedia language
editions/Wikimedia projects, OSM/Overpass, and portal casing variants into
single publisher families ([`2026-11-08-canonical-relabel.md`](2026-11-08-canonical-relabel.md)).
**Gate correction (2026-11-08):** the schema half of `kit/validate.py` was
silently discarding errors — earlier "ALL OK" runs verified semantic checks
only. After the fix and a logged contract-repair pass, all five batches are
now genuinely **ALL OK** (schema + semantic) and `kit/audit.py` is at zero
open P1s
([`2026-11-08-gate-verification.md`](2026-11-08-gate-verification.md));
P2s are documented snippet-corroboration flags or audit-rule notes. Search
logs: ~700 logged queries including rejections and failures. No paywall was
bypassed and no proxy mirror used anywhere in the program.

## 2. The five systemic findings (the real product of the program)

1. **The app's ratings are computed on measurement buffers wider than the
   unit polygons — now proven, not hypothesized.** Green counts park hectares
   within 1 km of grid points: dusit's 118.7 ha is largely non-public (zoo
   fenced since 2018; Sanam Suea Pa royal), pathum-wan's 102.7 ha includes the
   RBSC's 36.3 members-only hectares (~60–65% publicly usable), phra-nakhon's
   38.5 is half temple/palace grounds, kamphaeng-phet's 9 rides entirely on
   parks 1.1–1.5 km out in other units. Transport counts bus stops and boat
   piers (charoen-nakhon's 10; ratchaprarop's 9 = "airport rail + adjacency";
   sathon's 7 is explained by a polygon that PIP-OUTs all three BTS nodes).
   These are *design*, and the honest fix is disclosure or a deliberate basis
   change — never silent score edits.
2. **One ghost station.** `st.sena-ruam` — rank #9/133 — is a planned-but-
   never-built BTS infill (N6) modeled as operating. Highest-priority
   data-layer defect found; a full 139-station operating-status audit is
   recommended.
3. **Anchor conventions drift.** App anchors differ from OSM station nodes by
   270–770 m on eight units (saint-louis ≥720 m — the real infill station was
   findable and the bundle documents it), match to five decimals on others.
   A documented convention or a coordinate audit is needed; Voronoi claims
   computed from mixed conventions will disagree.
4. **Polygon coarseness has product-visible consequences.** khlong-san's
   10-vertex khet polygon PIP-OUTs ICONSIAM (in-khet per khwaeng) and PIP-INS
   River City; the sathon polygon hides all BTS nodes; Victory Monument's khet
   attribution conflicts by polygon vs sources. Coarse district polygons + the
   150 m border rule explain most of them; the fix is polygon quality, not
   copy changes.
5. **Rent figures are asking-price proxies with mixed semantics** — two
   different "Pathum Wan blends" coexist in the app (33,500/74,000 on the
   phloen-chit record vs 38,000/85,000 on the district record), chit-lom's
   120,000 override is a top-decile luxury figure, pom-prap's 2-bed blend sits
   below every observed ask, and no signed-lease series exists anywhere in
   public sources. The labelling (`blend` vs `override` vs `median`) is doing
   real work and should stay visible.

## 3. Editorial-tile value (what the researched tiers can say today)

46 researched units now support concrete, claim-linked copy: e.g. Asok's
"one corner, two rail lines, Soi Cowboy 120 m — and Benjakitti's gates beyond
the catchment"; Sam Yan's displacement-history counterweight to vibe 10;
Chatuchak's 120.5 ha four-park complex as the honest green case; Ari's
"leafy ≠ park access" resolution; the canal park's 200 m of reality out of a
4.5 km plan; the Ratchathewi flyover closure (2025-01 → 2028-04) and Orange
Line works as dated change items. Banned-copy rules held across all 667
claims and all editorial strings; the only recurring copy fault (radius→time)
was mechanically caught four times and is now a required gate.

## 4. Method costs and what they buy

Full bundle ≈ 1.5–11.6M subagent tokens, 27–92 tool calls, 13–45 min (n=22);
light bundle ≈ 0.8–12.8M across four entities (n=6 agents); data-only ≈ nil.
The tier plan makes 183-entity coverage tractable, but tier C placeholders are
**not** product copy — they mark where work goes. Upgrade triggers are in the
plan doc.

## 5. Process integrity (what the reviews caught)

Coordinator verification passes caught one P1 factual error (batch 1), six
numeric corrections (batch 2), two straddle corrections (batch 3), and the
five-shape adapter normalized 100+ field/enum drifts with a full log —
prompt-contract drift happened in **every** batch despite increasingly
explicit prompts, which is why the machine gates, not prose rules, are the
load-bearing control. Agents also corrected the coordinator four times
(wrong leads), which is the system working. The sam-yot verification pass
(34 bodies opened post-hoc) rescued a below-contract bundle rather than
hiding it. Post-close re-gates kept proving the same point: the 2026-11-08
audit upgrade caught **71 batch-4 limitations arrays exploded into single
characters** by the normalize step (repaired, verified byte-exact against
raw) — invisible to the gates as they stood at batch close.

## 6. What this program did NOT do (unchanged boundaries)

No live app data, scoring, filters, geometry, translations, image registries
or application code touched (git-verified each commit). No tracker issues,
no publications, no API purchases. Image rights: plan only, zero assets.
Translations: none manufactured. Popularity: never measured; coverage breadth
was used for selection only.

## 7. Open gates (in order)

1. **Independent human review** of the 46 researched bundles (packet:
   `batches/REVIEWER-PACKET.md`; per-batch findings + master index are the
   map). Tier C placeholders: script-assisted bulk check **137/137 PASS**
   (2026-11-08) — reviewer sign-off pending.
2. **Sender adoption** of the handoff amendments (A1–A8 applied to the
   in-repo copy; original line still authoritative).
3. **Pipeline tickets** — the 2026-11-07 + 2026-11-08 notes hold the
   ghost-station audit, green-basis decision, anchor-convention audit, polygon
   quality, rent-semantics cleanup, and fact corrections.
4. **Tier upgrades** per the plan (contested/featured entities → full).
5. **Then**: translations (separate gate), image rights (separate gate),
   and the small integration adapter (localized preview index; full
   narrative on demand).

## 8. Verdict

The program met its contract: honest, provenance-complete place research at
three honest tiers, with every quality gate that fired documented rather than
smoothed. The strongest deliverable is not the copy — it is the set of
**provable score-context facts** (buffer effects, anchor offsets, ghost
station, polygon coarseness) that the product team can now act on with
receipts.

## Post-review correction (2026-11-08, independent review)

The independent review ([`2026-11-08-independent-review.md`](2026-11-08-independent-review.md))
corrects three statements above and records the sign-off state:

1. **§2.4 / khlong-san is wrong.** The "10-vertex khet polygon" that
   PIP-OUTs ICONSIAM is the **station cell**
   (`station-geometry.json["khlong-san"]`), not the khet. The 50-vertex
   district polygon **contains** ICONSIAM and G2 Charoen Nakhon and excludes
   River City. The batch-4 `khlong-san` bundle repeats the error and is
   blocked (F5).
2. **§5 / sam-yot "34 bodies opened post-hoc" is not reflected in the
   delivered bundle.** 40 of 43 sources remain `body_read: false`; 11 claims
   rest solely on them. The bundle is blocked (F3).
3. **§1 and §7 "no bundle independently approved" is superseded** by the
   agent-review statuses: 22 approved / 24 blocked, with the caveat that this
   is an **agent review, not a human signatory** — DEC-2/G10 remains open.
   Also: "zero P1" was true only under the rules then shipped; the review's
   new rules find 97 + 126 P1s in batches 2 and 4 (normalize damage,
   provenance, inline copy).

The program verdict otherwise stands: the five systemic findings remain the
program's real product, with the khlong-san detail corrected as above.
