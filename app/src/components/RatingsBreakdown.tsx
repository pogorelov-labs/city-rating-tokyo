import { getTranslations } from 'next-intl/server';
import { Link } from '@/i18n/navigation';
import { dataLabel } from '@/i18n/message-key';
import { RATING_LABELS, type BangkokRentProvenance, type StationConfidence, type StationRatings, type StationSources } from '@/lib/types';
import { categoryDeviationColor, pigmentName } from '@/lib/scoring';
import { rentTooltip } from '@/lib/bangkok-rent';
import Tooltip from '@/components/Tooltip';
import RatingBar from '@/components/RatingBar';
import ConfidenceBadge, { ConfidenceIcon } from '@/components/ConfidenceBadge';

const KEYS = Object.keys(RATING_LABELS) as (keyof StationRatings)[];

type Props = {
  kind: 'tokyo' | 'district' | 'station'; ratings: StationRatings; medians: StationRatings;
  confidence?: StationConfidence | null; sources?: StationSources | null; dataDate?: string | null;
  rent?: BangkokRentProvenance;
};

/** Render the same rating contract with city-specific, server-translated explanations. */
export default async function RatingsBreakdown({ kind, ratings, medians, confidence, sources, dataDate, rent }: Props) {
  const t = await getTranslations();
  const tokyo = kind === 'tokyo';
  const keys = tokyo ? Object.keys(ratings) as (keyof StationRatings)[] : KEYS;
  const caption = tokyo ? <>{t('station.ratingsCaption')}{confidence ? t('station.ratingsCaptionWithConfidence') : null}</>
    : kind === 'district' ? t('bangkok.district.ratingsCaption') : t('bangkok.station.ratingsCaption');
  return <section className="bg-white rounded-lg border border-gray-200 p-5">
    <div className="flex items-baseline justify-between gap-2 mb-2">
      <h2 className="font-bold text-lg">{t('station.ratingsTitle')}</h2>
      {dataDate && <span className="text-xs text-gray-500 shrink-0">{t('station.dataFreshness.label', { date: dataDate })}</span>}
    </div>
    <p className="text-[11px] text-gray-500 leading-relaxed mb-3 max-w-xl">{caption}</p>
    <div className="space-y-3">
      {keys.map((key) => {
        const val = ratings[key]; const conf = confidence?.[key]; const srcs = sources?.[key];
        const median = medians[key]; const dev = val - median;
        const barColor = categoryDeviationColor(val, median); const pigment = pigmentName(dev);
        const direction = dev > 0 ? t('station.devAbove') : t('station.devBelow');
        const devPhrase = tokyo
          ? dev === 0 ? t('station.barTooltipDevExact', { median }) : t('station.barTooltipDev', { median, dev: Math.abs(dev), direction })
          : kind === 'district'
            ? dev === 0 ? t('bangkok.district.barTooltipDevExact', { median }) : t('bangkok.district.barTooltipDev', { median, dev: Math.abs(dev), direction })
            : dev === 0 ? t('bangkok.station.barTooltipDevExact', { median }) : t('bangkok.station.barTooltipDev', { median, dev: Math.abs(dev), direction });
        const labelDevSummary = dev === 0 ? t('station.labelDevExact') : dev > 0 ? t('station.labelDevAbove', { dev: Math.abs(dev) }) : t('station.labelDevBelow', { dev: Math.abs(dev) });
        const medianText = tokyo ? t('station.tokyoMedian', { value: median }) : kind === 'district' ? t('bangkok.district.bangkokMedian', { value: median }) : t('bangkok.station.bangkokMedian', { value: median });
        const valueText = tokyo ? t('station.thisStation', { value: val }) : kind === 'district' ? t('bangkok.district.thisDistrict', { value: val }) : t('bangkok.station.thisArea', { value: val });
        const descriptionKey = kind === 'station' && key === 'rent' && rent?.provenance === 'station_override' ? 'bangkok.rent.proxyConfidence'
          : conf === 'editorial' && kind === 'station' ? 'confidence.editorial.descriptionDistrictLevel'
          : conf === 'editorial' && kind === 'district' ? 'confidence.editorial.descriptionResearch' : undefined;
        return <div key={key} className="flex items-center gap-3">
          <div className="w-6 shrink-0 flex justify-center items-center">{conf && <ConfidenceBadge level={conf} sources={srcs} descriptionKey={descriptionKey} />}</div>
          <Tooltip showHelpIcon={false} content={<>
            <span>{!tokyo && key === 'rent' && rent ? rentTooltip(t, rent) : t(`ratingTooltips.${key}`)}</span>
            {srcs && srcs.length > 0 && <span className="block mt-1.5 text-gray-400">{t('station.sourcesLabel')} {srcs.map((s) => dataLabel(t, 'sources', s)).join(', ')}</span>}
            <span className="block mt-1.5 pt-1.5 border-t border-gray-600/40 tabular-nums">{medianText}<br />{valueText} ({labelDevSummary})</span>
            {tokyo && dataDate && <span className="block mt-1 text-gray-500 text-[10px]">{t('station.dataDate', { date: dataDate })}</span>}
          </>}><span className="text-sm w-32 text-gray-600 cursor-help">{t(`ratings.${key}`)}</span></Tooltip>
          <Tooltip wrapper="div" showHelpIcon={false} className="flex-1" content={<>
            <span className="font-semibold">{t('station.barTooltipScore', { label: t(`ratings.${key}`), value: val })}</span>
            <span className="block mt-1">{devPhrase}</span>
            <span className="block mt-1 italic text-gray-400">{t('station.barTooltipPigment', { jp: pigment.jp, en: pigment.en, tone: pigment.tone })}</span>
          </>}><RatingBar value={val} median={median} fillColor={barColor} /></Tooltip>
          <span className="text-sm font-bold tabular-nums w-6 text-right">{val}</span>
          <span className="w-3 text-center text-sm font-medium leading-none tabular-nums" style={{ color: barColor, opacity: 0.65 }} aria-hidden>{dev > 0 ? '↑' : dev < 0 ? '↓' : '−'}</span>
        </div>;
      })}
    </div>
    {(!tokyo || confidence) && <div className="mt-4 pt-3 border-t border-gray-100 flex flex-wrap items-center gap-2 text-[10px] text-gray-600">
      {(['strong', 'moderate', 'estimate', 'editorial'] as const).map((level) => <span key={level} className="inline-flex items-center gap-1.5 rounded-full border border-gray-200 bg-gray-50 px-2 py-0.5"><ConfidenceIcon level={level} size={10} />{t(`confidence.${level}.label`)}</span>)}
    </div>}
    <details className="group mt-3">
      <summary className="flex items-center gap-1.5 cursor-pointer text-[11px] text-gray-600 hover:text-gray-800 select-none marker:hidden list-none">
        <svg className="w-3 h-3 text-gray-400 transition-transform group-open:rotate-90 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M9 18l6-6-6-6" /></svg>
        {t('station.howRatingsWork.title')}
      </summary>
      <div className={tokyo ? 'mt-2 pl-5 text-[11px] text-gray-600 leading-relaxed' : 'mt-2 pl-5 text-[11px] text-gray-600 leading-relaxed space-y-1.5'}>
        <p>{tokyo ? t('station.howRatingsWork.summary') : kind === 'district' ? t('bangkok.district.howRatingsWork') : t('bangkok.station.howRatingsWork')}</p>
        {!tokyo && <p>{kind === 'district' ? t('bangkok.district.relativeNote') : t('bangkok.station.relativeNote')}</p>}
        <Link href={tokyo ? '/methodology' : '/methodology#bangkok'} className={tokyo ? 'inline-block mt-1.5 text-blue-600 hover:underline font-medium' : 'inline-block text-blue-600 hover:underline font-medium'}>{t('station.howRatingsWork.learnMore')}</Link>
      </div>
    </details>
  </section>;
}
