import { getTranslations } from 'next-intl/server';
export default async function AirMethodology() {
  const t = await getTranslations('air');
  return <section id="air" className="scroll-mt-6 space-y-3 text-sm text-gray-700">
    <h2 className="text-xl font-bold text-gray-900">{t('methodTitle')}</h2>
    {['methodScope','methodLive','methodSeason','methodMissing','methodPermissions'].map(k=><p key={k}>{t(k)}</p>)}
    <ul className="list-disc pl-5">
      {[
        [t('tokyoSource'),'https://soramame.env.go.jp/'],
        [t('bangkokSource'),'https://air4thai.pcd.go.th/'],
        [t('pollenSource'),'https://www.hokeniryo1.metro.tokyo.lg.jp/allergy/'],
        [t('reproduce'),'https://github.com/pogorelov-labs/city-rating-tokyo/tree/main/data/air'],
      ].map(([label,url])=><li key={url}><a href={url} target="_blank" rel="noopener noreferrer" className="inline-flex min-h-11 items-center text-blue-700 underline">{label}</a></li>)}
    </ul>
  </section>;
}
