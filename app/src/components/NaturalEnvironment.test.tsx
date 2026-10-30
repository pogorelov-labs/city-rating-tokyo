import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { Providers, messages } from '@/test/providers';
import { NaturalEnvironment } from './NaturalEnvironment';

vi.mock('@/lib/use-is-touch', () => ({ useIsTouch: () => false }));

describe('seismic probability presentation', () => {
  for (const locale of ['en', 'ja', 'ru'] as const) {
    it(`${locale} uses the displayed probability's legend instead of an unrelated stored tier`, () => {
      render(<Providers locale={locale}><NaturalEnvironment environment={{ seismic_prob_i60: 0.089, seismic_risk_tier: 'high' }} /></Providers>);
      const row = screen.getByText(messages[locale].station.seismicRisk).parentElement!;
      expect(row).toHaveTextContent(messages[locale].seismicTiers.moderate.label);
      expect(row).toHaveTextContent(new Intl.NumberFormat(locale, { maximumFractionDigits: 1 }).format(8.9));
    });
  }
});
