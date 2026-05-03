import type { Metadata } from 'next';
import { setRequestLocale, getTranslations } from 'next-intl/server';
import { Link } from '@/i18n/navigation';
import { ApiAccessForm } from './ApiAccessForm';

export const metadata: Metadata = {
  title: 'API Access — Tokyo Neighborhood Explorer',
  description:
    'Request an API key for the city-rating MCP server. Programmatic access to ratings, descriptions, and semantic search across 1,493 Tokyo stations.',
};

export default async function ApiAccessPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations('apiAccess');

  return (
    <div className="min-h-dvh bg-white">
      <header className="border-b border-gray-200 bg-white sticky top-0 z-10">
        <div className="max-w-3xl mx-auto px-4 py-3 flex items-center justify-between">
          <Link href="/" className="text-sm text-gray-600 hover:text-gray-900">
            ← {t('back')}
          </Link>
          <h1 className="text-base font-semibold text-gray-900">{t('title')}</h1>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-4 py-8 space-y-8">
        <section className="space-y-3">
          <h2 className="text-2xl font-bold text-gray-900">{t('heading')}</h2>
          <p className="text-gray-700 leading-relaxed">{t('intro')}</p>
        </section>

        <section className="space-y-3">
          <h3 className="text-lg font-semibold text-gray-900">{t('whatYouGet')}</h3>
          <ul className="text-sm text-gray-700 list-disc pl-5 space-y-1">
            <li>{t('feature1')}</li>
            <li>{t('feature2')}</li>
            <li>{t('feature3')}</li>
            <li>{t('feature4')}</li>
          </ul>
        </section>

        <section className="space-y-3">
          <h3 className="text-lg font-semibold text-gray-900">{t('howItWorks')}</h3>
          <ol className="text-sm text-gray-700 list-decimal pl-5 space-y-1">
            <li>{t('step1')}</li>
            <li>{t('step2')}</li>
            <li>{t('step3')}</li>
          </ol>
        </section>

        <section className="border border-gray-200 rounded-lg p-5 bg-gray-50">
          <h3 className="text-lg font-semibold text-gray-900 mb-3">{t('formTitle')}</h3>
          <ApiAccessForm />
        </section>

        <section className="text-xs text-gray-500 pt-4 border-t border-gray-100">
          <p>
            {t('endpoint')}: <code className="bg-gray-100 px-1 py-0.5 rounded">https://city-rating.pogorelov.dev/mcp</code>
          </p>
          <p className="mt-1">
            {t('docs')}:{' '}
            <a
              href="https://github.com/pogorelov-labs/city-rating/blob/main/mcp/README.md"
              className="text-blue-600 hover:underline"
              target="_blank"
              rel="noreferrer"
            >
              mcp/README.md
            </a>
          </p>
        </section>
      </main>
    </div>
  );
}
