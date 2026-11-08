# B-2 + B-4 pipeline receipts — anchor & polygon audits (2026-11-08)

Research-side audit receipts for pipeline tickets **B-2** (anchor-convention
audit) and **B-4** (polygon quality pass). No app data touched; every probe
is reproducible with `kit/check_geometry.py` and the committed CSVs. These
receipts update/correct earlier statements — see §3, where one prior claim is
**overturned by better probes**.

## 1. B-2 — app anchor vs published coordinate offsets (133 station areas)

Method: for each area, the app anchor (`stations.json` lat/lng) vs the
primary coordinate of the area's EN Wikipedia article (MediaWiki API,
`prop=coordinates`, redirects followed, retries + convergence rounds; a
flaky-network day — 3 extra convergence passes were needed and logged).
Artifacts: [`2026-11-08-b2-anchor-audit.csv`](2026-11-08-b2-anchor-audit.csv)
(92 audited offsets) and
[`2026-11-08-b2-anchor-missing.csv`](2026-11-08-b2-anchor-missing.csv)
(41 remaining: 20 HTTP errors — mostly non-existent articles, 19 articles
without coordinate templates, 2 no-wiki-title).

| Band | Count | Reading |
|---|---|---|
| ≤ 100 m | 84 (91%) | the app anchors are **systematically correct** — the earlier "anchor conventions drift" worry is a *tail*, not a system |
| 101–250 m | 5 | sam-yan/sam-yot ≈108 m (MRT node vs catchment anchor — fine), ratchaprarop 101 m, phasi-charoen 93 m, taling-chan 84 m |
| 251–500 m | 2 | **wat-mangkon 346 m** (confirms batch-2's "~320 m Wikipedia infobox conflict" — the *Wikipedia* side is displaced); **bang-son 293 m** (new) |
| > 500 m | 1 | **don-mueang 658 m** (new — the article targets the railway station complex; the app anchor sits at the airport rail link stop) |

**Ticket-relevant conclusions (B-2):**
1. The program's earlier framing ("anchor conventions drift 270–770 m on ≥8
   units") **overstated the scope**: the corpus-wide audit shows 91% within
   100 m. The genuine cases are the *known* ones (saint-louis ~720 m —
   article has no coordinates, hand-verified earlier; chit-lom — Wikipedia's
   coordinate is displaced per batch-2; wat-mangkon — Wikipedia infobox vs
   app ~320 m) plus **three new named cases**: bang-son (293 m), don-mueang
   (658 m), wutthakat (241 m).
2. The distance-base rule (B-2): distance claims in bundles should key on the
   **app anchor** (they do — briefs instructed this), with affected claims
   marked where the anchor itself is defective (saint-louis already marked;
   add bang-son/don-mueang if any distance claims cite them).
3. `sena-ruam` appears in the missing list with its Wikipedia article present
   — the ghost station; its removal is staged on the pipeline branch (B-1).

## 2. B-4 — polygon PIP case table (kit/check_geometry.py, `--khet` where noted)

| # | Case | Probe | Result | Reading |
|---|---|---|---|---|
| 1 | khlong-san khet ring (50 vertices) contains ICONSIAM | `--khet khlong-san` 13.7265/100.5103 | **IN** | confirms review F5: the earlier "excludes ICONSIAM" claim had measured the station cell |
| 2 | khlong-san ring contains G2 Charoen Nakhon (Gold Line) | `--khet khlong-san` 13.7265/100.5090 | **IN** | consistent with khwaeng Wat Kanlaya |
| 3 | khlong-san ring excludes River City | `--khet khlong-san` 13.7360/100.5137 | **OUT** | correct — River City is Bang Rak |
| 4 | **sathon: all three BTS-line anchors inside the khet ring** | `--khet sathon` with the TRUE app anchors (surasak 13.71927/100.52146, chong-nonsi 13.7238/100.52933, saint-louis 13.72082/100.52669) | **IN ×3** | **overturns the earlier "all three BTS nodes PIP-out" claim** — see §3 |
| 5 | thon-buri ring excludes BTS Wongwian Yai | `--khet thon-buri` 13.7208/100.5161 (wiki) and the TRUE app anchor 13.72108/100.49516 | **OUT ×2** | confirms the finding: Wongwian Yai sits in khlong-san per administration; the app anchor is >1.2 km outside the thon-buri ring |
| 6 | phaya-thai ring CONTAINS the Victory Monument circle | `--khet phaya-thai` 13.7699/100.5350 (wiki) | **IN** | the app's phaya-thai polygon agrees with phaya-thai attribution… |
| 7 | …while ratchathewi ring excludes it | `--khet ratchathewi` same point | **OUT** | so the encyclopedias/Gazette (Ratchathewi) vs app polygon (phaya-thai) conflict is real and lives in the polygon, not the anchors |
| 8 | BTS Phaya Thai + ARL outside the phaya-thai khet | `--khet phaya-thai` 13.75696/100.53382 (TRUE anchor) | **OUT** (ratchathewi: **IN**) | confirms the batch-2 finding with the true anchor |
| 9 | victory-monument station cell excludes the monument circle | station cell 13.7699/100.5350 | **OUT** (cell top edge 13.76978) | the monument sits ~10–20 m beyond the cell's northern tip — a genuine catchment-edge artifact worth a pipeline note |

## 2b. Coverage update + a self-inflicted data-loss lesson (fifth review, same day)

- The 20 "HTTPError" rows were **transient rate-limiting, not dead links** —
  a delayed retry recovered 8 more areas → audit now **100/133** (90 ≤100 m;
  drift cases unchanged: don-mueang 658, wat-mangkon 346, bang-son 293;
  wutthakat 241 = minor). Remaining 35 missing: 19 articles without
  coordinates, 4 without an EN article, 12 persistent fetch-errors
  (documented; ~83% coverage is the accepted ceiling for this environment).
- **Process lesson:** two successive write crashes truncated the audit CSV
  (write-open truncates before the crash; one run then wrote an empty list
  over it). Restored from git (273ceb2) — the committed-artifact discipline
  saved the data — and the recovery now builds both final lists in memory
  before opening any file for write. Verify-a-fix-by-its-effect extends to:
  *never open write mode on an artifact until its replacement content is
  fully constructed.*

## 3. Corrections this audit makes to the program record

1. **sathon "all three BTS nodes PIP-out" is overturned.** The claim (batch-4
   framing "the clean mechanism for transport 7", repeated in the independent
   review's verification section) was probed with coordinates that do not
   match the app's actual anchors. With the true anchors, **all three nodes
   are inside the khet ring**; the sathon transport-7 mechanism question
   returns to *unexplained* (likely measurement-buffer, like the other
   ratings — the B-3/B-4 family), not polygon edge. The earlier review text
   already hedged ("metres-sensitive; holds for the app anchors") — the
   hedge was right and the underlying probe was wrong.
2. **B-2 scope corrected**: "drift on ≥8 units" → 91% of anchors within
   100 m; genuine drift is 6 named cases (saint-louis, chit-lom-side
   Wikipedia displacement, wat-mangkon-Wikipedia, bang-son, don-mueang,
   wutthakat), most of them *Wikipedia-side* displacement, not app-side.
3. **New pipeline-note candidates**: S6-adjacent (from batch 5) and
   victory-monument cell-edge (case 9) — recorded in the plan's D-1/B-4 rows
   via this document.

## 3b. Drift-case classification (post-audit, same day)

All four offset cases are **same-station displacements** — the app never
anchors the wrong station:
- wat-mangkon 346 m — Wikipedia infobox conflict (batch-2 record, confirmed);
- bang-son 293 m — large elevated interchange complex (MRT Purple + SRT Light
  Red); article coordinate vs app anchor at the complex's other part;
- don-mueang 658 m — SRT Dark Red Line Don Mueang; the station complex's
  position vs the article coordinate (the complex was rebuilt/moved platforms
  in the 2020s);
- wutthakat 241 m — BTS Silom node precision vs catchment anchor.

Ticket-relevant rule holds: bundles key distance claims on app anchors; the
four cases need no bundle marks unless a claim cites a distance to the
*Wikipedia* coordinate (none do).

## 4. What stays blocked

Polygon **re-sourcing** (replacing coarse khet rings with better boundaries)
and any anchor **correction** are build-side changes — they ride the B-1
replay on the pipeline branch once the build machine is available. This
document is the receipts half only.
