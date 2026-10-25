import { getTranslations } from 'next-intl/server';
import { institutionSnapshotDate, institutionSources, type InstitutionFact } from '@/lib/institutions';

export async function InstitutionFacts({ fact }: { fact?: InstitutionFact }) {
  const t = await getTranslations('institutions');
  return (
    <section className="bg-white rounded-lg border border-gray-200 p-5" aria-labelledby="institutions-heading">
      <h2 id="institutions-heading" className="font-bold text-lg mb-3">{t('title')}</h2>
      {!fact ? <p className="text-sm text-gray-600">{t('missing')}</p> : (
        <>
          <p className="text-sm font-medium text-gray-900">
            {t(fact.scope === 'district' ? 'embassiesDistrict' : 'embassiesStation', { count: fact.embassies })}
          </p>
          <p className="mt-1 text-xs text-gray-600">{t(fact.scope === 'district' ? 'districtDistance' : 'stationDistance')}</p>
          <p className="mt-2 text-xs text-gray-600">{t('embassyLimit')}</p>
          <p className="mt-1 text-xs text-gray-600">{t(fact.city === 'tokyo' ? 'tokyoEmbassyDate' : 'bangkokEmbassyDate')}</p>
          <div className="flex flex-wrap gap-x-4 text-xs">
            <a className="inline-flex min-h-11 items-center text-blue-700 underline" href={institutionSources.osm}>© OpenStreetMap contributors · ODbL</a>
            <a className="inline-flex min-h-11 items-center text-blue-700 underline" href={institutionSources.wikidata}>Wikidata · CC0</a>
          </div>
          <div className="border-t border-gray-100 pt-3 mt-1">
            {fact.medicine == null ? (
              <p className="text-sm text-gray-600">{t('medicineUnavailable')}</p>
            ) : (
              <>
                <p className="text-sm font-medium text-gray-900">{t('medicine', { count: fact.medicine })}</p>
                <p className="mt-1 text-xs text-gray-600">{t('medicineLimit')}</p>
                <a className="inline-flex min-h-11 items-center text-xs text-blue-700 underline" href={institutionSources.medicine}>{t('medicineSource')}</a>
              </>
            )}
          </div>
          <p className="mt-2 text-xs text-gray-600">{t('snapshot', { date: institutionSnapshotDate })}</p>
        </>
      )}
    </section>
  );
}
