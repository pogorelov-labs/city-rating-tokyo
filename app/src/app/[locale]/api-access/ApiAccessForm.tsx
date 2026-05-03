'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';

type SuccessResponse = {
  success: true;
  key: string;
  status: 'pending';
  message: string;
};

type ErrorResponse = { error: string };

export function ApiAccessForm() {
  const t = useTranslations('apiAccess');
  const [email, setEmail] = useState('');
  const [useCase, setUseCase] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [issued, setIssued] = useState<SuccessResponse | null>(null);
  const [copied, setCopied] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const res = await fetch('/api/api-access', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email.trim(), use_case: useCase.trim() }),
      });
      const body = (await res.json()) as SuccessResponse | ErrorResponse;
      if (!res.ok || 'error' in body) {
        setError('error' in body ? body.error : t('errorGeneric'));
      } else {
        setIssued(body);
      }
    } catch {
      setError(t('errorNetwork'));
    } finally {
      setSubmitting(false);
    }
  }

  if (issued) {
    return (
      <div className="space-y-4">
        <div className="rounded-md bg-green-50 border border-green-200 p-3">
          <p className="text-sm font-medium text-green-900">{t('successTitle')}</p>
          <p className="text-sm text-green-800 mt-1">{t('successPending')}</p>
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-700 mb-1">{t('yourKey')}</label>
          <div className="flex gap-2">
            <code className="flex-1 px-3 py-2 bg-white border border-gray-300 rounded font-mono text-sm break-all">
              {issued.key}
            </code>
            <button
              type="button"
              onClick={() => {
                navigator.clipboard.writeText(issued.key);
                setCopied(true);
                setTimeout(() => setCopied(false), 1500);
              }}
              className="px-3 py-2 text-sm bg-gray-900 text-white rounded hover:bg-gray-800"
            >
              {copied ? t('copied') : t('copy')}
            </button>
          </div>
          <p className="text-xs text-amber-700 mt-2 font-medium">⚠ {t('saveWarning')}</p>
        </div>

        <div className="rounded-md bg-gray-100 p-3 text-xs text-gray-700 space-y-2">
          <p className="font-medium">{t('howToUse')}</p>
          <pre className="overflow-x-auto bg-white p-2 rounded border border-gray-200 text-[11px]">{`curl -H "Authorization: Bearer ${issued.key}" \\
  https://city-rating.pogorelov.dev/mcp`}</pre>
          <p>{t('claudeDesktop')}</p>
        </div>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">
          {t('emailLabel')}
        </label>
        <input
          id="email"
          type="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="w-full px-3 py-2 border border-gray-300 rounded text-base focus:outline-none focus:ring-2 focus:ring-blue-500"
          placeholder="you@example.com"
          autoComplete="email"
          disabled={submitting}
        />
      </div>

      <div>
        <label htmlFor="useCase" className="block text-sm font-medium text-gray-700 mb-1">
          {t('useCaseLabel')}
        </label>
        <textarea
          id="useCase"
          required
          minLength={10}
          maxLength={500}
          value={useCase}
          onChange={(e) => setUseCase(e.target.value)}
          className="w-full px-3 py-2 border border-gray-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 min-h-[100px]"
          placeholder={t('useCasePlaceholder')}
          disabled={submitting}
        />
        <p className="text-xs text-gray-500 mt-1">{useCase.length} / 500</p>
      </div>

      {error ? (
        <div className="rounded-md bg-red-50 border border-red-200 p-3 text-sm text-red-800">
          {error}
        </div>
      ) : null}

      <button
        type="submit"
        disabled={submitting || !email || useCase.length < 10}
        className="w-full px-4 py-2 bg-gray-900 text-white rounded font-medium hover:bg-gray-800 disabled:bg-gray-400 disabled:cursor-not-allowed"
      >
        {submitting ? t('submitting') : t('submit')}
      </button>
    </form>
  );
}
