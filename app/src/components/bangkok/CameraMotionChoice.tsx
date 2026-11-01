'use client';

import { useSyncExternalStore } from 'react';
import { useTranslations } from 'next-intl';
import { bangkokMotion, setBangkokMotion, subscribeBangkokMotion } from '@/lib/map-motion';

export default function CameraMotionChoice({ onChoose }: { onChoose?: () => void }) {
  const t = useTranslations('map');
  const value = useSyncExternalStore(subscribeBangkokMotion, bangkokMotion, () => 'system');
  return <label className="bkk-motion-choice">
    <span>{t('cameraMotion')}</span>
    <select value={value} aria-label={t('cameraMotion')}
      onChange={event => { setBangkokMotion(event.target.value === 'smooth' ? 'smooth' : 'system'); onChoose?.(); }}>
      <option value="system">{t('motionSystem')}</option>
      <option value="smooth">{t('motionSmooth')}</option>
    </select>
  </label>;
}
