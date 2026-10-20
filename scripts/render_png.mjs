// Optional PNG fallback for the SVG figures: node scripts/render_png.mjs <edition-id>
// Uses Playwright (Chromium). PNG bytes are not bit-reproducible across engines;
// the SVG files are the canonical figures. Light colour scheme, device scale 2.
import { readdirSync, mkdirSync, readFileSync, realpathSync, lstatSync } from 'node:fs';
import { join, resolve, relative, isAbsolute, dirname } from 'node:path';
import { spawnSync } from 'node:child_process';
import { pathToFileURL } from 'node:url';
import { createRequire } from 'node:module';

const root = resolve(import.meta.dirname, '..');
if (process.argv[2] !== '--worker') {
  const edition = process.argv[2];
  if (!/^\d{4}-\d{2}-\d{2}_\d{4}-\d{2}-\d{2}-r[1-9]\d*$/.test(edition || '')) throw Error('usage: render_png.mjs <edition-id> [--preview <external-directory>]');
  const extra = process.argv.slice(3);
  if (extra.length && (extra.length !== 2 || extra[0] !== '--preview')) throw Error('unknown_png_option');
  const run = spawnSync('python', ['-I', '-B', join(root, 'scripts/dwr.py'), 'png-fallback', '--edition', edition, ...extra], { stdio: 'inherit' });
  if (run.error) throw run.error;
  process.exit(run.status ?? 2);
}
// This worker can only create preview bytes. Canonical installation belongs to
// Python's shared admission/transaction and cannot be selected by worker flags.
const dir = realpathSync(process.argv[3]);
const contained = (parent, child) => { const p = relative(realpathSync(parent), child); return p === '' || (!p.startsWith('..') && !isAbsolute(p)); };
for (const canonical of ['data', 'figures', 'config', 'schemas']) {
  if (contained(join(root, canonical), dir)) throw Error('canonical_png_worker_destination_refused');
}
if (contained(root, dir) && !contained(join(root, '.dwr-work'), dir)) throw Error('png_worker_repository_destination_refused');
const out = join(dir, 'png');
if (lstatSync(out, { throwIfNoEntry: false })?.isSymbolicLink()) throw Error('png_link_refused');
mkdirSync(out, { recursive: true });
const require = createRequire(join(process.env.DWR_PLAYWRIGHT_DIR || root, 'noop.js'));
const { chromium } = require('playwright');
const browser = await chromium.launch();
try {
  const files = readdirSync(dir).filter((name) => /\.(en|fr)(\.compact)?\.svg$/.test(name)).sort();
  for (const name of files) {
    const svg = readFileSync(join(dir, name), 'utf8');
    const width = Number(/width="(\d+)"/.exec(svg)[1]);
    const height = Math.ceil(Number(/height="([\d.]+)"/.exec(svg)[1]));
    const page = await browser.newPage({ viewport: { width, height }, deviceScaleFactor: 2, colorScheme: 'light' });
    const source = pathToFileURL(join(dir, name)).href;
    await page.route('**/*', route => route.request().url() === source ? route.continue() : route.abort());
    await page.goto(pathToFileURL(join(dir, name)).href);
    await page.screenshot({ path: join(out, name.replace(/\.svg$/, '.png')), omitBackground: false });
    await page.close();
    console.log(`${name} -> png ${width}x${height} @2x`);
  }
} finally {
  await browser.close();
}
