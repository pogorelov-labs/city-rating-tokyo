import { expect, test } from '@playwright/test';

declare global {
  interface Window {
    guideLabTimings: { lcp: number; cls: number };
  }
}

for (const path of ['/station/shibuya', '/bangkok/station/asok', '/bangkok/district/watthana']) {
  test(`guide lab timings ${path}`, async ({ page }, testInfo) => {
    await page.setViewportSize({ width: 1280, height: 800 });
    await page.addInitScript(() => {
      window.guideLabTimings = { lcp: 0, cls: 0 };
      new PerformanceObserver(list => {
        for (const entry of list.getEntries()) window.guideLabTimings.lcp = entry.startTime;
      }).observe({ type: 'largest-contentful-paint', buffered: true });
      new PerformanceObserver(list => {
        for (const entry of list.getEntries()) {
          const shift = entry as PerformanceEntry & { hadRecentInput: boolean; value: number };
          if (!shift.hadRecentInput) window.guideLabTimings.cls += shift.value;
        }
      }).observe({ type: 'layout-shift', buffered: true });
    });
    await page.goto(path);
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
    await page.waitForLoadState('networkidle');
    const timings = await page.evaluate(() => window.guideLabTimings);
    await testInfo.attach('local-lab-timings', {
      body: JSON.stringify({ path, ...timings, scope: 'local single run; no INP or field percentile measurement' }),
      contentType: 'application/json',
    });
    expect(timings.lcp).toBeGreaterThan(0);
    expect(timings.cls).toBeLessThanOrEqual(0.1);
  });
}
