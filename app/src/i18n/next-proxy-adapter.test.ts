import { afterEach, describe, expect, it } from 'vitest';
import { createRequire } from 'node:module';

// Exercise Next's installed Node adapter and route-relative comparison, rather
// than modeling their URL behavior in a mocked middleware response.
const require = createRequire(import.meta.url);
const { adapter } = require('next/dist/server/web/adapter');
const { getRelativeURL } = require('next/dist/shared/lib/router/utils/relativize-url');
const original = process.env.__NEXT_NO_MIDDLEWARE_URL_NORMALIZE;

afterEach(() => {
  if (original === undefined) delete process.env.__NEXT_NO_MIDDLEWARE_URL_NORMALIZE;
  else process.env.__NEXT_NO_MIDDLEWARE_URL_NORMALIZE = original;
});

describe('Next Node proxy URL normalization', () => {
  it.each([false, true])('keeps the bind-origin rewrite absolute and internal (RSC: %s)', async (rsc) => {
    process.env.__NEXT_NO_MIDDLEWARE_URL_NORMALIZE = '1';
    const initUrl = `https://127.0.0.1:3170/bangkok?level=grid${rsc ? '&_rsc=abc' : ''}`;
    let seenUrl = '';
    const result = await adapter({
      page: 'middleware',
      request: { url: initUrl, method: 'GET', headers: { 'x-forwarded-host': 'public.example', 'x-forwarded-proto': 'https', ...(rsc ? { rsc: '1' } : {}) }, nextConfig: {} },
      handler: (request: Request) => {
        seenUrl = request.url;
        return new Response(null, { headers: { 'x-middleware-rewrite': new URL('/en/bangkok?level=grid', request.url).toString() } });
      },
    });
    const rewrite = result.response.headers.get('x-middleware-rewrite');
    expect(seenUrl).toBe(initUrl);
    expect(rewrite).toBe(`https://127.0.0.1:3170/en/bangkok?level=grid${rsc ? '&_rsc=abc' : ''}`);
    expect(getRelativeURL(rewrite, initUrl)).toBe(`/en/bangkok?level=grid${rsc ? '&_rsc=abc' : ''}`);
  });

  it('rejects root-relative rewrite headers in the adapter', async () => {
    process.env.__NEXT_NO_MIDDLEWARE_URL_NORMALIZE = '1';
    await expect(adapter({ page: 'middleware', request: { url: 'http://127.0.0.1:3170/', method: 'GET', headers: {}, nextConfig: {} },
      handler: () => new Response(null, { headers: { 'x-middleware-rewrite': '/en' } }) })).rejects.toThrow();
  });
});
