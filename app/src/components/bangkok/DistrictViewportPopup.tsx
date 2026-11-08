'use client';

import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { Popup, useMap } from 'react-leaflet';
import L from 'leaflet';
import './district-popup.css';
import { districtPopupOffset } from './district-popup-layout';

type Position = [number, number];

/** Keep the selected district card in the map workspace even at maxBounds. */
export default function DistrictViewportPopup({ position, bounds, children }: {
  position: Position; bounds: [Position, Position]; children: ReactNode;
}) {
  const map = useMap();
  const popup = useRef<L.Popup | null>(null);
  const [revision, setRevision] = useState(0);
  const layout = useMemo(() => {
    // Map camera and size are mutable; move/resize increments this revision.
    void revision;
    const size = map.getSize(), point = map.latLngToContainerPoint(position);
    const width = Math.max(1, Math.min(306, size.x - 36));
    const height = Math.max(1, Math.min(440, size.y - 74));
    const southwest = map.latLngToContainerPoint(bounds[0]), northeast = map.latLngToContainerPoint(bounds[1]);
    const outline = { left: Math.min(southwest.x, northeast.x), right: Math.max(southwest.x, northeast.x),
      top: Math.min(southwest.y, northeast.y), bottom: Math.max(southwest.y, northeast.y) };
    const offset = districtPopupOffset(size, point, width, height, outline);
    return { width, height, offset: L.point(offset.x, offset.y) };
  }, [map, position, bounds, revision]);
  useEffect(() => {
    const update = () => setRevision((n) => n + 1);
    map.on('moveend', update); map.on('resize', update);
    return () => { map.off('moveend', update); map.off('resize', update); };
  }, [map]);
  useEffect(() => {
    if (!popup.current) return;
    popup.current.options.offset = layout.offset;
    popup.current.options.minWidth = layout.width;
    popup.current.options.maxWidth = layout.width;
    popup.current.getElement()?.classList.toggle('bkk-detached', Math.abs(layout.offset.x) > 1 || Math.abs(layout.offset.y) > 1);
    popup.current.update();
  }, [layout]);
  return <Popup ref={popup} className="area-guide-popup bkk-district-popup" closeButton={false}
    position={position} autoPan={false} offset={layout.offset} minWidth={layout.width} maxWidth={layout.width}
    >
    <div className="bkk-district-popup-card" style={{ width: layout.width, height: layout.height }}>{children}</div>
  </Popup>;
}
