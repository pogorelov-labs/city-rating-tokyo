# Contributing to City Rating

A short guide for humans and AI agents working on this codebase. Read this before making changes.

## Architecture in one paragraph

1493 Tokyo train stations, 10 rating categories, 3 locales (EN/JA/RU), ~4493 SSG pages. **Next.js 16** frontend (`app/`) renders static pages at build time from `app/src/data/*.json` + `demo-ratings.ts`. A **Python scraper pipeline** (`scripts/`) writes to **NocoDB** (SQLite-backed); `compute-ratings.py` normalizes and writes `computed_ratings`; `export-ratings.py` generates `demo-ratings.ts`. A **FastMCP server** (`mcp/`) exposes the dataset to AI clients via a datamart JSON + semantic search at `city-rating.pogorelov.dev/mcp`. Deployed via **Coolify** (Docker) on a VPS with Traefik path-based routing.

## The three scoring copies (and the schema package)

Scoring logic exists in three places:
1. **`app/src/lib/scoring.ts`** — TypeScript, frontend runtime (composite scores, colors, dealbreaker filtering)
2. **`scripts/compute-ratings.py`** — Python, offline pipeline (log-percentile normalization, rent regression, absolute caps)
3. **`mcp/src/city_rating_mcp/scoring.py`** — Python, MCP runtime (composite scores + dealbreaker filtering, a hand-maintained mirror of the TS)

The shared constants (`RENT_FLOOR`, `RENT_CEILING`, `RATING_KEYS`, `DEFAULT_WEIGHTS`, `DEFAULT_FILTERS`, `ABSOLUTE_CAPS`) live in **`packages/schema/`** — a single source of truth with codegen for TS and Python. If you change a constant, change it in `packages/schema/constants.json` and re-run `npm run gen`.

### Load-bearing invariants (breaking these silently corrupts data or URLs)

1. **`RATING_KEYS` order is positional.** The URL `?w=` param encodes weights as a comma-separated positional list in `RATING_KEYS` order. **Never reorder, alphabetize, or sort this array.** The `LEGACY_WEIGHT_KEYS` constant exists for backwards-compatible decoding of old URLs — never delete it.

2. **`RENT_FLOOR` / `RENT_CEILING` appear in 3 languages.** They MUST agree across `scoring.ts`, `compute-ratings.py`, and `mcp/scoring.py`. The schema package enforces this; do not re-introduce local copies.

3. **`1k_1ldk` and `2ldk` are digit-prefixed JSON keys.** Pydantic models use `Field(alias="1k_1ldk")` with `populate_by_name=True`. TypeScript uses quoted string-literal keys. Never rename these to `k1_1ldk` or similar — they match the NocoDB / Suumo / e-Stat data shape.

4. **`DEFAULT_WEIGHTS` keys must be in `RATING_KEYS` order.** JSON object key order is preserved by spec and by every parser here, but `json.dumps(sort_keys=True)` would break it. The codegen uses `sort_keys=False`; do not "clean up" the JSON by sorting.

5. **The embeddings rebuild is a hidden coupling.** `scripts/build-embeddings.py` reads `app/src/data/generated-descriptions.json` and produces `data/embeddings.npz` (bind-mounted into the MCP container via Coolify). Any change to descriptions invalidates the embeddings — re-run `build-embeddings.py` (~110 min on the VPS) and re-upload the `.npz` to the Coolify persistent volume.

6. **Nothing the app imports can live outside `app/`.** The Next.js Docker build context is `app/` (per `app/Dockerfile`, `app/.dockerignore`). Any import that resolves to `../packages/...` or similar escapes the context and breaks Coolify builds — local builds pass (file exists on disk) but prod fails. This bit `slug-redirects.json` (PR #86) and the schema package's tsconfig alias (caught in review before merge). The codegen dual-emits the schema TS into `app/src/lib/schema/` specifically to stay in-context. If you add a new cross-package import, vendor it or change the build context — don't use a tsconfig path alias that escapes `app/`.

7. **CI status check is named `build`.** The required check on `main` is `build` (the job name in `ci.yml`). If you rename the job or restructure the workflow, you MUST register the new check name in GitHub branch protection before merging, or every PR will be blocked.

8. **`main` deploys to production on merge.** Coolify auto-deploys from `main`. Every merge triggers a production build of a 4493-page site. Do not merge without local verification.

## URL state backcompat

`app/src/lib/url-state.ts` encodes/decodes filter state to URL params. The decoder sniffs 9-value vs 10-value weight arrays:
- **9 values** → `LEGACY_WEIGHT_KEYS` (old pre-reorder order, daily_essentials defaulted)
- **10 values** → `WEIGHT_KEYS` (current life-first order)

Do not "improve" this sniff to be smarter — old shared URLs depend on the exact length-based discrimination. The comment at `url-state.ts:72-74` notes a known ambiguity (10-value URLs from a brief transition window) that is deliberately left as-is.

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

Scrapers run as ad-hoc Docker containers on the VPS (no scheduler yet). They are incremental — safe to restart. See `CLAUDE.md` "Running Scrapers on VPS" for the `docker run` recipes.

## Testing

- **Vitest** (`cd app && npm test`): scoring pure functions, URL state round-trip, dealbreaker filtering
- **pytest** (`pytest` from repo root): `compute-ratings.py` normalization/caps, cross-language schema parity
- **Playwright** (e2e): planned; not yet wired. The `.claude/skills/` (flyto-visual-test, perf-capture, prod-smoke-test) document manual verification flows.

## MCP server development

```bash
cd mcp && pip install -e ".[dev]"
ruff check src/
pytest

# Smoke test (requires datamart + embeddings — deploy-time check, not CI)
python scripts/smoke-test.py
```

The MCP container runs as a non-root user (`mcp`, uid 1001). The Dockerfile copies `packages/schema/python` into the image and sets `PYTHONPATH` so the MCP runtime imports `city_rating_schema` (the shared constants).

## Branch protection on `main`

- Requires the `build` status check (CI: `tsc --noEmit` + `npm run build` + `npm audit` + now MCP `ruff`/`pytest`)
- No force-push, no deletion (admin bypass available for emergencies)
- No PR review enforcement (merging is convention, not API-enforced) — be disciplined

## When you change scoring constants

1. Edit `packages/schema/constants.json`
2. `cd packages/schema && npm run gen`
3. Verify `git diff` shows only the expected generated changes in `packages/schema/ts/`, `packages/schema/python/`, AND `app/src/lib/schema/` (the codegen dual-emits to keep the vendored copy inside the app's Docker build context)
4. Run `cd app && npm test` and `pytest` — the unit tests guard the URL-backcompat invariant and scoring edge cases. The cross-language parity test (`scripts/test_schema_parity.py`) parses the actual generated TS from `app/src/lib/schema/constants.ts` and compares every value against the Python `city_rating_schema` package, so it catches real drift across languages. Both the parity test and the codegen drift gate (`npm run gen && git diff --exit-code`) run in CI (the `schema` job).

**Codegen drift gate:** CI's `schema` job asserts that `npm run gen` produces no uncommitted changes. If you edit `constants.json` without running `gen`, or hand-edit a generated file, CI fails. Always edit the JSON source and re-run `gen`.
