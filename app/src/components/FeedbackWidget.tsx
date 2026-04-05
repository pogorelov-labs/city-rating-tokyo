'use client';

import { useState, useEffect } from 'react';
import { getVisitorId } from '@/lib/visitor-id';

interface FeedbackWidgetProps {
  stationSlug?: string;
  stationName?: string;
  source: 'station_page' | 'general';
}

function storageKey(slug?: string) {
  return `feedback_${slug || 'general'}`;
}

const COPY = {
  station_page: {
    title: 'Know this area?',
    description: (name: string) =>
      `Share what it\u2019s like living near ${name} \u2014 your tips help others choose.`,
    placeholder: "What's the vibe? Best spots? Anything to watch out for?",
    button: 'Share Tip',
    thanks: 'Thanks for sharing!',
    again: 'Add another tip',
  },
  general: {
    title: 'Got feedback?',
    description: () =>
      'Tell us how we can make this site more useful \u2014 missing features, wrong data, new ideas.',
    placeholder: 'What would make this site better for you?',
    button: 'Send Feedback',
    thanks: 'Thanks for your feedback!',
    again: 'Send more',
  },
};

export default function FeedbackWidget({ stationSlug, stationName, source }: FeedbackWidgetProps) {
  const [comment, setComment] = useState('');
  const [phase, setPhase] = useState<'idle' | 'submitting' | 'done' | 'error'>('idle');
  const copy = COPY[source];

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
          vote: 'up',
          comment: comment.trim(),
          station_slug: stationSlug || undefined,
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
      <div className="bg-green-50 rounded-lg border border-green-200 p-4 text-center">
        <p className="text-green-700 font-medium text-sm">{copy.thanks}</p>
        <button
          onClick={() => {
            localStorage.removeItem(storageKey(stationSlug));
            setPhase('idle');
            setComment('');
          }}
          className="text-xs text-green-600 hover:underline mt-1"
        >
          {copy.again}
        </button>
      </div>
    );
  }

  return (
    <div className="bg-amber-50 rounded-lg border border-amber-200 p-4">
      <h2 className="font-bold text-sm mb-1">{copy.title}</h2>
      <p className="text-xs text-gray-600 mb-2">
        {copy.description(stationName || '')}
      </p>
      <textarea
        value={comment}
        onChange={(e) => setComment(e.target.value)}
        placeholder={copy.placeholder}
        rows={source === 'general' ? 2 : 3}
        maxLength={1000}
        className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400 focus:border-transparent resize-none"
      />
      {phase === 'error' && (
        <p className="text-xs text-red-600 mt-1">Could not send. Please try again.</p>
      )}
      <div className="flex items-center justify-between mt-2">
        <span className="text-xs text-gray-400">{comment.length}/1000</span>
        <button
          onClick={handleSubmit}
          disabled={!comment.trim() || phase === 'submitting'}
          className="px-3 py-1.5 rounded-md text-xs font-medium bg-amber-500 text-white hover:bg-amber-600 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          {phase === 'submitting' ? 'Sending...' : copy.button}
        </button>
      </div>
    </div>
  );
}
