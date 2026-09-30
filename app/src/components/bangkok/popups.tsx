'use client';

import { useLocale, useTranslations } from 'next-intl';
import type { Locale } from '@/i18n/routing';
import { Link } from '@/i18n/navigation';
import { RATING_LABELS, type StationRatings } from '@/lib/types';
import { areaPath, formatRentShort } from '@/lib/cities';
import { categoryDeviationColor } from '@/lib/scoring';
import { stationDisplayName } from '@/lib/station-name';
import { stationAreaKey } from '@/lib/area-key';
import { NEAR_STATION_M, type CellInfo } from '@/lib/bangkok-grid';
import RatingBar from '@/components/RatingBar';
import { StationTooltipHero } from '@/components/map-shared';
import type { ScoredArea } from './StationAreaLayer';

const RATING_KEYS = Object.keys(RATING_LABELS) as (keyof StationRatings)[];

export interface LineChip {
  name: string;
  color: string;
}

function LineChips({ ids, lineChip }: { ids: string[]; lineChip: (id: string) => LineChip | null }) {
  return (
    <div className="flex flex-wrap gap-x-2 gap-y-0.5 mb-1">
      {ids.map((lid) => {
        const chip = lineChip(lid);
        if (!chip) return null;
        return (
          <span key={lid} className="inline-flex items-center gap-1 text-[10px] text-gray-700">
            <span className="inline-block h-2 w-2 rounded-full" style={{ backgroundColor: chip.color }} />
            {chip.name}
          </span>
        );
      })}
    </div>
  );
}

function CompareButton({
  isCompared,
  compareFull,
  onCompare,
  onUncompare,
}: {
  isCompared: boolean;
  compareFull: boolean;
  onCompare: () => void;
  onUncompare: () => void;
}) {
  const t = useTranslations();
  return isCompared ? (
    <button onClick={(e) => { e.stopPropagation(); onUncompare(); }} className="text-red-500 text-xs hover:underline">
      {t('map.removeCompare')}
    </button>
  ) : (
    <button
      onClick={(e) => { e.stopPropagation(); onCompare(); }}
      className="text-purple-600 text-xs hover:underline disabled:opacity-40"
      disabled={compareFull}
    >
      {t('map.compare')}
    </button>
  );
}

/** Desktop popup of a selected station area. */
export function StationAreaPopupBody({
  area,
  thumb,
  color,
  lineChip,
  districtName,
  isCompared,
  compareFull,
  onCompare,
  onUncompare,
}: {
  area: ScoredArea;
  thumb?: string;
  color: string;
  lineChip: (id: string) => LineChip | null;
  districtName: (slug: string) => string;
  isCompared: boolean;
  compareFull: boolean;
  onCompare: () => void;
  onUncompare: () => void;
}) {
  const t = useTranslations();
  const locale = useLocale() as Locale;
  const names = stationDisplayName(area, locale);
  return (
    <div className="min-w-[220px] max-w-[260px]">
      <div style={{ margin: '-10px -12px 8px', overflow: 'hidden', borderRadius: '8px 8px 0 0' }}>
        <StationTooltipHero
          key={`popup-${area.slug}`}
          slug={area.slug}
          thumb={thumb}
          lqip={undefined}
          nameEn={names.primary}
          nameJp={names.secondary}
          score={area.score}
          color={color}
        />
      </div>
      <div className="font-bold text-base">{names.primary}</div>
      <div className="text-gray-500 text-sm mb-1">{names.secondary}</div>
      {area.score !== null && <div className="text-lg font-bold text-slate-800">{area.score.toFixed(1)} / 10</div>}
      <LineChips ids={area.line_ids ?? []} lineChip={lineChip} />
      <div className="text-xs text-gray-500 mb-2">
        {t('map.stationAreaCaption')}
        {area.district && <> · {districtName(area.district)}</>}
        {area.rent_1k != null && <> · ~{formatRentShort('bangkok', area.rent_1k)}/mo</>}
      </div>
      <div className="flex items-center gap-3 mt-1">
        <Link
          href={areaPath('bangkok', area.slug)}
          className="text-blue-600 text-xs hover:underline"
          data-umami-event="view-details"
          data-umami-event-station={area.slug}
        >
          {t('map.viewDetails')}
        </Link>
        <CompareButton isCompared={isCompared} compareFull={compareFull} onCompare={onCompare} onUncompare={onUncompare} />
      </div>
    </div>
  );
}

/**
 * Everything the grid knows about one 200 m cell: its ten ratings against
 * the grid median, the commute to each hub, the nearest station and links
 * to the district and station-area pages. Shared by the desktop popup and
 * the touch bottom card.
 */
export function CellDetails({
  info,
  score,
  medians,
  stationName,
  areaName,
  districtName,
  compact = false,
}: {
  info: CellInfo;
  score: number | null;
  medians: Record<keyof StationRatings, number>;
  stationName: (id: string) => string;
  areaName: (id: string) => string;
  districtName: (slug: string) => string;
  compact?: boolean;
}) {
  const t = useTranslations();
  const station = info.stationId ? stationName(info.stationId) : null;
  const walkMin = info.stationDistanceM !== null ? Math.max(1, Math.round((info.stationDistanceM * 1.3) / 75)) : null;
  const near = station && info.stationDistanceM !== null && info.stationDistanceM <= NEAR_STATION_M;
  return (
    <div className={compact ? '' : 'min-w-[240px] max-w-[270px]'}>
      <div className="flex items-baseline justify-between gap-3">
        <div className="min-w-0">
          <div className="font-bold text-sm">{near ? t('map.cellNear', { station }) : t('map.cellTitle')}</div>
          <div className="text-gray-500 text-xs">
            {t('map.cellCaption')} · {districtName(info.districtSlug)}
          </div>
        </div>
        {score !== null && <div className="text-lg font-bold text-slate-800 shrink-0">{score.toFixed(1)}</div>}
      </div>
      <div className="mt-2 space-y-1">
        {RATING_KEYS.map((key) => {
          const v = info.ratings[key];
          const district = key === 'rent' || key === 'safety';
          return (
            <div key={key} className="flex items-center gap-2 text-[11px]">
              <span className="w-20 shrink-0 truncate text-gray-600" title={t(`ratings.${key}`)}>
                {t(`shortLabels.${key}`)}
                {district && <span className="text-gray-400">*</span>}
              </span>
              <div className="flex-1">
                <RatingBar value={v} median={medians[key]} fillColor={categoryDeviationColor(v, medians[key])} />
              </div>
              <span className="w-4 text-right font-semibold tabular-nums">{v}</span>
            </div>
          );
        })}
      </div>
      <div className="mt-2 text-[11px] text-gray-600 leading-relaxed">
        {walkMin !== null && station ? (
          <div>{t('map.cellWalkDistance', { station, minutes: walkMin, meters: Math.round(info.stationDistanceM! / 10) * 10 })}</div>
        ) : (
          <div>{t('map.cellNoStation')}</div>
        )}
        <div className="flex flex-wrap gap-x-2 gap-y-0.5 mt-0.5 text-gray-500">
          {Object.entries(info.hubMinutes).map(([hub, m]) => (
            <span key={hub} className="tabular-nums">
              {t(`hubs.${hub}`)} {m}m
            </span>
          ))}
        </div>
      </div>
      <p className="mt-1.5 text-[10px] text-gray-400 leading-snug">
        {t('map.cellDistrictNote')}
        {info.weight < 0.3 && <> {t('map.cellSparse')}</>}
      </p>
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mt-1.5">
        <Link
          href={areaPath('bangkok', info.districtSlug)}
          className="text-blue-600 text-xs hover:underline"
          data-umami-event="cell-district"
          data-umami-event-station={info.districtSlug}
        >
          {t('map.cellDistrictLink', { district: districtName(info.districtSlug) })}
        </Link>
        {info.areaId && (
          <Link
            href={areaPath('bangkok', stationAreaKey(info.areaId))}
            className="text-blue-600 text-xs hover:underline"
            data-umami-event="cell-station-area"
            data-umami-event-station={info.areaId}
          >
            {t('map.cellAreaLink', { station: areaName(info.areaId) })}
          </Link>
        )}
      </div>
    </div>
  );
}
