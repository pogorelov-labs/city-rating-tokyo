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
running on :3000 it is reused locally. CI builds the release artifact and starts
its standalone server; it does not use the development server. Set
`E2E_PORT` to an available port to run alongside another local server.

To check an already running production build, set its URL explicitly. The
harness then uses that server and does not start or stop one:

```bash
E2E_PRODUCTION=1 PLAYWRIGHT_BASE_URL=http://localhost:3011 npm run test:e2e
```

With a prepared standalone build, `E2E_PRODUCTION=1 npm run test:e2e` lets the
harness start and stop the production server itself. Copy `app/public` into
`app/.next/standalone/public` and `app/.next/static` into
`app/.next/standalone/.next/static` first, as CI does.

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
- Station and district guides — comparison plot/table, commute bars, geographic
  scope and expandable local facts
- All three guide types in EN/JA/RU, including category evidence and rent sources
- Destination, comparison and custom weights survive locale switching
- Automated accessibility checks on the redesigned guide surfaces
- City switch — weights carry over from Tokyo, yen filters do not
- Canvas marker selection, desktop popup and district navigation; touch zoom
  retains the selected station at tablet width (`map-interactions.spec.ts`).
- Phone-width selected-area cards, zoom and Close controls, including the
  short phone viewport and expanded air panel.

Intentionally **not** covered here:

- **Visual regression** — handled by the `flyto-visual-test` skill.
- **Field performance** — local lab checks capture LCP and layout shifts;
  they do not measure INP or field percentiles.

## CI

The `e2e` job installs Chromium, builds the normal app with the lab disabled,
packages its public/static assets, and runs the full suite against the
standalone server with retries disabled. CI uses software WebGL for functional
coverage, not performance measurements. Its failure fails the CI check; branch
protection must also require the `e2e` status for it to gate merging.

## Bangkok renderer release checks

The default suite exercises Bangkok's 3D map and its standard-map fallback,
including locale controls, selection, sharing, accessibility controls and
failure recovery. Leaflet-specific interactions explicitly select the standard
map; Tokyo continues to use Leaflet. The normal configuration excludes the
renderer lab tests.

For an existing server, `E2E_BASE_URL` is also supported as an alternative to
`PLAYWRIGHT_BASE_URL`; the harness will not launch a server. Set `E2E_PRODUCTION=1` to include
production-only worker and security-header checks. For example:

```sh
E2E_PRODUCTION=1 E2E_BASE_URL=http://localhost:3170 npx playwright test
```

The renderer lab is opt-in. Run its separate configuration with a server built
or started with `BANGKOK_RENDERER_LAB=1`; without `E2E_BASE_URL` the configuration
starts a local dev server with that setting:

```sh
npx playwright test --config=playwright.prototype.config.ts
```

The lab's diagnostics are intentionally unavailable on production routes.
Playwright's generated reports and failure artifacts belong in ignored paths.

CI also starts a separate opt-in lab server after the normal release suite. This
checks graphics-context replay and that diagnostic state is removed when leaving
the lab; those routes remain disabled in the release artifact.
