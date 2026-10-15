import { getTranslations } from 'next-intl/server';
import { Link } from '@/i18n/navigation';
import type { QuietnessFact } from '@/lib/schema/noise-types';

export async function QuietnessFacts({ fact }: { fact?: QuietnessFact }) {
  const t = await getTranslations('quietness');
  const available = fact?.status === 'available' && fact.day != null && fact.night != null;
  return (
    <section className="bg-white rounded-lg border border-gray-200 p-5" aria-labelledby="quietness-heading">
      <div className="flex flex-wrap items-center gap-2 mb-3">
        <h2 id="quietness-heading" className="font-bold text-lg">{t('title')}</h2>
        <span className="rounded-full border border-gray-300 px-2 py-0.5 text-xs text-gray-600">{t('estimate')}</span>
      </div>
      {available ? (
        <>
          <dl className="grid grid-cols-2 gap-6 text-sm">
            {(['day', 'night'] as const).map(period => (
              <div key={period}>
                <dt className="text-gray-600">{t(period)} <span className="block text-xs">{t(`${period}Hours`)}</span></dt>
                <dd className="mt-1 font-semibold text-2xl tabular-nums text-gray-900">
                  {fact[period]?.toFixed(1)} <span className="text-sm font-normal text-gray-600">/ 10</span>
                </dd>
              </div>
            ))}
          </dl>
          <p className="mt-3 text-sm text-gray-600">{t('scale')}</p>
          <p className="mt-2 text-sm text-gray-600">{t('limits')}</p>
          {fact.calibration === 'uncalibrated_transfer' && (
            <p className="mt-2 text-sm text-gray-700">{t('bangkokUncalibrated')}</p>
          )}
        </>
      ) : <p className="text-sm text-gray-600">{t('missing')}</p>}

      {fact?.anchors.map(anchor => (
        <div key={anchor.id} className="mt-4 border-t border-gray-200 pt-3 text-sm">
          <h3 className="font-semibold text-gray-900">{t('anchorTitle', { year: anchor.year })}</h3>
          <p className="mt-1 text-gray-700">{anchor.address} · {anchor.road}</p>
          <p className="mt-1 tabular-nums text-gray-900">
            {t('anchorValues', { day: anchor.day_db, night: anchor.night_db })}
          </p>
          <p className="mt-1 text-xs text-gray-600">{anchor.start_date} – {anchor.end_date}</p>
          <p className="mt-1 text-xs text-gray-600">
            {t('anchorLocation', { distance: anchor.distance_m, year: anchor.coordinate_year })}
          </p>
          <a className="inline-flex min-h-11 items-center text-blue-700 underline" href={anchor.source_url} target="_blank" rel="noopener noreferrer">
            {t('anchorSource')}
          </a>
        </div>
      ))}
      {fact?.calibration === 'tokyo_roadside' && fact.anchors.length === 0 && (
        <p className="mt-3 text-xs text-gray-600">{t('noAnchor')}</p>
      )}
      {fact?.complaints && (
        <p className="mt-3 text-xs text-gray-600">
          {t('complaints', { municipality: fact.complaints.municipality, series: fact.complaints.series.map(row => `${row.year}: ${row.count}`).join(' · ') })}
        </p>
      )}
      <div className="mt-2 text-xs text-gray-600">
        {fact && <p>{t('source', { date: fact.data_date })}</p>}
        <Link href="/methodology#quietness" className="inline-flex min-h-11 items-center text-blue-700 underline">{t('methodology')}</Link>
      </div>
    </section>
  );
}
