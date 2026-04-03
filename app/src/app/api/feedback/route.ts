import { NextRequest, NextResponse } from 'next/server';

const NOCODB_API_URL = process.env.NOCODB_API_URL!;
const NOCODB_API_TOKEN = process.env.NOCODB_API_TOKEN!;
const NOCODB_TABLE_ID = process.env.NOCODB_TABLE_ID!;

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { vote, comment, station_slug, page_url, visitor_id } = body;

    if (!vote && !comment) {
      return NextResponse.json({ error: 'vote or comment required' }, { status: 400 });
    }

    if (comment && comment.length > 1000) {
      return NextResponse.json({ error: 'comment too long' }, { status: 400 });
    }

    const res = await fetch(`${NOCODB_API_URL}/api/v2/tables/${NOCODB_TABLE_ID}/records`, {
      method: 'POST',
      headers: {
        'xc-token': NOCODB_API_TOKEN,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        vote: vote || null,
        comment: comment || null,
        station_slug: station_slug || null,
        page_url: page_url || null,
        visitor_id: visitor_id || null,
        user_agent: req.headers.get('user-agent') || null,
        source: station_slug ? 'station_page' : 'general',
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
