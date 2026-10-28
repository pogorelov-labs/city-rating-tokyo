# Contributing to City Rating

A short guide for humans and AI agents working on this codebase. Read this before making changes.

## Architecture in one paragraph

City Rating covers **1,493 Greater Tokyo stations** and Bangkok's **50 districts, 133 station areas and 39,149 grid cells** at **200 m**, with **179 rail stations / 10 lines**. Both cities share **10 rating categories** and **EN/JA/RU**. The Next.js frontend (`app/`) renders from committed JSON and `demo-ratings.ts`. Tokyo's Python pipeline (`scripts/`) reads/writes the configured datastore; Bangkok has a separate acquisition/offline-build pipeline (`scripts/bangkok/`). The MCP service (`mcp/`) currently exposes Tokyo through a datamart and semantic search. See [fresh-clone setup and prerequisites](README.md#getting-started). Production deployment is automated from `main`; deployment details are maintained outside this public repository.

## The three scoring copies (and the schema package)

Scoring logic exists in three places:
1. **`app/src/lib/scoring.ts`** — TypeScript, frontend runtime (composite scores, colors, dealbreaker filtering)
2. **`scripts/compute-ratings.py`** — Python, offline pipeline (log-percentile normalization, rent regression, absolute caps)
3. **`mcp/src/city_rating_mcp/scoring.py`** — Python, MCP runtime (composite scores + dealbreaker filtering, a hand-maintained mirror of the TS)

The frontend shares named-area results through [scoring-react.tsx](app/src/lib/scoring-react.tsx)
and adapts the resident-weighted Bangkok grid through [scoring-grid-react.ts](app/src/lib/scoring-grid-react.ts).
The homepage provider shares results across the map and responsive panels;
these adapters reuse the pure scoring contracts rather than defining another
normalization policy. See the [current module map](CLAUDE.md#key-files) for map
controllers and the shared area-card/detail family.

The shared constants (`RENT_FLOOR`, `RENT_CEILING`, `RATING_KEYS`, `DEFAULT_WEIGHTS`, `DEFAULT_FILTERS`, `ABSOLUTE_CAPS`) live in **`packages/schema/`** — a single source of truth with codegen for TS and Python. If you change a constant, change it in `packages/schema/constants.json` and re-run `npm run gen`.

### Load-bearing invariants (breaking these silently corrupts data or URLs)

1. **`RATING_KEYS` order is positional.** The URL `?w=` param encodes weights as a comma-separated positional list in `RATING_KEYS` order. **Never reorder, alphabetize, or sort this array.** The `LEGACY_WEIGHT_KEYS` constant exists for backwards-compatible decoding of old URLs — never delete it.

2. **`RENT_FLOOR` / `RENT_CEILING` appear in 3 languages.** They MUST agree across `scoring.ts`, `compute-ratings.py`, and `mcp/scoring.py`. The schema package enforces this; do not re-introduce local copies.

3. **`1k_1ldk` and `2ldk` are digit-prefixed JSON keys.** Pydantic models use `Field(alias="1k_1ldk")` with `populate_by_name=True`. TypeScript uses quoted string-literal keys. Never rename these to `k1_1ldk` or similar — they match the NocoDB / Suumo / e-Stat data shape.

4. **`DEFAULT_WEIGHTS` keys must be in `RATING_KEYS` order.** JSON object key order is preserved by spec and by every parser here, but `json.dumps(sort_keys=True)` would break it. The codegen uses `sort_keys=False`; do not "clean up" the JSON by sorting.

5. **The embeddings rebuild is a hidden coupling.** `scripts/build-embeddings.py` reads `app/src/data/generated-descriptions.json` and produces `data/embeddings.npz` for the production deployment environment. Any change to descriptions invalidates the embeddings — re-run `build-embeddings.py` and supply the regenerated `.npz` through the private operational environment. Delivery instructions are maintained outside this public repository.

6. **Nothing the app imports can live outside `app/`.** The Next.js build context is `app/` (per `app/Dockerfile`, `app/.dockerignore`). Any import that resolves to `../packages/...` or similar escapes the context and breaks the production build — local builds pass (file exists on disk) but prod fails. This bit `slug-redirects.json` (PR #86) and the schema package's tsconfig alias (caught in review before merge). The codegen dual-emits the schema TS into `app/src/lib/schema/` specifically to stay in-context. If you add a new cross-package import, vendor it or change the build context — don't use a tsconfig path alias that escapes `app/`.

7. **CI status check is named `build`.** The required check on `main` is `build` (the job name in `ci.yml`). If you rename the job or restructure the workflow, you MUST register the new check name in GitHub branch protection before merging, or every PR will be blocked.

8. **`main` deploys to production on merge.** Production deployment is automated from `main`. Every merge triggers a production build of both cities' pages. Verify the scope before merging; page totals are build output, not a fixed project invariant.

## URL state backcompat

`app/src/lib/url-state.ts` encodes/decodes filter state to URL params. The decoder sniffs 9-value vs 10-value weight arrays:
- **9 values** → `LEGACY_WEIGHT_KEYS` (old pre-reorder order, daily_essentials defaulted)
- **10 values** → `WEIGHT_KEYS` (current life-first order)

Do not "improve" this sniff to be smarter — old shared URLs depend on the exact length-based discrimination. The comment at `url-state.ts:72-74` notes a known ambiguity (10-value URLs from a brief transition window) that is deliberately left as-is.

## Public repository and changelog rules

- This repository is public. Do not add internal infrastructure or deployment
  details: host/service names, deployment platform, host, container, or
  orchestrator names, network topology, private URLs, credentials,
  worker/session identifiers, CI run IDs, or internal QA artifacts.
- Changelog and release notes are user-facing: what changed, compatibility,
  and user-impacting limitations. Do not paste hashes, manifests, gate lists,
  or engineering receipts; put technical evidence in a research note or the PR
  body and link it.
- Release notes in `docs/releases/<tag>.md` follow the same rules.

## Releases

Follow the [release runbook](docs/RELEASING.md): update the changelog and release
notes, pass `build`, `schema`, `mcp` and `bangkok` on both the PR and main merge
commit, then publish an annotated version tag and GitHub release when release
publication is authorized. v0.1.0 was the first release; v0.1.1 packages the
separately merged Bangkok refresh. Release version bumps update the app package
and lockfile together. Data refreshes require a separate PR; code/docs work
does not imply regeneration. See the [completed Bangkok remediation record](docs/DATA_REFRESH_REMEDIATION.md).

## Tickets and verification

### Before implementation

Use the canonical ticket description to state the problem, context and accepted
scope. Include observable **Done when:** criteria and how each will be checked.
For a legacy one-line ticket, establish these before implementing; do not infer
permission for source acquisition, publication or operator actions from a title.

```text
Problem: What is wrong or missing, and for whom?
Context / accepted scope: Relevant evidence and decisions; included/excluded work.
Done when:
- Observable result and the check that demonstrates it.
- Required compatibility, data-quality or publication constraints still hold.
Verification plan: Tests, source comparison or UI/production checks needed for this scope.
```

Update the description when an accepted decision changes scope, and preserve
the prior decision/history through links. Implementation notes and verification
comments supplement that description; they do not silently override it.

### Verification before Done

Add a comment recording what was actually checked. A small change can use three
lines; larger work should map evidence to each acceptance criterion:

```text
Scope/result: What shipped; PR and tested commit; merge reference if merged.
Checks: Commands or observed behavior and actual results; CI/evidence links; live/rollout status.
Limits/follow-ups: What was not checked or remains blocked; linked tail, owner/action and reopen condition.
```

Identify skipped, failed, not-required and unverified checks explicitly. Only
claim production behavior when it was observed; a docs-only task can record
production checks as not required. CI passing, a merge, a published release and
an operator activation are separate facts. Read the current CI workflow and
record required and advisory check results separately. Keep technical evidence in the PR
or tracker record and apply the public-copy rules to repository documents.

### Scope splits and blocked follow-ups

If an accepted shipped slice is complete but the original task also contains
blocked work, record the accepted scope change in the parent description and
link a follow-up for every remaining requirement before closing that slice.
The follow-up keeps the unmet criterion, blocker, required owner/action,
verification plan and reopen condition. Source access, publication rights or
rollout requirements stay unmet until separately verified. A blocked tail's
definition is not evidence that its implementation has run.

Use **Todo** for accepted, next-up work when useful; **Backlog** may hold work
awaiting acceptance or a named unblock condition. **In Progress** means active
work. **Done** requires the accepted criteria and a verification record;
**Cancelled** requires a recorded decision. There is no need to move unrelated
tickets merely to adopt this convention.

### Draft PR triage

At a status review, inspect open drafts. A draft older than **14 days** must
have a dated decision comment: **merge**, **close**, or **blocked**. A blocked
decision names the responsible owner/action and condition for revisiting it.
Confirm the current PR state first: for an already merged or closed PR, record
that outcome and its link in the ticket instead of reopening or re-triaging it.
Age alone does not authorize merging or closing; required checks, review and
current publishing authorization still apply.

## Pipeline refresh workflow

```bash
# Full refresh: scrape → compute → export → build → commit → push
scripts/refresh-ratings.sh

# Dry run (no writes, no commit)
scripts/refresh-ratings.sh --dry-run

# Force push to main (requires admin bypass — branch protection normally blocks)
scripts/refresh-ratings.sh --push --force-main
```

`refresh-ratings.sh` now exits non-zero if any station lacks a computed rating (`missing_count > 0`), unless `export-ratings.py` is called directly with `--allow-missing`. This prevents partial exports from shipping silently.

Scrapers run in a private operational environment. They are incremental and safe to restart. Access and execution instructions are maintained outside this public repository.

## Testing

- **ESLint** (`cd app && npm run lint`): Next.js + TypeScript + React hooks / React Compiler rules. Runs in CI's `build` job; errors fail it, warnings don't
- **Vitest** (`cd app && npm test`): scoring pure functions, URL state round-trip, dealbreaker filtering
- **pytest** (`pytest` from repo root): `compute-ratings.py` normalization/caps, cross-language schema parity
- **Playwright**: the advisory `e2e` CI job runs the browser smoke suite. See [e2e/README.md](e2e/README.md) for local setup and the current CI selection.

## MCP server development

Use Python 3.11 or newer. The shared schema must be on `PYTHONPATH`, as in CI.
Run these commands from the repository root:

```bash
cd mcp && pip install -e ".[dev]"
ruff check src/
PYTHONPATH=../packages/schema/python pytest tests/ -q

# Smoke test (requires datamart + embeddings — deploy-time check, not CI)
python scripts/smoke-test.py
```

`mcp/Dockerfile` copies `packages/schema/python` and sets `PYTHONPATH` so the MCP runtime imports `city_rating_schema` (the shared constants). Production runtime settings are maintained outside this public repository.

## Branch protection on `main`

- Requires the `build` status check (CI: `npm run lint` + `tsc --noEmit` + `npm run build` + `npm audit` + now MCP `ruff`/`pytest`)
- No force-push, no deletion (admin bypass available for emergencies)
- No PR review enforcement (merging is convention, not API-enforced) — be disciplined

## When you change scoring constants

1. Edit `packages/schema/constants.json`
2. `cd packages/schema && npm run gen`
3. Verify `git diff` shows only the expected generated changes in `packages/schema/ts/`, `packages/schema/python/`, AND `app/src/lib/schema/` (the codegen dual-emits to keep the vendored copy inside the app's build context)
4. Run `cd app && npm test` and `pytest` — the unit tests guard the URL-backcompat invariant and scoring edge cases. The cross-language parity test (`scripts/test_schema_parity.py`) parses the actual generated TS from `app/src/lib/schema/constants.ts` and compares every value against the Python `city_rating_schema` package, so it catches real drift across languages. Both the parity test and the codegen drift gate (`npm run gen && git diff --exit-code`) run in CI (the `schema` job).

**Codegen drift gate:** CI's `schema` job asserts that `npm run gen` produces no uncommitted changes. If you edit `constants.json` without running `gen`, or hand-edit a generated file, CI fails. Always edit the JSON source and re-run `gen`.
