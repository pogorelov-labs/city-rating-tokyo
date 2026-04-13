'use client';

import { useState, useSyncExternalStore } from 'react';
import { useTranslations } from 'next-intl';
import { getVisitorId } from '@/lib/visitor-id';

const FEEDBACK_LS_SYNC = 'city-rating-feedback-ls-sync';

function subscribeFeedbackStorage(key: string, onChange: () => void) {
  if (typeof window === 'undefined') return () => {};
  const onStorage = (e: StorageEvent) => {
    if (e.key === key || e.key === null) onChange();
  };
  const onSync = () => onChange();
  window.addEventListener('storage', onStorage);
  window.addEventListener(FEEDBACK_LS_SYNC, onSync);
  return () => {
    window.removeEventListener('storage', onStorage);
    window.removeEventListener(FEEDBACK_LS_SYNC, onSync);
  };
}

function notifyFeedbackStorageSync() {
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new Event(FEEDBACK_LS_SYNC));
  }
}

interface FeedbackWidgetProps {
  stationSlug?: string;
  stationName?: string;
  source: 'station_page' | 'general';
}

function storageKey(slug?: string) {
  return `feedback_${slug || 'general'}`;
}

export default function FeedbackWidget({ stationSlug, stationName, source }: FeedbackWidgetProps) {
  const t = useTranslations('feedback');
  const ns = source === 'station_page' ? 'station' : 'general';
  const [comment, setComment] = useState('');
  const [phase, setPhase] = useState<'idle' | 'submitting' | 'error'>('idle');
  const [submitError, setSubmitError] = useState<string | null>(null);

  const lsKey = storageKey(stationSlug);
  const alreadySent = useSyncExternalStore(
    (onChange) => subscribeFeedbackStorage(lsKey, onChange),
    () => (typeof window !== 'undefined' ? !!localStorage.getItem(lsKey) : false),
    () => false,
  );

  const handleSubmit = async () => {
    if (!comment.trim()) return;
    setSubmitError(null);
    setPhase('submitting');
    try {
      const res = await fetch('/api/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          vote: 'up',
          comment: comment.trim(),
          station_slug: stationSlug || undefined,
          page_url: window.location.pathname,
          visitor_id: getVisitorId(),
          source,
        }),
      });
      const data: { error?: string } = await res.json().catch(() => ({}));
      if (res.ok) {
        localStorage.setItem(storageKey(stationSlug), '1');
        notifyFeedbackStorageSync();
        setPhase('idle');
      } else {
        setPhase('error');
        setSubmitError(
          typeof data.error === 'string'
            ? data.error
            : res.status === 429
              ? t('rateLimitError')
              : t('genericError'),
        );
      }
    } catch {
      setPhase('error');
      setSubmitError(t('genericError'));
    }
  };

  if (alreadySent) {
    return (
      <div className="bg-green-50 rounded-lg border border-green-200 p-4 text-center">
        <p className="text-green-700 font-medium text-sm">{t(`${ns}.thanks`)}</p>
        <button
          onClick={() => {
            localStorage.removeItem(storageKey(stationSlug));
            notifyFeedbackStorageSync();
            setPhase('idle');
            setSubmitError(null);
            setComment('');
          }}
          className="text-xs text-green-600 hover:underline mt-1"
        >
          {t(`${ns}.again`)}
        </button>
      </div>
    );
  }

  return (
    <div className="bg-amber-50 rounded-lg border border-amber-200 p-4">
      <h2 className="font-bold text-sm mb-1">{t(`${ns}.title`)}</h2>
      <p className="text-xs text-gray-600 mb-2">
        {t(`${ns}.description`, { name: stationName || '' })}
      </p>
      <textarea
        value={comment}
        onChange={(e) => setComment(e.target.value)}
        placeholder={t(`${ns}.placeholder`)}
        rows={source === 'general' ? 2 : 3}
        maxLength={1000}
        className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400 focus:border-transparent resize-none"
      />
      {phase === 'error' && submitError && (
        <p className="text-xs text-red-600 mt-1">{submitError}</p>
      )}
      <div className="flex items-center justify-between mt-2">
        <span className="text-xs text-gray-400">{t('charCount', { count: comment.length })}</span>
        <button
          onClick={handleSubmit}
          disabled={!comment.trim() || phase === 'submitting'}
          className="px-3 py-1.5 rounded-md text-xs font-medium bg-amber-500 text-white hover:bg-amber-600 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          {phase === 'submitting' ? t('sending') : t(`${ns}.button`)}
        </button>
      </div>
    </div>
  );
}
