import { chromium } from '@playwright/test';
import { mkdir, open, writeFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import os from 'node:os';

const args = process.argv.slice(2);
const arg = (name, fallback) => { const i = args.indexOf(name); return i < 0 ? fallback : args[i + 1]; };
const output = resolve(arg('--output', 'research/bangkok/notes/render-stages/after.json'));
const baseURL = arg('--base-url', 'http://localhost:3170');
const runs = Number(arg('--samples', '3'));
const renderer = arg('--renderer', 'maplibre');
if (!Number.isInteger(runs) || runs < 1 || !['maplibre', 'leaflet'].includes(renderer)) throw new Error('Use a positive integer --samples and --renderer maplibre|leaflet');
const camera = { lng: 100.5606, lat: 13.7374, zoom: 16, pitch: renderer === 'leaflet' ? 0 : 50, bearing: -20 };
const report = { capturedAt: new Date().toISOString(), cpu: os.cpus()[0]?.model, renderer, runs,
  method: 'Production server. React profiling availability is recorded per run. Fresh Chrome per run, 1440x900 DPR1. Stage CPU numbers are elapsed main-thread time, not sampled CPU utilization. Async source completion includes queueing; GPU queries sample 1/8 frames. Percentiles retain last 256 observations; counts/totals cover the whole phase. Nested/inclusive stages must not be summed. Ablations are incremental workloads, not additive per-layer accounting.', results: [] };
await mkdir(dirname(output), { recursive: true });
for (let run = 0; run < runs; run++) {
  const browser = await chromium.launch({ channel: 'chrome', headless: !args.includes('--headed') });
  const bcdp = await browser.newBrowserCDPSession();
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1, locale: 'en-US' });
  const page = await context.newPage(), cdp = await context.newCDPSession(page);
  const row = { run: run + 1, phases: {}, errors: [] };
  try {
    const info = await bcdp.send('SystemInfo.getInfo');
    row.gpu = info.gpu.auxAttributes?.glRenderer; row.browser = browser.version();
    if (/swiftshader|llvmpipe|software/i.test(row.gpu)) throw new Error('Software GPU; do not compare to hardware runs');
    page.on('pageerror', (e) => row.errors.push(e.message));
    await cdp.send('Performance.enable');
    await page.addInitScript((camera) => { window.__bangkokInitialCamera = camera; }, camera);
    await page.goto(`${baseURL}/bangkok/prototype/${renderer}?lv=grid&profile=1`);
    await page.bringToFront();
    const settle = async () => {
      await page.waitForFunction(() => window.__bangkokRenderer?.ready(), null, { timeout: 45_000 });
      await page.waitForTimeout(180);
    };
    await settle();
    if (await page.locator('nextjs-portal').count()) throw new Error('Use next build --profile and next start, not next dev');
    row.readyMs = await page.evaluate(() => performance.now());
    const snap = () => page.evaluate(() => ({ ...window.__bangkokProfile.snapshot(), renderer: window.__bangkokRenderer.stats() }));
    row.phases.cold = await snap();
    row.reactProfilingAvailable = Object.keys(row.phases.cold.stages).some((name) => name.startsWith('react.'));
    const phase = async (name, fn) => {
      await page.evaluate(() => window.__bangkokProfile.reset());
      const metrics = async () => Object.fromEntries((await cdp.send('Performance.getMetrics')).metrics.map((m) => [m.name, m.value]));
      const before = await metrics();
      await fn(); await settle(); row.phases[name] = await snap();
      const after = await metrics();
      row.phases[name].browserWork = Object.fromEntries(['TaskDuration', 'ScriptDuration', 'LayoutDuration', 'RecalcStyleDuration', 'LayoutCount', 'RecalcStyleCount'].map((k) => [k, after[k] - before[k]]));
    };
    const weight = async (i) => {
      const version = await page.evaluate((i) => {
        const input = document.querySelector('aside input[aria-label="Weights: Food & Dining"]');
        if (!input) throw new Error('English food-weight control missing');
        const before = window.__bangkokGridPaint?.version ?? 0;
        Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(input, i % 2 ? '12' : '25');
        input.dispatchEvent(new Event('input', { bubbles: true })); return before;
      }, i);
      await page.waitForFunction((before) => window.__bangkokGridPaint.version > before, version); await settle();
    };
    await phase('weights', async () => { for (let i = 0; i < 8; i++) await weight(i); });
    await phase('family-filter', async () => {
      const box = page.locator('aside').getByRole('checkbox', { name: /Family-friendly/ });
      for (let i = 0; i < 6; i++) { await box.setChecked(i % 2 === 0); await settle(); }
    });
    if (renderer === 'maplibre') await phase('buildings-toggle', async () => {
      for (let i = 0; i < 6; i++) { await page.getByRole('button', { name: 'Buildings', exact: true }).click(); await settle(); }
    });
    const motion = async (view = camera) => {
      for (const c of [{ ...view, lng: view.lng + .0124, zoom: view.zoom + 1 }, view]) {
        await page.evaluate((c) => window.__bangkokRenderer.setCamera(c, 1300), c); await page.waitForTimeout(1450);
      }
    };
    await motion(); await settle();
    const trace = args.includes('--trace') && run === 0;
    if (trace) await bcdp.send('Tracing.start', { categories: 'devtools.timeline,v8.execute,disabled-by-default-v8.cpu_profiler,cc,gpu', transferMode: 'ReturnAsStream' });
    await phase('camera', motion);
    if (trace) {
      const done = new Promise((r) => bcdp.once('Tracing.tracingComplete', r));
      await bcdp.send('Tracing.end'); const { stream } = await done;
      const file = await open(output.replace(/\.json$/, '.trace.json'), 'w');
      try {
        let eof = false;
        while (!eof) { const chunk = await bcdp.send('IO.read', { handle: stream }); await file.write(chunk.base64Encoded ? Buffer.from(chunk.data, 'base64') : chunk.data); eof = chunk.eof; }
      } finally { await file.close(); await bcdp.send('IO.close', { handle: stream }); }
    }
    if (renderer === 'maplibre') {
      await page.evaluate(() => { window.__bangkokProfile.gpuTarget = 'grid'; });
      await phase('grid-gpu', motion);
      await page.evaluate(() => { window.__bangkokProfile.gpuTarget = 'frame'; });
      // Paired all/off/all at a resident, fixed camera path. Results include
      // batching/overdraw interactions; they are not individual draw durations.
      for (const group of ['buildings', 'grid', 'rail', 'labels']) {
        await page.evaluate((g) => window.__bangkokRenderer.setLayerGroup(g, false), group); await settle();
        await phase(`without-${group}`, motion);
        await page.evaluate((g) => window.__bangkokRenderer.setLayerGroup(g, true), group); await settle();
      }
      await phase('camera-repeat', motion);
      if (args.includes('--scenes')) {
        for (const [level, view] of [
          ['Districts', { lng: 100.58, lat: 13.77, zoom: 12, pitch: 0, bearing: 0 }],
          ['Stations', { ...camera, zoom: 14.5, pitch: 35 }],
        ]) {
          await page.getByRole('radio', { name: level, exact: true }).click();
          await page.evaluate((c) => window.__bangkokRenderer.setCamera(c), view); await settle();
          await motion(view); await settle();
          await phase(`${level}-all`, () => motion(view));
          if (run === 0) await page.screenshot({ path: resolve(dirname(output), `${level.toLowerCase()}.png`) });
          for (const group of ['areas', 'labels', 'rail']) {
            await page.evaluate((g) => window.__bangkokRenderer.setLayerGroup(g, false), group); await settle();
            await phase(`${level}-without-${group}`, () => motion(view));
            await page.evaluate((g) => window.__bangkokRenderer.setLayerGroup(g, true), group); await settle();
          }
        }
        await phase('named-hover', async () => {
          const box = await page.getByTestId('maplibre-map').boundingBox();
          for (let i = 0; i < 20; i++) {
            const point = await page.evaluate((i) => window.__bangkokRenderer.project(i % 2 ? 100.56036 : 100.553, i % 2 ? 13.73704 : 13.7405), i);
            await page.mouse.move(box.x + point.x, box.y + point.y); await page.waitForTimeout(40);
          }
          await page.mouse.move(10, 10);
        });
      }
    }
    await cdp.send('HeapProfiler.collectGarbage'); row.memory = await cdp.send('Runtime.getHeapUsage');
    row.dom = await cdp.send('Memory.getDOMCounters'); row.workers = page.workers().length;
    if (run === 0) await page.screenshot({ path: output.replace(/\.json$/, '.png') });
    console.log(JSON.stringify({ run: row.run, gpu: row.phases.camera.gpuStatus, frames: row.phases.camera.stages['map.frame'], weights: row.phases.weights.stages['areas.sync'], labelRebuilds: row.phases.weights.stages['source.bkk-labels.submit']?.calls ?? 0 }));
  } catch (e) { row.failure = String(e); console.error(row.failure); process.exitCode = 1; }
  finally { report.results.push(row); await writeFile(output, JSON.stringify(report, null, 2) + '\n'); await browser.close(); }
}
