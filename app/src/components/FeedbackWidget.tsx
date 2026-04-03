'use client';

import { useState, useEffect } from 'react';
import { getVisitorId } from '@/lib/visitor-id';

interface FeedbackWidgetProps {
  stationSlug: string;
  stationName: string;
  source: 'station_page' | 'general';
}

function storageKey(slug: string) {
  return `feedback_${slug}`;
}

export default function FeedbackWidget({ stationSlug, stationName, source }: FeedbackWidgetProps) {
  const [comment, setComment] = useState('');
  const [phase, setPhase] = useState<'idle' | 'submitting' | 'done' | 'error'>('idle');

  useEffect(() => {
    if (typeof window !== 'undefined' && localStorage.getItem(storageKey(stationSlug))) {
      setPhase('done');
    }
  }, [stationSlug]);

  const handleSubmit = async () => {
    if (!comment.trim()) return;
    setPhase('submitting');
    try {
      const res = await fetch('/api/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          comment: comment.trim(),
          station_slug: stationSlug,
          page_url: window.location.pathname,
          visitor_id: getVisitorId(),
          source,
        }),
      });
      if (res.ok) {
        localStorage.setItem(storageKey(stationSlug), '1');
        setPhase('done');
      } else {
        setPhase('error');
      }
    } catch {
      setPhase('error');
    }
  };

  if (phase === 'done') {
    return (
      <div className="bg-green-50 rounded-lg border border-green-200 p-5 text-center">
        <p className="text-green-700 font-medium">Thanks for sharing!</p>
        <button
          onClick={() => {
            localStorage.removeItem(storageKey(stationSlug));
            setPhase('idle');
            setComment('');
          }}
          className="text-sm text-green-600 hover:underline mt-1"
        >
          Add another tip
        </button>
      </div>
    );
  }

  return (
    <div className="bg-amber-50 rounded-lg border border-amber-200 p-5">
      <h2 className="font-bold text-lg mb-1">Know this area?</h2>
      <p className="text-sm text-gray-600 mb-3">
        Share what it&apos;s like living near {stationName} &mdash; your tips help others choose.
      </p>
      <textarea
        value={comment}
        onChange={(e) => setComment(e.target.value)}
        placeholder="What's the vibe? Best spots? Anything to watch out for?"
        rows={3}
        maxLength={1000}
        className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400 focus:border-transparent resize-none"
      />
      {phase === 'error' && (
        <p className="text-sm text-red-600 mt-1">Could not send. Please try again.</p>
      )}
      <div className="flex items-center justify-between mt-2">
        <span className="text-xs text-gray-400">{comment.length}/1000</span>
        <button
          onClick={handleSubmit}
          disabled={!comment.trim() || phase === 'submitting'}
          className="px-4 py-1.5 rounded-md text-sm font-medium bg-amber-500 text-white hover:bg-amber-600 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          {phase === 'submitting' ? 'Sending...' : 'Share Tip'}
        </button>
      </div>
    </div>
  );
}
