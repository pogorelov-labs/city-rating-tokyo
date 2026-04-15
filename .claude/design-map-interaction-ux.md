# Design: Map Interaction UX Overhaul — CRTKY-114

## Design Research Sources

- [Map UI Patterns — Info Popup](https://mapuipatterns.com/info-popup/) — click-triggered popups as standard; one popup at a time; click elsewhere to dismiss; dock to bottom on mobile
- [Eleken — Map UI Design Best Practices](https://www.eleken.co/blog-posts/map-ui-design) — hover = preview, click = commitment; consistent click behavior across map areas; Airbnb bidirectional list↔map hover
- [IxDF — Progressive Disclosure](https://ixdf.org/literature/topics/progressive-disclosure) — overview → zoom → details-on-demand (Shneiderman's mantra)
- [Appcues — Tooltip Best Practices](https://www.appcues.com/blog/tooltips) — misleading CTAs in non-interactive tooltips cause rage clicks
- [Cieden — Tooltip UX Issues](https://cieden.com/book/atoms/tooltip/tooltip-ux-issues) — tooltips that block interaction or promise actions they can't deliver
- [Airbnb Map Platform — Adam Shutsa](https://adamshutsa.com/map-platform/) — price pins, card kicker on click, progressive density by zoom level
- [Raw Studio — Maps as Core UX](https://raw.studio/blog/using-maps-as-the-core-ux-in-real-estate-platforms/) — bounding-box search, pin clustering, card interaction patterns
- [NN/G — Bottom Sheet Guidelines](https://www.nngroup.com/articles/bottom-sheet/) — maps are the ideal bottom-sheet use case; include visible close button; nonmodal → modal on expand
- [LogRocket — Bottom Sheet UX](https://blog.logrocket.com/ux-design/bottom-sheets-optimized-ux/) — bottom sheets achieve 25-30% higher engagement than traditional modals
- [Android Police — Google Maps Sheets Redesign](https://www.androidpolice.com/google-maps-on-android-is-now-all-in-on-its-sheets-first-makeover/) — Google Maps all-in on sheet-based navigation; tap pin → bottom card slides up
- [Material Design 3 — Bottom Sheets](https://m3.material.io/components/bottom-sheets/guidelines) — standard, modal, expandable variants; drag handle affordance

## Industry Patterns

| App | Hover (desktop) | Click/Tap | Zoom on click | Mobile presentation | Dismiss |
|-----|-------|-------|---------------|---------------------|---------|
| Google Maps | Label on pin | Info card | Pan to center, no zoom | **Bottom sheet** slides up | Click background / swipe down |
| Apple Maps | Label on pin | Info card | Pan to center, no zoom | **Bottom card** | Tap background / swipe down |
| Airbnb | Price on pin; sidebar highlight | Card kicker (photo + info) | No zoom | **Bottom card**, horizontal swipe for nearby | Click another pin / background |
| Zillow/Redfin | Price on pin | Detail card | No zoom | **Bottom card** with photo | Click background |
| **Us (current)** | **Rich tooltip (image + CTA)** | **flyTo → nothing** | **Yes (z12→z14)** | **Leaflet popup (clips off-screen)** | **Popup closes but halo lingers** |

Key difference: our markers are unlabeled colored dots (not price/name labels). The hover tooltip IS the label — it's the only way to identify a dot without clicking. This justifies keeping the tooltip rich.

Our flyTo zoom is also justified: at z10-12 our circles are ~6px. Zooming to z14 provides spatial context (streets, nearby POIs) that tiny dots can't. Google Maps/Airbnb don't need to zoom because their pins already show names/prices.

## Design Principles (from research)

1. **Hover = preview, click = commitment.** Hover shows info; click shows actions.
2. **Click content must be ≥ hover content.** Click is a higher-intent gesture. Showing LESS after click is an anti-pattern (information downgrade).
3. **One overlay at a time on the same target.** Tooltip + popup on the same marker = visual noise.
4. **Click elsewhere = dismiss.** Modern pattern: no X button needed on desktop, click map background to close.
5. **Progressive disclosure.** Overview → zoom → details-on-demand. Our flyTo IS the zoom step, but we're missing the "details" step after landing.
6. **Misleading CTA = rage clicks.** "Click for details →" in a non-interactive element that doesn't deliver details on click is a textbook anti-pattern.
7. **Mobile: bottom-docked card, not floating popup.** Every major map app docks info to screen bottom on mobile. Floating popups clip off-screen, compete with UI chrome, have no reliable position. Bottom cards are viewport-anchored, always visible, always reachable.

## Current Problems

### P1: Misleading CTA in tooltip
Tooltip shows "Click for details →" but clicking triggers flyTo, not navigation. The tooltip itself isn't interactive — it disappears on mouseout. CTA promises an action the UI can't deliver.

### P2: Dead end after flyTo
Click → flyTo animation → nothing. The `closePopup()` call in FlyToStation (line 70) kills Leaflet's auto-opened popup. After the animation, the user sees the marker but has no way to proceed without clicking again. Most users won't know to click twice.

Race condition details:
```
Click marker → Leaflet auto-opens Popup
  → setSelectedStation(slug) → React re-render
  → FlyToStation useLayoutEffect: map.closePopup() ← kills popup
  → map.flyTo() → animation plays
  → moveend → nothing opens the popup back
```

### P3: Tooltip/popup overlap on same marker
When popup IS open (after second click), hovering the same marker also shows the tooltip. Both layers visible on the same target. The larger tooltip sits behind the smaller popup.

### P4: Information downgrade on click
Hover tooltip: image + name + score + snippet + line count + rent (rich, 260px).
Click popup: name + score + "View details" + "Compare" (sparse, minimal).
Click shows LESS than hover — backwards from every major map app.

### P5: Selected station halo lingers
Clicking map background closes the popup (Leaflet default) but `selectedStation` stays set in zustand. The blue halo and enlarged marker persist with no popup visible.

### P6: Touch dead end (same as P2)
Touch has no hover. First tap = flyTo → dead end. Same race condition as desktop. The handoff claim that "touch is fine" is only true for taps on nearby markers (roughDist < 0.003° at zoom ≥13, the early-return path in FlyToStation line 66-67).

### P7: Popup clips off-screen on mobile
`autoPan={false}` means Leaflet does NOT scroll the map to make the popup visible. flyTo centers the marker on screen, popup opens above it. On a 375px phone with the popup growing upward, the top portion (including action buttons) can extend above the viewport. Currently hidden because the popup rarely opens on touch (P6 masks P7).

### P8: Tiny touch targets in popup
"View details →" and "+ Compare" are `text-xs` (12px) links. Below WCAG 44px minimum tap target. These are the primary actions on touch — the user's whole goal.

## Architecture Decision: Two Presentation Modes

### Desktop: Leaflet Popup (near marker)
Leaflet `<Popup>` anchored to the marker. Correct for desktop — spatial connection between dot and card is preserved. User's eyes stay near the marker.

### Touch: Bottom-docked card (React component, outside Leaflet)
Fixed-position card at the bottom of the viewport. Standard mobile map pattern (Google Maps, Apple Maps, Airbnb, Zillow all do this). Resolves P7, P8, T1, T5 simultaneously. Rendered as a React component in `MapWrapper.tsx`, not as a Leaflet Popup.

**Why not Leaflet Popup on mobile:**
- Floating popup has no reliable position on small screens (P7).
- `autoPan={true}` creates janky two-step animation and defeats flyTo centering.
- Popup below marker competes with bottom UI (drawer button, zoom controls, safe-area).
- flyTo offset hack is fragile and device-dependent.
- Nobody ships floating Leaflet popups on mobile in 2025. It's a desktop-era pattern.

**Why bottom card is NOT overengineering:**
- Content is identical — extract shared `StationInfoCard` component used by both.
- Trigger is simple: `selectedStation !== null && !isFlying && isTouch`.
- Lives in `MapWrapper.tsx` as a sibling to `MapView` and `ComparePanel`.
- We REMOVE the Leaflet `<Popup>` on touch (`{!isTouch && <Popup>}`), making touch code simpler.
- LQIP blur-up still works for the image (same `StationTooltipHero` or simplified variant).

### Bottom card specification

```
+------------------------------------------+
|                                          |
|              MAP (interactive)           |
|                                          |
|          ● selected marker               |
|                                          |
+------------------------------------------+
| ┌──────────────────────────────────────┐ |
| │ [img]  Station Name           8.2   │ |
| │ 60×60  Secondary name               │ |
| │        2 lines · ~¥95k/mo           │ |
| │                                      │ |
| │  [ View details → ]  [ + Compare ]  │ |
| └──────────────────────────────────────┘ |
|          safe-area-inset-bottom          |
+------------------------------------------+
```

| Property | Value | Rationale |
|----------|-------|-----------|
| Position | `fixed bottom-0 left-3 right-3` | Full-width with margin, like MobileSearchPill |
| Z-index | `z-[800]` | Above Leaflet (700), below MobileSearchPill (999), MobileDrawer (1000+) |
| Height | ~140-160px | Image 60px + text + buttons. Covers ~30-35% of 375px screen |
| Image | Horizontal layout, 60×60 thumbnail left, text right | Compact — not the tall vertical tooltip hero |
| Buttons | `min-h-[44px]` pill buttons | WCAG tap target compliance |
| Enter animation | `translateY(100%) → translateY(0)`, 200ms ease-out | Smooth slide-up |
| Exit animation | `translateY(0) → translateY(100%)`, 150ms ease-in | Slightly faster exit |
| Safe area | `pb-[env(safe-area-inset-bottom)]` | iPhone home indicator clearance |
| Close | X button top-right (NN/G: always include visible close button) | Primary dismiss affordance |
| Background tap | Tap clean map background → dismiss | Secondary dismiss (Leaflet `click` event, no drag) |
| Station switch | Tap another marker → card transitions to new station | Card stays visible, content swaps with crossfade |

### T8 stacking: ComparePanel + bottom card

When both are visible (2+ compared stations AND a selected station):
- Bottom card renders at `z-[950]` (above ComparePanel z-900).
- ComparePanel peeks below the bottom card.
- Low priority edge case — acceptable overlap.

## User Scenarios (Final)

### Desktop

#### S1: "What's this dot?" — hover marker
**Intent:** Quick identification while scanning.
**Decision:** Keep rich tooltip (image, name, score, snippet, lines, rent). **Remove "Click for details →"** only. Tooltip is informational, not actionable.

#### S2: "Tell me more" — click marker (zoomed out)
**Intent:** Committed interest. Wants to explore this station.
**Decision:** flyTo → **auto-open Leaflet Popup after moveend**. Popup includes image + snippet + actions (remove `isTouch` gate on `StationTooltipHero` in Popup). Click = upgrade from hover (same info + action buttons).

**Auto-open mechanism:** Store a ref to the selected station's CircleMarker (`selectedMarkerRef`). In `onFlyEnd` callback, call `selectedMarkerRef.current?.openPopup()`. No zustand, no 1493-effect scan, one ref on the active marker.

```tsx
const selectedMarkerRef = useRef<L.CircleMarker>(null);
const onFlyEnd = useCallback(() => {
  setIsFlying(false);
  selectedMarkerRef.current?.openPopup();
}, []);

// In render:
<CircleMarker
  ref={station.slug === selectedStation ? selectedMarkerRef : undefined}
  ...
>
```

#### S3: "Tell me more" — click marker (already zoomed in)
**Decision:** Auto-open fix from S2 covers >200m case. <200m early-return → Leaflet auto-opens popup. Tooltip suppression covers overlap.

#### S4: "View details" — click link in popup
**Decision:** No change. Works.

#### S5: "Compare" — click button in popup
**Decision:** No change. Works.

#### S6: "Never mind" — click map background
**Decision:** **Clear selectedStation on background click (desktop only).** Check `e.originalEvent.target` for `.leaflet-interactive` to distinguish from marker clicks.

#### S10: Hover another marker while popup is open
**Decision:** No change. Different markers, no spatial conflict. 400ms delay prevents flicker.

#### S11: Click another marker while popup is open (far)
**Decision:** S2 auto-open handles. A closes → fly to B → B auto-opens.

#### S11b: Click another marker mid-flight
**Decision:** No change. useLayoutEffect cleanup is correct. Verified safe.

#### S12: Click adjacent marker while popup is open
**Decision:** S2 auto-open covers >200m. <200m already works.

#### S13: Re-click same station
**Decision:** No change. Leaflet toggles popup. Works as expected.

#### S14: Zoom out with popup open
**Decision:** Defer. Minor, standard behavior.

#### Tooltip/popup overlap — same marker
**Decision:** **Suppress tooltip when popup is open on same marker.** Track `openPopupSlug` via Popup `add`/`remove` events. Render: `{!isTouch && openPopupSlug !== station.slug && <Tooltip>}`.

### Touch / Mobile

#### S7a: Tap marker (zoomed in, <200m)
**Decision:** FlyToStation early-returns. Bottom card appears reactively (reads `selectedStation` from zustand). No Leaflet Popup involved.

#### S7b: Tap marker (zoomed out, far)
**Decision:** flyTo plays → `isFlying=true` (card hidden during flight) → `isFlying=false` after moveend → bottom card slides up. No Leaflet Popup, no race condition, no `closePopup()` interaction.

#### S7c: Tap ranked list item in MobileDrawer
**Decision:** Drawer closes (300ms) → setSelectedStation → flyTo → bottom card after landing. Verify drawer close + flyTo don't visually conflict.

#### S7d: Tap search result in MobileSearchPill
**Decision:** handleSelect → blur() (keyboard dismiss) → setSelectedStation → flyTo → bottom card after landing. Keyboard should dismiss before card renders (blur is sync).

#### S6t: Tap map background to dismiss (touch)
**Decision:** Bottom card has visible X button (primary dismiss). Background tap also dismisses — Leaflet `click` only fires on clean taps (no drag), so accidental dismiss during pan is unlikely. Both affordances available.

#### T2: No image prefetch on touch
**Decision:** Accept. LQIP provides instant blur placeholder. Sharp thumbnail loads in ~200-500ms. Acceptable on mobile.

## Implementation Plan

### Priority 1: Must fix (blocks UX)
1. **Bottom card component** — `MobileStationCard.tsx`. Fixed-position, slides up/down. Reads `selectedStation` + `isFlying` + station data. 44px action buttons. Image with LQIP. X to close. Rendered in `MapWrapper.tsx` gated by `isTouch`.
2. **Remove Leaflet Popup on touch** — `{!isTouch && <Popup>}` in Map.tsx. Simplifies touch path.
3. **Auto-open Leaflet Popup on desktop** — `selectedMarkerRef` + `onFlyEnd` callback in Map.tsx.
4. **Remove "Click for details →"** — delete the CTA line from tooltip content in Map.tsx.

### Priority 2: Should fix (degrades experience)
5. **Add image+snippet to desktop popup** — remove `isTouch` gate on `StationTooltipHero` in Popup. Show image on desktop too.
6. **Suppress tooltip when popup open** — track `openPopupSlug`, conditional render.
7. **Background click dismiss (desktop)** — `useMapEvents` click handler, clear selectedStation when clicking non-interactive target.

### Priority 3: Defer
8. T8: ComparePanel + bottom card stacking (edge case).
9. S14: Zoom-out popup floating.

## Key Files to Modify

| File | Changes |
|------|---------|
| `app/src/components/MobileStationCard.tsx` | **New.** Bottom-docked touch card component. |
| `app/src/components/MapWrapper.tsx` | Add `MobileStationCard` (lazy-loaded, gated by touch + selectedStation). |
| `app/src/components/Map.tsx` | Remove CTA from tooltip. Gate `<Popup>` on `!isTouch`. Add `selectedMarkerRef` + auto-open in `onFlyEnd`. Track `openPopupSlug` for tooltip suppression. Add image+snippet to desktop popup. Background click handler. |
| `app/src/messages/{en,ja,ru}/common.json` | Remove or repurpose `map.clickForDetails` key. |
| `app/src/app/globals.css` | Bottom card slide animation (if not using Tailwind transitions). |

## Constraints

- **Don't break flyTo animation** — canvas fade, halo hide, tile prefetch must continue working.
- **Don't break hover↔list link** — `hoveredStation` from FilterPanel/ranked list must still show halo on map marker.
- **Performance** — bottom card is one React component reading one zustand selector. No per-marker overhead.
- **i18n** — any new strings need entries in all 3 locale files (en/ja/ru).
- **Bottom card must not block map interaction** — map stays pannable/zoomable behind the card. Card covers ~30% of screen, 70% is interactive map.

## Test Matrix

| # | Action | Platform | Expected |
|---|--------|----------|----------|
| 1 | Hover marker, wait 400ms | Desktop | Tooltip: image + name + score + lines + rent. NO "Click for details" |
| 2 | Click marker (zoomed out) | Desktop | flyTo → Leaflet popup auto-opens with image + name + score + snippet + actions |
| 3 | Click "View details" in popup | Desktop | Navigates to station page |
| 4 | Click "+ Compare" in popup | Desktop | Station added to compare |
| 5 | Hover same marker while popup open | Desktop | Tooltip does NOT appear |
| 6 | Hover different marker while popup open | Desktop | Tooltip appears on other marker, popup stays |
| 7 | Click map background | Desktop | Popup closes, halo disappears, selectedStation null |
| 8 | Click another marker (far) | Desktop | A popup closes, fly to B, B popup auto-opens |
| 9 | Click another marker mid-flight | Desktop | A interrupted, fly to B, B popup auto-opens |
| 10 | Click adjacent marker | Desktop | Short fly (or no fly if <200m), popup opens on new station |
| 11 | Re-click same station | Desktop | Popup toggles closed |
| 12 | Tap marker (zoomed out) | Touch | flyTo → bottom card slides up with image + name + score + actions |
| 13 | Tap marker (zoomed in) | Touch | Bottom card appears (no flyTo if <200m) |
| 14 | Tap "View details" in bottom card | Touch | Navigates to station page |
| 15 | Tap "+ Compare" in bottom card | Touch | Station added to compare |
| 16 | Tap X on bottom card | Touch | Card slides down, selectedStation cleared |
| 17 | Tap map background | Touch | Card slides down |
| 18 | Tap another marker while card open | Touch | Card transitions to new station |
| 19 | Tap ranked list item (MobileDrawer) | Touch | Drawer closes, flyTo, bottom card appears |
| 20 | Tap search result (MobileSearchPill) | Touch | Keyboard dismisses, flyTo, bottom card appears |
| 21 | Bottom card visible + zoom out | Touch | Card stays fixed at bottom, marker may leave view |
| 22 | Bottom card + ComparePanel both visible | Touch | Card renders above ComparePanel |
| 23 | Hover marker → move away before 400ms | Desktop | No tooltip flicker |
