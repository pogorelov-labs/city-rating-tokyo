'use client';

import { useEffect, useState } from 'react';
import { Circle, CircleMarker, MapContainer, Polygon, Polyline, Popup, TileLayer, Tooltip, useMap } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import railData from '@/data/bangkok/rail.json';
import { BASEMAP } from '@/lib/basemap';
import type { CardArea, Point } from './model';
import styles from './cards.module.css';

const RAIL = railData as unknown as { lines: { id: string; color: string; paths: Point[][] }[] };

function Frame({ area, version }: { area: CardArea; version: number }) {
  const map = useMap();
  useEffect(() => {
    map.invalidateSize();
    map.fitBounds(area.map.bbox, { padding: [22, 22], animate: false, maxZoom: 16 });
  }, [area.map.bbox, map, version]);
  return null;
}

export default function AreaMap({ area, expanded = false }: { area: CardArea; expanded?: boolean }) {
  const [outline, setOutline] = useState(true);
  const [rail, setRail] = useState(true);
  const [frameVersion, setFrameVersion] = useState(0);
  return <div className={`${styles.mapRoot} ${expanded ? styles.expandedMap : ''}`}>
    <MapContainer center={area.map.center} zoom={14} className={styles.leafletMap} scrollWheelZoom={false} attributionControl zoomControl>
      <Frame area={area} version={frameVersion} />
      <TileLayer url={BASEMAP.url} attribution={BASEMAP.attribution} maxZoom={19} />
      {outline && (area.map.polygons ? <Polygon positions={area.map.polygons} pathOptions={{ color: '#2563eb', weight: 2, fillColor: '#2563eb', fillOpacity: 0.09 }} /> : <Circle center={area.map.center} radius={800} pathOptions={{ color: '#2563eb', weight: 2, dashArray: '5 5', fillOpacity: 0.06 }} />)}
      {rail && area.city === 'bangkok' && RAIL.lines.filter(line => area.map.lineIds.includes(line.id)).map(line => <Polyline key={line.id} positions={line.paths} pathOptions={{ color: line.color, weight: 3, opacity: 0.8 }} />)}
      {rail && area.map.stations.map(station => {
        const selected = area.map.stationIds.includes(station.id);
        return <CircleMarker key={station.id} center={[station.lat, station.lng]} radius={selected ? 6 : 4} pathOptions={{ color: '#182b3c', weight: 2, fillColor: selected ? '#2563eb' : '#fff', fillOpacity: 1 }}>
          <Tooltip direction="top">{station.name}</Tooltip><Popup><strong>{station.name}</strong><br />{selected ? 'Station serving this area' : 'Nearby rail station'}</Popup>
        </CircleMarker>;
      })}
    </MapContainer>
    <div className={styles.mapControls} aria-label="Map layers"><label><input type="checkbox" checked={outline} onChange={e => setOutline(e.target.checked)} />Area outline</label><label><input type="checkbox" checked={rail} onChange={e => setRail(e.target.checked)} />Rail stations</label><button onClick={() => setFrameVersion(v => v + 1)}>Reset view</button></div>
  </div>;
}
