'use client';

import RentNote from '@/components/bangkok/RentNote';
import { AreaCardActions, AreaCardMeta } from '@/components/area-card';

import { useLocale, useTranslations } from 'next-intl';
import type { Locale } from '@/i18n/routing';
import { type MapStation } from '@/lib/types';
import { formatRentShort } from '@/lib/cities';
import { stationDisplayName } from '@/lib/station-name';
import { StationTooltipHero } from '@/components/map-shared';
import type { ScoredArea } from './StationAreaLayer';


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
      <AreaCardMeta primary={names.primary} secondary={names.secondary} score={area.score} />
      <LineChips ids={area.line_ids ?? []} lineChip={lineChip} />
      <div className="text-xs text-gray-500 mb-2">
        {t('map.stationAreaCaption')}
        {area.district && <> · {districtName(area.district)}</>}
        {area.rent_1k != null && <> · ~{formatRentShort('bangkok', area.rent_1k)}/mo</>}
        {area.rent_provenance && <RentNote rent={area.rent_provenance} compact />}
      </div>
      <AreaCardActions city="bangkok" slug={area.slug} isCompared={isCompared} compareFull={compareFull}
        onCompare={onCompare} onUncompare={onUncompare} />
    </div>
  );
}

export { CellDetails } from './CellDetails';

export function DistrictPopupBody({
  district: d,
  thumb,
  snippet,
  color,
  isCompared,
  compareFull,
  onCompare,
  onUncompare,
}: {
  district: MapStation & { score: number | null };
  thumb?: string;
  snippet?: string;
  color: string;
  isCompared: boolean;
  compareFull: boolean;
  onCompare: () => void;
  onUncompare: () => void;
}) {
  const t = useTranslations();
  const locale = useLocale() as Locale;
  const names = stationDisplayName(d, locale);
  return (
    <div className="min-w-[220px] max-w-[260px]">
      <div style={{ margin: '-10px -12px 8px', overflow: 'hidden', borderRadius: '8px 8px 0 0' }}>
        <StationTooltipHero
          key={`popup-${d.slug}`}
          slug={d.slug}
          thumb={thumb}
          lqip={undefined}
          nameEn={names.primary}
          nameJp={d.name_th ?? names.secondary}
          score={d.score}
          color={color}
        />
      </div>
      <AreaCardMeta primary={names.primary} secondary={names.secondary} score={d.score} />
      <div className="text-xs text-gray-500 mb-2">
        {d.station_count ? (
          <>
            {t('filter.stations', { count: d.station_count })} · {t('filter.lines', { count: d.line_count })}
          </>
        ) : (
          t('map.noRailInDistrict')
        )}
        {d.rent_1k != null && <> · ~{formatRentShort('bangkok', d.rent_1k)}/mo</>}
        {d.rent_provenance && <RentNote rent={d.rent_provenance} compact />}
      </div>
      {snippet && <div className="text-xs text-gray-600 mb-2 line-clamp-3 leading-relaxed">{snippet}</div>}
      <AreaCardActions city="bangkok" slug={d.slug} isCompared={isCompared} compareFull={compareFull}
        onCompare={onCompare} onUncompare={onUncompare} />
    </div>
  );
}
