import { getFormatter, getTranslations } from 'next-intl/server';
import context from '@/data/safety/context.json';

/** Metropolitan citations only; deliberately has no station/district input. */
export default async function SafetyMethodology() {
  const t = await getTranslations('safetyFacts');
  const format = await getFormatter();
  const { traffic, welfare } = context.facts;
  const surveyMonth = format.dateTime(new Date(`${welfare.period.start}T00:00:00Z`), {
    month: 'long', year: 'numeric', timeZone: 'UTC',
  });
  return (
    <section id="safety-context" aria-labelledby="safety-context-title" className="scroll-mt-6 space-y-5 text-sm leading-relaxed text-gray-700">
      <div className="space-y-2">
        <h2 id="safety-context-title" className="text-xl font-bold text-gray-900">{t('title')}</h2>
        <p>{t('intro')}</p>
      </div>
      <div className="space-y-2">
        <h3 className="font-semibold text-gray-900">{t('roadTitle')}</h3>
        <p>{t('roadCount', { year: traffic.period.start.slice(0, 4), ...traffic.values })}</p>
        <p>{t('roadScope')}</p>
        <a href={traffic.source_url} className="inline-flex min-h-11 items-center text-blue-700 underline underline-offset-2 focus-visible:outline-2 focus-visible:outline-offset-2">{t('roadSource')}</a>
      </div>
      <div className="space-y-2">
        <h3 className="font-semibold text-gray-900">{t('welfareTitle')}</h3>
        <p>{t('welfareCount', { period: surveyMonth, ...welfare.values })}</p>
        <p>{t('welfareScope')}</p>
        <a href={welfare.source_url} className="inline-flex min-h-11 items-center text-blue-700 underline underline-offset-2 focus-visible:outline-2 focus-visible:outline-offset-2">{t('welfareSource')}</a>
      </div>
      <div className="space-y-2">
        <h3 className="font-semibold text-gray-900">{t('bangkokTitle')}</h3>
        <p>{t('bangkokScope')}</p>
      </div>
      <p className="text-xs text-gray-600">
        {t('verified')}{' '}
        <time dateTime={context.verified_at}>{format.dateTime(new Date(`${context.verified_at}T00:00:00Z`), { dateStyle: 'long', timeZone: 'UTC' })}</time>
      </p>
    </section>
  );
}
