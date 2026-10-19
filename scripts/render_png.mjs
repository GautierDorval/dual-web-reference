// Optional PNG fallback for the SVG figures: node scripts/render_png.mjs <edition-id>
// Uses Playwright (Chromium). PNG bytes are not bit-reproducible across engines;
// the SVG files are the canonical figures. Light colour scheme, device scale 2.
import { readdirSync, mkdirSync, readFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import { createRequire } from 'node:module';

const edition = process.argv[2];
if (!/^\d{4}-\d{2}-\d{2}_\d{4}-\d{2}-\d{2}-r\d+$/.test(edition || '')) throw Error('usage: render_png.mjs <edition-id>');
const root = resolve(import.meta.dirname, '..');
const frozen = JSON.parse(readFileSync(join(root, 'config/historical-editions.json'), 'utf8'));
if (frozen.editions[edition]) throw Error('historical_edition_immutable');
const dir = join(root, 'figures', edition);
const out = join(dir, 'png');
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
    await page.route(/^https?:/, route => route.abort());
    await page.goto(pathToFileURL(join(dir, name)).href);
    await page.screenshot({ path: join(out, name.replace(/\.svg$/, '.png')), omitBackground: false });
    await page.close();
    console.log(`${name} -> png ${width}x${height} @2x`);
  }
} finally {
  await browser.close();
}
