/** Local, opt-in renderer lab instrumentation. No telemetry or unbounded history. */
export type TimingKind = 'cpu-wall' | 'latency' | 'gpu';
export type GpuTarget = 'off' | 'frame' | 'grid';
interface Series { kind: TimingKind; calls: number; totalMs: number; maxMs: number; units: number; bytes: number; samples: number[] }
export class RenderProfile {
  private stages = new Map<string, Series>();
  generation = 0;
  gpuTarget: GpuTarget = 'frame';
  gpuStatus = 'not attached';
  constructor(readonly capacity = 256, readonly maxStages = 96) {}
  record(name: string, ms: number, kind: TimingKind = 'cpu-wall', units = 0, bytes = 0) {
    if (!Number.isFinite(ms) || ms < 0) return;
    let s = this.stages.get(name);
    if (!s) {
      if (this.stages.size >= this.maxStages) return;
      s = { kind, calls: 0, totalMs: 0, maxMs: 0, units: 0, bytes: 0, samples: [] };
      this.stages.set(name, s);
    }
    s.samples[s.calls % this.capacity] = ms;
    s.calls++; s.totalMs += ms; s.maxMs = Math.max(s.maxMs, ms); s.units += units; s.bytes += bytes;
  }
  reset() { this.stages.clear(); this.generation++; }
  snapshot() {
    return { gpuStatus: this.gpuStatus, gpuTarget: this.gpuTarget, sampleCapacity: this.capacity,
      stages: Object.fromEntries([...this.stages].map(([name, s]) => {
        const sorted = [...s.samples].sort((a, b) => a - b);
        const percentile = (p: number) => sorted[Math.min(sorted.length - 1, Math.floor(sorted.length * p))] ?? 0;
        return [name, { kind: s.kind, calls: s.calls, totalMs: s.totalMs, meanMs: s.totalMs / s.calls,
          p50Ms: percentile(.5), p95Ms: percentile(.95), maxMs: s.maxMs, units: s.units, bytes: s.bytes, retainedSamples: sorted.length }];
      })) };
  }
}

declare global { interface Window { __bangkokProfile?: RenderProfile } }
let labOwners = 0;
/** A lab may contain several profiled regions and renderers at the same time. */
export function retainRendererLab(): () => void {
  labOwners++;
  let released = false;
  return () => {
    if (released) return;
    released = true;
    if (--labOwners === 0 && typeof window !== 'undefined') {
      window.__bangkokProfile?.reset();
      delete window.__bangkokProfile;
      delete window.__bangkokGridPaint;
    }
  };
}
export function renderProfile(): RenderProfile | undefined {
  if (typeof window === 'undefined' || !labOwners) return;
  if (/\/bangkok\/prototype\//.test(window.location.pathname) && new URLSearchParams(window.location.search).get('profile') === '1') {
    return window.__bangkokProfile ??= new RenderProfile();
  }
}
export function measure<T>(name: string, fn: () => T, units = 0, bytes = 0): T {
  const p = renderProfile();
  if (!p) return fn();
  const start = performance.now();
  try { return fn(); } finally { p.record(name, performance.now() - start, 'cpu-wall', units, bytes); }
}
/** Async elapsed time includes queueing and waiting; it is NOT worker CPU time. */
export async function measureAsync<T>(name: string, fn: () => Promise<T>, bytes = 0): Promise<T> {
  const p = renderProfile();
  if (!p) return fn();
  const start = performance.now(), generation = p.generation;
  try { return await fn(); } finally { if (generation === p.generation) p.record(name, performance.now() - start, 'latency', 0, bytes); }
}
