import { test, expect } from '@playwright/test';
import en from '../app/src/messages/en/common.json';
import ja from '../app/src/messages/ja/common.json';
import ru from '../app/src/messages/ru/common.json';

const weights = '28,18,12,0,12,0,0,12,18,0';
const locales = [
  { locale: 'en', prefix: '', messages: en },
  { locale: 'ja', prefix: '/ja', messages: ja },
  { locale: 'ru', prefix: '/ru', messages: ru },
];

for (const { locale, prefix, messages } of locales) {
  for (const direction of [
    { name: 'Tokyo to Bangkok', from: `${prefix || '/'}?w=${weights}&mr=150000&mc=50`, city: messages.city.bangkok, destination: `${prefix}/bangkok` },
    { name: 'Bangkok to Tokyo', from: `${prefix}/bangkok?w=${weights}&mr=20000&mc=50`, city: messages.city.tokyo, destination: prefix || '/' },
  ]) {
    test(`${locale} ${direction.name} carries weights into a fresh browser context`, async ({ page, browser }) => {
      await page.goto(direction.from);
      const cityLink = page.getByRole('navigation', { name: messages.city.switchLabel })
        .getByRole('link', { name: direction.city, exact: true });
      await expect.poll(async () => {
        const href = await cityLink.getAttribute('href');
        return href ? new URL(href, page.url()).searchParams.get('w') : null;
      }).toBe(weights);
      const href = new URL((await cityLink.getAttribute('href'))!, page.url());
      expect(href.pathname).toBe(direction.destination);
      expect([...href.searchParams.keys()]).toEqual(['w']);

      const freshContext = await browser.newContext();
      try {
        const fresh = await freshContext.newPage();
        await fresh.goto(href.href);
        await expect(fresh.locator('html')).toHaveAttribute('lang', locale);
        await expect.poll(() => new URL(fresh.url()).searchParams.get('w')).toBe(weights);
        expect([...new URL(fresh.url()).searchParams.keys()]).toEqual(['w']);
        const weightGroup = fresh.getByRole('heading', { name: messages.filter.weights, exact: true }).locator('..');
        const controls = weightGroup.locator('input[type="range"]');
        await expect(controls).toHaveCount(10);
        for (const [index, value] of weights.split(',').entries()) {
          await expect(controls.nth(index)).toHaveValue(value);
        }
      } finally {
        await freshContext.close();
      }
    });
  }
}
