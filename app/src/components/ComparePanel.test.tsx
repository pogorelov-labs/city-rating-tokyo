import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import { NextIntlClientProvider } from 'next-intl';
import { Providers, messages } from '@/test/providers';
import { station } from '@/test/stations';
import { getCityActions, useAppStore } from '@/lib/store';
import { getBangkokMapDistricts, getBangkokMapStationAreas } from '@/lib/bangkok-data';
import { bangkokClientMessages } from '@/lib/bangkok-client-messages';
import { formatRentShort } from '@/lib/cities';
import ComparePanel from './ComparePanel';

vi.mock('./CompareRadarChart', () => ({ default: () => null }));

beforeEach(() => useAppStore.setState(useAppStore.getInitialState(), true));

describe('ComparePanel rent provenance', () => {
  it.each(['en', 'ja', 'ru'] as const)('%s distinguishes proxies, blends and editorial estimates with Bangkok client messages', (locale) => {
    const areas = [...getBangkokMapStationAreas(), ...getBangkokMapDistricts()];
    const compared = ['st.asok', 'st.siam', 'pathum-wan'].map((slug) => areas.find((area) => area.slug === slug)!);
    for (const area of compared) getCityActions('bangkok').addCompareStation(area.slug);
    const clientMessages = bangkokClientMessages(messages[locale]);

    render(
      <Providers city="bangkok" locale={locale}>
        <NextIntlClientProvider locale={locale} messages={clientMessages}>
          <ComparePanel stations={compared} />
        </NextIntlClientProvider>
      </Providers>,
    );

    const row = screen.getByText(messages[locale].compare.rent1bed).closest('tr')!;
    const [, proxy, blend, editorial] = within(row).getAllByRole('cell');
    expect(within(proxy).getByText(clientMessages.bangkok.rent.medianLabel)).toBeInTheDocument();
    expect(proxy).toHaveTextContent('DooAsset');
    expect(proxy).toHaveTextContent(compared[0].rent_provenance!.as_of);
    expect(within(blend).getByText(clientMessages.bangkok.rent.blendLabel)).toBeInTheDocument();
    expect(within(editorial).getByText(clientMessages.bangkok.rent.editorialLabel)).toBeInTheDocument();
    for (const [index, cell] of [proxy, blend, editorial].entries()) {
      expect(cell).toHaveTextContent(formatRentShort('bangkok', compared[index].rent_1k!));
    }
  });

  it('keeps Tokyo rent cells value-only when provenance is absent', () => {
    const compared = [station('alpha'), station('beta', { rent_1k: 150000 })];
    for (const area of compared) getCityActions('tokyo').addCompareStation(area.slug);

    render(<Providers><ComparePanel stations={compared} /></Providers>);

    const row = screen.getByText(messages.en.compare.rent1k).closest('tr')!;
    const [, first, second] = within(row).getAllByRole('cell');
    expect(first).toHaveTextContent(/^¥100k$/);
    expect(second).toHaveTextContent(/^¥150k$/);
    expect(first.childElementCount).toBe(0);
    expect(second.childElementCount).toBe(0);
  });
});
