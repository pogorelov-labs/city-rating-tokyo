/**
 * Shared security helpers for public POST route handlers.
 *
 * Used by:
 *   - src/app/api/feedback/route.ts
 *   - src/app/api/api-access/route.ts
 *
 * These routes are public (no auth) and sit behind the Coolify/Traefik
 * reverse proxy, so they must validate the Origin header and read the
 * client IP from proxy-set headers correctly.
 */

import type { NextRequest } from 'next/server';

/**
 * Origins permitted to issue browser requests against the public APIs.
 * The production site is the only browser origin; everything else is
 * rejected for browser-shaped requests.
 */
const ALLOWED_BROWSER_ORIGINS = new Set<string>([
  'https://city-rating.pogorelov.dev',
]);

/**
 * Optional dev origin. Set `ALLOWED_DEV_ORIGIN` (e.g. `http://localhost:3000`)
 * in the local environment to allow development requests. We deliberately do
 * NOT match `http://localhost*` because that also matches attacker hosts like
 * `http://localhost.evil.com`.
 */
const ALLOWED_DEV_ORIGIN = process.env.ALLOWED_DEV_ORIGIN;

/**
 * Heuristic: does this request look like it came from a browser?
 *
 * Browsers always send an `Origin` header on cross-origin/state-changing
 * requests, and modern browsers also send `Sec-Fetch-Mode` and `Referer`.
 * If any of those are present, we treat the request as browser-shaped and
 * require the Origin to be on the allowlist.
 *
 * Non-browser clients (curl, server-to-server, the MCP server) typically
 * send none of these headers and are allowed through without an Origin.
 */
function looksLikeBrowser(req: NextRequest): boolean {
  return (
    req.headers.get('origin') !== null ||
    req.headers.get('sec-fetch-mode') !== null ||
    req.headers.get('referer') !== null
  );
}

/**
 * Validate the Origin header against the allowlist.
 *
 * Returns `true` if the request is allowed to proceed, `false` if it should
 * be rejected with 403. The rules are:
 *
 *   1. If an Origin header is present, it must EXACTLY match an entry on the
 *      allowlist (production origin, or `ALLOWED_DEV_ORIGIN` if set). This
 *      blocks `evil.pogorelov.dev` and `localhost.evil.com` style bypasses
 *      that suffix/prefix matching would permit.
 *   2. If no Origin header is present, the request is only allowed when it
 *      does NOT look browser-shaped (no `Sec-Fetch-Mode`, no `Referer`).
 *      Real browsers always send Origin on POSTs, so an Origin-less request
 *      that otherwise looks like a browser is treated as spoofed/forbidden.
 *      Server-to-server / curl clients without those headers are allowed.
 */
export function validateOrigin(req: NextRequest): boolean {
  const origin = req.headers.get('origin');

  if (origin !== null) {
    if (ALLOWED_BROWSER_ORIGINS.has(origin)) return true;
    if (ALLOWED_DEV_ORIGIN && origin === ALLOWED_DEV_ORIGIN) return true;
    return false;
  }

  // No Origin header. Allow only if the request doesn't look browser-shaped.
  return !looksLikeBrowser(req);
}

/**
 * Resolve the originating client IP from proxy headers.
 *
 * The app runs behind the Coolify/Traefik reverse proxy, which appends each
 * hop to `x-forwarded-for` and sets `x-real-ip` to the immediate client.
 *
 * TRUSTED-PROXY ASSUMPTION: we trust Traefik to be the LAST entity writing
 * `x-forwarded-for`. The leftmost entries are client-controlled and therefore
 * unsafe — a client can forge them to defeat IP-based rate limiting. We read
 * the RIGHTMOST (last) hop, which is the one our trusted proxy appended.
 *
 * If there is no `x-forwarded-for`, fall back to `x-real-ip` (also set by
 * the proxy). If neither header is present, return `'unknown'` so rate
 * limiting still keys against something.
 */
export function getClientIP(req: NextRequest): string {
  const xff = req.headers.get('x-forwarded-for');
  if (xff) {
    const hops = xff.split(',').map((h) => h.trim()).filter(Boolean);
    if (hops.length > 0) {
      // Last hop = appended by our trusted proxy (Traefik). See note above.
      return hops[hops.length - 1];
    }
  }

  return req.headers.get('x-real-ip') || 'unknown';
}
