import { describe, expect, it } from 'vitest';
import { boxPixels, escapeHtml, labelWidth, mapLabel } from './bangkok-labels';

describe('Bangkok map labels', () => {
  it('escapes text before it enters Leaflet HTML', () => {
    expect(escapeHtml(`<A & "B" 'C'>`)).toBe('&lt;A &amp; &quot;B&quot; &#39;C&#39;&gt;');
  });
  it('removes the ward suffix only from Japanese labels', () => {
    expect(mapLabel('中央区', 'ja')).toBe('中央');
    expect(mapLabel('中央区', 'en')).toBe('中央区');
    expect(mapLabel('区中央', 'ja')).toBe('区中央');
  });
  it('estimates wider CJK names and larger boxes at higher zoom', () => {
    expect(labelWidth('中央')).toBeGreaterThan(labelWidth('AB'));
    const box: [[number, number], [number, number]] = [[13.7, 100.5], [13.71, 100.51]];
    const low = boxPixels(box, 12);
    const high = boxPixels(box, 13);
    expect(high.w).toBeCloseTo(low.w * 2);
    expect(high.h).toBeCloseTo(low.h * 2);
  });
});

import type { MapStation } from './types';
import { districtMapLabels, stationAreaMapLabels } from './bangkok-labels';

const named = (slug: string, name: string) => ({ slug, name_en: name, name_jp: '中央区', lat: 13.75, lng: 100.5 }) as MapStation;
const largeBox: [[number, number], [number, number]] = [[13.7, 100.4], [13.8, 100.6]];
const smallBox: [[number, number], [number, number]] = [[13.75, 100.5], [13.75001, 100.50001]];

describe('label descriptors', () => {
  it('preserves order, hides labels that do not fit, and escapes names', () => {
    const labels = districtMapLabels([named('a', 'A&B'), named('missing', 'Missing'), named('small', 'Small')], {
      a: { bbox: largeBox, label: [13.75, 100.5] }, small: { bbox: smallBox, label: [13.75, 100.5] },
    }, 13, 'en');
    expect(labels.map((label) => label.key)).toEqual(['a']);
    expect(labels[0].html).toBe('<span>A&amp;B</span>');
    expect(districtMapLabels([named('a', 'A')], { a: { bbox: largeBox, label: [13.75, 100.5] } }, 13, 'ja')[0].html).toBe('<span>中央</span>');
  });
  it('shows station areas from zoom 13 and uses the first interchange name', () => {
    const area = named('st.asok', 'Asok / Sukhumvit');
    const shapes = { asok: { bbox: largeBox } };
    expect(stationAreaMapLabels([area], shapes, 12, 'en')).toEqual([]);
    expect(stationAreaMapLabels([area], shapes, 13, 'en')).toEqual([{ key: 'st.asok', pos: [13.75, 100.5], className: 'district-label station-area-label', html: '<span>Asok</span>' }]);
  });
});
