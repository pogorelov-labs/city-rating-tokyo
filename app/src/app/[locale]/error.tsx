'use client';

import { useEffect } from 'react';
import { useTranslations } from 'next-intl';
import { trackError } from '@/lib/track-error';

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const t = useTranslations('error');

  useEffect(() => {
    trackError('render', {
      message: error.message,
      digest: error.digest || '',
    });
  }, [error]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="text-center p-8">
        <h2 className="text-lg font-bold mb-2">{t('somethingWentWrong')}</h2>
        <p className="text-sm text-gray-500 mb-4">{t('unexpectedError')}</p>
        <button
          onClick={reset}
          className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700"
        >
          {t('tryAgain')}
        </button>
      </div>
    </div>
  );
}
