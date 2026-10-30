import { render } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { MapSelectionBounds } from './map-selection';

const { map, listeners } = vi.hoisted(() => {
  const listeners = new Map<string, Set<() => void>>();
  const map = {
    getBoundsZoom: vi.fn(() => 14), getBounds: vi.fn(() => ({ contains: () => false })),
    getZoom: vi.fn(() => 12), closePopup: vi.fn(), flyToBounds: vi.fn(),
    on: vi.fn((event: string, fn: () => void) => { if (!listeners.has(event)) listeners.set(event, new Set()); listeners.get(event)!.add(fn); }),
    off: vi.fn((event: string, fn: () => void) => listeners.get(event)?.delete(fn)),
    stop: vi.fn(() => { for (const fn of listeners.get('moveend') ?? []) fn(); }),
  };
  return { map, listeners };
});
vi.mock('react-leaflet', () => ({ useMap: () => map }));
vi.mock('@/i18n/navigation', () => ({ Link: () => null }));

describe('Bangkok map flight ownership', () => {
  it('supersedes old listeners before stopping an old flight and releases the new flight on unload', () => {
    const start = vi.fn(); const end = vi.fn();
    const props = { bounds: [[13, 100], [14, 101]] as [[number, number], [number, number]], bottomInset: 0, onFlyStart: start, onFlyEnd: end };
    const view = render(<MapSelectionBounds {...props} key="first" />);
    view.rerender(<MapSelectionBounds {...props} key="second" />);
    expect(start).toHaveBeenCalledTimes(2);
    expect(end).not.toHaveBeenCalled();
    expect(listeners.get('moveend')?.size).toBe(1);
    expect(listeners.get('unload')?.size).toBe(1);
    for (const fn of listeners.get('unload') ?? []) fn();
    expect(end).toHaveBeenCalledOnce();
    expect(listeners.get('moveend')?.size).toBe(0);
    expect(listeners.get('unload')?.size).toBe(0);
  });
});
