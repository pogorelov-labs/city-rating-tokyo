import type { Station, StationSources } from '@/lib/types';

/**
 * Returns true when a station's ratings were produced primarily by a human
 * researcher (qualitative / "editorial") rather than purely from scraped
 * quantitative data. CRTKY-52.
 *
 * Detection rule (per the ticket): a station is "editorial" when ANY source
 * array in `station.sources` contains the literal token `'ai_research'`. The
 * confidence legend's wisteria-purple `editorial` level (see
 * ConfidenceBadge.tsx) is the visual analog of the same concept.
 */
export function isEditorialStation(station: Pick<Station, 'sources'>): boolean {
  if (!station.sources) return false;
  return Object.values(station.sources as StationSources).some(
    (arr) => Array.isArray(arr) && arr.includes('ai_research'),
  );
}
