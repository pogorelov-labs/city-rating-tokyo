import { describe, expect, it, vi } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';
import { createTranslator } from 'next-intl';
import type { Locale } from '@/i18n/routing';
import { messages } from '@/test/providers';
import { getInstitutions, institutionSources } from '@/lib/institutions';
import { InstitutionFacts } from './InstitutionFacts';

let locale: Locale = 'en';
vi.mock('next-intl/server', () => ({
  getTranslations: async () => createTranslator({ locale, messages: messages[locale], namespace: 'institutions' }),
}));

for (const lang of ['en', 'ja', 'ru'] as const) {
  describe(lang, () => {
    it('renders polygon counts and unavailable medicine with source links', async () => {
      locale = lang;
      const t = createTranslator({ locale, messages: messages[locale], namespace: 'institutions' });
      render(await InstitutionFacts({ fact: getInstitutions('bangkok', 'district', 'pathum-wan') }));
      expect(screen.getByText(t('embassiesDistrict', { count: 23 }))).toBeVisible();
      expect(screen.getByText(t('districtDistance'))).toBeVisible();
      expect(screen.getByText(t('medicineUnavailable'))).toBeVisible();
      expect(screen.queryByText(t('medicine', { count: 0 }))).not.toBeInTheDocument();
      expect(screen.getByRole('link', { name: /OpenStreetMap/ })).toHaveAttribute('href', institutionSources.osm);
      expect(screen.getByRole('link', { name: /Wikidata/ })).toHaveAttribute('href', institutionSources.wikidata);
      cleanup();
    });
    it('renders medical facilities, straight-line limits and the JNTO directory', async () => {
      locale = lang;
      const t = createTranslator({ locale, messages: messages[locale], namespace: 'institutions' });
      render(await InstitutionFacts({ fact: getInstitutions('tokyo', 'station', 'hiroo') }));
      expect(screen.getByText(t('embassiesStation', { count: 40 }))).toBeVisible();
      expect(screen.getByText(t('stationDistance'))).toBeVisible();
      expect(screen.getByText(t('medicine', { count: 61 }))).toBeVisible();
      expect(screen.getByText(t('medicineLimit'))).toBeVisible();
      expect(screen.getByRole('link', { name: t('medicineSource') })).toHaveAttribute('href', institutionSources.medicine);
      cleanup();
    });
    it('keeps computed zero visible and missing joins distinct', async () => {
      locale = lang;
      const t = createTranslator({ locale, messages: messages[locale], namespace: 'institutions' });
      render(await InstitutionFacts({ fact: getInstitutions('bangkok', 'district', 'bang-bon') }));
      expect(screen.getByText(t('embassiesDistrict', { count: 0 }))).toBeVisible();
      expect(screen.getByText(t('embassyLimit'))).toBeVisible();
      cleanup();
      render(await InstitutionFacts({ fact: getInstitutions('bangkok', 'district', 'not-a-district') }));
      expect(screen.getByText(t('missing'))).toBeVisible();
      expect(screen.queryByText(t('embassiesDistrict', { count: 0 }))).not.toBeInTheDocument();
      cleanup();
    });
  });
}
