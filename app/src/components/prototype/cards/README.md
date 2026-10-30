# Area card prototype

Run from `app/`:

```sh
npm run dev -- --port 3010
```

Open `http://localhost:3010/en/prototype/cards`.

- District: `/en/prototype/cards?area=bangkok-district-pathum-wan`
- Compact card: `/en/prototype/cards?area=bangkok-station-asok&view=compact`
- Tokyo: `/en/prototype/cards?area=tokyo-kichijoji`

## Question

Can a shared station/district guide make the place, cost, selected commute and
trade-offs clear before the user has to interpret the full score breakdown?

Expected observation: a user can identify the rent cohort and estimate status,
choose a destination, distinguish an area's score from the appropriate city and
level reference, and see the geographic scope without opening methodology text.

## Scope

Nine real examples: Kichijoji, Nakano, Shinjuku; Asok, Ari, Phrom Phong; Pathum Wan,
Sathon and Bang Na. English copy is edited from existing descriptions and facts.
All numeric values come from the existing loaders and snapshots. Medians use
the existing city/level registry. Score profiles use the existing weights.

The prototype has its own route, state and CSS module. Existing detail pages,
ranking formulas and map/store behavior are unchanged. It makes no remote
mutations. Photos and visible basemap tiles use the app's existing providers.

Production access requires `ENABLE_CARD_PROTOTYPE=true`; otherwise the route
returns not found. The page also sets `noindex, nofollow`. This is an opt-in
preview, not a replacement for production detail pages.

## Interactions

- Choose any of the nine areas, then switch between guide and compact card.
- Choose a score profile; the headline and disclosed weights update together.
- Compare against the correct city/level median or another example in that cohort.
- Open category evidence with a native button.
- Choose a commute destination in the headline or the commute bars.
- Toggle the area outline and rail stations; zoom and reset the real map.
- Expand rent definitions, source links, score weights and environmental context.

## Data boundaries

- Asking-rent medians, editorial estimates and Tokyo layout averages retain their
  distinct labels. Phrom Phong's composition-skew warning stays beside its rents.
- Zero-minute trips remain zero, including Asok to Asok.
- Bangkok maps use published polygons. Tokyo's dashed 800 m circle is explicitly
  an orientation radius, not a shared boundary for all category inputs.
- The crowding-based ranking is named separately from modeled outdoor quietness.
- Air observations are not interpolated to the neighborhood. No historical
  series, live route, walking-time claim or uncertainty interval is fabricated.
- The user can review visual hierarchy here; this prototype does not establish
  that the underlying datasets are complete or current.

## Verification

Browser checks cover all nine areas, desktop and phone layouts, same-cohort
comparison, live score profiles, category evidence, map layers, rent sources,
and the zero-minute/skewed-sample cases. TypeScript and scoped ESLint are the
code checks. A full production build, field performance and comprehensive
assistive-technology testing are outside this prototype's validation.

The existing development CSP blocks React's optional `eval` debugging support;
the dev server reports that diagnostic on both original and prototype pages.
No CSP relaxation is included in this prototype.
