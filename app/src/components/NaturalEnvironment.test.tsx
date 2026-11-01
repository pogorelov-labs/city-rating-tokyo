import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { Providers, messages } from '@/test/providers';
import { NaturalEnvironment } from './NaturalEnvironment';

vi.mock('@/lib/use-is-touch', () => ({ useIsTouch: () => false }));

describe('seismic probability presentation', () => {
  for (const locale of ['en', 'ja', 'ru'] as const) {
    it(`${locale} classifies the displayed probability using the producer's bands`, () => {
      const { rerender } = render(<Providers locale={locale}><NaturalEnvironment environment={{ seismic_prob_i60: 0.089, seismic_risk_tier: 'low' }} /></Providers>);
      const row = screen.getByText(messages[locale].station.seismicRisk).parentElement!;
      expect(row).toHaveTextContent(messages[locale].seismicTiers.high.label);
      expect(row).toHaveTextContent(new Intl.NumberFormat(locale, { maximumFractionDigits: 1 }).format(8.9));
      for (const [probability, tier] of [
        [0.0299, 'low'], [0.03, 'moderate'], [0.0599, 'moderate'],
        [0.06, 'high'], [0.2599, 'high'], [0.26, 'very_high'], [0.27, 'very_high'],
      ] as const) {
        rerender(<Providers locale={locale}><NaturalEnvironment environment={{ seismic_prob_i60: probability }} /></Providers>);
        const probabilityRow = screen.getByText(messages[locale].station.seismicRisk).parentElement;
        expect(probabilityRow).toHaveTextContent(messages[locale].seismicTiers[tier].label);
        expect(probabilityRow).toHaveTextContent(new Intl.NumberFormat(locale, { maximumFractionDigits: 2 }).format(probability * 100));
      }
      for (const tier of ['low', 'moderate', 'high', 'very_high'] as const) {
        expect(screen.getByText(new RegExp(messages[locale].seismicTiers[tier].description))).toBeInTheDocument();
      }
    });
  }
});
