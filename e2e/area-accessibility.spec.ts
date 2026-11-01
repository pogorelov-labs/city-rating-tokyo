import AxeBuilder from '@axe-core/playwright';
import { expect, test } from '@playwright/test';
import en from '../app/src/messages/en/common.json';
import ja from '../app/src/messages/ja/common.json';
import ru from '../app/src/messages/ru/common.json';

const cases = [
  { path: '/station/shibuya', messages: en, width: 1280, height: 800 },
  { path: '/ja/bangkok/station/asok', messages: ja, width: 390, height: 844 },
  { path: '/ru/bangkok/district/bang-bon', messages: ru, width: 320, height: 780 },
];

for (const { path, messages, width, height } of cases) {
  test(`guide accessibility ${path}`, async ({ page }, testInfo) => {
    await page.setViewportSize({ width, height });
    await page.goto(path);
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
    await page.keyboard.press('Tab');
    await expect(page.getByRole('link', { name: messages.areaGuide.skip })).toBeFocused();
    await page.keyboard.press('Enter');
    await expect(page).toHaveURL(/#area-content$/);

    const table = page.getByRole('table', { name: messages.areaGuide.comparison.caption });
    await table.getByRole('button', { name: messages.areaGuide.categories.transport }).click();
    await page.locator('#data-details summary').filter({ hasText: messages.areaGuide.rent.sources }).click();
    const environment = page.locator('summary').filter({ hasText: messages.areaGuide.extras.environment });
    if (await environment.count()) await environment.click();
    await page.getByRole('heading', { name: messages.areaGuide.map.title }).scrollIntoViewIfNeeded();
    await expect(page.locator('.leaflet-container')).toBeVisible({ timeout: 15_000 });

    const result = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa'])
      .analyze();
    await testInfo.attach('accessibility-results', {
      body: JSON.stringify({ violations: result.violations, incomplete: result.incomplete }, null, 2),
      contentType: 'application/json',
    });
    expect(result.violations).toEqual([]);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  });
}
