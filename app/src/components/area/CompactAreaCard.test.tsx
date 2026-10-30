import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import type { ComponentProps, ReactNode } from 'react';
import { Providers, messages } from '@/test/providers';
import { station } from '@/test/stations';
import { DEFAULT_WEIGHTS, PRESET_PROFILES } from '@/lib/types';
import CompactAreaCard from './CompactAreaCard';

vi.mock('@/i18n/navigation', () => ({
  Link: ({ children, ...props }: ComponentProps<'a'> & { children: ReactNode }) => <a {...props}>{children}</a>,
}));

describe('shared station/district compact cards', () => {
  for (const locale of ['en', 'ja', 'ru'] as const) {
    it(`${locale} names actions and estimates, retains a zero-minute trip and carries non-default weights`, () => {
      const weights = PRESET_PROFILES.find(profile => profile.id === 'family')!.weights;
      const area = { ...station('st.asok'), name_en: 'Asok', name_jp: 'アソーク', name_th: 'อโศก', min_transit: 0, rent_1k: 26500 };
      render(<Providers locale={locale} city="bangkok"><CompactAreaCard area={area} city="bangkok" score={7.7} weights={weights} onCompare={() => {}} /></Providers>);
      const link = screen.getByRole('link', { name: new RegExp(messages[locale].areaGuide.compact.explore) });
      expect(link.getAttribute('href')).toMatch(/^\/bangkok\/station\/asok\?w=/);
      expect(screen.getByText(new RegExp(`^0`))).toHaveTextContent('0');
      expect(screen.getByText(new RegExp(messages[locale].areaGuide.compact.custom))).toBeInTheDocument();
    });
    it(`${locale} identifies a missing Tokyo rent without calling it an estimate`, () => {
      render(<Providers locale={locale}><CompactAreaCard area={{ ...station('gora'), rent_1k: null, rent_source: 'computed', rent_updated: '2026-04' }} city="tokyo" score={6} weights={DEFAULT_WEIGHTS} /></Providers>);
      expect(screen.getByText(messages[locale].areaGuide.rent.provenance.unavailable)).toBeInTheDocument();
      expect(screen.getByText(messages[locale].areaGuide.rent.definition.unavailable)).toBeInTheDocument();
      expect(screen.queryByText(messages[locale].areaGuide.rent.definition.estimate)).not.toBeInTheDocument();
    });
  }

  it('labels municipal Tokyo rent rather than presenting it as a station listing average', () => {
    render(<Providers><CompactAreaCard area={{ ...station('alpha'), rent_source: 'estat' }} city="tokyo" score={6} weights={DEFAULT_WEIGHTS} /></Providers>);
    expect(screen.getByText(messages.en.areaGuide.rent.provenance.municipalAverage)).toBeInTheDocument();
    expect(screen.queryByText(messages.en.areaGuide.rent.provenance.stationAverage)).not.toBeInTheDocument();
  });

  it('keeps the composition warning visible and the comparison limit functional', () => {
    const area = { ...station('st.phrom-phong'), rent_provenance: {
      metric: 'median_asking_by_bedroom' as const, provenance: 'station_override' as const,
      confidence: 'estimate' as const, as_of: '2026-10-25', sample_size: { one_bed: 19, two_bed: 26 }, sources: [], composition_skew: true,
    } };
    const compare = vi.fn();
    const remove = vi.fn();
    const { rerender } = render(<Providers city="bangkok"><CompactAreaCard area={area} city="bangkok" score={6.7}
      weights={DEFAULT_WEIGHTS} compareFull onCompare={compare} onUncompare={remove} /></Providers>);
    expect(screen.getByText(messages.en.areaGuide.rent.skewShort)).toBeVisible();
    expect(screen.getByRole('button', { name: messages.en.map.compare })).toBeDisabled();
    rerender(<Providers city="bangkok"><CompactAreaCard area={area} city="bangkok" score={6.7}
      weights={DEFAULT_WEIGHTS} compareFull isCompared onCompare={compare} onUncompare={remove} /></Providers>);
    fireEvent.click(screen.getByRole('button', { name: messages.en.map.removeCompare }));
    expect(remove).toHaveBeenCalledOnce();
    expect(compare).not.toHaveBeenCalled();
  });

  it('closes without bubbling the click to the map wrapper', () => {
    const close = vi.fn();
    const mapClick = vi.fn();
    render(<Providers><div onClick={mapClick}><CompactAreaCard area={station('alpha')} city="tokyo"
      score={6} weights={DEFAULT_WEIGHTS} onClose={close} /></div></Providers>);
    fireEvent.click(screen.getByRole('button', { name: messages.en.areaGuide.compact.close }));
    expect(close).toHaveBeenCalledOnce();
    expect(mapClick).not.toHaveBeenCalled();
  });
});
