import { createTranslator } from 'next-intl';
import { describe, expect, it } from 'vitest';
import { dataLabel } from './message-key';
import en from '@/messages/en/common.json';
import ja from '@/messages/ja/common.json';
import ru from '@/messages/ru/common.json';

describe('data-provided translation IDs', () => {
  for (const locale of ['en', 'ja', 'ru'] as const) {
    const messages = { en, ja, ru }[locale];
    it(`${locale}: known IDs translate and unknown IDs remain readable`, () => {
      const t = createTranslator({ locale, messages });
      expect(dataLabel(t, 'sources', 'osm')).toBe(messages.sources.osm);
      expect(dataLabel(t, 'hubs', 'shibuya')).toBe(messages.hubs.shibuya);
      expect(dataLabel(t, 'sources', 'future-provider')).toBe('future-provider');
      expect(dataLabel(t, 'hubs', 'future-hub')).toBe('future-hub');
    });
  }
});
