import { expect, test } from '@playwright/test';
import en from '../app/src/messages/en/common.json';
import ja from '../app/src/messages/ja/common.json';
import ru from '../app/src/messages/ru/common.json';

const locales = [{ prefix: '', messages: en }, { prefix: '/ja', messages: ja }, { prefix: '/ru', messages: ru }];
const areas = [
  { name: 'Tokyo station', query: '/?s=akihabara', detail: '/station/akihabara', city: 'tokyo', kind: 'station' },
  { name: 'Bangkok district', query: '/bangkok?lv=district&s=pathum-wan', detail: '/bangkok/district/pathum-wan', city: 'bangkok', kind: 'district' },
  { name: 'Bangkok station', query: '/bangkok?lv=station&s=st.asok', detail: '/bangkok/station/asok', city: 'bangkok', kind: 'station' },
] as const;

for (const touch of [false, true]) {
  test.describe(touch ? 'touch compact cards' : 'desktop compact cards', () => {
    test.use({ viewport: touch ? { width: 390, height: 844 } : { width: 1280, height: 800 }, isMobile: touch, hasTouch: touch });
    for (const { prefix, messages } of locales) for (const area of areas) {
      test(`${prefix || '/en'} ${area.name}`, async ({ page }) => {
        await page.goto(`${prefix}${area.query}`);
        const card = touch ? page.getByRole('dialog').filter({ has: page.getByRole('link', { name: messages.areaGuide.compact.explore }) }) : page.locator('.area-guide-popup');
        await expect(card).toBeVisible({ timeout: 30_000 });
        await expect(card.getByText(`${messages.areaGuide.cities[area.city]} · ${messages.areaGuide.kinds[area.kind]}`, { exact: true })).toBeVisible();
        await expect(card.getByText(`${area.city === 'tokyo' ? messages.areaGuide.rent.smallTokyo : messages.areaGuide.rent.oneBedroom} ${messages.areaGuide.rent.perMonth}`, { exact: true })).toBeVisible();
        await expect(card.getByText(messages.areaGuide.compact.scope, { exact: false })).toBeVisible();
        const link = card.getByRole('link', { name: messages.areaGuide.compact.explore });
        await expect(link).toHaveAttribute('href', `${prefix}${area.detail}`);
        const compare = card.getByRole('button', { name: messages.map.compare, exact: true });
        const press = async (target: typeof compare) => touch ? target.tap() : target.click();
        await expect.poll(async () => { const box = await link.boundingBox(); return box ? box.y + box.height : Infinity; }, { timeout: 15_000 }).toBeLessThanOrEqual(touch ? 844 : 800);
        const bounds = await link.boundingBox();
        const outer = await card.boundingBox();
        expect(bounds && outer).toBeTruthy();
        expect(bounds!.x).toBeGreaterThanOrEqual(outer!.x - 1);
        expect(bounds!.x + bounds!.width).toBeLessThanOrEqual(Math.min(outer!.x + outer!.width, touch ? 390 : 1280) + 1);
        expect(bounds!.y).toBeGreaterThanOrEqual(0);
        expect(bounds!.y + bounds!.height).toBeLessThanOrEqual(touch ? 844 : 800);
        await press(compare);
        const remove = card.getByRole('button', { name: messages.map.removeCompare, exact: true });
        await expect(remove).toBeVisible();
        await press(remove);
        await expect(compare).toBeVisible();
        const close = card.getByRole('button', { name: touch ? (area.kind === 'district' ? messages.map.closeCardDistrict : messages.map.closeCard) : messages.areaGuide.compact.close });
        await press(close);
        await expect(card).toBeHidden();
        await expect.poll(() => new URL(page.url()).searchParams.get('s')).toBeNull();
        expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
      });
    }
  });
}

test('Tokyo desktop reopens a closed, already centered station from search', async ({ page }) => {
  await page.setViewportSize({ width: 1920, height: 1200 });
  await page.goto('/?s=akihabara');
  const popup = page.locator('.area-guide-popup');
  await expect(popup).toBeVisible({ timeout: 30_000 });
  await popup.getByRole('button', { name: en.areaGuide.compact.close }).click();
  await expect(popup).toBeHidden();
  await expect.poll(() => new URL(page.url()).searchParams.get('s')).toBeNull();
  await page.getByPlaceholder(en.filter.searchPlaceholder).filter({ visible: true }).fill('Akihabara');
  await page.locator('[data-umami-event="search-select"][data-umami-event-station="akihabara"]').filter({ visible: true }).click();
  await expect.poll(() => new URL(page.url()).searchParams.get('s')).toBe('akihabara');
  await expect(popup).toBeVisible({ timeout: 10_000 });
});
