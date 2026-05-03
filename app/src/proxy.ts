import createMiddleware from 'next-intl/middleware';
import { routing } from './i18n/routing';

export default createMiddleware(routing);

export const config = {
  // Match all pathnames except API routes, Next.js internals, and static files.
  // The trailing slash on `api/` is intentional: `(?!api|...)` would also
  // exclude any path that *starts with* "api" — e.g. `/api-access` — which
  // would then 404 instead of being redirected by next-intl to
  // `/<defaultLocale>/api-access`.
  matcher: '/((?!api/|_next|.*\\..*).*)',
};
