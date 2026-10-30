import { render } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { MapSelectionPoint } from './map-selection';

const { map } = vi.hoisted(() => ({ map: {
  getZoom: vi.fn(() => 12), getCenter: vi.fn(() => ({ lat: 0, lng: 0 })),
  closePopup: vi.fn(), getContainer: vi.fn(() => document.createElement('div')),
  flyTo: vi.fn(), setView: vi.fn(), on: vi.fn(), off: vi.fn(),
} }));
vi.mock('@/i18n/navigation', () => ({ Link: () => null }));
vi.mock('react-leaflet', () => ({ useMap: () => map }));

describe('Tokyo map flight cancellation', () => {
  it('releases flight state and detaches its listener when selection disappears', () => {
    const start = vi.fn(); const end = vi.fn(); const cancel = vi.fn();
    const { unmount } = render(<MapSelectionPoint lat={1} lng={1} onFlyStart={start} onFlyEnd={end} onFlyCancel={cancel} />);
    expect(start).toHaveBeenCalledOnce();
    unmount();
    expect(cancel).toHaveBeenCalledOnce();
    expect(end).not.toHaveBeenCalled();
    expect(map.off).toHaveBeenCalledWith('moveend', expect.any(Function));
  });
});
