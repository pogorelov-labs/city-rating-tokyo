import { createTranslator } from 'next-intl';
import { describe, expect, it, vi } from 'vitest';
import en from '@/messages/en/common.json';
import ja from '@/messages/ja/common.json';
import ru from '@/messages/ru/common.json';

vi.mock('@/lib/data', () => ({ getStation: () => undefined, getStations: () => [] }));
vi.mock('@/i18n/navigation', () => ({ Link: () => null }));
vi.mock('next/dynamic', () => ({ default: () => () => null }));
vi.mock('next/navigation', () => ({ notFound: () => { throw new Error('NOT_FOUND'); } }));
vi.mock('next-intl/server', () => ({
  getTranslations: async ({ locale, namespace }: { locale: 'en' | 'ja' | 'ru'; namespace: 'station' | 'error' }) =>
    createTranslator({ locale, namespace, messages: { en, ja, ru }[locale] }),
}));

import { generateMetadata } from './page';

describe('missing station metadata', () => {
  // A runtime page may call notFound() and let Next serve the layout's 404
  // metadata. Test this exported fallback directly so its locale is still a
  // checked contract rather than depending on framework 404 resolution order.
  for (const locale of ['en', 'ja', 'ru'] as const) {
    it(`uses the ${locale} missing-station title`, async () => {
      expect(await generateMetadata({ params: Promise.resolve({ locale, slug: 'missing' }) }))
        .toEqual({ title: { en, ja, ru }[locale].error.stationNotFound });
    });
  }
  it('rejects an unsupported route locale before calling translations', async () => {
    await expect(generateMetadata({ params: Promise.resolve({ locale: 'fr', slug: 'missing' }) }))
      .rejects.toThrow('NOT_FOUND');
  });
});
