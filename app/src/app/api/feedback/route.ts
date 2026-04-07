import { NextRequest, NextResponse } from 'next/server';

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const SLUG_RE = /^[a-z0-9-]+$/;

/** Last submit time per IP — only blocks rapid repeat (double-click / instant re-submit). */
const rateLimit = new Map<string, number>();

/** Min ms between posts from the same IP. Keep low so “Add another tip” works; anti-spam is NocoDB + moderation. */
const MIN_SUBMIT_INTERVAL_MS = 2500;

function getClientIP(req: NextRequest): string {
  return req.headers.get('x-forwarded-for')?.split(',')[0]?.trim()
    || req.headers.get('x-real-ip')
    || 'unknown';
}

export async function POST(req: NextRequest) {
  const origin = req.headers.get('origin');
  if (origin && !origin.endsWith('.pogorelov.dev')) {
    return NextResponse.json({ error: 'Forbidden' }, { status: 403 });
  }

  const NOCODB_API_URL = process.env.NOCODB_API_URL;
  const NOCODB_API_TOKEN = process.env.NOCODB_API_TOKEN;
  const NOCODB_TABLE_ID = process.env.NOCODB_TABLE_ID;

  if (!NOCODB_API_URL || !NOCODB_API_TOKEN || !NOCODB_TABLE_ID) {
    console.error('Missing NocoDB env vars');
    return NextResponse.json({ error: 'Server configuration error' }, { status: 500 });
  }

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
  if (comment !== undefined && comment !== null) {
    if (typeof comment !== 'string' || comment.length > 1000) {
      return NextResponse.json({ error: 'comment must be a string under 1000 chars' }, { status: 400 });
    }
  }
  if (station_slug && !SLUG_RE.test(station_slug)) {
    return NextResponse.json({ error: 'invalid station_slug format' }, { status: 400 });
  }
  if (!page_url || typeof page_url !== 'string' || page_url.length > 500 || !page_url.startsWith('/')) {
    return NextResponse.json({ error: 'page_url is required and must start with /' }, { status: 400 });
  }
  if (!visitor_id || !UUID_RE.test(visitor_id)) {
    return NextResponse.json({ error: 'visitor_id must be a valid UUID' }, { status: 400 });
  }
  if (!source || !['station_page', 'general'].includes(source)) {
    return NextResponse.json({ error: 'source must be "station_page" or "general"' }, { status: 400 });
  }

  // Rate limit by IP (short gap only — 10s broke legitimate “Add another tip” within one session)
  const clientIP = getClientIP(req);
  const now = Date.now();
  const lastSubmit = rateLimit.get(clientIP);
  if (lastSubmit && now - lastSubmit < MIN_SUBMIT_INTERVAL_MS) {
    const retrySec = Math.max(1, Math.ceil((MIN_SUBMIT_INTERVAL_MS - (now - lastSubmit)) / 1000));
    return NextResponse.json(
      { error: `Please wait ${retrySec}s before sending again (rate limit).` },
      { status: 429, headers: { 'Retry-After': String(retrySec) } },
    );
  }
  rateLimit.set(clientIP, now);

  if (rateLimit.size > 1_000) {
    for (const [key, ts] of rateLimit) {
      if (now - ts > 60_000) rateLimit.delete(key);
    }
  }

  // Strip HTML tags from comment
  const sanitizedComment = comment ? comment.replace(/<[^>]*>/g, '').trim() : null;

  const record = {
    vote,
    comment: sanitizedComment || null,
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
    console.error('Feedback API error:', err);
    return NextResponse.json({ error: 'Failed to save feedback' }, { status: 500 });
  }
}
