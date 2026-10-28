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
running on :3000 it is reused (locally); in CI a fresh one is started. Set
`E2E_PORT` to an available port to run alongside another local server.

## What's covered

`smoke.spec.ts` verifies the core flows return HTTP 200 and render a
key piece of content:

- Homepage `/` — Leaflet map container mounts
- Station detail `/station/shibuya` — station name renders
- Methodology `/methodology` — heading renders
- Japanese locale `/ja` — localized title renders
- Bangkok map `/bangkok` — 50 district polygons + city switcher state
- District detail `/bangkok/district/watthana` — heading and rail stations
- Bangkok district tooltips render in Leaflet's tooltip pane (above the polygons)
- Bangkok levels of detail — Stations (133 areas) and the 200 m grid (canvas, Best spots, top-5 pins)
- A grid cell click opens its popup (`?lv=grid&s=cell.N`)
- Station-area page `/bangkok/station/asok` — heading, next stops, translated radar legend
- District page radar legend is real copy, not a message key
- City switch — weights carry over from Tokyo, yen filters do not
- Canvas marker selection, desktop popup and district navigation; touch zoom
  retains the selected station at tablet width (`map-interactions.spec.ts`).
  At phone width the selected station card currently covers the zoom control;
  this test does not claim that control is accessible there.

Intentionally **not** covered here:

- **Visual regression** — handled by the `flyto-visual-test` skill.
- **Performance capture** — handled by the `perf-capture` skill.

## CI

The `e2e` job installs Chromium and runs `map-interactions.spec.ts` against a
fresh dev server with retries disabled. Its failure fails the CI check; branch
protection must also require the `e2e` status for it to gate merging.
