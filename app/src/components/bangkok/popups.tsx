'use client';

import LeafletAreaCard from '@/components/area/LeafletAreaCard';
import { useAppStore } from '@/lib/store';

import type { MapStation } from '@/lib/types';
import type { ScoredArea } from './StationAreaLayer';


export interface LineChip {
  name: string;
  color: string;
}

/** Desktop popup of a selected station area. */
export function StationAreaPopupBody({ area, thumb, snippet, isCompared, compareFull, onCompare, onUncompare }: {
  area: ScoredArea;
  thumb?: string;
  snippet?: string;
  color: string;
  lineChip: (id: string) => LineChip | null;
  districtName: (slug: string) => string;
  isCompared: boolean;
  compareFull: boolean;
  onCompare: () => void;
  onUncompare: () => void;
}) {
  const weights = useAppStore(state => state.weights);
  return <LeafletAreaCard area={area} city="bangkok" score={area.score} weights={weights}
    thumbnail={thumb ? { thumb } : undefined} snippet={snippet} isCompared={isCompared} compareFull={compareFull}
    onCompare={onCompare} onUncompare={onUncompare} />;
}

export { CellDetails } from './CellDetails';

export function DistrictPopupBody({ district, thumb, snippet, isCompared, compareFull, onCompare, onUncompare }: {
  district: MapStation & { score: number | null }; thumb?: string; snippet?: string; color: string;
  isCompared: boolean; compareFull: boolean; onCompare: () => void; onUncompare: () => void;
}) {
  const weights = useAppStore(state => state.weights);
  return <LeafletAreaCard area={district} city="bangkok" score={district.score} weights={weights}
    thumbnail={thumb ? { thumb } : undefined} snippet={snippet} isCompared={isCompared} compareFull={compareFull}
    onCompare={onCompare} onUncompare={onUncompare} />;
}
