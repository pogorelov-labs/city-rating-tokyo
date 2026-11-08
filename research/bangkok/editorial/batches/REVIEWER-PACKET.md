# Reviewer packet — editorial batches 1–2 (12 bundles)

> **Executed 2026-11-08** by an independent agent review: 22 approved / 24
> blocked of the 46 researched bundles; tier C 137/137 PASS. Bundle statuses
> are no longer `ready_for_review`. Results, finding IDs and the re-review
> path: [`../2026-11-08-independent-review.md`](../2026-11-08-independent-review.md).
> The human signatory (DEC-2) remains open. This packet is kept as the
> instruction record; several of its counts/pointers are stale by design and
> are listed in the report's F15.

For the independent review the handoff requires. Every bundle sits at
`ready_for_review` with `reviewer: null`; this packet makes the pass cheap and
specific. **Researcher self-checks are not this review.**

- Batches: `2026-11-05-pilot-zcode-main`, `2026-11-07-batch2-zcode-main` (full bundles), `2026-11-07-batch3-zcode-main` (10 full),
  `2026-11-07-batch4-light-zcode-main` (24 light), `2026-11-08-tail-data-only`
  (137 scripted placeholders — bulk-checkable: identity + no-web-claims only).
  Master index: `../2026-11-08-tier-plan.md`. Additional batch 3–4 stakes:
  the sena-ruam ghost station, the sam-yot verification pass, the sala-daeng/
  saint-louis/phetchaburi merge and anchor findings, and the five-shape adapter
  (`batch3/tools/normalize.py`) — all documented in the batch findings files.
- Contract: `research/bangkok/editorial/2026-11-05-handoff/HANDOFF.md`
  (receiver-amended 2026-11-07)
- Prior researcher verification: pilot `review/REVIEW-2026-11-07.md`; batch 2–4
  `review/findings.md` — read for what was already checked and accepted; do not
  re-litigate documented P2 residuals.

## 0. Mechanical gates (run first — should all pass)

```
K=research/bangkok/editorial/kit
python3 $K/validate.py --batch-dir <batch>        # expect ALL OK (both batches)
python3 $K/audit.py    --batch-dir <batch>        # pilot: 5 P2; batch2: 15 P2 — all documented snippet-source usage
python3 $K/check_geometry.py --file <points.json> # spot-check §2 items yourself
shasum -a 256 app/src/data/bangkok/*.json packages/schema/constants.json   # vs source-manifest.json
git status --short                                 # app/scoring data untouched
```

## 1. Reviewer checklist (per bundle)

1. **Identity/geography** — key, kind, name, catchment vs khet semantics in
   `scope_notes` matches `00-overview.md`; boundary claims consistent with the
   polygon checks recorded in the batch findings.
2. **Source quality/recency** — ≥3 publisher families; tourism/property
   sources labeled; dates recorded or null (never invented); volatile claims
   carry `recheck_by`.
3. **Claim support** — every claim's evidence locator actually points at the
   source section; paraphrase not quotation; no claim rests solely on a
   `body_read: false` source.
4. **Contradictions** — `conflicting` question statuses and `conflicted`
   claim labels read as honest gaps, not smoothed-over.
5. **Copy** — preview/lead concrete and claim-linked; banned words absent; no
   radius-derived walking durations; no pretended walking.

Sign-off mechanics: set `review.reviewer`, `review.reviewed_at`,
`review.status: approved` per bundle (or `blocked` with findings). Numeric
scores are NOT part of this review — score questions route to the pipeline
review (see `research/bangkok/notes/2026-11-07-editorial-batch-pipeline-followups-crtky130.md`).

## 2. Highest-stakes claims — verify these first (~45–60 min)

| Claim | Where | How to verify |
|---|---|---|
| Sala Daeng/Patpong are **outside** the chong-nonsi catchment (corrected F1) | pilot `profiles/st.chong-nonsi.json` c03 + scope_notes | `check_geometry.py --entity chong-nonsi --point 13.7285083 100.5341333` → expect `in_polygon=False` |
| Benjakitti's north band **is** inside the asok catchment (~457 m edge) | pilot `asok-c04`, `asok-c18` | `check_geometry.py --entity asok --point 13.7325 100.5605` → expect `True` |
| Green 10 not reproducible from nana's polygon (1.4 ha unidentified) | batch2 `st.nana.json` `nana-c14` + Q09 | read claim + try to name the park yourself (Overpass blocked for us too) |
| Bumrungrad **straddles** nana's boundary | batch2 `nana-c09` | `check_geometry.py --entity nana --point 13.7440 100.5540` (expect True) and `--point 13.7463 100.5526` (expect False) |
| Gold Line never crosses the river; transport 10 rests on piers+buses | batch2 `charoen-nakhon` c01/c02 + scope_notes | Wikipedia Gold Line (3 stations, 1.74–1.8 km) + `00-overview.md` transport row |
| BTS Phaya Thai + ARL are **outside** the phaya-thai khet | batch2 `phaya-thai-c05` (conflicted) | `check_geometry.py --entity phaya-thai --point 13.76 100.547` → expect `False`; note Victory Monument polygon conflict is deliberately open |
| Hua Lamphong lost long-distance rail 2023-01-19 | pilot `samphanthawong` rail claims | Wikipedia Hua Lamphong |
| Chong Nonsi canal park: 200 m opened 2021-12-25 of a 4.5 km plan | batch2/pilot `chong-nonsi-c06` | Wikipedia Chong Nonsi Canal Park |
| Asok footpath rebuild announced 2025-03-16/18 | pilot `asok-c10` | thethaiger.com article (URL in bundle sources) |
| Wat Mangkon Kamalawat inside wat-mangkon catchment (~54 m) | batch2 `wat-mangkon` + A8 note | `check_geometry.py --entity wat-mangkon --point 13.7419 100.5103` → expect `True`; confirm you do **not** "fix" the pilot's khet note |
| Pom-prap 2-bed editorial 24,000 below all observed asks | batch2 pom-prap rent claims + backlog CRTKY-141 note | HipFlat page (URL in bundle); treat as pipeline item, not a copy fix |
| Time Out anchors (dates/authors) | pilot thong-lo/ari bundles | timeout.com URLs in bundle sources; 2026-05-14 Thonglor / 2026-05-30 Ari |

## 3. Accepted residuals (documented — do not re-open without new evidence)

- Overpass unavailable: mapped park hectares unidentified (nana 1.4 ha,
  ratchathewi 1.0 ha, wat-mangkon 0.5 ha, charoen-nakhon 0.8 ha; phaya-thai
  14.8 ha undecomposed) — pipeline item, not a bundle fix.
- Snippet-only sources used as corroboration only, each flagged on the source
  record; no claim rests solely on one (machine-verified).
- Conflicting-by-design: Soi 38 night market status; Silom Walking Street
  schedule; Victory Monument khet attribution; Wat Ratchanatdaram khet;
  ICS opening month; Gold Line fare; Nana Plaza bar count/hours; Princess
  Mother Memorial Park location.
- Resident-voice thinner than ideal (Reddit/TripAdvisor 403) — noted in
  bundle review notes.

## 3a. 2026-11-08 canonicalization — what changed after the batches closed (B-10/G21)

Before you review, read [`../2026-11-08-canonical-relabel.md`](../2026-11-08-canonical-relabel.md).
Two machine passes edited bundles in place on 2026-11-08, both logged and
gated (`validate` ALL OK ×5; `audit` zero P1):

1. **Corroboration relabel under canonical publisher families.** 23 claims
   moved `corroborated → proposed` (mostly EN+TH Wikipedia pairs; full list in
   `../2026-11-08-canonical-relabel-log.jsonl`). Corpus counts are now
   **399 corroborated / 228 proposed / 40 conflicted**. If you reviewed
   earlier snapshots, statuses may differ — the canonical rule set is the
   authoritative one.
2. **71 batch-4 limitations arrays repaired** (a normalize bug had exploded
   them into single characters; reconstructions verified byte-exact against
   raw/). Spot-check a few batch-4 claims' `limitations` against their cited
   sources during your pass.
3. `wat-mangkon-c06` now carries structured `conflicts_with` links to
   c02/c04 (the only intra-bundle claim-vs-claim contradiction; source-level
   conflicts remain inside single claims by design).
4. Every manifest now carries `research_started_at`/`research_completed_at`
   (mtime-derived) and a `canonical_family_relabel` stamp; the tail batch
   gained the manifest it was missing.
5. **Same-day gate verification** ([`../2026-11-08-gate-verification.md`](../2026-11-08-gate-verification.md)):
   the schema half of `kit/validate.py` had been silently discarding errors —
   after the fix, a logged contract-repair pass made all bundles conform for
   real: URL-field annotations split to `limitations` (sam-yan's four
   Overpass records merged into one session record, annotations preserved),
   null `notes` coerced, boolean `commercial_context` normalized,
   `uncertainties` dicts flattened. Also: C-6 wave 1 flagged **4 dead URLs**
   as archived-citation status (source-record limitations). Reviewers should
   treat those limitation lines as machine-generated provenance notes, not
   researcher claims.


## 4. After the review

- Approved bundles → the integration adapter proposal (small localized
  preview index; full narrative/evidence on demand) — separate reviewed change.
- Batch 3 may dispatch once every pilot + batch-2 bundle is approved.
- Translations and image rights remain separate gates.
