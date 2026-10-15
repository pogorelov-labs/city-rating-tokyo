import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { Providers } from '@/test/providers';
import { MapLoading } from './MapWrapper';
import { TouchZoomControls } from './map-shared';

const map = vi.hoisted(() => ({ zoomIn: vi.fn(), zoomOut: vi.fn() }));
vi.mock('react-leaflet', () => ({ useMap: () => map }));
vi.mock('next/dynamic', () => ({ default: () => () => null }));
vi.mock('leaflet', () => ({ default: {} }));

describe('localized map loading and accessible zoom labels', () => {
  for (const [locale, loading, zoomIn, zoomOut] of [
    ['en', 'Loading map…', 'Zoom in', 'Zoom out'],
    ['ja', 'マップ読み込み中…', '拡大', '縮小'],
    ['ru', 'Загрузка карты…', 'Приблизить', 'Отдалить'],
  ] as const) {
    it(`${locale} renders translated status and working named buttons`, () => {
      map.zoomIn.mockClear(); map.zoomOut.mockClear();
      render(<Providers locale={locale}><MapLoading /><TouchZoomControls /></Providers>);
      expect(screen.getByRole('status')).toHaveTextContent(loading);
      fireEvent.click(screen.getByRole('button', { name: zoomIn }));
      fireEvent.click(screen.getByRole('button', { name: zoomOut }));
      expect(map.zoomIn).toHaveBeenCalledTimes(1);
      expect(map.zoomOut).toHaveBeenCalledTimes(1);
    });
  }
});
