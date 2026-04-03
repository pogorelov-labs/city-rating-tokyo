'use client';

import { useState } from 'react';

const FEEDBACK_EMAIL = 'feedback@tokyoexplorer.app';

export default function FeedbackForm({ stationName }: { stationName: string }) {
  const [text, setText] = useState('');
  const [sent, setSent] = useState(false);

  const handleSubmit = () => {
    if (!text.trim()) return;
    const subject = encodeURIComponent(`Feedback: ${stationName}`);
    const body = encodeURIComponent(text.trim());
    window.open(`mailto:${FEEDBACK_EMAIL}?subject=${subject}&body=${body}`, '_self');
    setSent(true);
  };

  if (sent) {
    return (
      <section className="bg-green-50 rounded-lg border border-green-200 p-5 text-center">
        <p className="text-green-700 font-medium">Thanks for your feedback!</p>
        <button
          onClick={() => { setSent(false); setText(''); }}
          className="text-sm text-green-600 hover:underline mt-1"
        >
          Send another
        </button>
      </section>
    );
  }

  return (
    <section className="bg-amber-50 rounded-lg border border-amber-200 p-5">
      <h2 className="font-bold text-lg mb-1">Know this area?</h2>
      <p className="text-sm text-gray-600 mb-3">
        Share what it&apos;s like living near {stationName} &mdash; your tips help others choose.
      </p>
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="What's the vibe? Best spots? Anything to watch out for?"
        rows={3}
        className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400 focus:border-transparent resize-none"
      />
      <div className="flex justify-end mt-2">
        <button
          onClick={handleSubmit}
          disabled={!text.trim()}
          className="px-4 py-1.5 rounded-md text-sm font-medium bg-amber-500 text-white hover:bg-amber-600 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          Send Feedback
        </button>
      </div>
    </section>
  );
}
