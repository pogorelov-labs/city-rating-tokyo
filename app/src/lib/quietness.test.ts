import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { createTranslator } from 'next-intl';
import { describe, expect, it, vi } from 'vitest';
import en from '@/messages/en/common.json';
import ja from '@/messages/ja/common.json';
import ru from '@/messages/ru/common.json';
import { getQuietness } from './quietness';
import type { QuietnessFact } from './schema/noise-types';

const localeState = vi.hoisted(() => ({ locale: 'en' as 'en' | 'ja' | 'ru' }));
vi.mock('next-intl/server', () => ({
  getTranslations: async (namespace: 'quietness') => createTranslator({
    locale: localeState.locale, messages: { en, ja, ru }[localeState.locale], namespace,
  }),
}));
vi.mock('@/i18n/navigation', () => ({
  Link: ({ children, href, ...props }: { children: React.ReactNode; href: string }) => createElement('a', { ...props, href }, children),
}));
import { QuietnessFacts } from '@/components/QuietnessFacts';
import { QuietnessMethodology } from '@/components/QuietnessMethodology';

async function render(fact?: QuietnessFact) {
  return renderToStaticMarkup(await QuietnessFacts({ fact }));
}

describe('quietness fact rendering', () => {
  for (const [locale, messages] of Object.entries({ en, ja, ru })) {
    it(`${locale}: day/night, estimate, scale, source and methodology render`, async () => {
      localeState.locale = locale as 'en' | 'ja' | 'ru';
      const html = await render(getQuietness('tokyo', 'shibuya'));
      for (const key of ['title', 'day', 'night', 'estimate', 'scale', 'limits'] as const) {
        // HTML serialization escapes ampersands in the English heading.
        expect(html).toContain(messages.quietness[key].replaceAll('&', '&amp;'));
      }
      expect(html).toContain('06:00–22:00');
      expect(html).toContain('22:00–06:00');
      expect(html).toContain('/methodology#quietness');
      expect(html).not.toContain('undefined');
      const method = renderToStaticMarkup(await QuietnessMethodology());
      expect(method).toContain('3.225');
      expect(method).toContain('4.296');
      expect(method).toContain('3.304');
      expect(method).toContain('4.278');
      expect(method).toContain(messages.quietness.methodBangkok);
    });
  }

  it('Bangkok discloses transfer and never displays fabricated measured dB', async () => {
    localeState.locale = 'en';
    const html = await render(getQuietness('bangkok', 'asok'));
    expect(html).toContain(en.quietness.bangkokUncalibrated);
    expect(html).not.toContain('Measured roadside');
    expect(html).not.toContain('dB');
  });

  it('Tokyo anchor has source, measurement year, dates and archived coordinate warning', async () => {
    localeState.locale = 'en';
    const html = await render(getQuietness('tokyo', 'akihabara'));
    expect(html).toContain('Measured roadside reference · FY2023');
    expect(html).toContain('Day 65 dB · Night 62 dB');
    expect(html).toContain('2023/11/13');
    expect(html).toContain('2013 coordinates');
    expect(html).toContain('not this station or a home');
    expect(html).toContain('https://www.kankyo.metro.tokyo.lg.jp/');
  });

  it('missing IDs and missing proxy coverage display unknown, not a perfect score', async () => {
    localeState.locale = 'en';
    expect(getQuietness('tokyo', 'does-not-exist')).toBeUndefined();
    const absent = await render();
    expect(absent).toContain(en.quietness.missing);
    expect(absent).not.toContain('/ 10');
    const fact = getQuietness('tokyo', 'shibuya')!;
    const incomplete = await render({ ...fact, status: 'missing_proxies', day: null, night: null });
    expect(incomplete).toContain(en.quietness.missing);
    expect(incomplete).not.toContain('/ 10');
  });
});
