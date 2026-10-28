// @vitest-environment jsdom
import { fireEvent, render } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

const { handlers, mapRef } = vi.hoisted(() => ({ handlers: { click: undefined as undefined | ((event: { originalEvent: { target: HTMLElement } }) => void) }, mapRef: { current: null as unknown } }));
vi.mock('react-leaflet', () => ({
  useMapEvents: (events: typeof handlers) => { handlers.click = events.click; },
  useMap: () => mapRef.current,
}));
import { MapDeselect, MapSelectionBounds, MapSelectionPoint } from './map-selection';

describe('map selection dismissal', () => {
  it('ignores controls and interactive shapes but dismisses background clicks', () => {
    const clear = vi.fn();
    render(<MapDeselect onClear={clear} clickClears escapeClears={false} />);
    const control = document.createElement('div');
    control.className = 'leaflet-control';
    const child = document.createElement('button');
    control.append(child);
    handlers.click?.({ originalEvent: { target: child } });
    const shape = document.createElement('div');
    shape.className = 'leaflet-interactive';
    handlers.click?.({ originalEvent: { target: shape } });
    expect(clear).not.toHaveBeenCalled();
    handlers.click?.({ originalEvent: { target: document.createElement('div') } });
    expect(clear).toHaveBeenCalledOnce();
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(clear).toHaveBeenCalledOnce();
  });
  it('keeps grid clicks for the grid handler and supports Bangkok Escape', () => {
    const clear = vi.fn();
    const { unmount } = render(<MapDeselect onClear={clear} clickClears={false} escapeClears />);
    handlers.click?.({ originalEvent: { target: document.createElement('div') } });
    expect(clear).not.toHaveBeenCalled();
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(clear).toHaveBeenCalledOnce();
    unmount();
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(clear).toHaveBeenCalledOnce();
  });
});


describe('map selection flights', () => {
  it('flies to Tokyo stations and clears the flight class on moveend', () => {
    const container = document.createElement('div');
    let done: (() => void) | undefined;
    const map = {
      getZoom: () => 10, getCenter: () => ({ lat: 35, lng: 139 }),
      getContainer: () => container, closePopup: vi.fn(), flyTo: vi.fn(),
      on: vi.fn((_event, handler) => { done = handler; }), off: vi.fn(),
    };
    mapRef.current = map;
    const start = vi.fn(); const end = vi.fn();
    render(<MapSelectionPoint lat={35.7} lng={139.7} onFlyStart={start} onFlyEnd={end} />);
    expect(start).toHaveBeenCalledOnce();
    expect(map.flyTo).toHaveBeenCalledWith([35.7, 139.7], 14, expect.objectContaining({ duration: 0.6 }));
    expect(container.classList.contains('map-flying')).toBe(true);
    done?.();
    expect(container.classList.contains('map-flying')).toBe(false);
    expect(end).toHaveBeenCalledOnce();
  });
  it('frames Bangkok bounds with bottom inset and settles even after deselection', () => {
    let done: (() => void) | undefined;
    const map = {
      getBoundsZoom: () => 14, getBounds: () => ({ contains: () => false }), getZoom: () => 10,
      closePopup: vi.fn(), flyToBounds: vi.fn(),
      on: vi.fn((_event, handler) => { done = handler; }), off: vi.fn(),
    };
    mapRef.current = map;
    const start = vi.fn(); const end = vi.fn();
    const { unmount } = render(<MapSelectionBounds bounds={[[13.7, 100.5], [13.8, 100.6]]} bottomInset={100} onFlyStart={start} onFlyEnd={end} />);
    expect(start).toHaveBeenCalledOnce();
    expect(map.flyToBounds).toHaveBeenCalledWith(expect.anything(), expect.objectContaining({ maxZoom: 14, paddingBottomRight: expect.objectContaining({ x: 40, y: 140 }) }));
    unmount();
    done?.();
    expect(end).toHaveBeenCalledOnce();
  });
});
