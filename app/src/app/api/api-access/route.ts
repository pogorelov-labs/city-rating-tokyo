import { createHash, randomBytes } from 'node:crypto';
import { NextRequest, NextResponse } from 'next/server';
import { getClientIP, validateOrigin } from '@/lib/api-security';

/**
 * MCP API key issuance.
 *
 * POST { email, use_case } → generates a random `crk_<32 hex>` key,
 * stores SHA-256(key) + email + use_case in NocoDB with status=pending,
 * and returns the plaintext key ONCE so the user can save it. The MCP
 * server only ever sees the hash — same hash function (SHA-256 hex).
 *
 * Admin reviews pending requests in NocoDB and flips status → 'active'.
 * The MCP refreshes its key cache every 5 min.
 */

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const MIN_SUBMIT_INTERVAL_MS = 60_000;
const MAX_USE_CASE_LEN = 500;
const MAX_EMAIL_LEN = 320;

const rateLimit = new Map<string, number>();

function generateKey(): string {
  return `crk_${randomBytes(16).toString('hex')}`;
}

function hashKey(plaintext: string): string {
  return createHash('sha256').update(plaintext).digest('hex');
}

export async function POST(req: NextRequest) {
  if (!validateOrigin(req)) {
    return NextResponse.json({ error: 'Forbidden' }, { status: 403 });
  }

  const NOCODB_API_URL = process.env.NOCODB_API_URL;
  const NOCODB_API_TOKEN = process.env.NOCODB_API_TOKEN;
  const NOCODB_API_KEYS_TABLE_ID = process.env.NOCODB_API_KEYS_TABLE_ID;

  if (!NOCODB_API_URL || !NOCODB_API_TOKEN || !NOCODB_API_KEYS_TABLE_ID) {
    console.error('Missing NocoDB env vars for api_keys');
    return NextResponse.json({ error: 'Server configuration error' }, { status: 500 });
  }

  let body: { email?: string; use_case?: string };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: 'Invalid JSON body' }, { status: 400 });
  }

  const email = (body.email || '').trim().toLowerCase();
  const useCase = (body.use_case || '').replace(/<[^>]*>/g, '').trim();

  if (!EMAIL_RE.test(email) || email.length > MAX_EMAIL_LEN) {
    return NextResponse.json({ error: 'Valid email required' }, { status: 400 });
  }
  if (useCase.length < 10 || useCase.length > MAX_USE_CASE_LEN) {
    return NextResponse.json(
      { error: `Use case must be 10–${MAX_USE_CASE_LEN} characters.` },
      { status: 400 },
    );
  }

  const clientIP = getClientIP(req);
  const now = Date.now();
  const lastSubmit = rateLimit.get(clientIP);
  if (lastSubmit && now - lastSubmit < MIN_SUBMIT_INTERVAL_MS) {
    const retrySec = Math.ceil((MIN_SUBMIT_INTERVAL_MS - (now - lastSubmit)) / 1000);
    return NextResponse.json(
      { error: `Please wait ${retrySec}s before requesting another key.` },
      { status: 429, headers: { 'Retry-After': String(retrySec) } },
    );
  }
  rateLimit.set(clientIP, now);
  if (rateLimit.size > 1_000) {
    for (const [k, ts] of rateLimit) {
      if (now - ts > 5 * 60_000) rateLimit.delete(k);
    }
  }

  const plaintextKey = generateKey();
  // NocoDB tracks creation time automatically via the system `CreatedAt` field;
  // don't send `created_at` explicitly — there is no such column in api_keys.
  const record = {
    key_hash: hashKey(plaintextKey),
    email,
    use_case: useCase,
    status: 'pending',
    rate_limit_per_min: 60,
  };

  try {
    const res = await fetch(
      `${NOCODB_API_URL}/api/v2/tables/${NOCODB_API_KEYS_TABLE_ID}/records`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'xc-token': NOCODB_API_TOKEN,
        },
        body: JSON.stringify(record),
      },
    );

    if (!res.ok) {
      const text = await res.text();
      console.error('NocoDB error:', res.status, text);
      return NextResponse.json({ error: 'Failed to register key' }, { status: 500 });
    }

    return NextResponse.json(
      {
        success: true,
        key: plaintextKey,
        status: 'pending',
        message:
          'Save this key now — it will not be shown again. ' +
          'It is in pending state; you will be notified when it is approved.',
      },
      { status: 201 },
    );
  } catch (err) {
    console.error('api-access route error:', err);
    return NextResponse.json({ error: 'Failed to register key' }, { status: 500 });
  }
}
