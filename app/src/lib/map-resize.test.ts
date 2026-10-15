import type { Map } from 'leaflet';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { observeMapContainer } from './map-resize';

afterEach(() => vi.unstubAllGlobals());

function setup(height = 700) {
  let notify = () => {};
  const observe = vi.fn();
  const disconnect = vi.fn();
  vi.stubGlobal('ResizeObserver', class {
    constructor(callback: () => void) { notify = callback; }
    observe = observe;
    disconnect = disconnect;
  });
  const container = { clientWidth: 900, clientHeight: height };
  const invalidateSize = vi.fn();
  const map = { getContainer: () => container, invalidateSize } as unknown as Pick<Map, 'getContainer' | 'invalidateSize'>;
  const stop = observeMapContainer(map);
  return { container, invalidateSize, observe, disconnect, stop, notify: () => notify() };
}

describe('Leaflet container resizing', () => {
  it('updates the viewport on panel open and close without a window resize', () => {
    const s = setup();
    expect(s.observe).toHaveBeenCalledWith(s.container);
    expect(s.invalidateSize).toHaveBeenCalledTimes(1);
    s.container.clientHeight = 350; s.notify(); // panel opens
    expect(s.invalidateSize).toHaveBeenCalledTimes(2);
    s.container.clientHeight = 700; s.notify(); // panel closes; exposed tiles redraw
    expect(s.invalidateSize).toHaveBeenCalledTimes(3);
    expect(s.invalidateSize).toHaveBeenLastCalledWith({ animate: false, pan: true, debounceMoveend: true });
    s.stop();
  });

  it('handles initialization with the panel open and later width changes', () => {
    const s = setup(350);
    s.container.clientHeight = 700; s.notify();
    s.container.clientWidth = 600; s.notify();
    expect(s.invalidateSize).toHaveBeenCalledTimes(3);
    s.stop();
  });

  it('ignores unchanged and hidden sizes, disconnects and ignores queued callbacks', () => {
    const s = setup();
    s.notify(); s.notify();
    s.container.clientHeight = 0; s.notify();
    expect(s.invalidateSize).toHaveBeenCalledTimes(1);
    s.container.clientHeight = 350; s.notify();
    // Simulate a notification caused by Leaflet updating its tile/overlay DOM.
    s.notify();
    expect(s.invalidateSize).toHaveBeenCalledTimes(2);
    s.stop();
    expect(s.disconnect).toHaveBeenCalledOnce();
    s.container.clientHeight = 700; s.notify();
    expect(s.invalidateSize).toHaveBeenCalledTimes(2);
  });
});
