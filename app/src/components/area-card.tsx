'use client';

import { useTranslations } from 'next-intl';
import { Link } from '@/i18n/navigation';
import { areaPath, type CityId } from '@/lib/cities';

/** The same actions retain their original compact popup and touch-card styles. */
export function AreaCardActions({ city, slug, isCompared, compareFull, onCompare, onUncompare, touch = false }: {
  city: CityId; slug: string; isCompared: boolean; compareFull: boolean;
  onCompare: () => void; onUncompare: () => void; touch?: boolean;
}) {
  const t = useTranslations();
  return (
    <div className={touch ? 'flex items-stretch gap-2 px-3 pb-3' : 'flex items-center gap-3 mt-1'}>
      <Link href={areaPath(city, slug)} data-umami-event="view-details" data-umami-event-station={slug}
        className={touch ? 'flex-1 flex items-center justify-center rounded-lg bg-blue-600 text-white text-sm font-medium active:bg-blue-700' : 'text-blue-600 text-xs hover:underline'}
        style={touch ? { minHeight: 44 } : undefined}>
        {t('map.viewDetails')}
      </Link>
      <CompareToggle isCompared={isCompared} compareFull={compareFull} onCompare={onCompare} onUncompare={onUncompare} touch={touch} />
    </div>
  );
}

export function CompareToggle({ isCompared, compareFull, onCompare, onUncompare, touch = false }: {
  isCompared: boolean; compareFull: boolean; onCompare: () => void; onUncompare: () => void; touch?: boolean;
}) {
  const t = useTranslations();
  const className = touch
    ? `flex-1 flex items-center justify-center rounded-lg text-sm font-medium border active:bg-gray-100 disabled:opacity-40 ${isCompared ? 'text-red-600 border-red-200 bg-red-50' : 'text-purple-700 border-purple-200 bg-purple-50'}`
    : isCompared ? 'text-red-500 text-xs hover:underline' : 'text-purple-600 text-xs hover:underline disabled:opacity-40';
  return <button onClick={(e) => { if (!touch) e.stopPropagation(); (isCompared ? onUncompare : onCompare)(); }}
    disabled={!isCompared && compareFull} className={className} style={touch ? { minHeight: 44 } : undefined}>
    {isCompared ? t('map.removeCompare') : t('map.compare')}
  </button>;
}

/** Name and score presentation for desktop popups and touch cards. */
export function AreaCardMeta({ primary, secondary, score, camera = false, variant = 'popup' }: {
  primary: string; secondary: string; score: number | null; camera?: boolean; variant?: 'popup' | 'tokyo' | 'touch';
}) {
  const t = useTranslations();
  const cameraIcon = camera && <span role="img" aria-label={t('filter.hasLiveCamera')} title={t('filter.hasLiveCamera')}
    className={variant === 'touch' ? 'text-base leading-none shrink-0' : 'text-base leading-none'}>📹</span>;
  if (variant === 'touch') return <div className="flex items-baseline justify-between gap-2">
    <div className="min-w-0">
      <div className="font-bold text-base truncate flex items-center gap-1.5"><span className="truncate">{primary}</span>{cameraIcon}</div>
      {secondary && <div className="text-gray-500 text-xs truncate">{secondary}</div>}
    </div>
    {score !== null && <div className="shrink-0 font-bold text-lg text-slate-800">{score.toFixed(1)}</div>}
  </div>;
  return <>
    {variant === 'tokyo' ? <div className="font-bold text-base flex items-center gap-1.5"><span>{primary}</span>{cameraIcon}</div> : <div className="font-bold text-base">{primary}</div>}
    <div className="text-gray-500 text-sm mb-1">{secondary}</div>
    {score !== null && <div className="text-lg font-bold text-slate-800">{score.toFixed(1)} / 10</div>}
  </>;
}
