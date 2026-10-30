'use client';

import { useMap } from 'react-leaflet';
import CompactAreaCard, { type CompactAreaCardProps } from './CompactAreaCard';

/** Keep Leaflet ownership and the touch-card lifecycle outside the shared view. */
export default function LeafletAreaCard(props: CompactAreaCardProps) {
  const map = useMap();
  return <CompactAreaCard {...props} onClose={() => map.closePopup()} />;
}
