# Bangkok map motion: experience, rules and quality gates

When a user lets go, the map should continue in the direction they were
moving. When they put a finger back down, the map should stay under it.
Those two moments tell us more about control than the total distance of a
straight flick.

## What the review found

The lab initially showed a glide while the user's open map stopped immediately.
The difference was the device's reduced-motion setting, so we added an explicit
Bangkok-only opt-in rather than changing the OS. A matched demo then proved
that **Smooth** added travel; it did not tell us whether the glide went the
right way, or whether the next touch still meant what the user intended.
These observations came from local Chromium mouse input and emulated touch;
they are reproductions, not field performance statistics.

| Reproduction | Previous behavior | Required result |
| --- | --- | --- |
| Drag 270 CSS px right, then 35 px left, and release on the tilted 3D map | The override coasted 139–140 px right. Native inertia continued 67–70 px left. | Coast left in both paths. No material rightward excursion followed by a correction. |
| Move two fingers in parallel, keeping their separation and angle fixed | Both paths followed the drag, but only the native path coasted. Catching its glide could select a cell. | Both paths coast and can be caught without picking. A pinch or a continued one-finger drag must not inherit the earlier throw. |
| Catch a glide, then tap the **same** spot 75 ms later | The first tap was hidden from picking but still armed double-tap zoom. The second tap zoomed instead of selecting. | The brake is consumed once; the next tap selects and zoom stays fixed. Ordinary double-tap zoom, tap-drag zoom and pinch must still work. |
| Touch and hold a gliding Leaflet map for 220 ms | A landmark continued 79–134 px under the stationary finger. | Stop on contact, not on the next move. Releasing the brake must not click the map; a new tap or drag works. |
| From zoom 14, press `+ + + −` before the first ease ends | Smooth Leaflet zoom ended at 13 instead of 16. | Accumulate from the intended destination, clamp at both limits, and discard that destination on external movement. |
| Open the air panel at a 1280 × 540 viewport | Only 223 px of map height remained. The 2D button sat entirely above the map and was not clickable. | Fold the tools using actual workspace width **and height**. Opening the menu must expose every action inside the workspace. |

After the fixes we replayed the review inputs as well as running the new
regressions. All six mouse-reversal traces finished left (three per device
policy). All five Leaflet catches showed zero additional pixels during the
hold. All three quick, same-place follow-up taps selected a cell at unchanged
zoom, and every in-range Leaflet zoom burst finished at 16. The wide/short
layout check also caught Leaflet's vertical zoom controls under the renderer
selector; both engines now use the available bottom row in that layout. Travel distance
varied with event timing; direction, ownership and the intended endpoint are
the durable requirements.

## Animation rules

- **Direct manipulation first.** Let the renderer handle drag, projection,
  constraints and animation. At release, pass one bounded displacement to the
  camera. Do not start a second animation loop, put continuous pointer updates
  into React or the city store, rescore areas, or upload new grid pixels.
- **Estimate the last deliberate movement.** Measure a short trailing interval
  in CSS pixels and include the pause before release. Discard old samples on a
  reversal. Track a two-finger translation by its centroid and contact IDs.
  Separate near-simultaneous lifts from lifting a finger and continuing to move.
  A held release, cancelled touch, changed contact set, pinch, pitch, or rotation
  must not reuse stale pan velocity.
- **Give the new contact ownership.** Braking is neither a pick nor the first
  tap of a zoom sequence. Restore recognizers for the next distinct contact,
  including a second finger added for a pinch. Cancel pending frames, timers
  and listeners on teardown. Keep normal map taps and ordinary double taps.
- **Respect the motion choice.** Follow device is the default. Only an explicit
  Smooth choice for Bangkok can override device reduced motion for its camera.
  Do not change OS preferences, the library-wide motion setting, Tokyo, drawer
  animations or shared URLs. Returning to Follow device must work without
  rebuilding the map.
- **Bound travel, not intent.** The pan constants live in
  [map-motion.ts](../app/src/lib/map-motion.ts). At the speed cap the 3D
  calculation requests about 458 ms and 378 CSS px of constant deceleration;
  Leaflet's native curve requests about 458 ms and 189 px. A viewport or a
  geographic bound may shorten travel. These are caps, not desired distances
  for every flick. Likewise, constrain a zoom destination on every button press,
  rather than applying all presses to an unfinished rendered frame.

## Automated gates

Use one worker and zero retries. Exercise both the normal and device-reduced
paths, including an explicit Smooth opt-in. A skipped case, a missing lab
route, or an unclassified input is not a pass.

Establish the precondition in the browser: wait for the map to settle, capture
the landmark at release, and see it move **before** sending a braking contact.
A driver round trip can miss a short coast. A test that catches an already
stationary map proves nothing. For a follow-up tap, use the same coordinates
and the stated delay; moving away or waiting out double-tap recognition hides
the bug. Keep failed traces instead of using retries as evidence.

| Gate | Observable pass condition | Regression suite |
| --- | --- | --- |
| Direction and contact identity | Reversal has a negative signed coast (more than 2 px left); no observed frame goes 2 px right of release. Holding still does not launch a coast. Translation, partial lifts, continued movement and pinches are separate cases. | [Velocity and contact tests](../e2e/bangkok-release-velocity.lab.spec.ts), [estimator tests](../app/src/components/bangkok/maplibre/pan-velocity.test.ts) |
| Braking and re-entry | The held landmark stays within sampling tolerance (under 3 CSS px on the 3D map; under 2 px in the Leaflet 220 ms hold). Catching does not pick. A same-position 75 ms follow-up selects without zoom; a later drag, ordinary double tap, tap-drag, pinch and cancellation still work. | [3D tap arbitration](../e2e/bangkok-brake-taps.lab.spec.ts), [Leaflet controls](../e2e/bangkok-leaflet-controls.lab.spec.ts) |
| Zoom intent | The burst from 14 finishes at 16, reversing at a zoom limit works, and an external reset to 12 followed by `+` finishes at 13. | [Leaflet controls](../e2e/bangkok-leaflet-controls.lab.spec.ts), [clamping and cleanup](../app/src/components/bangkok/leaflet-controls.test.tsx), [3D zoom and grid integrity](../e2e/bangkok-prototype.spec.ts) |
| State and cost | Switching the preference does not remount the renderer, change the URL or switch city filters. A camera-only gesture does not rescore the city or upload the grid texture. Follow device with reduced motion has no measurable post-release travel. | [Renderer lab](../e2e/bangkok-prototype.spec.ts), [public motion and filter controls](../e2e/bangkok-controls.spec.ts) |
| Controls fit | At 1280 px wide and 720, 540 and 440 px high, expand the air panel. Check the button’s **hit target** and its bounds before a trial click. The menu may scroll inside a tiny workspace; the page must not scroll to rescue an off-map button. Check short phones, the renderer selector, attribution, zoom, focus and Escape as well. | [Wide, short controls](../e2e/bangkok-camera-layout.spec.ts), [phone and fallback controls](../e2e/bangkok-release.spec.ts) |

From the repository root, with the [documented dependencies](../e2e/README.md)
installed:

```sh
npm --prefix app test
E2E_PORT=3171 npm run test:e2e:lab -- --workers=1 --retries=0
E2E_PRODUCTION=1 E2E_BASE_URL=http://127.0.0.1:3170 npm run test:e2e -- --workers=1 --retries=0
```

The last command expects the [packaged production-mode preview](BANGKOK_MAP.md#build-and-recovery)
with the lab disabled. If a **lab-enabled** server is already running, set
`E2E_BASE_URL` to that server instead of starting another dev process. Full
Chromium runs the lab; software WebGL in CI verifies behavior, not hardware FPS.

To retain the sampled reversal traces for a before/after comparison, use the
JSON reporter as well as the normal progress output:

```sh
E2E_PORT=3171 PLAYWRIGHT_JSON_OUTPUT_FILE=test-results/bangkok-motion.json npm run test:e2e:lab -- --workers=1 --retries=0 --reporter=line,json --grep 'release follows a late reversal'
```

Read the `signed-release` attachments (JSON bodies are base64-encoded in the
Playwright JSON report). Each contains the motion policy, input type, final
displacement, maximum wrong-way excursion and timestamped landmark positions.

## Before making a speed or smoothness claim

1. Compare the same input, renderer, camera, viewport, DPR, grid state and
   device-motion choice. Separate a cold load from a warm street view.
   Record the browser, hardware, display refresh rate and sample count.
2. Inspect the signed landmark trace across release, not just its endpoint.
   The reversal test attaches `signed-release` with per-frame time and screen
   displacement relative to the first frame after release. A distance, a
   screenshot or a single video alone cannot establish velocity continuity.
3. On the physical phone or desktop input device being claimed, run at least
   five warm slow drags, fast flicks, reversals and catches. Record
   input-to-first-visible movement, moving-frame p50/p95, gaps longer than
   two refresh intervals, and catch drift. Our hardware acceptance targets
   are a first response within two display intervals, a moving-frame p95
   within two intervals, and no unexplained warm stall over 100 ms. Two
   intervals are about 33 ms at 60 Hz and 17 ms at 120 Hz. If a target is
   missed, repeat on the published baseline under the same conditions and
   investigate before claiming sign-off. A `requestAnimationFrame` timestamp
   is not proof of a presented GPU frame; use a device performance trace or
   high-speed capture to substantiate input-to-visible latency.
4. Keep functional pass/fail separate from performance sign-off. If hardware
   was not tested, report **physical-device frame pacing unmeasured**. Keep
   captures and raw local traces out of public release copy.
