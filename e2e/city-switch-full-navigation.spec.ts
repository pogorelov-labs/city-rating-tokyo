import { test, expect } from '@playwright/test';
import en from '../app/src/messages/en/common.json';
import ja from '../app/src/messages/ja/common.json';

const weights = '28,18,12,0,12,0,0,12,18,0';

for (const scenario of [
  { name: 'English Tokyo to Bangkok', from: `/?w=${weights}&mr=150000`, city: en.city.bangkok, destination: '/bangkok', weightsLabel: en.filter.weights },
  { name: 'Japanese Bangkok to Tokyo', from: `/ja/bangkok?w=${weights}&mr=20000`, city: ja.city.tokyo, destination: '/ja', weightsLabel: ja.filter.weights },
]) {
  test(`${scenario.name} carries weights into a fresh browser context`, async ({ page, browser }) => {
    await page.goto(scenario.from);
    const cityLink = page.getByRole('navigation', { name: scenario.name.startsWith('English') ? en.city.switchLabel : ja.city.switchLabel })
      .getByRole('link', { name: scenario.city, exact: true });
    await expect.poll(async () => {
      const href = await cityLink.getAttribute('href');
      return href ? new URL(href, page.url()).searchParams.get('w') : null;
    }).toBe(weights);
    const href = new URL((await cityLink.getAttribute('href'))!, page.url());
    expect(href.pathname).toBe(scenario.destination);
    expect([...href.searchParams.keys()]).toEqual(['w']);

    const freshContext = await browser.newContext();
    try {
      const fresh = await freshContext.newPage();
      await fresh.goto(href.href);
      await expect.poll(() => new URL(fresh.url()).searchParams.get('w')).toBe(weights);
      expect(new URL(fresh.url()).searchParams.has('mr')).toBe(false);
      const weightGroup = fresh.getByRole('heading', { name: scenario.weightsLabel, exact: true }).locator('..');
      await expect(weightGroup.locator('input[type="range"]').first()).toHaveValue('28');
    } finally {
      await freshContext.close();
    }
  });
}
