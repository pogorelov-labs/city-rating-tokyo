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
- **Normalization is logged, not silent** — `assemble.py` prints a counts
  summary; `audit.py` recomputes corroboration/refs/banned-words/walk-time
  independently. P1 = fix before review; P2 = document in findings.

## Files

| File | Purpose |
|---|---|
| `scaffold.py` | create a unique batch skeleton + `batch.json` template (prefills scores from the handoff's `priority-seed.json` when given) |
| `agent-prompt-template.md` | per-entity subagent prompt with placeholders (embeds the enum contract, leads-are-hypotheses, access limits) |
| `check_geometry.py` | point-in-polygon + haversine against the app polygons (single point, `--file` batches, `--info`) |
| `assemble.py` | normalize raw agent JSON → schema bundles; driven by `batch.json`; logs every normalization; writes `search-log.jsonl` + `manifest.json` |
| `validate.py` | Draft-2020-12-subset schema validation + semantic reference closure → must print `ALL OK` |
| `audit.py` | independent recomputation audit (source IDs, corroboration, body-read reliance, dates, banned words, radius→time, ref closure, checks honesty) |
| `briefs.py` | derived markdown briefs from profiles |

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
