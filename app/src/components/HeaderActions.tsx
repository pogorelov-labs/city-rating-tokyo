'use client';

import { useState } from 'react';
import { Station } from '@/lib/types';
import { useAppStore } from '@/lib/store';
import { buildShareUrl } from '@/lib/url-state';
import ScatterPlotExplorer from './ScatterPlotExplorer';
import FeedbackWidget from './FeedbackWidget';

interface Props {
  stations: Station[];
}

export default function HeaderActions({ stations }: Props) {
  const [scatterOpen, setScatterOpen] = useState(false);
  const [feedbackOpen, setFeedbackOpen] = useState(false);
  const [copied, setCopied] = useState(false);

  const handleShare = async () => {
    const state = useAppStore.getState();
    const url = buildShareUrl(state);
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      window.umami?.track('error', { category: 'clipboard' });
    }
  };

  return (
    <>
      <button
        onClick={() => setScatterOpen(true)}
        className="text-xs px-3 py-1.5 rounded-lg border border-gray-200 bg-white hover:bg-gray-50 text-gray-600 transition-colors"
      >
        Scatter Plot
      </button>

      <button
        onClick={handleShare}
        className="text-xs px-3 py-1.5 rounded-lg border border-gray-200 bg-white hover:bg-gray-50 text-gray-600 transition-colors"
      >
        {copied ? 'Copied!' : 'Share'}
      </button>

      <button
        onClick={() => setFeedbackOpen(true)}
        data-umami-event="open-feedback-modal"
        className="text-xs px-3 py-1.5 rounded-lg border border-gray-200 bg-white hover:bg-gray-50 text-gray-600 transition-colors"
      >
        Feedback
      </button>

      {feedbackOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div
            className="absolute inset-0 bg-black/40"
            onClick={() => setFeedbackOpen(false)}
          />
          <div className="relative bg-white rounded-xl shadow-2xl max-w-md w-full p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-bold">Feedback</h2>
              <button
                onClick={() => setFeedbackOpen(false)}
                className="text-gray-400 hover:text-gray-600 p-1"
              >
                <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M18 6L6 18M6 6l12 12" />
                </svg>
              </button>
            </div>
            <FeedbackWidget source="general" />
          </div>
        </div>
      )}

      {scatterOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div
            className="absolute inset-0 bg-black/40"
            onClick={() => setScatterOpen(false)}
          />
          <div className="relative bg-white rounded-xl shadow-2xl max-w-3xl w-full max-h-[85vh] overflow-y-auto p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-bold">Scatter Plot Explorer</h2>
              <button
                onClick={() => setScatterOpen(false)}
                className="text-gray-400 hover:text-gray-600 p-1"
              >
                <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M18 6L6 18M6 6l12 12" />
                </svg>
              </button>
            </div>
            <ScatterPlotExplorer stations={stations} />
          </div>
        </div>
      )}
    </>
  );
}
