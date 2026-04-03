'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { getVisitorId } from '@/lib/visitor-id';
import { trackError } from '@/lib/track-error';

interface FeedbackWidgetProps {
  stationSlug?: string;
  source: 'station_page' | 'general';
}

type Phase = 'idle' | 'voted' | 'submitting' | 'done' | 'error';

function storageKey(slug?: string) {
  return `feedback_${slug || 'general'}`;
}

export default function FeedbackWidget({ stationSlug, source }: FeedbackWidgetProps) {
  const [phase, setPhase] = useState<Phase>('idle');
  const [vote, setVote] = useState<'up' | 'down' | null>(null);
  const [comment, setComment] = useState('');
  const [typing, setTyping] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Check if already submitted
  useEffect(() => {
    if (typeof window !== 'undefined' && localStorage.getItem(storageKey(stationSlug))) {
      setPhase('done');
    }
  }, [stationSlug]);

  const submit = useCallback(async (v: 'up' | 'down', text: string) => {
    setPhase('submitting');
    try {
      const res = await fetch('/api/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          vote: v,
          comment: text.trim() || undefined,
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
        trackError('fetch', { endpoint: '/api/feedback', status: String(res.status) });
        setPhase('error');
      }
    } catch {
      trackError('fetch', { endpoint: '/api/feedback', status: 'network' });
      setPhase('error');
    }
  }, [stationSlug, source]);

  const handleVote = (v: 'up' | 'down') => {
    setVote(v);
    setPhase('voted');
    // Auto-submit after 5s if user doesn't start typing
    timerRef.current = setTimeout(() => {
      if (!typing) submit(v, '');
    }, 5000);
  };

  const handleCommentChange = (text: string) => {
    setComment(text);
    if (!typing && text.length > 0) {
      setTyping(true);
      // Cancel auto-submit
      if (timerRef.current) {
        clearTimeout(timerRef.current);
        timerRef.current = null;
      }
    }
  };

  const handleSend = () => {
    if (vote) submit(vote, comment);
  };

  useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, []);

  if (phase === 'done') {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-5 text-center">
        <p className="text-sm text-gray-500">Thanks for your feedback!</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-5">
      <p className="text-sm font-medium text-gray-700 mb-3">
        {source === 'station_page' ? 'Was this page helpful?' : 'How is your experience?'}
      </p>

      <div className="flex items-center gap-2">
        <button
          onClick={() => handleVote('up')}
          disabled={phase === 'submitting'}
          data-umami-event="feedback-vote"
          data-umami-event-vote="up"
          className={`px-4 py-2 rounded-lg border text-sm transition-colors ${
            vote === 'up'
              ? 'bg-green-50 border-green-300 text-green-700'
              : 'border-gray-200 hover:bg-gray-50 text-gray-600'
          } disabled:opacity-50`}
        >
          👍 Yes
        </button>
        <button
          onClick={() => handleVote('down')}
          disabled={phase === 'submitting'}
          data-umami-event="feedback-vote"
          data-umami-event-vote="down"
          className={`px-4 py-2 rounded-lg border text-sm transition-colors ${
            vote === 'down'
              ? 'bg-red-50 border-red-300 text-red-700'
              : 'border-gray-200 hover:bg-gray-50 text-gray-600'
          } disabled:opacity-50`}
        >
          👎 No
        </button>

        {phase === 'submitting' && (
          <span className="text-xs text-gray-400 ml-2">Sending...</span>
        )}
        {phase === 'error' && (
          <button
            onClick={handleSend}
            className="text-xs text-red-500 hover:underline ml-2"
          >
            Failed — retry?
          </button>
        )}
      </div>

      {(phase === 'voted' || phase === 'error') && (
        <div className="mt-3 space-y-2">
          <textarea
            placeholder="Any comments? (optional)"
            value={comment}
            onChange={(e) => handleCommentChange(e.target.value)}
            maxLength={1000}
            rows={2}
            className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
          />
          <div className="flex items-center justify-between">
            <span className="text-xs text-gray-400">
              {typing ? '' : 'Auto-sending in a few seconds...'}
            </span>
            <button
              onClick={handleSend}
              data-umami-event="feedback-submit"
              className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 transition-colors"
            >
              Send Feedback
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
