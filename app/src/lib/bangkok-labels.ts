import type { Locale } from '@/i18n/routing';

type LatLng = [number, number];

export function escapeHtml(s: string): string {
  return s.replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]!);
}

/** Pixel size of a lat/lng box at a zoom (Web Mercator, fine at Bangkok's latitude). */
export function boxPixels(bbox: [LatLng, LatLng], zoom: number): { w: number; h: number } {
  const world = 256 * 2 ** zoom;
  const w = ((bbox[1][1] - bbox[0][1]) / 360) * world;
  const merc = (lat: number) => Math.log(Math.tan(Math.PI / 4 + (lat * Math.PI) / 360));
  const h = ((merc(bbox[1][0]) - merc(bbox[0][0])) / (2 * Math.PI)) * world;
  return { w, h };
}

/** Rough rendered width of an 11 px semibold label: kana / kanji are about
 *  twice as wide as Latin or Cyrillic glyphs. */
export function labelWidth(text: string): number {
  let w = 12;
  for (const ch of text) w += ch.charCodeAt(0) >= 0x2e80 ? 11 : 6.6;
  return w;
}

/** Map-label form of a name: the JA "区" (ward) suffix is implied on a map
 *  of districts and costs a full-width glyph in the densest part of the map. */
export function mapLabel(name: string, locale: Locale): string {
  return locale === 'ja' ? name.replace(/区$/, '') : name;
}


import type { MapStation } from '@/lib/types';
import { stationDisplayName, stationPrimaryName } from '@/lib/station-name';

interface LabelShape { bbox: [LatLng, LatLng]; label: LatLng }
interface AreaShape { bbox: [LatLng, LatLng] }
export interface MapLabel { key: string; pos: LatLng; className: string; html: string }

/** Compute label descriptors separately from Leaflet so fitting is testable without a DOM. */
export function districtMapLabels(districts: MapStation[], shapes: Record<string, LabelShape>, zoom: number, locale: Locale): MapLabel[] {
  return districts.flatMap((d) => {
    const shape = shapes[d.slug];
    if (!shape) return [];
    const name = mapLabel(stationDisplayName(d, locale).primary, locale);
    const { w, h } = boxPixels(shape.bbox, zoom);
    if (w < labelWidth(name) * 1.1 || h < 22) return [];
    return [{ key: d.slug, pos: shape.label, className: 'district-label', html: `<span>${escapeHtml(name)}</span>` }];
  });
}

export function stationAreaMapLabels(areas: MapStation[], shapes: Record<string, AreaShape>, zoom: number, locale: Locale): MapLabel[] {
  if (zoom < 13) return [];
  return areas.flatMap((a) => {
    const shape = shapes[a.slug.slice(3)];
    if (!shape) return [];
    const name = stationPrimaryName(a, locale).split(' / ')[0];
    if (boxPixels(shape.bbox, zoom).w < labelWidth(name) * 0.9) return [];
    return [{ key: a.slug, pos: [a.lat, a.lng] as LatLng, className: 'district-label station-area-label', html: `<span>${escapeHtml(name)}</span>` }];
  });
}
