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

for (const { locale, prefix, messages } of locales) {
  test(`${locale}: same-tab city round trip restores Bangkok filters, comparisons and weights`, async ({ page }) => {
    await page.goto(`${prefix}/bangkok?w=${weights}&flood=1&adult=1&c=watthana,phra-nakhon`);
    const sidebar = page.locator('aside');
    const flood = sidebar.getByRole('checkbox', { name: messages.filter.hideFloodRisk });
    const family = sidebar.getByRole('checkbox', { name: messages.filter.hideAdultZones });
    await expect(flood).toBeChecked();
    await expect(family).toBeChecked();
    if (locale === 'en') await expect(sidebar.getByText('16 of 50 districts match')).toBeVisible();
    if (locale === 'ru') await expect(sidebar.getByText('16 из 50 районов подходят')).toBeVisible();

    const switcher = page.getByRole('navigation', { name: messages.city.switchLabel });
    const tokyo = switcher.getByRole('link', { name: messages.city.tokyo, exact: true });
    const publicHref = new URL((await tokyo.getAttribute('href'))!, page.url());
    expect([...publicHref.searchParams.keys()]).toEqual(['w']);
    await tokyo.click();
    await expect.poll(() => new URL(page.url()).pathname).toBe(prefix || '/');
    await expect(sidebar.getByRole('checkbox', { name: messages.filter.hideFloodRisk })).not.toBeChecked();
    await expect(sidebar.getByRole('checkbox', { name: messages.filter.hideAdultZones })).not.toBeChecked();
    expect(new URL(page.url()).searchParams.has('adult')).toBe(false);
    expect(new URL(page.url()).searchParams.has('flood')).toBe(false);

    await switcher.getByRole('link', { name: messages.city.bangkok, exact: true }).click();
    await expect.poll(() => new URL(page.url()).pathname).toBe(`${prefix}/bangkok`);
    await expect(flood).toBeChecked();
    await expect(family).toBeChecked();
    const params = new URL(page.url()).searchParams;
    expect(Object.fromEntries(['w', 'flood', 'adult', 'c'].map(key => [key, params.get(key)]))).toEqual({
      w: weights, flood: '1', adult: '1', c: 'watthana,phra-nakhon',
    });
    if (locale === 'en') await expect(sidebar.getByText('16 of 50 districts match')).toBeVisible();
    if (locale === 'ru') await expect(sidebar.getByText('16 из 50 районов подходят')).toBeVisible();

    await page.goBack();
    await expect.poll(() => new URL(page.url()).pathname).toBe(prefix || '/');
    await page.goForward();
    await expect.poll(() => new URL(page.url()).pathname).toBe(`${prefix}/bangkok`);
    await expect(flood).toBeChecked();
    await expect(family).toBeChecked();
    expect(new URL(page.url()).searchParams.get('adult')).toBe('1');
    expect(new URL(page.url()).searchParams.get('flood')).toBe('1');
  });
}

test('same-tab city round trip restores Tokyo seismic and selection without leaking into Bangkok', async ({ page }) => {
  await page.goto(`/?w=${weights}&flood=1&adult=1&seismic=1&s=shibuya`);
  const sidebar = page.locator('aside');
  await expect(sidebar.getByRole('checkbox', { name: en.filter.hideHighSeismic })).toBeChecked();
  const switcher = page.getByRole('navigation', { name: en.city.switchLabel });
  await switcher.getByRole('link', { name: en.city.bangkok, exact: true }).click();
  await expect.poll(() => new URL(page.url()).pathname).toBe('/bangkok');
  expect([...new URL(page.url()).searchParams.keys()]).toEqual(['w']);
  await expect(sidebar.getByRole('checkbox', { name: en.filter.hideFloodRisk })).not.toBeChecked();
  await expect(sidebar.getByRole('checkbox', { name: en.filter.hideAdultZones })).not.toBeChecked();
  await switcher.getByRole('link', { name: en.city.tokyo, exact: true }).click();
  await expect.poll(() => new URL(page.url()).pathname).toBe('/');
  await expect(sidebar.getByRole('checkbox', { name: en.filter.hideHighSeismic })).toBeChecked();
  await expect(sidebar.getByRole('checkbox', { name: en.filter.hideFloodRisk })).toBeChecked();
  await expect(sidebar.getByRole('checkbox', { name: en.filter.hideAdultZones })).toBeChecked();
  const params = new URL(page.url()).searchParams;
  expect(Object.fromEntries(['w', 'flood', 'adult', 'seismic', 's'].map(key => [key, params.get(key)]))).toEqual({
    w: weights, flood: '1', adult: '1', seismic: '1', s: 'shibuya',
  });
});
