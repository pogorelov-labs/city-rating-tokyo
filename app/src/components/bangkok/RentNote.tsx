'use client';

import { useTranslations } from 'next-intl';
import type { BangkokRentProvenance } from '@/lib/types';
import { rentMetricLabel, rentSourceLabel } from '@/lib/bangkok-rent';

export default function RentNote({ rent, compact = false }: { rent: BangkokRentProvenance; compact?: boolean }) {
  const t = useTranslations();
  const proxy = rent.metric === 'median_asking_by_bedroom';
  const size = rent.source_typical_size_sqm;
  const sizes = size && (size.one_bed !== null || size.two_bed !== null)
    ? t('bangkok.rent.sourceSizes', {
      one: size.one_bed === null ? t('bangkok.rent.unpublishedSize') : t('bangkok.rent.sizeSqm', { size: size.one_bed }),
      two: size.two_bed === null ? t('bangkok.rent.unpublishedSize') : t('bangkok.rent.sizeSqm', { size: size.two_bed }),
    })
    : null;
  if (compact) return (
    <div className="text-xs text-gray-700 mt-1">
      <div>{rentMetricLabel(t, rent)}</div>
      {proxy && <div>{rentSourceLabel(t, rent)}</div>}
      {sizes && <div>{sizes}</div>}
      {rent.composition_skew && <div className="font-medium">{t('bangkok.rent.compositionSkew')}</div>}
    </div>
  );
  return (
    <div className="text-xs text-gray-700 mt-2 leading-relaxed">
      <div className="font-medium">{rentMetricLabel(t, rent)}</div>
      <div>{t('bangkok.rent.asOf', { date: rent.as_of })}</div>
      {rent.sources.map((source) => (
        <a key={source.id} href={source.url} target="_blank" rel="noopener noreferrer"
          className="inline-flex min-h-6 items-center text-blue-700 underline underline-offset-2 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-700">
          {source.publisher}
        </a>
      ))}
      {rent.sample_size && <div>{t('bangkok.rent.samples', { one: rent.sample_size.one_bed, two: rent.sample_size.two_bed })}</div>}
      {sizes && <div>{sizes}</div>}
      {rent.composition_skew && <div className="font-medium">{t('bangkok.rent.compositionSkew')}</div>}
      <details className="mt-1">
        <summary className="cursor-pointer min-h-6 py-1 underline underline-offset-2 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-700">
          {t('bangkok.rent.definitionLink')}
        </summary>
        <p className="mt-1">{t(proxy ? 'bangkok.rent.medianDefinition' : 'bangkok.rent.editorialDefinition')}</p>
        <p className="mt-1">{t(proxy ? 'bangkok.rent.medianLimitations' : 'bangkok.rent.editorialLimitations')}</p>
      </details>
    </div>
  );
}
