import { describe, expect, it } from 'vitest';
import { districtPopupOffset } from '@/components/bangkok/district-popup-layout';

describe('district popup placement', () => {
  it('moves the card away from a selected outline when a clear corner exists', () => {
    const size = { x: 992, y: 628 }, anchor = { x: 669, y: 304 };
    const offset = districtPopupOffset(size, anchor, 306, 440, { left: 614, top: 148, right: 724, bottom: 304 });
    const cardLeft = anchor.x + offset.x - 153, cardRight = cardLeft + 306;
    expect(cardLeft).toBeGreaterThanOrEqual(0);
    expect(cardRight).toBeLessThan(614);
    expect(anchor.y + offset.y).toBeLessThanOrEqual(size.y);
  });
  it('keeps an already clear placement instead of forcing a dock', () => {
    const offset = districtPopupOffset({ x: 992, y: 628 }, { x: 300, y: 580 }, 306, 440,
      { left: 700, top: 100, right: 800, bottom: 200 });
    expect(offset).toEqual({ x: 0, y: 0 });
  });
});
