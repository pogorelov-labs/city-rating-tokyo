import { test, expect } from '@playwright/test';
import en from '../app/src/messages/en/common.json';
import ja from '../app/src/messages/ja/common.json';
import ru from '../app/src/messages/ru/common.json';

const locales = [
  { prefix: '', messages: en },
  { prefix: '/ja', messages: ja },
  { prefix: '/ru', messages: ru },
];
const routes = [
  '/station/shibuya',
  '/bangkok/station/asok',
  '/bangkok/district/watthana',
];

test.describe('area guides', () => {
  for (const { prefix, messages } of locales) {
    for (const route of routes) {
      test(`${prefix || '/en'}${route} renders guide and evidence`, async ({ page }) => {
        const response = await page.goto(`${prefix}${route}`);
        expect(response?.status()).toBe(200);
        await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
        await expect(page.getByRole('heading', { name: messages.areaGuide.comparison.title })).toBeVisible();
        const table = page.getByRole('table', { name: messages.areaGuide.comparison.caption });
        await expect(table).toBeVisible();
        const category = table.getByRole('button', { name: messages.areaGuide.categories.transport });
        await category.click();
        await expect(category).toHaveAttribute('aria-expanded', 'true');
        await expect(table.getByText(messages.areaGuide.explanations.transport)).toBeVisible();
        await expect(page.getByRole('heading', { name: messages.areaGuide.commute.title })).toBeVisible();
        await page.getByRole('heading', { name: messages.areaGuide.map.title }).scrollIntoViewIfNeeded();
        await expect(page.locator('.leaflet-container')).toBeVisible({ timeout: 15_000 });
        await page.getByRole('link', { name: `${messages.areaGuide.rent.sources} ↓`, exact: true }).click();
        await expect(page.getByText(messages.areaGuide.rent.notLease)).toBeVisible();
      });
    }
    test(`${prefix || '/en'} Tokyo missing rent stays unavailable`, async ({ page }) => {
      await page.goto(`${prefix}/station/gora`);
      await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
      await expect(page.getByText(messages.areaGuide.rent.provenance.unavailable, { exact: true }).filter({ visible: true })).toHaveCount(2);
      await page.getByRole('link', { name: `${messages.areaGuide.rent.sources} ↓`, exact: true }).click();
      await expect(page.getByText(messages.areaGuide.rent.definition.unavailable, { exact: true })).toBeVisible();
      await expect(page.getByText(messages.areaGuide.rent.definition.estimate, { exact: true })).toHaveCount(0);
    });
  }

  test('destination, comparison and weights survive locale switching', async ({ page }) => {
    const weights = '28,18,12,0,12,0,0,12,18,0';
    await page.goto(`/bangkok/district/watthana?w=${weights}`);
    const destination = page.getByRole('combobox', { name: en.areaGuide.commute.destination });
    await destination.selectOption('asok');
    const reference = page.getByRole('combobox', { name: en.areaGuide.comparison.reference });
    const peer = await reference.locator('option').nth(1).getAttribute('value');
    expect(peer).toBeTruthy();
    await reference.selectOption(peer!);
    await page.getByRole('button', { name: 'JA', exact: true }).click();
    await expect(page).toHaveURL(/\/ja\/bangkok\/district\/watthana/);
    await expect.poll(() => new URL(page.url()).searchParams.get('hub')).toBe('asok');
    expect(new URL(page.url()).searchParams.get('reference')).toBe(peer);
    expect(new URL(page.url()).searchParams.get('w')).toBe(weights);
    await expect(page.getByRole('combobox', { name: ja.areaGuide.commute.destination })).toHaveValue('asok');
    await expect(page.getByRole('combobox', { name: ja.areaGuide.comparison.reference })).toHaveValue(peer!);
  });

  test('back restores a balanced guide after changing a nearby area', async ({ page }) => {
    await page.goto('/station/shibuya');
    await expect(page.getByRole('combobox', { name: en.areaGuide.score.priorities })).toHaveValue('balanced');
    const section = page.locator('section').filter({ has: page.getByRole('heading', { name: en.areaGuide.extras.neighbors }) });
    const link = section.getByRole('link').first();
    await expect(link).toBeVisible();
    await link.click();
    await expect(page).not.toHaveURL(/\/station\/shibuya(?:\?|$)/);
    const neighborPath = new URL(page.url()).pathname;
    await page.getByRole('combobox', { name: en.areaGuide.score.priorities }).selectOption('family');
    await expect.poll(() => new URL(page.url()).searchParams.get('w')).not.toBeNull();
    await page.goBack();
    await expect(page).toHaveURL(/\/station\/shibuya(?:\?|$)/);
    await expect(page.getByRole('combobox', { name: en.areaGuide.score.priorities })).toHaveValue('balanced');
    await expect.poll(() => new URL(page.url()).searchParams.get('w')).toBeNull();
    await page.goForward();
    await expect.poll(() => new URL(page.url()).pathname).toBe(neighborPath);
    await expect(page.getByRole('combobox', { name: en.areaGuide.score.priorities })).toHaveValue('family');
    await expect.poll(() => new URL(page.url()).searchParams.get('w')).not.toBeNull();
  });


  test('same-guide history restores destination, reference and weights', async ({ page }) => {
    await page.goto('/bangkok/district/watthana?hub=asok');
    const destination = page.getByRole('combobox', { name: en.areaGuide.commute.destination });
    const reference = page.getByRole('combobox', { name: en.areaGuide.comparison.reference });
    const priorities = page.getByRole('combobox', { name: en.areaGuide.score.priorities });
    await expect(destination).toHaveValue('asok');
    await page.evaluate(() => window.history.pushState(null, '', window.location.href));
    await destination.selectOption('siam');
    const peer = await reference.locator('option').nth(1).getAttribute('value');
    expect(peer).toBeTruthy();
    await reference.selectOption(peer!);
    await priorities.selectOption('family');
    await expect.poll(() => new URL(page.url()).searchParams.get('w')).not.toBeNull();
    await page.goBack();
    await expect(destination).toHaveValue('asok');
    await expect(reference).toHaveValue('median');
    await expect(priorities).toHaveValue('balanced');
    await expect.poll(() => new URL(page.url()).searchParams.get('w')).toBeNull();
  });

});
