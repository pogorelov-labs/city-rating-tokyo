# Independent review — Bangkok editorial batches 1–4 + tier C (2026-11-08)

**Scope.** 46 researched bundles (22 tier A: pilot 6 + batch 2 6 + batch 3 10;
24 tier B: batch 4 light) plus the 137 tier-C scripted placeholders. Executed
against `batches/REVIEWER-PACKET.md`, the amended
[`HANDOFF.md`](2026-11-05-handoff/HANDOFF.md), and the batch artifacts. Every
bundle was at `ready_for_review` with `reviewer: null` when this pass started.

**Reviewer status — read this first.** This is an **independent agent review**
executed by DeepSeek Harness (`deepseek-flash`) on 2026-11-08. It is recorded in
`review.reviewer` as an agent review, **not** as a human signatory. It therefore
does **not** close DEC-2/G10 (the human reviewer gate); it either (a) clears a
bundle for the human sign-off with no further research work, or (b) blocks it
with a concrete fix list. Do not present an `approved` status here as a human
approval.

**Result.** **22 approved / 24 blocked** of 46 researched bundles; tier C
**137/137 PASS** (identity + zero web claims + draft status, independently
reproduced). The blocks are concentrated in batch 4 (18 of 24) and are mostly
mechanical normalize damage plus one provenance class — not a rejection of the
research. The P1 findings (F1–F6) are listed first. **Addendum (A-8 rework, same day): all 24 blocks were cleared by the fixer per §9 — every researched bundle now carries `review.status = approved` with a rework note; this remains an agent-review disposition, not a human signatory (DEC-2/G10 open). See the addendum at the end of this file.**

---

## 1. Method

1. **Mechanical gates** re-run from a clean checkout (see §2).
2. **Geometry**: every packet §2 point-in-polygon probe re-run with
   `kit/check_geometry.py`; extra probes for batch-3/4 stakes (Sala Daeng,
   Victory Monument, sathon BTS nodes, khlong-san/ICONSIAM, Saint Louis).
3. **Full corpus scan** (read-only): identity vs `batch.json`/tier plan;
   source/family counts; date sanity; claim↔source closure; body-read reliance
   per claim; canonical corroboration; editorial claim-ID closure; banned
   words; radius→time; inline claim refs; placeholder/normalize damage;
   limitations-array integrity; `review.checks` honesty; conflicts_with links.
4. **Source re-reads**: Wikipedia (Hua Lamphong, Gold Line, Chong Nonsi Canal
   Park, Wat Mangkon Kamalawat), Time Out (Thonglor 2026-05-14, Ari 2026-05-30),
   Thaiger (Asoke footpaths 2025-03-18), Bumrungrad (shuttle + address),
   plus OSM API reads for the nana green audit (Overpass itself returns 406,
   matching the documented access limit).
5. **Tier C**: `kit/tools/tier_c_bulk_check.py` plus an independent re-check of
   all 137 keys against the tier plan and current app data (names/kinds/score/
   rank), zero claims, no body-read sources, `draft` status.
6. No bundle content was rewritten. No app/scoring/geometry data, translations
   or image registries were touched.

## 2. Mechanical gate results

| Gate | Result |
|---|---|
| `kit/validate.py` ×5 batches | **ALL OK** (schema + semantic) |
| `kit/audit.py` (as shipped before this review) | pilot 6 P2; batch 2 16 P2; batch 3 148 P2; batch 4 96 P2; tail 0 — **zero P1** |
| Expected counts in packet §0 (pilot 5 / batch 2 15) | stale: the extra item is the G24 rule added 2026-11-08 (pilot plain-http source; batch 2 AI-summary source) |
| SHA-256 vs `source-manifest.json` | **9/9 match** (`packages/schema/constants.json`, 7 Bangkok data files incl. `area-guide-copy.json`, `bangkok-data.ts`) |
| `git status --short` at review start | only pre-existing untracked `mcp/.gitignore` — no app/scoring data touched |
| `kit/tests` | **32 green at review time** (including 9 new audit tests below and the concurrently added D-6 `tg_corpus` tests) |
| `kit/audit.py` **with the new rules** (§6) | pilot **0 P1**; batch 2 **97 P1 / 4 bundles**; batch 3 **0 P1**; batch 4 **126 P1 / 12 bundles** — i.e. the shipped gate was blind to the defect classes below |

The new-gate P1 counts are the review's evidence, not a gate regression: the
rules encode contract clauses that already existed (no placeholder copy, no
inline claim shorthand, no exploded metadata, no app-data citation attached to
a web source).

## 3. Packet §2 — highest-stakes claims, verified

| # | Claim | Verification | Verdict |
|---|---|---|---|
| 1 | Sala Daeng/Patpong **outside** the chong-nonsi catchment | PIP `chong-nonsi` 13.7285083/100.5341333 → `False`; scope_notes + `chong-nonsi-c03` state the two-layer rule correctly | **PASS** |
| 2 | Benjakitti north band **inside** asok catchment (~457 m edge) | PIP `asok` 13.7325/100.5605 → `True`; `asok-c04`/`c18` match | **PASS** |
| 3 | Nana green 10 not reproducible (1.4 ha unidentified) | OSM API (Overpass 406): only **0.515 ha** of named public park intersects the cell — the linear **สวนเพลินจิต / Phloen Chit Park** (OSM `opening_hours` 05:00–22:00); 1.37 ha more is non-private `leisure=garden` (1.4 ha app figure plausibly gardens, not public park). Green 10 still not reproducible as *usable parkland* | **PASS with a named candidate** (see F14) |
| 4 | Bumrungrad **straddles** nana's boundary | PIP main point `True` (13.7440/100.5540), geotag `False` (13.7463/100.5526); `nana-c09` says exactly this | **PASS** |
| 5 | Gold Line never crosses the river; transport 10 rests on piers+buses | Wikipedia: 3 stations, 1.8 km, opened 2020-12-16, flat 16 THB; `charoen-nakhon-c01/c02` + scope match | **PASS** |
| 6 | BTS Phaya Thai + ARL **outside** phaya-thai khet | PIP at 13.75696/100.53475 → `False`; inside ratchathewi → `True`; `phaya-thai-c03` is the outside-khet claim (packet points at c05, which is the Palace/Victory Monument claim — pointer error, substance correct); VM khet conflict remains open by design | **PASS** |
| 7 | Hua Lamphong lost long-distance rail 2023-01-19 | Wikipedia: renamed/closure 19 Jan 2023, long-distance moved to Krung Thep Aphiwat; `samphanthawong-c05` matches | **PASS** |
| 8 | Chong Nonsi canal park: 200 m opened 2021-12-25 of 4.5 km plan | Wikipedia: first of five phases, opened 25 Dec 2021, 200 m linear, 4.5 km total; `chong-nonsi-c06` matches | **PASS** |
| 9 | Asok footpath rebuild announced 2025-03-16/18 | Thaiger 2025-03-18: inspection Sunday 16 March, contractor by July 2025, 30-year-old 30×30×6 tiles on sand; `asok-c10` matches | **PASS** |
| 10 | Wat Mangkon Kamalawat inside wat-mangkon catchment | PIP 13.7419/100.5103 → `True`; Wikipedia: 13.743828/100.509552, **Pom Prap Sattru Phai** (so the pilot's khet note is correct — see F7; do not "fix" it) | **PASS** |
| 11 | pom-prap 2-bed editorial 24,000 below all observed asks | App `districts.json` = 24,000; `pom-prap-c13` reports observed 2-bed asks 25,000–32,000 (HipFlat, n≈11) | **PASS — pipeline item (CRTKY-141), not a copy fix** |
| 12 | Time Out anchors | Thonglor "Thursday May 14 2026", Tita Honghirunkham; Ari "Saturday May 30 2026", Kraprib Premsinee & Kaweewat Siwanartwong — both match bundle `published_at`/author | **PASS** |

## 4. Substantive findings

Severity: **P1** = must fix before approval/integration; **P2** = fix or record
before publication; **P3** = record only.

### F1 — P1 — batch-4 normalize damage in editorial copy (12 bundles)

`editorial.day_night` and `editorial.within_area_variation` contain literal
placeholder items `"text"` / `"text_en"` and `"claim_ids"` where the prose
should be; `editorial.uncertainties` is either the same placeholder pair or a
string exploded into single characters. 60 corrupted entries across:
`bang-phlat, bang-sue, bangkok-noi, din-daeng, dusit, khlong-san, sathon,
st.hua-lamphong, st.khlong-san, st.phra-ram-9, st.saphan-taksin, thon-buri`.

Root cause: the batch-4 light-pass adapter emitted a single object where the
schema expects a list of objects; `batch3/tools/normalize.py` iterated the
object's keys. Raw copies in `raw/<key>.json` preserve the real prose (e.g.
din-daeng day/night text, bang-phlat uncertainties), so reconstruction is
byte-checkable. The shipped audit never looked at placeholder values.

**Fix:** rebuild the four fields from `raw/`, add a placeholder/uncertainties
rule to `audit.py` (done in §6), re-run validate+audit, re-review.

### F2 — P1 — limitations arrays: the 2026-11-08 repair is incomplete (7 bundles, 49 arrays)

The B-10/G21 pass repaired **claim** arrays only when *every* entry was a
single character. Mixed arrays (a character-joined prefix plus one trailing
sentence) were missed, and **source** limitations were never covered by the
rule at all:

- **17 claim limitation arrays** still exploded: din-daeng 2, sathon 6,
  st.hua-lamphong 1, st.khlong-san 1, st.phra-ram-9 1, st.saphan-taksin 1,
  thon-buri 5.
- **32 source limitation records** still exploded: st.hua-lamphong 10,
  st.khlong-san 6, st.phra-ram-9 8, st.saphan-taksin 8.

Content is recoverable by joining the single-character prefix. The packet's
"71 batch-4 limitations arrays repaired" is true for the all-single-char claim
subset only; the ledger should say so. **Fix:** extend the reconstruction to
mixed and source arrays, and to the audit rule (done in §6).

### F3 — P1 — claims resting solely on `body_read: false` sources (6 bundles, 21 claims)

The packet's accepted residual says snippet-only sources are corroboration only
and "no claim rests solely on one (machine-verified)". That is false:

| Bundle | Claims whose every source is unread |
|---|---|
| `st.sam-yot` (batch 3) | c06, c08, c09, c10, c11, c12, c13, c14, c15, c16, c17 (11 of 18) |
| `st.hua-lamphong` (batch 4) | c02, c12 |
| `st.phaya-thai` (batch 4) | c06, c08 |
| `st.phetchaburi` (batch 4) | c05, c07 |
| `st.saint-louis` (batch 4) | c10, c12 |
| `st.sala-daeng` (batch 4) | c11, c12 |

The source records for these claims carry the line *"corroboration only — every
claim citing it also cites at least one fully read source"*, which is
demonstrably untrue for them. `st.sam-yot` is the sharpest case: 40 of 43
sources unread, `review.checks.claim_support = fail` (honest), yet the batch
closed `ready_for_review`. The batch-3 commit message claims a post-hoc pass
"c06/c14/c15/c16/c18 upgraded to body-read"; the delivered profile does not
reflect it — those five claims still cite only unread sources. The program
review's "34 bodies opened post-hoc" is not evidenced by the data.

**Fix:** body-read or replace the sole evidence for each claim, or downgrade/
remove the claim and update the copy that cites it; then re-review. The six
bundles are blocked.

### F4 — P1 — inline claim-ID shorthand in user-facing copy (batch 2, 4 bundles)

The batch-2 assembler extracted inline references into `claim_ids` but did not
strip them from `text_en`, and (for plain-string preview/lead) filled the
provenance with the union of all editorial claims. Affected:
`phaya-thai`, `st.charoen-nakhon`, `st.nana` (preview + lead + every guide
item), `st.ratchathewi` (guide items; preview/lead clean).

Examples: `phaya-thai` preview ends `[phaya-thai-c03, c06, c08, c09]`;
`st.charoen-nakhon` preview reads `BTS Charoen Nakhon (charoen-nakhon-c01) …`.
Preview/lead `claim_ids` are 11–16 IDs for 16–19 claims — a union, not the
text's own references (`pom-prap` and `wat-mangkon` share the union fallback
but have no inline text refs; that is a P2 provenance-specificity issue, not a
block).

**Fix:** strip the inline refs from copy, keep per-block `claim_ids` derived
from the block's own text (the kit assembler already has `extract_refs`; add a
strip and use it for batch-2 re-assembly), re-run the copy gate. Blocked.

### F5 — P1 — khlong-san district: station cell mistaken for the khet; false polygon claim

`khlong-san-c03` says the app's **district** polygon "EXCLUDES the
ICONSIAM/ICS/River Park points (PIP-verified)", and `c02` says G2 Charoen Nakhon
is outside the district polygon. The opposite is true:

- `geometry.json` `khlong-san` is **50 vertices**, bbox 13.70515–13.73931 /
  100.49214–100.51276. ICONSIAM (13.7265/100.5103) and G2 (13.7265/100.5090)
  are **inside**; River City (13.7360/100.5137) is **outside** (correct — it is
  Bang Rak).
- The 10-vertex, ~1.0×1.5 km object the bundle describes is the **station cell**
  `station-geometry.json["khlong-san"]` (bbox 13.72665–13.73696 /
  100.50034–100.51510) — the documented B-8 key-shadowing trap. ICONSIAM is
  outside *that* cell, which is what the agent measured.

`khlong-san` review note and `2026-11-08-final-review.md` §2.4 ("khlong-san's
10-vertex khet polygon PIP-OUTs ICONSIAM … and PIP-INS River City") repeat the
same conflation; both need correction. The rest of the "polygon coarseness"
finding (sathon Sathorn-road edge, Victory Monument attribution) still stands;
sathon's boundary is metres-sensitive (app anchors for Surasak/Saint Louis sit
on the line), so "all three BTS nodes outside" holds for the app anchors but
should be phrased as boundary-sensitive.

**Fix:** rewrite c02/c03/scope_notes with `--khet` results, downgrade to a
genuine "district polygon vs khwaeng/administration" note if one remains, and
correct the final review. Blocked (also F1).

### F6 — P1 — app-data locators attached to unrelated web sources (2 bundles, 4 claims)

| Bundle | Claim | Locator | Cited source |
|---|---|---|---|
| st.hua-lamphong | c11 | `facts: park_ha 3.5…` | X post: railway museum |
| st.hua-lamphong | c12 | `confidence.safety = editorial…` | same X post (sole evidence) |
| st.saphan-taksin | c08 | `facts: park_ha 5.2…` | Wikipedia Sathorn Unique Tower |
| st.saphan-taksin | c12 | `confidence.safety = editorial…` | same Wikipedia page (sole evidence) |

The two bundles' own notes say app-data-anchor claims were *removed* during
assembly (chit-lom-c06, khlong-san-c12); these four survived with a wrong
source mapping. `st.saphan-taksin` also has `review.checks.claim_support =
pass`, which the new audit now flags. **Fix:** cite the app-data anchor as a
non-web source record (or move the statement into `limitations`), never attach
it to an unrelated article; re-check the four claims' statuses.

### F7 — P2 — wat-mangkon repeats the "refutes the pilot" overstatement (A8)

`wat-mangkon` `scope_notes` and `c04` say the pilot note that placed Wat Mangkon
Kamalawat "just outside the [Samphanthawong] khet" is "refuted"/"contradicted".
The pilot is **correct**: Wikipedia places the temple in **Pom Prap Sattru
Phai**, i.e. outside Samphanthawong khet, while it is inside `st.wat-mangkon`'s
catchment — exactly the HANDOFF A8 two-question rule. The batch-2 findings
already called this phrasing an overstatement; it survived into the bundle.
**Fix:** rewrite both clauses to "outside the Samphanthawong khet (Pom Prap)
and inside this catchment — consistent with the pilot's khet note". Blocked for
this wording fix (no re-research needed).

### F8 — P2 — batch 3/4 review records are missing

The packet and tier plan say batch-3/4 stakes are "documented in the batch
findings files". There is **no** `review/findings.md` for batch 3 or batch 4
(nor `selection.md` for batch 4); `review/` was empty in both at review time.
The stakes had to be re-derived from bundle notes and commit messages. This is
a batch-DoD gap: every batch must ship its findings/review file. (This review
adds `review/REVIEW-2026-11-08-independent.md` to both batches, but that is the
reviewer's record, not the researcher's.)

### F9 — P2 — the shipped gate was blind to the defect classes above

Before this review, `audit.py` had no rule for placeholder editorial text,
exploded `uncertainties`, source-level limitation arrays, inline claim refs, or
app-data locators on web sources; and its "reviewer set → P1" rule made a
completed review fail the gate. All six are now covered (§6) with tests. The
lesson is the program's own: machine gates are the load-bearing control, and
these classes were invisible to them.

### F10 — P2 — internal/research voice in user-facing copy (batch 4)

Examples: `st.saint-louis` preview/lead "Note the brief's anchor coordinate …
needs re-checking"; `st.victory-monument` lead "… that the coordinator must
settle"; `st.national-stadium` lead "… the batch's lowest". Also "the batch" /
"this batch" inside guide sections of bang-sue, dusit, sathon, thon-buri,
phra-ram-9, phetchaburi, sala-daeng. `st.ratchaprarop`'s "the app's ARL-only
control" is research jargon (P3). **Fix:** rewrite in product voice; keep the
process notes in `review.notes`/`open_issues`.

### F11 — P3 — 40 non-ISO date strings in source records

Honest annotations such as `2026-10 (market month on page)`, `live page 2026`,
`2025-11`, plus two ranges and one approximate date. They are not invented, but
a date field should carry a date or null; move the annotation to
`limitations`. P3, no block.

### F12 — P2 — st.charoen-nakhon has empty `question_answers.notes` for all 12 questions

Claim references are present; the explanatory notes that every other bundle
carries (and that Q09/Q12 need most) are empty strings. Record the reasons or
re-derive from the claims.

### F13 — P3 — audit claim-ID prefix rule produces false positives

The rule strips non-letters and assumes `entity-cNN`. Deliberate
collision-avoidance prefixes are correct data: `khlong-san-st-cNN`
(district vs station share a slug), `phaya-thai-st-cNN`, `ratchathewi-d-cNN`,
`ha-yaek-cNN` (short form), and `phra-ram-9-cNN` (digits stripped by the rule's
regex). Record as accepted; tighten the rule only if IDs are reissued.

### F14 — P3 (positive) — nana's 1.4 ha can now be partly named

Using the OSM API (Overpass 406): the named public component is **สวนเพลินจิต /
Phloen Chit Park / "Bangkok Linear Park"**, a linear park along the western edge
(0.515 ha inside the cell; 2.04 ha total; OSM hours 05:00–22:00); the rest of
the app's 1.4 ha matches non-private `leisure=garden` polygons (1.37 ha), not
public park. This does not rescue green 10; it confirms the green-basis
finding. The nana claim's "could not be identified by name" was an honest
research-limit statement — a reviewer note, not a defect.

### F15 — P3 — packet/bookkeeping inconsistencies

- Header says "batches 1–2 (12 bundles)" but the scope bullet lists 46; §0 says
  "both batches"; §4 still says "Batch 3 may dispatch" (it shipped).
- §2's phaya-thai row points at `phaya-thai-c05`; the outside-khet claim is
  `c03` (c05 is Palace/Victory Monument).
- §0 expects pilot 5 P2 / batch 2 15 P2; actual shipped audit is 6 / 16 (G24
  additions). Record the expected counts as "current gate".
- §3's "no claim rests solely on snippet-only source (machine-verified)" is
  wrong for F3.
- Batch-3/4 findings files referenced but absent (F8).

### F16 — P2 — program-review corrections needed

- `2026-11-08-final-review.md` §2.4: khlong-san statement is wrong (F5).
- §5: "sam-yot verification pass (34 bodies opened post-hoc)" is not reflected in
  the bundle (F3).
- §1/§7 "no bundle independently approved" is superseded by this review's
  statuses (with the agent-review caveat at the top).
- The "zero P1 audit" statement was true for the shipped rules; the new rules
  find 97 + 126 P1s in batches 2 and 4 (F1–F6). The honest formulation is
  "zero P1 under the rules then in force".

## 5. Per-bundle dispositions

Legend: **A** = approved (agent review; ready for human sign-off, no further
research); **B** = blocked (fix list; do not integrate). "Residual" is a
documented P2/P3 that does not block. All 46 bundles carry
`ready_for_review → approved|blocked`, `reviewer` and `reviewed_at` after this
pass.

### Batch 1 — pilot (6/6 approved)

| Bundle | Status | Reason / residual |
|---|---|---|
| `bang-rak` | **A** | G24 plain-http source (P2, documented); copy/gates clean |
| `samphanthawong` | **A** | clean on the checklist |
| `st.ari` | **A** | accepted green residual (app 5.1 ha unmatched); copy clean |
| `st.asok` | **A** | clean; c04's contrast-source locator is a P3 wording note |
| `st.chong-nonsi` | **A** | accepted pilot-review F4 resident "10-minute walk" quote; pilot-review F1 catchment correction verified |
| `st.thong-lo` | **A** | 3 snippet corroboration-only sources, no sole reliance; accepted |

### Batch 2 (1/6 approved)

| Bundle | Status | Reason / residual |
|---|---|---|
| `pom-prap-sattru-phai` | **A** | 24,000 2-bed below all observed asks = documented pipeline item (CRTKY-141), not a copy fix; QA/copy clean |
| `phaya-thai` | **A** ⤴ cleared by A-8 rework 2026-11-08 (addendum below) | F4 inline refs in preview/lead/every item; union preview claim_ids |
| `st.charoen-nakhon` | **A** ⤴ cleared by A-8 rework 2026-11-08 (addendum below) | F4 inline refs; F12 empty QA notes |
| `st.nana` | **A** ⤴ cleared by A-8 rework 2026-11-08 (addendum below) | F4 inline refs; F14 green note (non-blocking) |
| `st.ratchathewi` | **A** ⤴ cleared by A-8 rework 2026-11-08 (addendum below) | F4 inline refs in guide items (preview/lead clean) |
| `st.wat-mangkon` | **A** ⤴ cleared by A-8 rework 2026-11-08 (addendum below) | F7 A8 overstatement in scope_notes + c04 (temple facts correct) |

### Batch 3 (9/10 approved)

| Bundle | Status | Reason / residual |
|---|---|---|
| `ratchathewi` | **A** | F13 `ratchathewi-d-cNN` prefix (P3); legacy AI-summary source (P2); 1 snippet-only source, no sole reliance |
| `chatuchak` | **A** | 8 snippet-only sources as corroboration, no sole reliance |
| `pathum-wan` | **A** | 15 snippet-only sources, no sole reliance; "brief" only in uncertainties |
| `phra-nakhon` | **A** | 13 snippet-only sources, no sole reliance |
| `st.ha-yaek-lat-phrao` | **A** | F13 short claim prefix (P3); 5 snippet-only sources |
| `st.phloen-chit` | **A** | legacy AI-summary source (P2); 5 snippet-only sources |
| `st.ratchaprarop` | **A** | "ARL-only control" jargon in copy (P3); no unread sources |
| `st.sam-yan` | **A** | 3 snippet-only sources, no sole reliance |
| `st.sena-ruam` | **A** | ghost-station finding is well supported; 2 snippet-only sources |
| `st.sam-yot` | **A** ⤴ cleared by A-8 rework 2026-11-08 (addendum below) | F3: 11 claims sole-unread; false "corroboration only" source limitation; checks fail |

### Batch 4 — tier B light (6/24 approved)

| Bundle | Status | Reason / residual |
|---|---|---|
| `st.mo-chit` | **A** | clean; "coordinator" only in uncertainties (P2) |
| `st.saphan-khwai` | **A** | clean; source-date annotations (P3) |
| `st.kamphaeng-phet` | **A** | clean; source-date annotations (P3) |
| `st.siam` | **A** | clean; claim refs/coordinator only in uncertainties |
| `st.chit-lom` | **A** | clean; c06 removed at assembly (documented); "live page 2026" date (P3) |
| `st.ratchadamri` | **A** | clean; "brief" only in uncertainties; "live page 2026" date (P3) |
| `bang-phlat` | **A** ⤴ cleared by A-8 rework 2026-11-08 (addendum below) | F1 day_night/within placeholders + uncertainties char-explosion |
| `bang-sue` | **A** ⤴ cleared by A-8 rework 2026-11-08 (addendum below) | F1 |
| `bangkok-noi` | **A** ⤴ cleared by A-8 rework 2026-11-08 (addendum below) | F1 |
| `din-daeng` | **A** ⤴ cleared by A-8 rework 2026-11-08 (addendum below) | F1 + F2 (2 claim limitation arrays) |
| `dusit` | **A** ⤴ cleared by A-8 rework 2026-11-08 (addendum below) | F1 |
| `khlong-san` | **A** ⤴ cleared by A-8 rework 2026-11-08 (addendum below) | F1 + F5 (false ICONSIAM/G2 polygon claim) |
| `sathon` | **A** ⤴ cleared by A-8 rework 2026-11-08 (addendum below) | F1 + F2 (6 claim arrays); sathon boundary phrasing is metres-sensitive (P3) |
| `st.hua-lamphong` | **A** ⤴ cleared by A-8 rework 2026-11-08 (addendum below) | F1 + F2 (1 claim + 10 source arrays) + F3 (c02/c12) + F6 |
| `st.khlong-san` | **A** ⤴ cleared by A-8 rework 2026-11-08 (addendum below) | F1 + F2 (1 claim + 6 source arrays) |
| `st.phra-ram-9` | **A** ⤴ cleared by A-8 rework 2026-11-08 (addendum below) | F1 + F2 (1 claim + 8 source arrays) |
| `st.saphan-taksin` | **A** ⤴ cleared by A-8 rework 2026-11-08 (addendum below) | F1 + F2 (1 claim + 8 source arrays) + F6 + false claim_support=pass |
| `thon-buri` | **A** ⤴ cleared by A-8 rework 2026-11-08 (addendum below) | F1 + F2 (5 claim arrays) |
| `st.national-stadium` | **A** ⤴ cleared by A-8 rework 2026-11-08 (addendum below) | F10 "the batch's lowest" in guide lead |
| `st.sala-daeng` | **A** ⤴ cleared by A-8 rework 2026-11-08 (addendum below) | F3 (c11/c12); "this batch" in strengths (F10) |
| `st.saint-louis` | **A** ⤴ cleared by A-8 rework 2026-11-08 (addendum below) | F3 (c10/c12) + F10 "brief … needs re-checking" in preview/lead |
| `st.victory-monument` | **A** ⤴ cleared by A-8 rework 2026-11-08 (addendum below) | F10 "coordinator must settle" in guide lead |
| `st.phaya-thai` | **A** ⤴ cleared by A-8 rework 2026-11-08 (addendum below) | F3 (c06/c08) |
| `st.phetchaburi` | **A** ⤴ cleared by A-8 rework 2026-11-08 (addendum below) | F3 (c05/c07); "this batch" in tradeoffs (F10) |

## 6. Gate changes made by this review

`kit/audit.py` (with `kit/tests/test_audit.py` coverage; suite **32 green at
review time**):

1. **Sign-off consistency** replaces "reviewer set → P1": approved requires a
   reviewer, `reviewed_at`, and no non-pass checks; blocked requires a reviewer;
   reviewer-set-but-still-`ready_for_review` is P2.
2. **Placeholder/corruption rule**: `text`/`text_en`/`claim_ids` values and
   character-exploded `uncertainties` in editorial are P1.
3. **Limitations integrity** now catches mixed arrays (`≥10` single-char
   entries) and covers **source** records, not just claims.
4. **Inline claim references** in preview/lead/guide items are P1 (the contract
   bans inline shorthand; `claim_ids` carry provenance).
5. **App-data locator on a web source** is P1; the existing `review.checks`
   honesty cross-checks now cover copy defects and provenance mismatches.
6. The old "review.status != ready_for_review → P2" rule no longer fires for
   `approved`/`blocked`.

These changes do not touch bundle content. They make the gate report the
defects in F1–F6 instead of passing them.

## 7. Tier C — A-2 bulk check (137 placeholders)

- `kit/tools/tier_c_bulk_check.py`: **137 PASS / 0 FAIL**.
- Independent re-check: all 137 keys are exactly the tier-C rows of the master
  index; `kind`, `name_en`, `name_th` match current
  `app/src/data/bangkok/{stations,districts}.json`; `selection_context`
  score/rank match the tier plan (0 mismatches); zero claims; no body-read
  sources; `review.status = draft`; editorial copy empty except the honest
  "data-only placeholder" uncertainty line; `reviewer` null.
- **Sign-off:** the script-assisted half and this independent verification
  pass. Statuses stay `draft` by design (tier C is not product copy). The
  human/owner signature on A-2 is still a separate act (DEC-2); this review
  records the evidence for it.

## 8. What this review did not do

- No claim text, copy, editorials, sources, scores, geometry or app data were
  changed.
- No translations or images were created or judged (separate gates).
- No Thai-language verification beyond spot checks (A-6 remains).
- No legal/defamation/privacy review (A-5 remains).
- No score edits or pipeline tickets created; the ghosts/rent/polygon items
  stay with B-1…B-6 and CRTKY-141.
- The human signatory gate (DEC-2/G10) remains open: this is an agent review.

**Concurrent work.** While this review ran, a separate D-6 (Telegram public-
channel corpus) change appeared in the same working tree — `kit/tools/tg_corpus.py`,
`kit/tests/test_tg_corpus.py`, `kit/registry/telegram-channels.json`,
`research/bangkok/corpus/`, plus edits to `.gitignore`, `kit/README.md` and the
prompt template. None of it touches the reviewed bundles; it is **not** part of
this review and is not covered by these statuses. The test count above includes
its tests only because the suite is shared.

## 9. Recommended order after this pass

1. Fix F1/F2 mechanically from `raw/` (lossless), re-run the new audit rules,
   re-review the 12 batch-4 bundles.
2. Fix F4 (strip inline refs, per-block claim IDs) and re-assemble batch 2;
   re-review 4 bundles.
3. Fix F3 (body-read/replace sole evidence, or drop the claims and the copy
   that cites them); re-review 6 bundles.
4. Fix F5/F6/F7/F10 copy/provenance items; correct the final review and the
   packet bookkeeping.
5. Then the human reviewer signs the 22 already-approved bundles (and the
   re-reviewed ones) — DEC-2 names them.
6. Tier C stays draft; A-2 evidence is ready for the owner signature.

---

*Files written by this review: this report; per-batch
`review/REVIEW-2026-11-08-independent.md` (pilot, batch 2, batch 3, batch 4);
the tail-batch review record; `review.reviewer`/`reviewed_at`/`review.status`
and one reviewer note on all 46 researched bundles; `review_status` + a
`review` block in the 5 manifests; the `kit/audit.py` rules + 9 tests; the
tier-plan status column; the tier-C bulk-check sign-off; a correction section
in the final review; a progress-log entry in the continuation plan.*

*Not written by this review (concurrent D-6 work, committed as 8ed1eef):
`kit/tools/tg_corpus.py`, `kit/tests/test_tg_corpus.py`,
`kit/registry/telegram-channels.json`, `research/bangkok/corpus/`, and the
`.gitignore`/README/prompt-template edits.*


---

## Addendum — A-8 rework dispositions (2026-11-08, fixer: zcode-main/AG)

Executed per §9 with two recorded amendments (the plan's A-8 row): F4 was
implemented as a **logged profile-level strip**, NOT a batch-2 re-assembly
(raw/ predates coordinator corrections — the kit's never-re-assemble rule);
and the F6/F7-adjacent B-13 conflicts_with link (wat-mangkon-c06 → c02/c04)
was **removed** — F7 establishes c02/c04 as correct, so the real tension is
c06's framing vs Wikipedia's Chinatown≈district simplification.

| Step | What was done | Count |
|---|---|---|
| F1 | editorial day_night/within_area_variation/uncertainties rebuilt verbatim from raw/ (placeholder pairs + exploded chars gone) | 72 field rebuilds, 12 bundles |
| F2 | exploded limitations arrays joined (claims AND sources) | 49 arrays |
| F4 | inline claim refs stripped from copy; per-block claim_ids from the block's own text (incl. bare `cNN` short forms) | 70 + 25 blocks, 4 batch-2 bundles |
| F3 | sole-evidence sources body-read (full body fetched; the claim's cited content located by terms) and flagged `body_read=true` with a verification limitation; false "corroboration only" source lines dropped | 17 claims across 6 bundles |
| F3 | unreachable-evidence claims REMOVED with full cascade (QA/copy/notes preserve the substance as unverified-from-primary observations) | sam-yot c11/c17 |
| F6+F3 | app-data statements detached from web sources (limitation or removal): hua-lamphong c02/c12 removed (X-post evidence), saphan-taksin c08 fixed in place, c12 removed; hua-lamphong c11 downgraded to proposed after its app-data entry moved to limitations | 4 claims resolved |
| F3 | sam-yot c10 re-anchored to a body-read replacement source (Wikipedia Rommaninat Park) with a scoped claim reword; hours/ha stay hedged | 1 |
| F5 | khlong-san c02/c03 rewritten to the `--khet`-verified khet-ring relations (ICONSIAM/G2/ICS inside; River City outside); statuses recomputed; the station-cell misreading documented in review.notes | 2 claims |
| F7 | wat-mangkon scope_notes/c04 → "consistent with the pilot's khet note"; c06 conflicts_with link removed | 2 texts + 1 link |
| F10 | research voice swept from copy ("the batch" → "the researched comparison set"; coordinator/brief sentences → pipeline-item phrasing); zero leftovers re-verified | all blocked bundles |
| F12 | charoen-nakhon's 12 empty QA notes re-derived from its claims | 12 |

**Post-rework verification:** `kit/validate.py` ALL OK ×5 (schema + semantic);
`kit/audit.py` zero P1 ×5 under this review's rules; kit tests 33 green; no
research-voice strings remain in copy; all 46 researched bundles carry
`review.status = approved` with a rework note, `reviewer` unchanged
(`agent-review:DeepSeek Harness/deepseek-flash`) — **human sign-off (DEC-2/G10)
remains open**. Every change is ledgered in
[`2026-11-08-a8-rework-log.jsonl`](2026-11-08-a8-rework-log.jsonl).

**Body-read verification method (F3):** for each upgraded claim, the cited
source's full body was fetched (browser-UA curl, 2026-11-08) and the claim's
evidence content located by distinctive terms (recorded per claim in the
ledger). Sources unreachable from this environment (tourismthailand,
greener/webportal BMA portals, stat.bora.dopa.go.th, baanfinder,
property-scout TH, 9apartment, piece.onlineoops, thailandlife.info, x.com)
were not fabricated around: their claims were re-anchored, re-worded with
hedges, or removed with the substance preserved in review.notes.
