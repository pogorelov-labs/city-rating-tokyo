import { NextRequest, NextResponse } from 'next/server';

const NOCODB_API_URL = process.env.NOCODB_API_URL!;
const NOCODB_API_TOKEN = process.env.NOCODB_API_TOKEN!;
const NOCODB_TABLE_ID = process.env.NOCODB_TABLE_ID!;

const SLUG_RE = /^[a-z0-9-]{1,80}$/;
const UUID_RE = /^[0-9a-f-]{36}$/;
const PATH_RE = /^\/[a-z0-9/_-]{0,200}$/;

function sanitizeString(val: unknown, maxLen: number): string | null {
  if (typeof val !== 'string') return null;
  return val.slice(0, maxLen).trim() || null;
}

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { comment, station_slug, page_url, visitor_id } = body;

    const cleanComment = sanitizeString(comment, 1000);
    if (!cleanComment) {
      return NextResponse.json({ error: 'comment required' }, { status: 400 });
    }

    const cleanSlug = typeof station_slug === 'string' && SLUG_RE.test(station_slug)
      ? station_slug : null;
    const cleanPath = typeof page_url === 'string' && PATH_RE.test(page_url)
      ? page_url : null;
    const cleanVisitor = typeof visitor_id === 'string' && UUID_RE.test(visitor_id)
      ? visitor_id : null;

    const res = await fetch(`${NOCODB_API_URL}/api/v2/tables/${NOCODB_TABLE_ID}/records`, {
      method: 'POST',
      headers: {
        'xc-token': NOCODB_API_TOKEN,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        comment: cleanComment,
        station_slug: cleanSlug,
        page_url: cleanPath,
        visitor_id: cleanVisitor,
        user_agent: (req.headers.get('user-agent') || '').slice(0, 500) || null,
        source: cleanSlug ? 'station_page' : 'general',
      }),
    });

    if (!res.ok) {
      const text = await res.text();
      console.error('NocoDB error:', res.status, text);
      return NextResponse.json({ error: 'failed to save' }, { status: 500 });
    }

    return NextResponse.json({ ok: true });
  } catch (e) {
    console.error('Feedback API error:', e);
    return NextResponse.json({ error: 'server error' }, { status: 500 });
  }
}
