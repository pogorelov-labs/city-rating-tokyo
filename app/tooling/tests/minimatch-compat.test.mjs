import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const appRoot = path.resolve(__dirname, '../..');
const loadCommonJS = createRequire(path.join(appRoot, 'package.json'));
const bridge = loadCommonJS('minimatch');
const bridgeEntry = loadCommonJS.resolve('minimatch');

function packageFor(entry) {
  let dir = path.dirname(fs.realpathSync(entry));
  for (;;) {
    const file = path.join(dir, 'package.json');
    if (fs.existsSync(file)) {
      const metadata = JSON.parse(fs.readFileSync(file, 'utf8'));
      if (metadata.name) return metadata;
    }
    const parent = path.dirname(dir);
    if (parent === dir) throw new Error(`No package metadata for ${entry}`);
    dir = parent;
  }
}

test('legacy consumers resolve the bridge and it delegates to patched upstream', () => {
  assert.equal(packageFor(bridgeEntry).name, '@city-rating/minimatch-compat');
  assert.equal(fs.readFileSync(fs.realpathSync(bridgeEntry), 'utf8'),
    fs.readFileSync(path.join(appRoot, 'tooling/minimatch-compat/index.mjs'), 'utf8'),
    'installed adapter must match its committed source');
  const bridgeRequire = createRequire(bridgeEntry);
  const engine = packageFor(bridgeRequire.resolve('minimatch-core'));
  assert.equal(engine.name, 'minimatch');
  assert.equal(engine.version, '11.0.3');
  for (const consumer of ['eslint', '@eslint/config-array', '@eslint/eslintrc', 'eslint-plugin-import', 'eslint-plugin-react', 'eslint-plugin-jsx-a11y']) {
    const resolved = createRequire(loadCommonJS.resolve(consumer)).resolve('minimatch');
    assert.equal(fs.realpathSync(resolved), fs.realpathSync(bridgeEntry), `${consumer} must resolve the bridge`);
  }
  const estreeRequire = createRequire(loadCommonJS.resolve('@typescript-eslint/typescript-estree'));
  const estreeMatcher = packageFor(estreeRequire.resolve('minimatch'));
  assert.equal(estreeMatcher.name, 'minimatch');
  assert.equal(estreeMatcher.version, '11.0.3');
});

test('callable CommonJS, ESM default and named exports match representative glob contracts', async () => {
  assert.equal(typeof bridge, 'function');
  const esm = await import('minimatch');
  assert.equal(typeof esm.default, 'function');
  assert.equal(esm.default, bridge);
  assert.equal(esm.Minimatch, bridge.Minimatch);
  const cases = [
    ['src/components/Map.tsx', 'src/**/*.{ts,tsx}', {}, true],
    ['src/data/file.js', 'src/**/*.{ts,tsx}', {}, false],
    ['src/.hidden/file.ts', 'src/**/*.ts', {}, false],
    ['src/.hidden/file.ts', 'src/**/*.ts', { dot: true }, true],
    ['MAP.TSX', '*.tsx', { nocase: true }, true],
    ['nested/Map.tsx', '*.tsx', { matchBase: true }, true],
    ['src/file.test.ts', 'src/!(*.test).ts', {}, false],
    ['src/file.ts', 'src/!(*.test).ts', {}, true],
  ];
  for (const [file, pattern, options, expected] of cases) {
    assert.equal(bridge(file, pattern, options), expected, `${file} / ${pattern}`);
    assert.equal(esm.default(file, pattern, options), expected, `ESM ${file} / ${pattern}`);
  }
  const matcher = new bridge.Minimatch('src/**/Map.tsx');
  assert.equal(matcher.pattern, 'src/**/Map.tsx');
  assert.equal(matcher.match('src/components/Map.tsx'), true);
  assert.equal(matcher.match('other/components/Map.tsx'), false);
  assert.equal(matcher.match('src/components', true), true);
  assert.equal(matcher.match('other/components', true), false);
  assert.deepEqual(bridge.match(['src/a.ts', 'src/a.js'], 'src/*.ts'), ['src/a.ts']);
  assert.deepEqual(bridge.braceExpand('src/*.{ts,tsx}'), ['src/*.ts', 'src/*.tsx']);
});

test('unsupported regex APIs fail closed with actionable errors', () => {
  assert.throws(() => bridge.makeRe('src/*.ts'), /not supported.*matching has not been skipped/i);
  assert.throws(() => new bridge.Minimatch('src/*.ts').makeRe(), /not supported.*matching has not been skipped/i);
  assert.throws(() => bridge.defaults({ dot: true }), /not supported.*matching has not been skipped/i);
  assert.throws(() => bridge.Minimatch.defaults({ dot: true }), /not supported.*matching has not been skipped/i);
});

test('patched engine handles a bounded globparts amplification input', () => {
  // Exercise the upstream preprocessing regression in a capped child.
  // https://github.com/isaacs/minimatch/blob/77a0f5c/test/preprocess-limits.ts
  const child = spawnSync(process.execPath, ['--max-old-space-size=128', '-e',
    `const m = require('minimatch'); const p = Array(30).fill('**/../a/b').join('/'); const mm = new m.Minimatch(p, { optimizationLevel: 2, braceExpandMax: 64 }); if (mm.set.length > 64) process.exit(2);`],
  { cwd: appRoot, timeout: 5000, encoding: 'utf8' });
  assert.equal(child.error, undefined, `matcher child failed or timed out: ${child.error}`);
  assert.equal(child.status, 0, `matcher child exited ${child.status}: ${child.stderr}`);
});

test('real configured lint rules and ignores remain active', async () => {
  const { ESLint } = loadCommonJS('eslint');
  const eslint = new ESLint({ cwd: appRoot });
  const source = `import { useState } from 'react';\nexport default function Probe({ condition }: { condition: boolean }) { if (condition) useState(0); const value: any = 1; return <>{[1, 2].map(n => <span>{n}</span>)}<img src="/x.png" />{value}</>; }`;
  const [result] = await eslint.lintText(source, { filePath: path.join(appRoot, 'src/__lint_contract_probe__.tsx') });
  const rules = new Set(result.messages.map(m => m.ruleId));
  for (const rule of ['react-hooks/rules-of-hooks', '@typescript-eslint/no-explicit-any', 'react/jsx-key', '@next/next/no-img-element', 'jsx-a11y/alt-text']) assert.ok(rules.has(rule), `missing ${rule}`);
  const [importResult] = await eslint.lintText('export default () => <div />;', { filePath: path.join(appRoot, 'src/__lint_contract_import__.tsx') });
  assert.ok(importResult.messages.some(m => m.ruleId === 'import/no-anonymous-default-export'));
  const [tsResult] = await eslint.lintText('export const value: any = 1;', { filePath: path.join(appRoot, 'src/__lint_contract_probe__.ts') });
  assert.ok(tsResult.messages.some(m => m.ruleId === '@typescript-eslint/no-explicit-any'));
  assert.equal(await eslint.isPathIgnored(path.join(appRoot, 'src/__lint_contract_probe__.tsx')), false);
  for (const file of ['.next/probe.js', 'out/probe.js', 'build/probe.js', 'next-env.d.ts', 'public/map-assets/probe.js']) assert.equal(await eslint.isPathIgnored(path.join(appRoot, file)), true, file);
});

test('option-specific React, accessibility and import glob callers remain functional', async () => {
  const { ESLint } = loadCommonJS('eslint');
  const eslint = new ESLint({ cwd: appRoot, overrideConfig: { rules: {
    'react/jsx-pascal-case': ['error', { ignore: ['Bad*'] }],
    'jsx-a11y/label-has-associated-control': ['error', { controlComponents: ['Input*'] }],
    'import/order': ['error', { groups: ['builtin', 'external', 'internal'], pathGroups: [{ pattern: '@lib/**', group: 'internal', position: 'after' }], pathGroupsExcludedImportTypes: [] }],
  } } });
  const fixtures = [
    ['react', 'export const Probe = () => <><Bad_name /><Other_name /></>;', 'react/jsx-pascal-case', 'Other_name'],
    ['a11y', 'export const Probe = () => <><label>Name<InputThing /></label><label>Bad</label></>;', 'jsx-a11y/label-has-associated-control', 'associated with a control'],
    ['imports', "import local from '@lib/thing';\nimport fs from 'node:fs';\nexport { local, fs };", 'import/order', 'node:fs'],
  ];
  for (const [name, code, rule, message] of fixtures) {
    const [result] = await eslint.lintText(code, { filePath: path.join(appRoot, `src/__lint_caller_${name}__.tsx`) });
    const hits = result.messages.filter(m => m.ruleId === rule);
    assert.equal(hits.length, 1, `${name}: expected one ${rule} finding`);
    assert.ok(hits[0].message.includes(message), `${name}: unexpected message ${hits[0].message}`);
  }
});

test('a plugin requiring removed regex API fails visibly rather than skipping its rule', async () => {
  const { ESLint } = loadCommonJS('eslint');
  const eslint = new ESLint({ cwd: appRoot, overrideConfig: {
    rules: { 'import/no-internal-modules': ['error', { forbid: ['@private/**'] }] },
  } });
  await assert.rejects(
    eslint.lintText("import secret from '@private/secret'; export { secret };", { filePath: path.join(appRoot, 'src/__lint_unsupported__.ts') }),
    /makeRe\(\).*not supported.*matching has not been skipped/i,
  );
});
