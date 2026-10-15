import { getTranslations } from 'next-intl/server';
import calibration from '@/data/noise/calibration-summary.json';

export async function QuietnessMethodology() {
  const t = await getTranslations('quietness');
  const e = calibration.evaluation;
  return (
    <section id="quietness" className="scroll-mt-6 space-y-3 text-sm text-gray-700">
      <h2 className="text-xl font-bold text-gray-900">{t('title')}</h2>
      <p>{t('methodIntro')}</p>
      <p>{t('methodProxies')}</p>
      <p>{t('methodModel')}</p>
      <p>{t('methodScale')}</p>
      <p>{t('methodCalibration', {
        trainRows: calibration.training_rows, trainSites: calibration.training_locations,
        testSites: calibration.test_locations, dayMae: e.day.mae_db, nightMae: e.night.mae_db,
        dayBaseline: e.day.training_mean_baseline_mae_db, nightBaseline: e.night.training_mean_baseline_mae_db,
      })}</p>
      <p>{t('methodMatching', {
        matched: calibration.matched_readings_by_year['2023'],
        excluded: calibration.unmatched_addresses_by_year['2023'],
      })}</p>
      <p>{t('methodLimits')}</p>
      <p>{t('methodBangkok')}</p>
      <p>{t('methodComplaints')}</p>
      <h3 className="font-semibold text-gray-900">{t('methodSources')}</h3>
      <ul className="list-disc pl-5 space-y-1">
        {[
          ['sourceTmg', 'https://www.kankyo.metro.tokyo.lg.jp/vehicle/noise/result/cyousakekka'],
          ['sourceYearbook', 'https://www.toukei.metro.tokyo.lg.jp/tnenkan/2024/tn24qv191100.csv'],
          ['sourcePcd', 'https://gdcatalog.go.th/dataset/gdpublish-noise-monitor'],
          ['sourceCode', 'https://github.com/pogorelov-labs/city-rating-tokyo/tree/main/data/noise'],
        ].map(([key, href]) => (
          <li key={key}><a className="inline-flex min-h-11 items-center text-blue-700 underline" href={href} target="_blank" rel="noopener noreferrer">{t(key)}</a></li>
        ))}
      </ul>
    </section>
  );
}
