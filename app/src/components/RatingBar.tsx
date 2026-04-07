'use client';

interface RatingBarProps {
  /** The station's rating for this category, 1..10. */
  value: number;
  /** The Tokyo city median for this category, 1..10. */
  median: number;
  /** The diverging-palette color for this value vs median — typically `categoryDeviationColor(value, median)`. */
  fillColor: string;
}

/**
 * A single rating bar with three visual affordances that teach the
 * "bar color encodes deviation from the city median" rule at a glance:
 *
 *   1. Two-tone empty track — warm cream (#F5F1EC) LEFT of the median
 *      position, cool slate (#EFF2F4) RIGHT. Subliminally says
 *      "warm = below norm, cool = above norm".
 *   2. Filled portion — painted with the diverging akane↔kon pigment
 *      from the caller.
 *   3. Median tick — a 1 px slate-300 hairline at `median * 10%`. The
 *      Tufte reference line planted directly on the data. The eye
 *      learns where "typical" is without reading any words.
 *
 * Pure presentational: hover tooltips are handled at the call site by
 * wrapping this component in a `<Tooltip wrapper="div" showHelpIcon={false}>`.
 *
 * Pairs with:
 *   - `categoryDeviationColor(value, median)` in `@/lib/scoring`
 *   - `CITY_MEDIANS[key]` in `@/lib/scoring`
 *   - `pigmentName(dev)` in `@/lib/scoring` for the hover tooltip
 *
 * CRTKY-68 — color literacy v1.
 */
export default function RatingBar({ value, median, fillColor }: RatingBarProps) {
  const medianPct = median * 10;
  const valuePct = value * 10;

  return (
    <div className="w-full relative h-3">
      {/* Two-tone empty track: warm cream left of median, cool slate right */}
      <div className="absolute inset-0 rounded-full overflow-hidden flex">
        <div style={{ width: `${medianPct}%`, backgroundColor: '#F5F1EC' }} />
        <div className="flex-1" style={{ backgroundColor: '#EFF2F4' }} />
      </div>

      {/* Filled portion */}
      <div
        className="absolute top-0 left-0 h-full rounded-full transition-all"
        style={{ width: `${valuePct}%`, backgroundColor: fillColor }}
      />

      {/* Median tick — 1 px hairline at the city-norm position */}
      <div
        className="absolute top-0 bottom-0 w-px bg-slate-300"
        style={{ left: `${medianPct}%`, opacity: 0.7 }}
        aria-hidden
      />
    </div>
  );
}
