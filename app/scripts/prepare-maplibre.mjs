import { mkdir, readFile, copyFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
const root = new URL('../', import.meta.url);
const pkg = new URL('node_modules/maplibre-gl/', root);
const { version } = JSON.parse(await readFile(new URL('package.json', pkg), 'utf8'));
const destination = new URL('public/map-assets/', root);
await mkdir(destination, { recursive: true });
await copyFile(fileURLToPath(new URL('dist/maplibre-gl-worker.mjs', pkg)), fileURLToPath(new URL(`maplibre-gl-worker-${version}.mjs`, destination)));
await copyFile(fileURLToPath(new URL('LICENSE.txt', pkg)), fileURLToPath(new URL(`maplibre-gl-license-${version}.txt`, destination)));
