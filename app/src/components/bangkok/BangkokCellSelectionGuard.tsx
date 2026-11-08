'use client';

import { useEffect } from 'react';
import { bangkokCellKeyStatus, useBangkokGrid } from '@/lib/bangkok-grid';
import { useAppStore, useCityState } from '@/lib/store';

/** Reject invalid cell links without discarding unrelated city or filter state. */
export default function BangkokCellSelectionGuard() {
  const selected = useCityState(s => s.selectedStation);
  const compared = useCityState(s => s.compareStations);
  const keys = [selected, ...compared].filter((key): key is string => key !== null);
  const needsGrid = keys.some(key => bangkokCellKeyStatus(key, null) === 'pending');
  const { grid } = useBangkokGrid(needsGrid);

  useEffect(() => {
    const invalid = (key: string | null) => key !== null && bangkokCellKeyStatus(key, grid) === 'invalid';
    useAppStore.getState().updateCity('bangkok', state => {
      const nextCompared = state.compareStations.filter(key => !invalid(key));
      const selectionInvalid = invalid(state.selectedStation);
      if (!selectionInvalid && nextCompared.length === state.compareStations.length) return {};
      return {
        ...(selectionInvalid ? { selectedStation: null } : {}),
        ...(nextCompared.length !== state.compareStations.length ? { compareStations: nextCompared } : {}),
      };
    });
  }, [selected, compared, grid]);
  return null;
}
