import type { AppTranslator } from '@/i18n/message-key';
import type { BangkokRentProvenance } from './types';

export function rentMetricLabel(t: AppTranslator, rent: BangkokRentProvenance): string {
  return t(rent.metric === 'median_asking_by_bedroom'
    ? 'bangkok.rent.medianLabel'
    : rent.provenance === 'district_blend' ? 'bangkok.rent.blendLabel' : 'bangkok.rent.editorialLabel');
}

export function rentSourceLabel(t: AppTranslator, rent: BangkokRentProvenance): string {
  const source = rent.sources.map((s) => s.publisher).join(', ');
  const sample = rent.sample_size
    ? t('bangkok.rent.samples', { one: rent.sample_size.one_bed, two: rent.sample_size.two_bed })
    : '';
  return [source, rent.as_of, sample].filter(Boolean).join(' · ');
}

export function rentTooltip(t: AppTranslator, rent: BangkokRentProvenance): string {
  if (rent.metric !== 'median_asking_by_bedroom') {
    return t(rent.provenance === 'district_blend' ? 'bangkok.station.rentTooltip' : 'bangkok.district.rentTooltip');
  }
  return `${rentMetricLabel(t, rent)}. ${rentSourceLabel(t, rent)}. ${t('bangkok.rent.medianDefinition')} ${t('bangkok.rent.affordability')}`;
}
