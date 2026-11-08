import { expect, type Page } from '@playwright/test';

/** Exercise the standard-map fallback using the same control available to visitors. */
export async function useStandardBangkokMap(page: Page) {
  const renderer = page.locator('#bangkok-map-renderer');
  await expect(renderer).toBeVisible({ timeout: 20_000 });
  await renderer.selectOption('leaflet');
  await expect(page.locator('.leaflet-container')).toBeVisible({ timeout: 20_000 });
}
