# Bangkok editorial research kit

Shared tooling for the batched place-research workflow defined by
[`HANDOFF.md`](../2026-11-05-handoff/HANDOFF.md) (storage contract, method,
quality gates). Promoted from the pilot/batch-2 tooling on 2026-11-07 after
the review in
[`../2026-11-07-handoff-and-guide-update-review.md`](../2026-11-07-handoff-and-guide-update-review.md).

Standard-library only (no `jsonschema` dependency); every script is
cwd-independent and takes `--batch-dir` where relevant.

## Batch workflow

```
python3 kit/scaffold.py --batch-id 2026-11-07-batch3-zcode-main \
    --entities st.phloen-chit,st.ratchaprarop --seed <priority-seed.json>

# 1. Fill <batch>/batch.json (aliases, scope_notes, selection_rationale) and
#    <batch>/selection.md (three separate axes; axis-1 from raw/coverage-scan.json).
# 2. Dispatch research subagents (≤2 at a time) using
#    kit/agent-prompt-template.md, one per entity, writing raw/<key>.json.
# 3. Coordinator geometry pass BEFORE assembly:
python3 kit/check_geometry.py --file points.json        # boundary claims
python3 kit/raw_fixes-style corrections in raw/*.json   # assertion-guarded edits
# 4. Assemble + gates:
python3 kit/assemble.py  --batch-dir <batch>            # normalizes + logs every change
python3 kit/validate.py  --batch-dir <batch>            # schema subset + semantic refs → must be ALL OK
python3 kit/audit.py     --batch-dir <batch>            # P1s must be fixed; P2s documented
python3 kit/briefs.py    --batch-dir <batch>            # derived views
# 5. Write <batch>/review/findings.md; stop for review.
```

## Conventions the kit enforces (learned in batches 1–2)

- **Unit membership is decided by the app polygons** (`station-geometry.json`,
  `geometry.json`; rings are `[lat, lng]`, station keys unprefixed) — never by
  raw radius. Distances are context, not membership.
- **A rating may include area outside the unit** (green = park ha within 1 km
  of grid points; transport counts bus stops + boat piers; station crowd =
  all-POI density 400 m inverted). A mismatch between rating basis and unit is
  a pipeline question — record the mechanism, don't flag the score.
- **Brief leads are hypotheses.** Contradicting one with evidence is expected,
  valuable output.
- **Snippet-only sources** may corroborate but never be a claim's sole
  evidence, and carry a limitation string on the source record.
- **AI/search-summary provenance is banned** (F-2, standing): no AI answers or
  search summaries as evidence or even corroboration; every citation needs a
  stable https canonical URL (G24).
- **Corroboration is publisher-independent**: computed over canonical families
  (`canonical.py`), so English+Thai Wikipedia or OSM+Overpass never count as
  two publishers. Stored `publisher_family` strings stay raw.
- **Normalization is logged, not silent** — `assemble.py` prints a counts
  summary; `audit.py` recomputes corroboration/refs/banned-words/walk-time
  independently, sweeps user-facing text for injection/HTML (G20), and checks
  limitations integrity. P1 = fix before review; P2 = document in findings.
- **Never re-run `assemble.py` over a closed batch** — raw/ predates the
  coordinator corrections applied to profiles/ after assembly; post-assembly
  edits go through tools like `relabel_canonical.py` (in place, logged).

## Files

| File | Purpose |
|---|---|
| `scaffold.py` | create a unique batch skeleton + `batch.json` template (prefills scores from the handoff's `priority-seed.json` when given) |
| `agent-prompt-template.md` | per-entity subagent prompt with placeholders (embeds the enum contract, leads-are-hypotheses, access limits, F-2 AI-summary ban, conflicts_with rule) |
| `canonical.py` | canonical publisher-family mapping for corroboration independence (B-10/G21): Wikipedia language editions/Wikimedia projects = one family; OSM/Overpass = one; portal casing variants merge; agent-generic buckets never merged |
| `check_geometry.py` | point-in-polygon + haversine against the app polygons (single point, `--file` batches, `--info`, `--khet` to bypass station-key shadowing — B-8) |
| `assemble.py` | normalize raw agent JSON → schema bundles; driven by `batch.json`; logs every normalization; corroboration computed over canonical families; passes through `conflicts_with` (filtered to same-bundle ids); writes `search-log.jsonl` + `manifest.json` |
| `validate.py` | Draft-2020-12-subset schema validation + semantic reference closure incl. `conflicts_with` link integrity → must print `ALL OK`. Schema errors were silently discarded + anyOf didn't roll back failed variants until 2026-11-08 (see `../2026-11-08-gate-verification.md`) — both fixed; schema path pinned in-repo |
| `audit.py` | independent recomputation audit (source IDs, canonical corroboration, body-read reliance, dates, banned words, radius→time, ref closure, checks honesty) + standing **G20** injection/HTML sweep, **G24** URL-scheme/AI-summary checks, limitations-integrity rule |
| `briefs.py` | derived markdown briefs from profiles |
| `tools/relabel_canonical.py` | B-10 one-off pass: canonicalize corroboration labels in closed batches in place (never re-assemble closed batches) |
| `tools/build_source_registry.py` | B-11: build `registry/source-attributions.json` (canonical attribution per canonical URL) |
| `tools/populate_conflicts.py` | B-13: apply reviewer-derived claim↔claim conflict links |
| `tools/manifest_times.py` | B-14: stamp manifests with research start/end (mtime-derived) |
| `tools/contract_repair.py` | 2026-11-08 one-off: make closed bundles schema-conformant (URL annotation splits, null notes, bool commercial_context, dict uncertainties) — logged, idempotent |
| `tools/link_health.py` | C-6/G14: quarterly link-health wave over all canonical URLs (resolution only; dead → archived-citation flags) |
| `tests/` | unit tests (`python3 -m unittest discover -s kit/tests`) — canonical rules, assemble corroboration + normalizations, audit gate behavior |

`registry/source-attributions.json` — 547 canonical URLs → canonical
publisher/title + variants + citing entities; the adapter consults it for
merged citation views. Bundle provenance is never rewritten.

## Batch layout produced

```
<batch>/
  batch.json          # batch metadata + entity table (kit input)
  selection.md        # three axes kept separate (axis 1 = coverage scan)
  manifest.json       # assembled by kit (includes normalization counts)
  search-log.jsonl    # every query incl. rejections and failures
  raw/*.json          # subagent output (post-corrections)
  profiles/*.json     # authoritative bundles, schema-validated
  briefs/*.md         # derived views
  review/findings.md  # batch findings + verification results
```

## Status

`ready_for_review` culture: researcher-filled `checks` assert
"verified by the researcher, machine-checked where possible";
`reviewer`/`reviewed_at` stay null until an independent review passes.
Translation and image-rights gates are separate. Live application data is
never modified by this workflow.
