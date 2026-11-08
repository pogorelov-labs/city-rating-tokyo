import { describe, expect, it } from 'vitest';
import { contentSecurityPolicy } from '../content-security-policy';

describe('renderer content security policy', () => {
  it('permits the map provider as data across SPA routes, not as JavaScript', () => {
    const policy = contentSecurityPolicy();
    expect(policy).toContain("connect-src 'self' https://*.pogorelov.dev https://tiles.openfreemap.org");
    expect(policy).toContain("worker-src 'self' blob:");
    expect(policy.split('; ').find((d) => d.startsWith('script-src'))).not.toContain('openfreemap');
    expect(policy).not.toContain('unsafe-eval');
    expect(policy).toContain("frame-ancestors 'none'");
  });
  it('permits React development debugging only in development', () => {
    expect(contentSecurityPolicy({ development: true })).toContain("'unsafe-eval'");
    expect(contentSecurityPolicy({ development: false })).not.toContain("'unsafe-eval'");
  });
});
