# Contract-derived gate checklist (B-15, 2026-11-08)

The plan's B-15 response to the third review's Angle F: gates were growing
reactively (every defect class was found by an attention pass, never by the
contract). This checklist walks **HANDOFF.md's must-clauses in order** and
maps each to its machine gate or an explicit not-machine-checkable note.
Any future handoff change updates this file in the same commit. Seed rules:
the kit's current audit/validate/assemble behavior + the independent review's
six additions (2026-11-08).

| # | Handoff clause (section) | Machine gate | Status |
|---|---|---|---|
| 1 | Data-file SHA-256s vs `source-manifest.json` before research (§qualify) | shasum check (G3) | ✅ manual-run, scriptable |
| 2 | Env files inspected presence-only; contents never read | process rule | ⛔ not machine-checkable (behavioral) |
| 3 | No invented scored areas for unlinked stops; no separately researched 200 m cells (§unit) | assemble identity checks + tier plan | ⛔ judgment (audit P2 flags orphan-ish claims) |
| 4 | Unit geometry decided by app polygons, never raw radius (§geometry) | `check_geometry.py` (G4) + audit radius→time rule (G5) | ✅ |
| 5 | Geometry pass on every boundary claim BEFORE assembly | batch workflow step (G4) | ✅ process; coordinator runs it |
| 6 | All 12 questions answered with status + claim refs or reason (§questions) | validate + audit QA set/coverage (G1/G2) | ✅ |
| 7 | Body-read every cited source; snippets discovery-only, never sole evidence (§method) | audit body-read reliance + sole-evidence rule (review's rules, G2) | ✅ |
| 8 | ≥4 useful sources / ≥3 independent publisher families (tier A; ≥3/≥2 tier B) | assemble corroboration over canonical families (G21) + audit minimums | ✅ (family counts) |
| 9 | Claim IDs stable + entity-prefixed, deduped across bundles | audit prefix rule + global uniqueness sweep (B-arc1) | ✅ |
| 10 | Enum-exact output; nuance in limitations, never enums (§raw contract) | validate enums + assemble normalization log | ✅ |
| 11 | Normalizations logged, never silent | assemble counts in manifest (G2) | ✅ |
| 12 | Copy: no "vibrant"/"hidden gem"/"something for everyone"/interchangeable lists; concrete contrasts | audit BANNED rule (G5) | ✅ (the three phrases; "interchangeable lists" is ⛔ judgment — F10 voice sweep extends it) |
| 13 | Never state walking durations derived from the radius | audit WALKTIME rule (G5) | ✅ (advisory P2; known false-positive class) |
| 14 | No paywall bypass, no proxy mirrors; log inaccessible canonical URLs | process rule + audit G24 URL checks | ⛔ behavioral; G24 covers the citation side |
| 15 | No private addresses or personal data | audit personal-data scan planned (G17 → A-5) | ❌ to build (A-5) |
| 16 | AI/search-summary provenance banned (A-series/F-2) | audit G24 AI-summary markers | ✅ (marker-level; semantic detection ⛔) |
| 17 | Every citation = stable https canonical URL, hashed `src_` ID | validate URI + audit G24 scheme/id rules | ✅ |
| 18 | Corroboration = ≥2 *canonical* publisher families (G21/B-10) | assemble + audit via `canonical.py` | ✅ |
| 19 | `recheck_by` on volatile claims; registry updated every batch close | audit counts flags (G2) + `recheck-due.py` (C-5) | ✅ |
| 20 | `conflicts_with` populated where two claims contradict (B-13) | validate + audit link integrity | ✅ |
| 21 | Manifest completeness incl. research start/end (B-14) | manifest fields + `tools/manifest_times.py` | ✅ |
| 22 | Schema-valid bundles incl. semantic ref closure (storage contract) | `validate.py` (G1) — schema errors now genuinely enforced (gate-verification P0 fix) | ✅ |
| 23 | Editorial copy carries claim provenance; placeholders/internal voice banned (review F1/F4/F10 rules) | audit placeholder/inline-ref/sign-off-consistency rules | ✅ |
| 24 | Limitations arrays are real strings, not exploded fragments | audit integrity rule (≥10 single-char entries, claims AND sources) | ✅ |
| 25 | App-data anchors never ride web-source records (review F6 rule) | audit app-data-locator rule | ✅ |
| 26 | Tier-C placeholders: identity only, zero web claims, `draft` | audit data-only branch + `tier_c_bulk_check.py` (G9/A-2) | ✅ |
| 27 | Never launder tier C into guide prose (adapter rule) | E-6/E-5 adapter tests (to build — WS-E) | ❌ to build |
| 28 | Copy evidence bar: corroborated-only preview; proposed w/ attribution; human-sign-off key (E-5/G12) | adapter (to build) | ❌ to build |
| 29 | Corroboration is a label, not verification — reviewer checks substance (§gates) | G6/A-1 human pass | ⛔ human |
| 30 | Translation/image gates separate (WS-F/WS-G) | G18/G19 rubrics | ⛔ separate gates |

**Rule-relative counts convention (WS-H #10):** every audit summary reports
findings under the current rule version; "zero P1" claims cite the rule set.

**Reactivity audit of this file:** clauses 15, 27, 28 are the only ❌ items —
two belong to WS-E (adapter, gated on A-1), one to A-5. Everything else is
machine-checked or explicitly marked behavioral/human. Next reactive-gate
trigger: any future defect class gets both its audit rule AND a new row here
in the same commit.
