import { describe, expect, it } from 'vitest';
import { collapseInitialAttribution } from './attribution';

describe('compact attribution', () => {
  it('collapses once credits arrive and leaves subsequent user expansion alone', async () => {
    const details = document.createElement('details');
    const dispose = collapseInitialAttribution(details);
    details.classList.add('maplibregl-compact', 'maplibregl-compact-show');
    details.setAttribute('open', '');
    await Promise.resolve();
    expect(details).not.toHaveAttribute('open');
    expect(details).not.toHaveClass('maplibregl-compact-show');
    details.classList.add('maplibregl-compact-show');
    details.setAttribute('open', '');
    await Promise.resolve();
    expect(details).toHaveAttribute('open');
    expect(details).toHaveClass('maplibregl-compact-show');
    dispose();
  });
});
