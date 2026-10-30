import { describe, expect, it, vi } from 'vitest';
import { RenderProfile, renderProfile, retainRendererLab } from '../render-profile';

describe('bounded renderer profiling', () => {
  it('retains bounded samples while counting all work and rejects invalid durations', () => {
    const p = new RenderProfile(3, 2);
    for (const n of [1, 2, 3, 4, 5]) p.record('upload', n, 'cpu-wall', 1, 40);
    p.record('upload', NaN); p.record('upload', -1);
    p.record('worker', 12, 'latency'); p.record('overflow', 30);
    expect(p.snapshot().stages.upload).toMatchObject({ calls: 5, totalMs: 15, p50Ms: 4, p95Ms: 5, retainedSamples: 3, units: 5, bytes: 200 });
    expect(p.snapshot().stages.worker.kind).toBe('latency');
    expect(p.snapshot().stages.overflow).toBeUndefined();
  });
  it('invalidates outstanding async samples when a new phase begins', () => {
    const p = new RenderProfile();
    const generation = p.generation;
    p.record('frame', 5); p.reset();
    expect(p.generation).not.toBe(generation);
    expect(p.snapshot().stages).toEqual({});
  });
});


describe('renderer lab lifetime', () => {
  it('stops recording on navigation and removes diagnostics only after the final lab owner unmounts', () => {
    const fakeWindow = { location: { pathname: '/bangkok/prototype/maplibre', search: '?profile=1' }, __bangkokProfile: undefined as RenderProfile | undefined, __bangkokGridPaint: { version: 1, at: 0 } };
    vi.stubGlobal('window', fakeWindow);
    const first = retainRendererLab(), second = retainRendererLab();
    try {
      const profile = renderProfile();
      expect(profile).toBeInstanceOf(RenderProfile);
      first();
      expect(fakeWindow.__bangkokProfile).toBe(profile);
      expect(fakeWindow.__bangkokGridPaint).toBeDefined();
      fakeWindow.location.pathname = '/bangkok';
      expect(renderProfile()).toBeUndefined();
      second();
      expect(fakeWindow.__bangkokProfile).toBeUndefined();
      expect(fakeWindow.__bangkokGridPaint).toBeUndefined();
      first();
      expect(renderProfile()).toBeUndefined();
    } finally { first(); second(); vi.unstubAllGlobals(); }
  });
});
