'use client';

import { useLocale, useTranslations } from 'next-intl';
import { EnvironmentData, SeismicRiskTier } from '@/lib/types';
import Tooltip from './Tooltip';

const SEISMIC_COLORS: Record<SeismicRiskTier, string> = {
  low: '#6A8059',
  moderate: '#C9A227',
  high: '#B3574E',
  very_high: '#8C2926',
  unknown: '#828A8C',
};

interface Props {
  environment: EnvironmentData;
}

export function NaturalEnvironment({ environment }: Props) {
  const t = useTranslations();
  const locale = useLocale();
  const number = new Intl.NumberFormat(locale, { maximumFractionDigits: 2 });
  const { elevation_m, elevation_tier, seismic_prob_i60,
          flood_depth_m,
          michelin_stars, michelin_bib, hotels_800m, tourist_badge } = environment;

  if (elevation_m == null && seismic_prob_i60 == null
      && michelin_stars == null && michelin_bib == null
      && hotels_800m == null) return null;

  // Match the producer's probability bands and the displayed legend.
  const tier: SeismicRiskTier = seismic_prob_i60 == null || !Number.isFinite(seismic_prob_i60)
    ? 'unknown' : seismic_prob_i60 < 0.03 ? 'low'
      : seismic_prob_i60 < 0.06 ? 'moderate' : seismic_prob_i60 < 0.26 ? 'high' : 'very_high';
  const seismicColor = SEISMIC_COLORS[tier];
  const seismicLabel = t(`seismicTiers.${tier}.label`);
  const elevLabel = t(`elevationTiers.${elevation_tier ?? 'unknown'}`);
  const isFloodRisk = elevation_m != null && elevation_m < 5;

  // Select elevation tooltip text based on range
  const elevTooltipKey = elevation_m != null
    ? elevation_m < 0 ? 'belowSea'
      : elevation_m < 5 ? 'veryLow'
        : elevation_m < 20 ? 'low'
          : 'moderate'
    : 'moderate';

  // Select seismic tooltip text based on tier
  const seismicTooltipKey = tier === 'very_high' ? 'veryHigh'
    : tier === 'high' ? 'high'
      : tier === 'moderate' ? 'moderate'
        : 'low';

  return (
    <section className="bg-white rounded-lg border border-gray-200 p-5">
      <h2 className="font-bold text-lg mb-3">{t('station.naturalEnvironment')}</h2>
      <div className="space-y-3">
        {/* Elevation */}
        {elevation_m != null && (
          <div className="flex items-start gap-3">
            <span className="text-lg mt-0.5 shrink-0" aria-hidden>
              {isFloodRisk ? '⚠️' : elevation_m > 100 ? '⛰️' : '📍'}
            </span>
            <div className="min-w-0">
              <Tooltip
                showHelpIcon={false}
                content={
                  <>
                    <span className="font-semibold">{t('station.elevation', { value: elevation_m })}</span>
                    <span className="block mt-1">
                      {t(`elevationTooltips.${elevTooltipKey}`)}
                    </span>
                    <span className="block mt-1 text-gray-400 text-xs">{t('station.sourceElevation')}</span>
                  </>
                }
              >
                <div className="cursor-help">
                  <span className="text-sm font-medium text-gray-900">
                    {t('station.elevation', { value: elevation_m })}
                  </span>
                  <span className="text-xs text-gray-500 ml-1.5">{elevLabel}</span>
                  {isFloodRisk && (
                    <span className="ml-2 inline-flex items-center gap-1 rounded-full bg-amber-50 border border-amber-200 px-2 py-0.5 text-[10px] font-medium text-amber-700">
                      {t('station.floodRisk')}
                    </span>
                  )}
                </div>
              </Tooltip>
            </div>
          </div>
        )}

        {/* Seismic */}
        {seismic_prob_i60 != null && (
          <div className="flex items-start gap-3">
            <span className="text-lg mt-0.5 shrink-0" aria-hidden>
              {tier === 'very_high' ? '🔴' : tier === 'high' ? '🟠' : '🌍'}
            </span>
            <div className="min-w-0">
              <Tooltip
                showHelpIcon={false}
                content={
                  <>
                    <span className="font-semibold">
                      {t('station.seismicRisk')} {number.format(seismic_prob_i60 * 100)}% — {t('station.seismicProbability')}
                    </span>
                    <span className="block mt-1">
                      {t(`seismicTooltips.${seismicTooltipKey}`)}
                    </span>
                    <span className="block mt-1 text-gray-400 text-xs">{t('station.sourceSeismic')}</span>
                  </>
                }
              >
                <div className="cursor-help">
                  <span className="text-sm font-medium text-gray-900">
                    {t('station.seismicRisk')}
                  </span>
                  <span className="ml-1.5 inline-flex items-center gap-1.5">
                    <span
                      className="h-2 w-2 rounded-full shrink-0"
                      style={{ backgroundColor: seismicColor }}
                      aria-hidden
                    />
                    <span className="text-sm" style={{ color: seismicColor }}>
                      {seismicLabel}
                    </span>
                    <span className="text-xs text-gray-500">
                      ({number.format(seismic_prob_i60 * 100)}%)
                    </span>
                  </span>
                </div>
              </Tooltip>
              <p className="text-[11px] text-gray-500 mt-0.5 ml-0">
                {t('station.seismicProbability')}
              </p>
            </div>
          </div>
        )}

        {/* Flood depth from official zones (CRTKY-187, replaces SRTM badge) */}
        {flood_depth_m != null && flood_depth_m >= 0.5 && (
          <div className="flex items-start gap-3">
            <span className="text-lg mt-0.5 shrink-0" aria-hidden>🌊</span>
            <div className="min-w-0">
              <Tooltip
                showHelpIcon={false}
                content={
                  <>
                    <span className="font-semibold">{t('station.floodDepth', { depth: flood_depth_m })}</span>
                    <span className="block mt-1">{t('station.floodDepthTooltip')}</span>
                    <span className="block mt-1 text-gray-400 text-xs">{t('station.sourceFlood')}</span>
                  </>
                }
              >
                <div className="cursor-help">
                  <span className="text-sm font-medium text-gray-900">
                    {t('station.floodDepth', { depth: flood_depth_m })}
                  </span>
                  <span className="ml-2 inline-flex items-center gap-1 rounded-full bg-red-50 border border-red-200 px-2 py-0.5 text-[10px] font-medium text-red-700">
                    {t('station.floodRisk')}
                  </span>
                </div>
              </Tooltip>
            </div>
          </div>
        )}

        {/* Michelin restaurants nearby (CRTKY-191) */}
        {michelin_stars != null && (michelin_stars > 0 || (michelin_bib ?? 0) > 0) && (
          <div className="flex items-start gap-3">
            <span className="text-lg mt-0.5 shrink-0" aria-hidden>⭐</span>
            <div className="min-w-0">
              <Tooltip
                showHelpIcon={false}
                content={
                  <>
                    <span className="font-semibold">{t('station.michelin')}</span>
                    <span className="block mt-1">{t('station.michelinTooltip')}</span>
                    <span className="block mt-1 text-gray-400 text-xs">© Michelin Guide 2026</span>
                  </>
                }
              >
                <div className="cursor-help">
                  <span className="text-sm font-medium text-gray-900">
                    {t('station.michelin')}
                  </span>
                  <span className="text-xs text-gray-500 ml-1.5">
                    {michelin_stars > 0 && `${michelin_stars}★`}
                    {michelin_stars > 0 && (michelin_bib ?? 0) > 0 && ' · '}
                    {(michelin_bib ?? 0) > 0 && `${michelin_bib} Bib`}
                  </span>
                </div>
              </Tooltip>
            </div>
          </div>
        )}

        {/* Tourist load badge (CRTKY-193) */}
        {tourist_badge === true && hotels_800m != null && (
          <div className="flex items-start gap-3">
            <span className="text-lg mt-0.5 shrink-0" aria-hidden>🧳</span>
            <div className="min-w-0">
              <Tooltip
                showHelpIcon={false}
                content={
                  <>
                    <span className="font-semibold">{t('station.touristLoad')}</span>
                    <span className="block mt-1">{t('station.touristLoadTooltip')}</span>
                    <span className="block mt-1 text-gray-400 text-xs">{t('station.sourceTourism')}</span>
                  </>
                }
              >
                <div className="cursor-help">
                  <span className="text-sm font-medium text-gray-900">
                    {t('station.touristLoad')}
                  </span>
                  <span className="ml-2 inline-flex items-center gap-1 rounded-full bg-sky-50 border border-sky-200 px-2 py-0.5 text-[10px] font-medium text-sky-700">
                    {t('station.touristLoadBadge', { count: hotels_800m })}
                  </span>
                </div>
              </Tooltip>
            </div>
          </div>
        )}
      </div>

      {/* Legend */}
      <div className="mt-3 pt-2 border-t border-gray-100 flex flex-wrap gap-2">
        {(['low', 'moderate', 'high', 'very_high'] as const).map((tierKey) => (
          <span
            key={tierKey}
            className="inline-flex items-center gap-1 text-[10px] text-gray-500"
          >
            <span
              className="h-1.5 w-1.5 rounded-full shrink-0"
              style={{ backgroundColor: SEISMIC_COLORS[tierKey], opacity: 0.85 }}
              aria-hidden
            />
            {t(`seismicTiers.${tierKey}.label`)} ({t(`seismicTiers.${tierKey}.description`)})
          </span>
        ))}
      </div>
    </section>
  );
}
