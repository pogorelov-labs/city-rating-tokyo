import { NextRequest, NextResponse } from 'next/server';

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const SLUG_RE = /^[a-z0-9-]+$/;

const rateLimit = new Map<string, number>();

export async function POST(req: NextRequest) {
  let body: Record<string, unknown>;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: 'Invalid JSON' }, { status: 400 });
  }

  const { vote, comment, station_slug, page_url, visitor_id, source } = body as {
    vote?: string;
    comment?: string;
    station_slug?: string;
    page_url?: string;
    visitor_id?: string;
    source?: string;
  };

  // Validation
  if (!vote || !['up', 'down'].includes(vote)) {
    return NextResponse.json({ error: 'vote must be "up" or "down"' }, { status: 400 });
  }
  if (comment && (typeof comment !== 'string' || comment.length > 1000)) {
    return NextResponse.json({ error: 'comment must be a string under 1000 chars' }, { status: 400 });
  }
  if (station_slug && !SLUG_RE.test(station_slug)) {
    return NextResponse.json({ error: 'invalid station_slug format' }, { status: 400 });
  }
  if (!page_url || typeof page_url !== 'string' || page_url.length > 500) {
    return NextResponse.json({ error: 'page_url is required' }, { status: 400 });
  }
  if (!visitor_id || !UUID_RE.test(visitor_id)) {
    return NextResponse.json({ error: 'visitor_id must be a valid UUID' }, { status: 400 });
  }
  if (!source || !['station_page', 'general'].includes(source)) {
    return NextResponse.json({ error: 'source must be "station_page" or "general"' }, { status: 400 });
  }

  // Rate limit: 10s per visitor
  const now = Date.now();
  const lastSubmit = rateLimit.get(visitor_id);
  if (lastSubmit && now - lastSubmit < 10_000) {
    return NextResponse.json({ error: 'Please wait before submitting again' }, { status: 429 });
  }
  rateLimit.set(visitor_id, now);

  // Clean up old entries periodically
  if (rateLimit.size > 10_000) {
    for (const [key, ts] of rateLimit) {
      if (now - ts > 60_000) rateLimit.delete(key);
    }
  }

  const { NOCODB_API_URL, NOCODB_API_TOKEN, NOCODB_TABLE_ID } = process.env;
  if (!NOCODB_API_URL || !NOCODB_API_TOKEN || !NOCODB_TABLE_ID) {
    console.error('Missing NocoDB env vars');
    return NextResponse.json({ error: 'Server configuration error' }, { status: 500 });
  }

  const record = {
    vote,
    comment: comment?.trim() || null,
    station_slug: station_slug || null,
    page_url,
    visitor_id,
    user_agent: req.headers.get('user-agent') || null,
    created_at: new Date().toISOString(),
    source,
  };

  try {
    const res = await fetch(`${NOCODB_API_URL}/api/v2/tables/${NOCODB_TABLE_ID}/records`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'xc-token': NOCODB_API_TOKEN,
      },
      body: JSON.stringify(record),
    });

    if (!res.ok) {
      const text = await res.text();
      console.error('NocoDB error:', res.status, text);
      return NextResponse.json({ error: 'Failed to save feedback' }, { status: 500 });
    }

    return NextResponse.json({ success: true }, { status: 201 });
  } catch (err) {
    console.error('NocoDB request failed:', err);
    return NextResponse.json({ error: 'Failed to save feedback' }, { status: 500 });
  }
}
