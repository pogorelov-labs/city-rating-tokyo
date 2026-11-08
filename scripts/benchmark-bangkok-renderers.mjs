import { chromium } from '@playwright/test';
import { mkdir, writeFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { execFileSync } from 'node:child_process';
import os from 'node:os';

const args = process.argv.slice(2);
const arg = (name, fallback) => { const i = args.indexOf(name); return i < 0 ? fallback : args[i + 1]; };
const baseURL = arg('--base-url', 'http://localhost:3170');
const output = resolve(arg('--output', 'research/bangkok/notes/renderer-benchmark/results.json'));
const samples = Number(arg('--samples', '3'));
const headed = args.includes('--headed');
const viewport = { width: 1440, height: 900 };
const percentile = (a, p) => { const s = [...a].sort((x, y) => x - y); return s[Math.min(s.length - 1, Math.floor(s.length * p))] ?? 0; };
await mkdir(dirname(output), { recursive: true });
const results = [];
const modes = [
  { name: 'leaflet-2d', renderer: 'leaflet', pitch: 0, bearing: 0 },
  { name: 'maplibre-2d', renderer: 'maplibre', pitch: 0, bearing: 0 },
  { name: 'maplibre-3d', renderer: 'maplibre', pitch: 50, bearing: -20 },
].filter((mode) => arg('--modes', 'leaflet-2d,maplibre-2d,maplibre-3d').split(',').includes(mode.name));
if (!Number.isInteger(samples) || samples < 1 || !modes.length) throw new Error('Use a positive integer --samples and at least one supported --modes entry');
const report = { capturedAt: new Date().toISOString(), platform: `${os.platform()} ${os.release()} ${os.arch()}`, cpu: os.cpus()[0]?.model,
  totalSystemMemory: os.totalmem(), viewport, dpr: 1, headed, samples, baseURL, runtime: arg('--runtime', 'production server; record build scope with the results'),
  method: 'Fresh Chrome process per sample; cache disabled for initial readiness, then enabled and route primed. Same 256-pixel-world camera scale. RAF intervals measure scheduling, not GPU-presented frames. Post-GC heap is main-page only; summed process RSS includes shared pages and is not unique physical memory. 3D adds work absent from Leaflet. Provider/network differences remain part of cold readiness.', results };

for (let sample = 0; sample < samples; sample++) {
  // Rotate order to reduce one-directional warm-up or thermal bias.
  const order = modes.slice(sample % modes.length).concat(modes.slice(0, sample % modes.length));
  for (const mode of order) {
    const browser = await chromium.launch({ channel: 'chrome', headless: !headed });
    const browserCdp = await browser.newBrowserCDPSession();
    let row;
    try {
      const info = await browserCdp.send('SystemInfo.getInfo');
      const gpu = String(info.gpu.auxAttributes?.glRenderer ?? info.gpu.devices?.[0]?.deviceString ?? 'unknown');
      if (/swiftshader|llvmpipe|software/i.test(gpu)) throw new Error(`Software renderer: ${gpu}. Rerun with --headed; do not use this as a GPU comparison.`);
      const context = await browser.newContext({ viewport, deviceScaleFactor: 1, locale: 'en-US' });
      const page = await context.newPage();
      const cdp = await context.newCDPSession(page);
      await cdp.send('Network.enable'); await cdp.send('Network.setCacheDisabled', { cacheDisabled: true });
      const errors = [], failedRequests = [];
      page.on('pageerror', (e) => errors.push(e.message));
      page.on('requestfailed', (r) => failedRequests.push({ url: r.url().split('?')[0], error: r.failure()?.errorText }));
      const camera = { lng: 100.5606, lat: 13.7374, zoom: 16, pitch: mode.pitch, bearing: mode.bearing };
      await page.addInitScript((initial) => {
        window.__bangkokInitialCamera = initial;
        window.__bangkokInitialBuildings = initial.pitch > 0;
        window.__lab = { lcp: null, cls: 0, tasks: [] };
        new PerformanceObserver((l) => { for (const e of l.getEntries()) window.__lab.lcp = e.startTime; }).observe({ type: 'largest-contentful-paint', buffered: true });
        new PerformanceObserver((l) => { for (const e of l.getEntries()) if (!e.hadRecentInput) window.__lab.cls += e.value; }).observe({ type: 'layout-shift', buffered: true });
        new PerformanceObserver((l) => { for (const e of l.getEntries()) window.__lab.tasks.push({ start: e.startTime, duration: e.duration }); }).observe({ type: 'longtask', buffered: true });
      }, camera);
      await page.goto(`${baseURL}/bangkok/prototype/${mode.renderer}?lv=grid`, { waitUntil: 'domcontentloaded' });
      await page.bringToFront();
      await page.waitForFunction(() => window.__bangkokRenderer?.ready() &&
        (window.__bangkokRenderer.renderer !== 'leaflet' || document.querySelector('canvas.bkk-grid-canvas')), null, { timeout: 45_000 });
      if (await page.evaluate(() => !!document.querySelector('nextjs-portal, [data-nextjs-dev-overlay]'))) {
        throw new Error('Development server detected. Build the prototype and run npm start before benchmarking.');
      }
      const readyMs = await page.evaluate(() => performance.now());
      await page.waitForTimeout(500);
      const cold = await page.evaluate(() => ({ readyStats: window.__bangkokRenderer.stats(), lcpMs: window.__lab.lcp, cls: window.__lab.cls,
        resources: performance.getEntriesByType('resource').reduce((o, r) => { const host = new URL(r.name).host; const g = o[host] ??= { count: 0, transferBytes: 0, decodedBytes: 0 }; g.count++; g.transferBytes += r.transferSize; g.decodedBytes += r.decodedBodySize; return o; }, {}) }));
      await cdp.send('Network.setCacheDisabled', { cacheDisabled: false });
      const path = [
        { ...camera, lng: 100.5806, lat: 13.731 },
        { ...camera, lng: 100.5806, lat: 13.731, zoom: 18 },
        { ...camera, zoom: 16 },
        camera,
      ];
      for (const point of path) {
        await page.evaluate((c) => window.__bangkokRenderer.setCamera(c), point);
        await page.waitForFunction(() => window.__bangkokRenderer.ready(), null, { timeout: 30_000 });
      }
      await page.waitForTimeout(300);
      const memory = async () => {
        await cdp.send('HeapProfiler.collectGarbage');
        const heap = await cdp.send('Runtime.getHeapUsage');
        const dom = await cdp.send('Memory.getDOMCounters');
        const { processInfo } = await browserCdp.send('SystemInfo.getProcessInfo');
        let rss = [];
        if (os.platform() !== 'win32') {
          const text = execFileSync('ps', ['-o', 'pid=,rss=', '-p', processInfo.map((p) => p.id).join(',')], { encoding: 'utf8' });
          rss = text.trim().split('\n').map((line) => { const [pid, kib] = line.trim().split(/\s+/).map(Number); return { type: processInfo.find((p) => p.id === pid)?.type, bytes: kib * 1024 }; });
        }
        return { ...heap, dom, workerCount: page.workers().length, processRss: rss, summedProcessRss: rss.reduce((n, r) => n + r.bytes, 0) };
      };
      const before = await memory();
      const motion = await page.evaluate(async (path) => {
        const frames = []; let active = true, previous = performance.now(); const start = previous;
        const tick = (time) => { if (!active) return; frames.push(time - previous); previous = time; requestAnimationFrame(tick); };
        requestAnimationFrame(tick);
        for (const camera of path) { window.__bangkokRenderer.setCamera(camera, 1500); await new Promise((r) => setTimeout(r, 1600)); }
        active = false;
        return { frames: frames.slice(1), duration: performance.now() - start, longTasks: window.__lab.tasks.filter((t) => t.start >= start), stats: window.__bangkokRenderer.stats() };
      }, path);
      const updateTimes = [];
      for (let i = 0; i < 6; i++) {
        const update = await page.evaluate((i) => {
          const input = document.querySelector('aside input[aria-label="Weights: Food & Dining"]');
          if (!input) throw new Error('Food weight control missing');
          const before = window.__bangkokGridPaint?.version ?? 0;
          const start = performance.now();
          Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(input, i % 2 ? '12' : '25');
          input.dispatchEvent(new Event('input', { bubbles: true }));
          return { before, start };
        }, i);
        await page.waitForFunction((v) => (window.__bangkokGridPaint?.version ?? 0) > v, update.before, { timeout: 5000 });
        updateTimes.push(await page.evaluate((start) => window.__bangkokGridPaint.at - start, update.start));
      }
      const after = await memory();
      if (sample === 0) await page.screenshot({ path: resolve(dirname(output), `${mode.name}.png`) });
      row = { mode: mode.name, sample: sample + 1, browser: browser.version(), gpu, readyMs, cold, memoryBefore: before, memoryAfter: after,
        motion: { durationMs: motion.duration, frameCount: motion.frames.length, rafMeanIntervalMs: motion.frames.reduce((a, b) => a + b, 0) / motion.frames.length,
          rafP50Ms: percentile(motion.frames, .5), rafP95Ms: percentile(motion.frames, .95), rafP99Ms: percentile(motion.frames, .99), rafMaxMs: Math.max(...motion.frames),
          framesOver33ms: motion.frames.filter((n) => n > 33.4).length, longTasks: motion.longTasks, stats: motion.stats },
        weightUpdateMs: updateTimes, errors, failedRequests };
      console.log(JSON.stringify({ mode: row.mode, sample: row.sample, readyMs: Math.round(readyMs), rafP95Ms: row.motion.rafP95Ms, retainedHeapMiB: after.usedSize / 1048576, weightUpdateP50Ms: percentile(updateTimes, .5), errors: errors.length }));
    } catch (error) {
      row = { mode: mode.name, sample: sample + 1, failure: String(error) };
      console.error(JSON.stringify(row));
    } finally {
      results.push(row); await writeFile(output, JSON.stringify(report, null, 2) + '\n'); await browser.close();
    }
  }
}
if (results.some((r) => r.failure)) process.exitCode = 1;
