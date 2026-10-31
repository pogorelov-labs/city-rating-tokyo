import { expect, test } from '@playwright/test';
import environment from '../app/src/data/environment-data.json';
import en from '../app/src/messages/en/common.json';
import ja from '../app/src/messages/ja/common.json';
import ru from '../app/src/messages/ru/common.json';

const locales = [
  { locale: 'en', prefix: '', messages: en },
  { locale: 'ja', prefix: '/ja', messages: ja },
  { locale: 'ru', prefix: '/ru', messages: ru },
] as const;

for (const { locale, prefix, messages } of locales) {
  test(`${locale}: Tokyo seismic filter includes the 26% boundary`, async ({ page }) => {
    await page.goto(prefix || '/');
    const caption = messages.filter.seismicThreshold;
    expect(caption).toContain(locale === 'ja' ? '26%以上' : '≥26%');
    await expect(page.getByRole('checkbox', {
      name: `${messages.filter.hideHighSeismic}${caption}`,
      exact: true,
    })).toBeVisible();
  });

  for (const [slug, tier, probability] of [
    ['kichijoji', 'high', 0.0888],
    ['ageo', 'moderate', 0.0597],
  ] as const) {
    test(`${locale}: ${slug} shows its seismic probability and producer band`, async ({ page }) => {
      expect(environment[slug].seismic_prob_i60).toBe(probability);
      expect(environment[slug].seismic_risk_tier).toBe(tier);
      const response = await page.goto(`${prefix}/station/${slug}`);
      expect(response?.status()).toBe(200);
      const disclosure = page.locator('details').filter({ has: page.locator('summary').filter({ hasText: messages.areaGuide.extras.environment }) });
      await disclosure.locator('summary').click();
      const section = disclosure.locator('section').filter({ has: page.getByText(messages.station.seismicRisk, { exact: true }) });
      const row = section.getByText(messages.station.seismicRisk, { exact: true }).locator('..');
      await expect(row).toContainText(messages.seismicTiers[tier].label);
      await expect(row).toContainText(`${new Intl.NumberFormat(locale, { maximumFractionDigits: 2 }).format(probability * 100)}%`);
      for (const band of ['low', 'moderate', 'high', 'very_high'] as const) {
        await expect(section.getByText(`${messages.seismicTiers[band].label} (${messages.seismicTiers[band].description})`, { exact: true })).toBeVisible();
      }
    });
  }
}
