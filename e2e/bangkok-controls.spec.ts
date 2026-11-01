import { test, expect } from '@playwright/test';
import { resolve } from 'node:path';

test.use({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });

test('phone camera tools leave room for the map and restore keyboard focus', async ({ page }) => {
  await page.goto('/bangkok?lv=station&s=st.asok');
  const tools = page.getByRole('button', { name: '3D map controls' });
  await expect(tools).toBeEnabled({ timeout: 30_000 });
  await expect(page.getByRole('button', { name: 'Buildings' })).toBeHidden();
  await tools.tap();
  const buildings = page.getByRole('button', { name: 'Buildings' });
  await expect(buildings).toHaveAttribute('aria-pressed', 'true');
  await buildings.tap();
  await expect(tools).toBeFocused();
  await tools.press('Enter');
  await expect(buildings).toHaveAttribute('aria-pressed', 'false');
  await buildings.press('Escape');
  await expect(tools).toBeFocused();
  await expect(tools).toHaveAttribute('aria-expanded', 'false');
  expect(new URL(page.url()).searchParams.get('s')).toBe('st.asok');
  const active = page.getByRole('radio', { name: 'Stations', exact: true });
  await active.press('End');
  await expect(page.getByRole('radio', { name: /200 m/ })).toBeFocused();
  await expect(page.getByRole('radio', { name: /200 m/ })).toHaveAttribute('aria-checked', 'true');
  await page.keyboard.press('Home');
  await expect(page.getByRole('radio', { name: 'Districts' })).toBeFocused();
});

test('filter sheet follows the finger, cancels a drag, and leaves filter scrolling native', async ({ page, context }) => {
  await page.goto('/bangkok?adult=1');
  const launcher = page.getByRole('button', { name: 'Filters', exact: true });
  await launcher.tap();
  const sheet = page.getByRole('dialog', { name: 'Filters & Ranking' });
  await expect(sheet.getByRole('button', { name: 'Close filters' })).toBeFocused();
  await expect(sheet.getByRole('checkbox', { name: /Family-friendly/ })).toBeChecked();
  await expect.poll(() => sheet.evaluate(el => el.matches(':modal') && el.getAnimations().every(a => a.playState !== 'running') && el.dataset.open === 'true')).toBe(true);
  const grip = (await sheet.locator('.map-filter-grip').boundingBox())!;
  const x = Math.round(grip.x + grip.width / 2), y = Math.round(grip.y + 15);
  const client = await context.newCDPSession(page);
  const touch = (type: 'touchStart' | 'touchMove' | 'touchEnd' | 'touchCancel', dy = 0) =>
    client.send('Input.dispatchTouchEvent', { type, touchPoints: type === 'touchEnd' || type === 'touchCancel' ? [] : [{ x, y: y + dy }] });
  await touch('touchStart'); await touch('touchMove', 42);
  await expect(sheet).toHaveAttribute('data-dragging', 'true');
  await expect.poll(() => sheet.evaluate(el => Math.round(el.getBoundingClientRect().top))).toBe(Math.round(grip.y + 42));
  await touch('touchCancel');
  await expect.poll(() => sheet.evaluate(el => Math.round(el.getBoundingClientRect().top))).toBe(Math.round(grip.y));
  // Start over plain body text, not a slider/checkbox, and deliver a swipe
  // across display frames so Chromium can distinguish scrolling from a tap.
  const weights = (await sheet.getByRole('heading', { name: 'Weights', exact: true }).boundingBox())!;
  const bodyOffset = Math.round(weights.y + weights.height / 2) - y;
  await touch('touchStart', bodyOffset);
  for (const travel of [24, 48, 72, 96, 120, 144]) {
    await touch('touchMove', bodyOffset - travel);
    await page.evaluate(() => new Promise<void>(resolve => requestAnimationFrame(() => resolve())));
  }
  await touch('touchEnd');
  await expect.poll(() => sheet.locator('.map-filter-scroll').evaluate(el => el.scrollTop)).toBeGreaterThan(0);
  await touch('touchStart'); await touch('touchMove', 160); await touch('touchEnd');
  await expect(sheet).toBeHidden();
  expect(new URL(page.url()).searchParams.get('adult')).toBe('1');
  await client.detach();
});

test('reduced-motion sheet closes on Escape or a ranking choice without losing filters', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto('/bangkok?adult=1');
  const launcher = page.getByRole('button', { name: 'Filters', exact: true });
  await launcher.focus(); await page.keyboard.press('Enter');
  const sheet = page.getByRole('dialog', { name: 'Filters & Ranking' });
  const close = sheet.getByRole('button', { name: 'Close filters' });
  await expect(close).toBeFocused();
  await expect(sheet.getByRole('slider', { name: /rent.*maximum/i })).toHaveAttribute('aria-valuetext', 'No limit');
  await expect(sheet.getByRole('slider', { name: /commute.*minimum/i })).toHaveCount(1);
  await page.addScriptTag({ path: resolve('app/node_modules/axe-core/axe.min.js') });
  const violations = await page.evaluate(async () => {
    const { axe } = window as unknown as { axe: typeof import('axe-core') };
    const result = await axe.run({ include: ['.map-filter-grip', 'dialog:modal input[type="range"]'] },
      { runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21aa'] } });
    return result.violations.map(v => v.id);
  });
  expect(violations).toEqual([]);
  expect(await sheet.evaluate(el => getComputedStyle(el).transitionDuration)).toBe('0s');
  await page.keyboard.press('Tab');
  expect(await sheet.evaluate(el => el.contains(document.activeElement))).toBe(true);
  await page.keyboard.press('Escape');
  await expect(sheet).toBeHidden(); await expect(launcher).toBeFocused();
  await launcher.tap();
  await page.setViewportSize({ width: 900, height: 700 });
  await expect(sheet).toBeHidden();
  await expect.poll(() => page.evaluate(() => document.querySelectorAll('dialog:modal').length)).toBe(0);
  await page.setViewportSize({ width: 390, height: 844 });
  await launcher.tap();
  await sheet.locator('[data-umami-event="ranked-select"]').first().tap();
  await expect(sheet).toBeHidden();
  await expect.poll(() => new URL(page.url()).searchParams.get('s')).toBeTruthy();
  expect(new URL(page.url()).searchParams.get('adult')).toBe('1');
});
