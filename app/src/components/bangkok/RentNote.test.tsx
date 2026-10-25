import { describe, expect, it } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';
import { NextIntlClientProvider } from 'next-intl';
import en from '@/messages/en/common.json';
import ja from '@/messages/ja/common.json';
import ru from '@/messages/ru/common.json';
import { getBangkokStationArea, getBangkokMapStationAreas } from '@/lib/bangkok-data';
import { bangkokClientMessages } from '@/lib/bangkok-client-messages';
import RentNote from './RentNote';

describe('Bangkok rent provenance', () => {
  it.each(['en', 'ja', 'ru'] as const)('%s keeps every shared client namespace in the nested provider', (locale) => {
    const messages = { en, ja, ru }[locale];
    const client = bangkokClientMessages(messages);
    for (const [namespace, value] of Object.entries(messages)) {
      if (!['bangkok', 'quietness', 'air', 'safetyFacts', 'institutions'].includes(namespace)) {
        expect(client[namespace as keyof typeof client]).toEqual(value);
      }
    }
    expect(client.bangkok.rent).toEqual(messages.bangkok.rent);
  });

  it.each(['en', 'ja', 'ru'] as const)('%s identifies the median proxy, source, date and both bedroom samples', (locale) => {
    const messages = { en, ja, ru }[locale];
    const rent = getBangkokStationArea('asok')!.rent;
    const clientMessages = bangkokClientMessages(messages);
    expect(Object.keys(clientMessages.bangkok)).toEqual(['rent']);
    render(<NextIntlClientProvider locale={locale} messages={clientMessages}><RentNote rent={rent} /></NextIntlClientProvider>);
    expect(screen.getByText(messages.bangkok.rent.medianLabel)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'DooAsset' })).toHaveAttribute('href', rent.sources[0].url);
    expect(screen.getByText(messages.bangkok.rent.samples.replace('{one}', '30').replace('{two}', '18'))).toBeInTheDocument();
    expect(screen.getByText(messages.bangkok.rent.asOf.replace('{date}', '2026-10-25'))).toBeInTheDocument();
    expect(screen.getByText(messages.bangkok.rent.medianDefinition)).toBeInTheDocument();
    expect(screen.queryByText(messages.bangkok.rent.editorialLabel)).not.toBeInTheDocument();
    cleanup();
  });

  it('keeps unsourced areas editorial in details and compact map notes', () => {
    const rent = getBangkokStationArea('siam')!.rent;
    render(<NextIntlClientProvider locale="en" messages={en}><RentNote rent={rent} compact /></NextIntlClientProvider>);
    expect(screen.getByText(en.bangkok.rent.blendLabel)).toBeInTheDocument();
    expect(screen.queryByText(/DooAsset/)).not.toBeInTheDocument();
    expect(screen.queryByText(/n=/)).not.toBeInTheDocument();
    cleanup();
  });

  it('preserves the source and sample in the map payload', () => {
    const area = getBangkokStationArea('asok')!;
    const mapped = getBangkokMapStationAreas().find((a) => a.slug === 'st.asok')!;
    expect(mapped.rent_1k).toBe(area.rent.one_bed);
    expect(mapped.rent_provenance?.metric).toBe('median_asking_by_bedroom');
    expect(mapped.rent_provenance?.sources[0].url).toBe(area.rent.sources[0].url);
    expect(mapped.rent_provenance?.sample_size).toEqual(area.rent.sample_size);
  });

  it.each(['chit-lom', 'chong-nonsi', 'phrom-phong'])('%s surfaces the size/composition mismatch beside the value', (id) => {
    const rent = getBangkokStationArea(id)!.rent;
    render(<NextIntlClientProvider locale="en" messages={en}><RentNote rent={rent} /></NextIntlClientProvider>);
    expect(screen.getByText(en.bangkok.rent.compositionSkew)).toBeInTheDocument();
    const size = rent.source_typical_size_sqm!;
    expect(screen.getByText(en.bangkok.rent.sourceSizes
      .replace('{one}', size.one_bed === null ? en.bangkok.rent.unpublishedSize : en.bangkok.rent.sizeSqm.replace('{size}', String(size.one_bed)))
      .replace('{two}', size.two_bed === null ? en.bangkok.rent.unpublishedSize : en.bangkok.rent.sizeSqm.replace('{size}', String(size.two_bed))))).toBeInTheDocument();
    cleanup();
  });
});
