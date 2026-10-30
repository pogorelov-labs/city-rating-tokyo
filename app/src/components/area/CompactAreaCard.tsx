'use client';

import Image from 'next/image';
import { useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';
import { Link } from '@/i18n/navigation';
import type { Locale } from '@/i18n/routing';
import type { CityId } from '@/lib/cities';
import type { MapStation, WeightConfig } from '@/lib/types';
import { DEFAULT_WEIGHTS } from '@/lib/types';
import { areaKind } from '@/lib/area-key';
import { stationDisplayName } from '@/lib/station-name';
import { GUIDE_CATEGORIES, guideDetailHref, guideMoney } from '@/lib/area-guide';
import styles from './compact-area-card.module.css';

export interface CompactAreaCardProps {
  area: MapStation;
  city: CityId;
  score: number | null;
  weights: WeightConfig;
  thumbnail?: { thumb: string; lqip?: string };
  snippet?: string;
  variant?: 'popup' | 'mobile' | 'hover';
  isCompared?: boolean;
  compareFull?: boolean;
  onCompare?: () => void;
  onUncompare?: () => void;
  onClose?: () => void;
  closeLabel?: string;
}

export default function CompactAreaCard({ area, city, score, weights, thumbnail, snippet, variant = 'popup',
  isCompared = false, compareFull = false, onCompare, onUncompare, onClose, closeLabel }: CompactAreaCardProps) {
  const t = useTranslations('areaGuide');
  const all = useTranslations();
  const locale = useLocale() as Locale;
  const names = stationDisplayName(area, locale);
  const [photoFailed, setPhotoFailed] = useState(false);
  const district = city === 'bangkok' && areaKind(area.slug) === 'district';
  const kind = district ? 'district' : 'station';
  const balanced = GUIDE_CATEGORIES.every(key => weights[key] === DEFAULT_WEIGHTS[key]);
  const provenance = area.rent_provenance;
  const rentKind = provenance?.metric === 'median_asking_by_bedroom' ? 'bedroomMedian'
    : provenance?.provenance === 'district_blend' ? 'districtBlend'
    : provenance ? 'estimate'
    : area.rent_source === 'estat' ? 'municipalAverage'
    : area.rent_source === 'suumo' || area.rent_source === 'homes' ? 'stationAverage'
    : area.rent_source ? 'estimate' : 'reference';
  const date = provenance?.as_of ?? area.rent_updated;
  const nf = new Intl.NumberFormat(locale, { maximumFractionDigits: 1 });
  const origin = city === 'tokyo' ? 'tokyo' : kind;
  return (
    <article className={`${styles.card} ${styles[variant]}`} aria-label={names.primary}>
      {thumbnail?.thumb && !photoFailed && <Image className={styles.photo} src={thumbnail.thumb} alt={names.primary}
        width={600} height={220} unoptimized loading="eager" onError={() => setPhotoFailed(true)} />}
      <div className={styles.body}>
        <p className={styles.scope}>{t(`cities.${city}`)} · {t(`kinds.${kind}`)}</p>
        <div className={styles.titleRow}>
          <div className={styles.nameBlock}><h2>{names.primary}</h2>{names.secondary && <p className={styles.localName}>{names.secondary}</p>}</div>
          {score != null && <div className={styles.score}>{nf.format(score)}<small>/10</small></div>}
        </div>
        {snippet && <p className={styles.summary}>{snippet}</p>}
        <div className={styles.stats}>
          <div><span>{t(city === 'tokyo' ? 'rent.smallTokyo' : 'rent.oneBedroom')} {t('rent.perMonth')}</span>
            <strong>{guideMoney(city, area.rent_1k, locale) ?? t('unavailable')}</strong>
        <p className={`${styles.qualifier} ${provenance?.composition_skew ? styles.skewed : ''}`}>
          {t(provenance?.composition_skew ? 'rent.skewShort' : `rent.provenance.${rentKind}`)}
        </p></div>
          <div><span>{t('commute.fastest')}</span>
            <strong>{area.min_transit == null ? '—' : nf.format(area.min_transit)}<small> {t('units.min')}</small></strong></div>
        </div>

        <p className={styles.qualifier}>{t(`commute.origin.${origin}`)} · {t('rail.services', { count: area.line_count })}</p>
        {district && area.station_count === 0 && <p className={styles.qualifier}>{t('rail.none')}</p>}
        {area.hasLiveCamera && <p className={styles.camera}>{t('compact.camera')}</p>}
        <p className={styles.scoreBasis}>{t(balanced ? 'compact.balanced' : 'compact.custom')} · {t('compact.scope')}</p>
        {variant !== 'hover' && <>

          {(date || provenance?.sources.length) && <details className={styles.evidence}>
            <summary>{t('rent.sources')}</summary>
            <div>
              {date && <p>{t('snapshot', { date })}</p>}
              {provenance?.sample_size && <p>{t('rent.samples', { one: provenance.sample_size.one_bed, two: provenance.sample_size.two_bed })}</p>}
              {provenance?.source_typical_size_sqm && <p>{t('rent.sizes', {
                one: provenance.source_typical_size_sqm.one_bed == null ? t('unavailable') : `${nf.format(provenance.source_typical_size_sqm.one_bed)} m²`,
                two: provenance.source_typical_size_sqm.two_bed == null ? t('unavailable') : `${nf.format(provenance.source_typical_size_sqm.two_bed)} m²`,
              })}</p>}
              {rentKind !== 'reference' && <p>{t(`rent.definition.${rentKind}`)}</p>}
              {provenance?.sources.map(source => <a key={source.id} href={source.url} target="_blank" rel="noopener noreferrer">{source.publisher} ↗</a>)}
            </div>
          </details>}
        </>}
      </div>
      {variant !== 'hover' && (
          <div className={styles.actions}>
            <Link className={styles.primary} href={guideDetailHref(city, area.slug, weights)}
              onClick={event => event.stopPropagation()} data-umami-event="view-details" data-umami-event-station={area.slug}>
              {t('compact.explore')} <span aria-hidden="true">↗</span>
            </Link>
            {(onCompare || onUncompare) && <button disabled={!isCompared && compareFull} className={styles.compare}
              onClick={event => { event.stopPropagation(); if (isCompared) onUncompare?.(); else onCompare?.(); }}>
              {all(isCompared ? 'map.removeCompare' : 'map.compare')}
            </button>}
          </div>
      )}
      {onClose && <button className={styles.close} aria-label={closeLabel ?? t('compact.close')} onClick={onClose}>×</button>}
    </article>
  );
}
