import { describe, expect, it, vi } from 'vitest';
import type L from 'leaflet';
import { installSmoothZoom, installCoastBrake } from './leaflet-controls';

function fixture() {
  const container = document.createElement('div');
  const handlers = new Map<string, () => void>();
  let current = 14;
  const map = {
    getContainer: () => container, getZoom: () => current,
    getMinZoom: () => 10, getMaxZoom: () => 16, getCenter: () => ({}),
    on: (names: string, handler: () => void) => names.split(' ').forEach(name => handlers.set(name, handler)),
    off: (names: string) => names.split(' ').forEach(name => handlers.delete(name)),
    flyTo: vi.fn((...args: [unknown, number, unknown]) => { void args; handlers.get('movestart')?.(); }),
    stop: vi.fn(() => { handlers.get('moveend')?.(); }),
  };
  return { map, container, handlers, setZoom: (n: number) => { current = n; } };
}

describe('Bangkok Leaflet controls', () => {
  it('accumulates, clamps, and clears intent after external motion or teardown', () => {
    const f = fixture();
    const control = installSmoothZoom(f.map as unknown as L.Map);
    [1, 1, 1, -1].forEach(n => control.step(n));
    expect(f.map.flyTo.mock.calls.map(call => call[1])).toEqual([15, 16, 16, 15]);
    f.setZoom(12); f.handlers.get('movestart')?.(); control.step(1);
    expect(f.map.flyTo.mock.lastCall?.[1]).toBe(13);
    f.setZoom(11); f.container.dispatchEvent(new MouseEvent('mousedown', { bubbles: true })); control.step(-1);
    control.step(-1); control.step(1);
    expect(f.map.flyTo.mock.calls.slice(-3).map(call => call[1])).toEqual([10, 10, 11]);
    control.dispose();
    expect(f.handlers.size).toBe(0);
  });

  it('only cancels the stationary touch that stopped an active coast', () => {
    const f = fixture();
    const dispose = installCoastBrake(f.map as unknown as L.Map);
    const touch = (type: string, x: number) => {
      const event = new Event(type, { bubbles: true, cancelable: true });
      Object.defineProperty(event, 'touches', { value: type === 'touchend' ? [] : [{ clientX: x, clientY: 10 }] });
      f.container.dispatchEvent(event);
      return event;
    };
    touch('touchstart', 10);
    expect(f.map.stop).not.toHaveBeenCalled();
    f.handlers.get('dragend')?.();
    touch('touchstart', 10);
    expect(f.map.stop).toHaveBeenCalledOnce();
    expect(touch('touchend', 10).defaultPrevented).toBe(true);
    touch('touchstart', 10);
    expect(touch('touchend', 10).defaultPrevented).toBe(false);
    f.handlers.get('dragend')?.();
    touch('touchstart', 10); touch('touchmove', 30);
    expect(touch('touchend', 30).defaultPrevented).toBe(false);
    f.handlers.get('dragend')?.();
    const control = document.createElement('div'); control.className = 'leaflet-control';
    const button = document.createElement('button'); control.append(button); f.container.append(control);
    const event = new Event('touchstart', { bubbles: true, cancelable: true });
    Object.defineProperty(event, 'touches', { value: [{ clientX: 10, clientY: 10 }] });
    button.dispatchEvent(event);
    expect(f.map.stop).toHaveBeenCalledTimes(2);
    dispose();
    touch('touchstart', 10);
    expect(f.map.stop).toHaveBeenCalledTimes(2);
  });
});
