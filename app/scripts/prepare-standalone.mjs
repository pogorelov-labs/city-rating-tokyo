import { access, cp } from 'node:fs/promises';

// Mirror the public/static copies made by the production Dockerfile.
const root = new URL('../', import.meta.url);
const standalone = new URL('.next/standalone/', root);
await access(new URL('server.js', standalone));
await cp(new URL('public/', root), new URL('public/', standalone), { recursive: true });
await cp(new URL('.next/static/', root), new URL('.next/static/', standalone), { recursive: true });
