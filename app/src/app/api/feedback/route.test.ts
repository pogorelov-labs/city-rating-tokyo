/**
 * Feedback API input validation: every page's FeedbackWidget must be able to
 * post — including Bangkok station-area pages, whose key is `st.<id>`.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { NextRequest } from 'next/server';

let ip = 0;

function post(body: Record<string, unknown>) {
  // A fresh client IP per request keeps the per-IP cooldown out of the way.
  ip += 1;
  return new NextRequest('https://city-rating.pogorelov.dev/api/feedback', {
    method: 'POST',
    headers: { 'content-type': 'application/json', 'x-forwarded-for': `203.0.113.${ip}` },
    body: JSON.stringify(body),
  });
}

const VALID = {
  vote: 'up',
  page_url: '/bangkok/station/asok',
  visitor_id: '123e4567-e89b-12d3-a456-426614174000',
  source: 'station_page',
};

describe('POST /api/feedback', () => {
  beforeEach(() => {
    vi.stubEnv('NOCODB_API_URL', 'https://nocodb.example');
    vi.stubEnv('NOCODB_API_TOKEN', 'test-token');
    vi.stubEnv('NOCODB_TABLE_ID', 'test-table');
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({ Id: 1 }), { status: 200 })));
  });
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.unstubAllGlobals();
  });

  it.each(['shibuya', 'watthana', 'st.asok', 'st.krung-thep-aphiwat'])('accepts the area key %s', async (slug) => {
    const { POST } = await import('./route');
    const res = await POST(post({ ...VALID, station_slug: slug }));
    expect(res.status, await res.clone().text()).toBeLessThan(400);
  });

  it.each(['st.', 'St.Asok', 'cell.12', 'asok/../x', 'bad slug'])('rejects %s', async (slug) => {
    const { POST } = await import('./route');
    const res = await POST(post({ ...VALID, station_slug: slug }));
    expect(res.status).toBe(400);
  });
});
