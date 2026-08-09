# End-to-end tests (Playwright)

This directory holds the city-rating Playwright smoke suite. The harness is
rooted at the repo root (`package.json`, `playwright.config.ts`) even though
the app under test lives under `./app`, because the e2e tests are a
repo-level concern rather than something the Next.js app should ship in its
own bundle.

## Running locally

From the repo root:

```bash
# one-time: install the chromium binary Playwright drives
npx playwright install chromium

# start the dev server, run the suite, tear the server down
npm run test:e2e

# interactive UI mode (watch + step-through)
npm run test:e2e:ui
```

`npm run test:e2e` boots `next dev` on port 3000 automatically via the
`webServer` block in `playwright.config.ts`. If a dev server is already
running on :3000 it is reused (locally); in CI a fresh one is started.

## What's covered

`smoke.spec.ts` verifies the four core flows return HTTP 200 and render a
key piece of content:

- Homepage `/` — Leaflet map container mounts
- Station detail `/station/shibuya` — station name renders
- Methodology `/methodology` — heading renders
- Japanese locale `/ja` — localized title renders

Intentionally **not** covered here:

- **Visual regression** — handled by the `flyto-visual-test` skill.
- **Performance capture** — handled by the `perf-capture` skill.

## Why not CI?

These tests require a running dev server, which is heavier than the value
the smoke check adds on every push. They are intended as a **pre-deploy
gate**: run `npm run test:e2e` locally before shipping. If we later want
them in CI we can add a dedicated workflow (separate from the existing
lint/build job) that brings the server up inside the runner.
