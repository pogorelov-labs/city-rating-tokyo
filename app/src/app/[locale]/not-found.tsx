import { getTranslations } from 'next-intl/server';
import { Link } from '@/i18n/navigation';

/**
 * Custom 404 page for the [locale] segment.
 *
 * Without this, notFound() calls from station pages render a blank page —
 * the [locale] layout provides <html>/<body> but Next.js's built-in
 * not-found component renders nothing inside it. This component provides
 * a visible message + a link back to the map.
 */
export default async function NotFound() {
  const t = await getTranslations();

  return (
    <div className="min-h-[50vh] flex flex-col items-center justify-center gap-4 px-4 text-center">
      <h1 className="text-2xl font-bold text-gray-900">
        {t('error.notFoundTitle')}
      </h1>
      <p className="text-gray-600 max-w-md">
        {t('error.notFoundDescription')}
      </p>
      <Link
        href="/"
        className="mt-2 px-4 py-2 bg-gray-900 text-white rounded-lg hover:bg-gray-700 transition-colors text-sm font-medium"
      >
        {t('nav.backToMap')}
      </Link>
    </div>
  );
}
