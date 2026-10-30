# Bangkok map

Bangkok uses MapLibre GL JS for its default map. Leaflet remains the standard
map option and automatic fallback; Tokyo continues to use Leaflet. Both Bangkok
renderers consume the same scoring, filtering, selected-area, comparison and URL
state. Changing renderer does not reset that state.

## Rendering

- District and station-area geometry is installed once in native vector layers.
  Stable promoted IDs connect score, hover, selection and comparison state to
  rendered features. Paint updates skip unchanged values.
- The 200 m grid is one 330 × 257 RGBA texture over a fixed Mercator strip mesh.
  Camera movement changes transform/opacity uniforms without scoring or texture
  uploads. Coordinates use a local origin to preserve precision at street zoom.
- Buildings use opaque extrusion geometry. Parks, grass, water and park names
  come from the existing vector tiles. Geographic colors stay muted while scores
  keep their established palette.
- React renders controls and detail cards. MapLibre owns map geometry, label
  collision, camera animation and picking. The mobile cell card computes only
  its selected score.

The decoded grid and a small number of recent score/filter results are shared
between consumers. The renderer releases its map, WebGL resources, listeners
and observers when unmounted. A recoverable graphics-context loss rebuilds map
resources and state; an unsuccessful recovery falls back to the standard map.

## Build and recovery

Use Node 20 and the committed npm lockfile. `predev` and `prebuild` copy the worker
from the pinned MapLibre dependency to the versioned `/map-assets/` path. That
worker is a generated build asset and must be included in the deployed public
files. The dependency's full license notices are copied alongside it at the
versioned `maplibre-gl-license-<version>.txt` path. App documents and the worker response allow the map-data provider through
CSP so client-side city navigation works without a reload. Tokyo does not request
that provider until Bangkok is opened. The provider is not allowed as a script
origin, and production `eval` remains disabled.

```sh
cd app
npm ci
npm run build
npm run prepare:standalone
PORT=3000 HOSTNAME=127.0.0.1 npm run start:standalone
```

The standalone output is rooted in `app/`, matching the production build context.
`prepare:standalone` makes the same public/static copies as the Dockerfile.
English paths have no locale prefix. `skipProxyUrlNormalize` preserves the origin
of their internal locale rewrites when the standalone bind address differs from
the proxy worker's normalized hostname. The runtime suite exercises ordinary,
localized and client navigation paths; retain those checks on Next.js upgrades.

`BANGKOK_MAP_RENDERER=leaflet` selects the standard-map default **at build time**.
For an image build, pass the corresponding build argument. Changing this variable
only after static pages have been built does not change their default renderer.
Visitors can still choose either map. No database migration or rating rebuild is
part of this release.

Initialization or rendering failures preserve the shared state while offering
the standard map. A failed code download disables the 3D choice for that page
load; a new page load retries the download. Temporary individual tile failures
do not reset the camera or change the user's preferences.

## Diagnostics

Comparison routes require `BANGKOK_RENDERER_LAB=1`; leave it unset or `0` for a
release build. The routes are excluded from the sitemap and are not indexed.
Only those lab views expose renderer and profiling globals. Production routes
do not expose them, including after navigation out of a lab view.

Visit `/bangkok/prototype/maplibre?lv=grid&profile=1` for the bounded local
profiler. React subtree timings require `next build --profile`. Profiling starts
after a lab owner mounts, so computations before that effect are not captured.
CPU elapsed time, asynchronous source completion and GPU queries are separate
measurements and must not be added as if they were exclusive costs. The GPU
adapter is version-guarded; it disables itself until reviewed after an upgrade.

```sh
node scripts/profile-bangkok-rendering.mjs --samples 3 --output .release-checks/stages.json
node scripts/benchmark-bangkok-renderers.mjs --samples 3 --output .release-checks/renderers.json
```

Use an ordinary production build without profiling for user-facing timing checks.
RAF cadence is not GPU-presented FPS; page heap excludes worker/GPU memory.
Layer ablations estimate incremental work and are not additive. Raw local traces,
screenshots and process measurements stay outside the published source.

## Verification

The browser suite covers the production route in all three locales, standard-map
compatibility, rendered parks and selections, filters/shared links, pointer and
touch behavior, failure fallback and worker/CSP delivery. CI uses a software GPU
for functional WebGL coverage, not performance claims. Real-device validation is
still useful before changing the default quality budget for slower phones.

Building detail and the availability of remote basemap tiles depend on the data
provider. Scores retain their own published source dates and confidence labels;
basemap refreshes do not regenerate the rating dataset.
