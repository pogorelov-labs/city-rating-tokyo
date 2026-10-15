import { describe, expect, it, vi } from 'vitest';
import { createFormatter, createTranslator } from 'next-intl';
import { renderToStaticMarkup } from 'react-dom/server';
import en from '@/messages/en/common.json';
import ja from '@/messages/ja/common.json';
import ru from '@/messages/ru/common.json';
import context from '@/data/safety/context.json';
import SafetyMethodology from '@/components/SafetyMethodology';

const messages = { en, ja, ru };
let locale: keyof typeof messages = 'en';
vi.mock('next-intl/server', () => ({
  getTranslations: async () => createTranslator({ locale, messages: messages[locale], namespace: 'safetyFacts' }),
  getFormatter: async () => createFormatter({ locale, timeZone: 'UTC' }),
}));

describe('metropolitan factual context', () => {
  for (const language of ['en', 'ja', 'ru'] as const) {
    it(`renders the complete ${language} brief with actual ICU values and citations`, async () => {
      locale = language;
      const html = renderToStaticMarkup(await SafetyMethodology());
      expect(html).toContain(messages[language].safetyFacts.title);
      expect(html).toContain(messages[language].safetyFacts.welfareScope);
      expect(html).toContain(messages[language].safetyFacts.bangkokScope);
      expect(html).toContain(new Intl.NumberFormat(language).format(30176));
      expect(html).toContain('507');
      expect(html).toContain('134');
      expect(html).not.toMatch(/\{(?:year|period|people|accidents|fatalities)/);
      expect(html).toContain('dateTime="2026-10-15"');
      expect(html).toContain(context.facts.traffic.source_url);
      expect(html).toContain(context.facts.welfare.source_url);
      expect(html).toContain('aria-labelledby="safety-context-title"');
      expect(html).not.toMatch(/geojson|datastore|research\/snapshots|bkk_accident|PRIVATE_ROW/);
    });
  }
  it('does not relabel metropolitan evidence as local or per-capita data', () => {
    expect(context.facts.traffic.scope).toBe('tokyo_metropolis_mpd_jurisdiction');
    expect(context.facts.welfare.scope).toBe('tokyo_23_wards_tama_and_national_rivers');
    expect(context.facts.traffic.denominator).toBeNull();
    expect(context.facts.welfare.denominator).toBeNull();
    expect(context.facts.traffic.period).toEqual({ start: '2025-01-01', end: '2025-12-31' });
    expect(context.facts.welfare.period).toEqual({ start: '2026-01-01', end: '2026-01-31' });
  });
});
