# Shared area guides and compact cards

The production routes for every Tokyo station, Bangkok station area and Bangkok
district use `AreaGuide`. The original approved experiment is retained under
`../prototype/cards/` and its dev-only route.

- `lib/area-guide-data.ts` normalizes the selected record server-side. Heavy
  snapshots and geometry stay off homepage card payloads. References use the
  correct city and area-type medians; peers stay in that cohort.
- `AreaGuide.tsx` renders the hierarchy, accessible comparison table/plot,
  selectable commute bars, real scope map, sources and score profile.
- `AreaGuideExtras.tsx` retains local descriptions, transport/last-train details,
  institutional counts, environmental context, photos, cameras and source facts
  behind native disclosures.
- `CompactAreaCard` supplies desktop, hover and touch presentation. Its action
  footer stays outside the scrolling body. `LeafletAreaCard` owns map-specific
  close behavior; `MobileStationCard` retains the existing flight/animation
  lifecycle.
- `AreaLink` and `withGuideWeights` preserve the existing weight URL format.
  Locale switching preserves destination and comparison query context.

All new UI copy uses the `areaGuide` namespace in EN/JA/RU. Reviewed summaries
live in `data/area-guide-copy.json`; unreviewed station areas use factual leads,
and unreviewed district overviews retain the first localized setting sentence.
Full original descriptions remain available as notes.

Keep rent cohorts, published medians, district estimates, proxy inventory skew,
source dates and geography distinct. Tokyo's dashed circle is a reference;
Bangkok uses the published polygons. The crowd-based ranking is separate from
modeled outdoor quietness. Missing values are not zero and zero-minute trips
are not missing.

Validation includes all 1,676 area adapters, existing route/locale contracts,
compact actions and the touch lifecycle. Browser tests cover the production
guides, accessibility checks and map interactions. No new runtime dependencies
are required.

Local development: `cd app` then `npm run dev -- --port 3010`.
The checked standalone production preview uses port 3011 with hostname
`localhost`; this is a local preview, not a deployment.
