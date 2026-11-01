import { describe, expect, it, vi } from 'vitest';
import { districtBounds, districtPadding, frameDistrict } from '@/components/bangkok/maplibre/district-camera';
import geometry from '@/data/bangkok/geometry.json';

describe('district camera', () => {
  it('uses the published district bounds in map longitude/latitude order', () => {
    const [[south, west], [north, east]] = geometry['nong-chok'].bbox;
    expect(districtBounds('nong-chok')).toEqual([[west, south], [east, north]]);
    expect(districtBounds('st.asok')).toBeUndefined();
  });
  it('reserves the card region within both desktop and short touch workspaces', () => {
    expect(districtPadding(992, 600, false)).toEqual({ left: 330, right: 40, top: 40, bottom: 40 });
    const touch = districtPadding(320, 200, true);
    expect(touch.bottom).toBe(140);
    expect(touch.top + touch.bottom).toBeLessThan(200);
    const tall = districtPadding(390, 750, true, 420, 100);
    expect(tall.bottom).toBe(444);
    expect(tall.top).toBe(108);
  });
  it('uses a planar bounds fit with current bearing and reduced-motion duration', () => {
    const target = { center: [100.8, 13.9], zoom: 10, bearing: -20 };
    const cameraForBounds = vi.fn(() => target), stop = vi.fn(), easeTo = vi.fn();
    const map = { getContainer: () => ({ clientWidth: 992, clientHeight: 600, closest: () => null }), getBearing: () => -20,
      cameraForBounds, stop, easeTo } as unknown as Parameters<typeof frameDistrict>[0];
    expect(frameDistrict(map, 'nong-chok', false, 0)).toBe(true);
    expect(cameraForBounds).toHaveBeenCalledWith(districtBounds('nong-chok'), expect.objectContaining({ bearing: -20, absolutePadding: true, padding: districtPadding(992, 600, false) }));
    expect(easeTo).toHaveBeenCalledWith({ ...target, pitch: 0, duration: 0 });
    expect(frameDistrict(map, 'unknown', false, 0)).toBe(false);
    expect(stop).toHaveBeenCalledTimes(1);
  });
});
