import { describe, expect, it } from 'vitest';
import { panReleaseVelocity } from './pan-velocity';

const p = (x: number, time: number, y = 0) => ({ x, y, time });
describe('pan release velocity', () => {
  it('uses the final reversal rather than the earlier drag', () => {
    const v = panReleaseVelocity([p(0, 0), p(100, 20), p(200, 40), p(183, 55), p(165, 70)], p(165, 75));
    expect(v?.dx).toBe(-35);
    expect(v?.speed).toBeGreaterThan(0);
  });
  it('retains velocity for a continuous diagonal pan', () => {
    const v = panReleaseVelocity([p(0, 0), p(20, 20, 10), p(40, 40, 20)], p(40, 45, 20));
    expect(v?.dx).toBe(40);
    expect(v?.dy).toBe(20);
  });
  it('does not coast after holding still', () => {
    expect(panReleaseVelocity([p(0, 0), p(100, 20)], p(100, 150))).toBeUndefined();
  });
  it('accounts for a short pause and ignores tiny movement', () => {
    expect(panReleaseVelocity([p(0, 0), p(20, 20)], p(20, 80))?.speed).toBe(250);
    expect(panReleaseVelocity([p(0, 0), p(1, 20)], p(1, 25))).toBeUndefined();
  });
});
