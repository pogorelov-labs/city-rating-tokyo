# Component and locale contracts

`npm run test` runs both Vitest projects (including in the existing CI build job):

- `node`: `src/**/*.test.ts`, preserving the existing Node environment.
- `components`: `src/**/*.test.tsx`, jsdom with explicit RTL cleanup and jest-dom matchers.

Run one environment with `npm run test -- --project components` or `--project node`.
The added dev dependencies are pinned to releases supporting CI Node 20; newer
jsdom and jest-dom majors/minors have raised their minimum Node version.

Component suites use the real city store and next-intl provider. Animation-frame
callbacks are controlled independently from fake timers to reproduce throttled-tab
races. Leaflet and grid downloads are outside these component contracts. jsdom
checks DOM/state behavior, not browser layout, paint or actual CSS animation.

`i18n/messages.test.ts` compares every namespace/leaf in EN, JA and RU, including
missing, extra and wrong-shaped entries. New namespaces are included automatically.
EN messages and `routing.locales` define next-intl's `AppConfig`; CI's `tsc` also
checks `i18n/type-contract.ts` negative assertions. Keep dynamic key lists literal
(`as const`) and narrow route locale strings with `hasLocale`. External source/hub
IDs go through the guarded `dataLabel` boundary and retain unknown-ID fallbacks.

CRTKY-158's one-off negative CI experiment is recorded in the PR validation notes:
a temporary incorrect drawer assertion must fail `npm run test` in CI, then a
normal follow-up commit restores it. No permanently failing probe is retained.
