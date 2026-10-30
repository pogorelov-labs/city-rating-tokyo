'use client';

import { useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';
import { Circle, CircleMarker, MapContainer, Polygon, Polyline, Popup, TileLayer, Tooltip, useMap } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import { BASEMAP } from '@/lib/basemap';
import railData from '@/data/bangkok/rail.json';
import type { AreaGuideData, MapPoint } from '@/lib/area-guide';
import styles from './area-guide.module.css';

const RAIL = railData as unknown as { lines: { id: string; color: string; paths: MapPoint[][] }[] };

function Frame({ bbox, version }: { bbox: AreaGuideData['map']['bbox']; version: number }) {
  const map = useMap();
  useEffect(() => {
    const element = map.getContainer();
    const fit = () => {
      map.invalidateSize();
      map.fitBounds(bbox, { padding: [22, 22], animate: false, maxZoom: 16 });
    };
    fit();
    const observer = new ResizeObserver(fit);
    observer.observe(element);
    return () => observer.disconnect();
  }, [bbox, map, version]);
  return null;
}

export default function AreaGuideMap({ area }: { area: AreaGuideData }) {
  const t = useTranslations('areaGuide');
  const [outline, setOutline] = useState(true);
  const [rail, setRail] = useState(true);
  const [version, setVersion] = useState(0);
  return (
    <div className={styles.mapRoot}>
      <MapContainer center={area.map.center} zoom={14} className={styles.leafletMap} scrollWheelZoom={false} zoomControl={false}>
        <Frame bbox={area.map.bbox} version={version} />
        <TileLayer url={BASEMAP.url} attribution={BASEMAP.attribution} maxZoom={19} />
        <ZoomButtons />
        {outline && (area.map.polygons
          ? <Polygon positions={area.map.polygons} pathOptions={{ color: '#2563eb', weight: 2, fillOpacity: 0.09 }} />
          : <Circle center={area.map.center} radius={800} pathOptions={{ color: '#2563eb', weight: 2, dashArray: '5 5', fillOpacity: 0.06 }} />)}
        {rail && area.city === 'bangkok' && RAIL.lines.filter(line => area.map.lineIds.includes(line.id)).map(line => (
          <Polyline key={line.id} positions={line.paths} pathOptions={{ color: line.color, weight: 3, opacity: 0.8 }} />
        ))}
        {rail && area.map.stations.map(station => (
          <CircleMarker key={station.id} center={[station.lat, station.lng]} radius={station.selected ? 6 : 4}
            pathOptions={{ color: '#182b3c', weight: 2, fillColor: station.selected ? '#2563eb' : '#fff', fillOpacity: 1 }}>
            <Tooltip direction="top">{station.name}</Tooltip>
            <Popup><strong>{station.name}</strong><br />{t(station.selected ? 'map.stationSelected' : 'map.stationNearby')}</Popup>
          </CircleMarker>
        ))}
      </MapContainer>
      <div className={styles.mapControls} role="group" aria-label={t('map.layers')}>
        <label><input type="checkbox" checked={outline} onChange={event => setOutline(event.target.checked)} />{t('map.outline')}</label>
        <label><input type="checkbox" checked={rail} onChange={event => setRail(event.target.checked)} />{t('map.rail')}</label>
        <button onClick={() => setVersion(value => value + 1)}>{t('map.reset')}</button>
      </div>
    </div>
  );
}

function ZoomButtons() {
  const map = useMap();
  const t = useTranslations('areaGuide');
  return (
    <div className="leaflet-top leaflet-left" style={{ pointerEvents: 'none' }}>
      <div className="leaflet-control leaflet-bar" style={{ pointerEvents: 'auto', border: '1px solid #dce3e7', boxShadow: 'none' }}>
        <button className="block w-11 h-11 sm:w-9 sm:h-9 bg-white border-b border-gray-200 text-lg" aria-label={t('map.zoomIn')} onClick={() => map.zoomIn()}>+</button>
        <button className="block w-11 h-11 sm:w-9 sm:h-9 bg-white text-lg" aria-label={t('map.zoomOut')} onClick={() => map.zoomOut()}>−</button>
      </div>
    </div>
  );
}
