import { getTranslations } from 'next-intl/server';
import { Link } from '@/i18n/navigation';
import { SOURCES, type AirCity } from '@/lib/air/model';
import AirLiveChip, { type AirLabels } from './AirLiveChip';
export default async function AirPanel({ city, compact = false }: { city: AirCity; compact?: boolean }) {
  const t = await getTranslations('air');
  const labels = Object.fromEntries(['loading','fresh','stale','unavailable','permission_pending','observed','fetched','coverage','preliminary'].map(k=>[k,t(k)])) as AirLabels;
  const content = <section aria-labelledby={`air-${city}-title`} className="bg-white rounded-lg border border-gray-200 p-5 space-y-3">
    <h2 id={`air-${city}-title`} className="font-bold text-lg">{t('title', {city:t(city)})}</h2>
    <p className="text-sm text-gray-700">{t(`${city}Scope`)}</p>
    <AirLiveChip city={city} labels={labels} />
    <div className="border-t border-gray-200 pt-3 text-sm space-y-2">
      <h3 className="font-semibold text-gray-900">{t(`${city}Season`)}</h3>
      <p className="text-gray-600">{t('historyUnavailable')}</p>
      {city === 'tokyo' && <p className="text-gray-600">{t('pollenUnavailable')}</p>}
    </div>
    <p className="text-xs text-gray-600">{t('notRating')}</p>
    <div className="flex flex-wrap gap-x-5 text-sm">
      <a href={SOURCES[city].url} target="_blank" rel="noopener noreferrer" className="inline-flex min-h-11 items-center text-blue-700 underline">{t(`${city}Source`)}</a>
      <Link href="/methodology#air" className="inline-flex min-h-11 items-center text-blue-700 underline">{t('methodology')}</Link>
    </div>
  </section>;
  return compact ? <details className="shrink-0 border-b border-gray-200 bg-white max-h-[50dvh] overflow-auto">
    <summary className="min-h-11 flex items-center cursor-pointer px-4 text-sm text-blue-700 list-item">{t('title',{city:t(city)})} · PM2.5</summary>
    <div className="max-w-4xl mx-auto px-4 pb-3">{content}</div>
  </details> : content;
}
