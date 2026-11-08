import { expect, test, type Locator } from '@playwright/test';
import ru from '../app/src/messages/ru/common.json';

// A visible node can still be clipped by the map or covered by another
// toolbar. Check the real hit target before a trial click can scroll anything.
async function reachable(control: Locator) {
  await expect.poll(() => control.evaluate(el => {
    const r = el.getBoundingClientRect(), map = el.closest('.map-workspace')!.getBoundingClientRect();
    const hit = document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2);
    return r.width > 0 && r.height > 0 && r.top >= map.top - 1 && r.bottom <= map.bottom + 1 &&
      r.left >= map.left - 1 && r.right <= map.right + 1 && !!hit && el.contains(hit);
  })).toBe(true);
  await control.click({ trial: true, timeout: 3_000 });
}

test('wide, short Bangkok workspaces keep every camera command reachable when the air panel opens', async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 720 });
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto('/ru/bangkok');
  const air = page.locator('summary').filter({ hasText: 'Бангкок: воздух и сезоны' });
  const button = (name: string) => page.getByRole('button', { name, exact: true });
  const tools = button(ru.map.mapControls), flat = button(ru.map.view2d);
  await expect(flat).toBeEnabled({ timeout: 30_000 });
  await reachable(flat);
  await air.click();
  for (const height of [720, 540, 440]) {
    await page.setViewportSize({ width: 1280, height });
    await expect(tools).toBeEnabled();
    await reachable(tools);
    for (const name of [ru.map.zoomIn, ru.map.zoomOut, ru.map.resetBearing, ru.map.railNetwork, ru.map.heatmap]) {
      await reachable(button(name));
    }
    await reachable(page.getByRole('combobox', { name: ru.map.rendererLabel }));
    const attribution = page.locator('.maplibregl-ctrl-attrib-button');
    await reachable(attribution);
    if (height === 540) {
      await attribution.click();
      await reachable(page.getByRole('link', { name: 'OpenFreeMap', exact: true }));
      await attribution.click();
    }
    await tools.click();
    await expect(tools).toHaveAttribute('aria-expanded', 'true');
    for (const action of [flat, button(ru.map.buildings), button(ru.map.resetAsok), page.getByRole('combobox', { name: ru.map.cameraMotion })]) {
      // In the shallowest map the menu scrolls internally; the document and
      // workspace must not scroll to rescue a misplaced floating control.
      await action.evaluate(el => {
        const menu = el.closest('.map-control-popover')!;
        const r = el.getBoundingClientRect(), m = menu.getBoundingClientRect();
        if (r.top < m.top) menu.scrollTop += r.top - m.top - 2;
        if (r.bottom > m.bottom) menu.scrollTop += r.bottom - m.bottom + 2;
      });
      await reachable(action);
    }
    await page.keyboard.press('Escape');
    await expect(tools).toHaveAttribute('aria-expanded', 'false');
  }
  // Exercise a command, its reverse and returning to the ordinary desktop.
  await tools.click(); await flat.click();
  await tools.click(); await button(ru.map.view3d).click();
  await air.click();
  await page.setViewportSize({ width: 1280, height: 720 });
  await expect(tools).toBeHidden();
  await reachable(flat);
});

test('wide, short standard map keeps the zoom row clear of the renderer and motion choices', async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 540 });
  await page.goto('/ru/bangkok');
  const renderer = page.getByRole('combobox', { name: ru.map.rendererLabel });
  await renderer.selectOption('leaflet');
  await expect(page.locator('.leaflet-container')).toBeVisible();
  await page.locator('summary').filter({ hasText: 'Бангкок: воздух и сезоны' }).click();
  for (const height of [540, 440, 720]) {
    await page.setViewportSize({ width: 1280, height });
    await reachable(renderer);
    await reachable(page.getByRole('combobox', { name: ru.map.cameraMotion }));
    for (const name of [ru.map.zoomIn, ru.map.zoomOut]) {
      await reachable(page.getByRole('button', { name, exact: true }));
    }
  }
});
