// @vitest-environment jsdom
import { DEFAULT_WEIGHTS } from '@/lib/types';
import { act, render } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { ScoredArea } from './StationAreaLayer';

const { events } = vi.hoisted(() => ({ events: { current: {} as Record<string, () => void> } }));
vi.mock('react-leaflet', () => ({
  Pane: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  Polygon: ({ children, eventHandlers }: { children: React.ReactNode; eventHandlers: Record<string, () => void> }) => { events.current = eventHandlers; return <div>{children}</div>; },
  Tooltip: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));
vi.mock('next-intl', () => ({ useTranslations: () => (key: string) => key, useLocale: () => 'en' }));
vi.mock('@/components/area/CompactAreaCard', () => ({ default: () => null }));
import StationAreaLayer from './StationAreaLayer';

afterEach(() => vi.useRealTimers());
describe('station area interactions', () => {
  it('cancels hover dismissal on re-entry and suppresses a double-click selection', () => {
    vi.useFakeTimers();
    const onHover = vi.fn(); const onSelect = vi.fn();
    const area = { slug: 'st.asok', name_en: 'Asok', name_jp: 'アソーク', lat: 13.7, lng: 100.5, score: 5 } as ScoredArea;
    render(<StationAreaLayer weights={DEFAULT_WEIGHTS} thumbnails={{}} snippets={{}} areas={[area]} shapes={{ asok: { bbox: [[13.7,100.5],[13.8,100.6]], polygons: [] } }} passing={new Set(['st.asok'])}
      colorFor={() => '#fff'} filteredFill="#ddd" selected={null} hovered={null} heatmapMode={false} isTouch
      reasonsFor={() => []} lineChip={() => null} districtName={() => ''} onSelect={onSelect} onHover={onHover} />);
    act(() => { events.current.mouseout(); vi.advanceTimersByTime(100); events.current.mouseover(); vi.advanceTimersByTime(75); });
    expect(onHover).toHaveBeenCalledTimes(1);
    expect(onHover).toHaveBeenCalledWith('st.asok');
    act(() => { events.current.click(); events.current.dblclick(); vi.advanceTimersByTime(230); });
    expect(onSelect).not.toHaveBeenCalled();
    act(() => { events.current.click(); vi.advanceTimersByTime(230); });
    expect(onSelect).toHaveBeenCalledWith('st.asok');
  });
});
