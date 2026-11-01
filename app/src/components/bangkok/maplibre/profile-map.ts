import { getVersion, type Map as LibreMap } from 'maplibre-gl';
import { renderProfile, type RenderProfile } from '@/lib/render-profile';

interface TimerExtension { TIME_ELAPSED_EXT: number; GPU_DISJOINT_EXT: number }
type Pending = { query: WebGLQuery; stage: string; generation: number; created: number };
const samplers = new WeakMap<WebGL2RenderingContext, GpuSampler>();
class GpuSampler {
  private pending: Pending[] = [];
  private timer: ReturnType<typeof setTimeout> | undefined;
  private active: Pending | undefined;
  private frame = 0;
  constructor(private gl: WebGL2RenderingContext, private ext: TimerExtension, private profile: RenderProfile) {}
  begin(target: 'frame' | 'grid') {
    if (this.profile.gpuTarget !== target || ++this.frame % 8 || this.active || this.pending.length >= 8 || this.gl.isContextLost()) return false;
    // Never nest TIME_ELAPSED queries, including ones owned by another tool.
    if (this.gl.getQuery(this.ext.TIME_ELAPSED_EXT, this.gl.CURRENT_QUERY)) return false;
    const query = this.gl.createQuery(); if (!query) return false;
    this.active = { query, stage: `gpu.${target}`, generation: this.profile.generation, created: performance.now() };
    this.gl.beginQuery(this.ext.TIME_ELAPSED_EXT, query); return true;
  }
  end() {
    if (!this.active) return;
    if (!this.gl.isContextLost()) { this.gl.endQuery(this.ext.TIME_ELAPSED_EXT); this.pending.push(this.active); }
    this.active = undefined;
    this.timer ??= setTimeout(() => this.poll(), 32);
  }
  private poll() {
    this.timer = undefined;
    if (this.gl.isContextLost()) { this.clear(); return; }
    const disjoint = this.gl.getParameter(this.ext.GPU_DISJOINT_EXT);
    this.pending = this.pending.filter((p) => {
      const available = this.gl.getQueryParameter(p.query, this.gl.QUERY_RESULT_AVAILABLE);
      if (!disjoint && !available && performance.now() - p.created < 5000) return true;
      if (!disjoint && available && p.generation === this.profile.generation) {
        this.profile.record(p.stage, this.gl.getQueryParameter(p.query, this.gl.QUERY_RESULT) / 1e6, 'gpu');
      }
      this.gl.deleteQuery(p.query); return false;
    });
    if (this.pending.length) this.timer = setTimeout(() => this.poll(), 32);
  }
  clear() {
    clearTimeout(this.timer); this.timer = undefined;
    if (!this.gl.isContextLost()) {
      if (this.active) { this.gl.endQuery(this.ext.TIME_ELAPSED_EXT); this.gl.deleteQuery(this.active.query); }
      this.pending.forEach((p) => this.gl.deleteQuery(p.query));
    }
    this.active = undefined; this.pending = [];
  }
}

export function profileGridGpu(gl: WebGL2RenderingContext, draw: () => void) {
  const sampler = samplers.get(gl), sampled = sampler?.begin('grid');
  try { draw(); } finally { if (sampled) sampler?.end(); }
}

/** Lab-only adapter for the pinned MapLibre 6.16 renderer. There is no public
 * renderstart event in this version. The wrapper brackets the whole _render,
 * including style/placement, GL submission and synchronous render listeners.
 * Upgrade this adapter explicitly if MapLibre changes; never ship it enabled.
 */
export function attachMapProfile(map: LibreMap): () => void {
  const p = renderProfile(); if (!p) return () => {};
  if (getVersion() !== '6.16.0') { p.gpuStatus = 'renderer adapter needs review for this MapLibre version'; return () => {}; }
  const internal = map as LibreMap & { _render: (time: number) => LibreMap };
  if (typeof internal._render !== 'function') { p.gpuStatus = 'renderer adapter unavailable'; return () => {}; }
  const gl = map.getCanvas().getContext('webgl2');
  const ext = gl?.getExtension('EXT_disjoint_timer_query_webgl2') as TimerExtension | null;
  let gpu = gl && ext ? new GpuSampler(gl, ext, p) : undefined;
  p.gpuStatus = gpu ? 'available; one in eight frames; disjoint results discarded' : 'unavailable: EXT_disjoint_timer_query_webgl2';
  if (gl && gpu) samplers.set(gl, gpu);
  const original = internal._render;
  const wrapped = function (this: LibreMap, time: number) {
    const start = performance.now(), sampled = gpu?.begin('frame');
    try { return original.call(this, time); }
    finally { if (sampled) gpu?.end(); p.record('map.frame', performance.now() - start); }
  };
  internal._render = wrapped;
  const lost = () => { gpu?.clear(); p.gpuStatus = 'context lost'; };
  const restored = () => {
    // WebGL extensions must be enabled again after context restoration.
    const next = gl?.getExtension('EXT_disjoint_timer_query_webgl2') as TimerExtension | null;
    gpu = gl && next ? new GpuSampler(gl, next, p) : undefined;
    p.gpuStatus = gpu ? 'available; one in eight frames; disjoint results discarded' : 'unavailable after restoration';
    if (gl) { if (gpu) samplers.set(gl, gpu); else samplers.delete(gl); }
  };
  map.on('webglcontextlost', lost); map.on('webglcontextrestored', restored);
  return () => { if (internal._render === wrapped) internal._render = original; map.off('webglcontextlost', lost); map.off('webglcontextrestored', restored); gpu?.clear(); if (gl) samplers.delete(gl); };
}
