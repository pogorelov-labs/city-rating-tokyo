import { describe, expect, it, vi } from 'vitest';
import { classifyMapError, ContextRecoveryTimer } from '@/components/bangkok/maplibre/map-errors';
import en from '@/messages/en/common.json';
import ja from '@/messages/ja/common.json';
import ru from '@/messages/ru/common.json';
import { bangkokClientMessages } from '@/lib/bangkok-client-messages';

describe('MapLibre availability', () => {
  it('ignores cancelled requests, reports style failure and keeps tile errors recoverable', () => {
    expect(classifyMapError({ name: 'AbortError', message: 'aborted' }, false)).toBe('ignore');
    expect(classifyMapError({ message: 'request canceled' }, true)).toBe('ignore');
    expect(classifyMapError({ message: 'Failed to fetch https://tiles.openfreemap.org/styles/positron' }, false)).toBe('load');
    expect(classifyMapError({ message: 'tile failed' }, true)).toBe('tile');
    expect(classifyMapError({ message: 'tile failed' }, false)).toBe('ignore');
  });
  it('keeps all renderer controls and fallback messages available to each client locale', () => {
    const keys = ['rendererLabel', 'rendererThreeD', 'rendererStandard', 'rendererUnavailableWebgl', 'rendererUnavailableLoad', 'rendererUnavailableContext', 'mapControls', 'view2d', 'view3d', 'buildings', 'resetAsok', 'selectedArea', 'closeSelectedArea', 'interactiveBangkok', 'resetBearing', 'mapAttribution', 'tileError'] as const;
    for (const messages of [en, ja, ru]) {
      const client = bangkokClientMessages(messages);
      for (const key of keys) expect(client).toHaveProperty(`map.${key}`, expect.any(String));
    }
  });
});


describe('context recovery timeout', () => {
  it('allows restoration and reports only a loss or style rebuild that exceeds the deadline', () => {
    vi.useFakeTimers();
    try {
      const fail = vi.fn();
      const timer = new ContextRecoveryTimer(fail, 100);
      timer.start();
      vi.advanceTimersByTime(90);
      timer.clear();
      timer.start();
      vi.advanceTimersByTime(90);
      expect(fail).not.toHaveBeenCalled();
      timer.clear();
      vi.advanceTimersByTime(100);
      expect(fail).not.toHaveBeenCalled();
      timer.start();
      vi.advanceTimersByTime(100);
      expect(fail).toHaveBeenCalledTimes(1);
      timer.clear();
    } finally { vi.useRealTimers(); }
  });
});
