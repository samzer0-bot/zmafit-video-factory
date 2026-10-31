// Builds the lead-magnet PDF + PNG previews of every page (used in the ad video).
// Usage: node lead-magnet/build.mjs
import {createRequire} from 'node:module';
const {chromium} = createRequire(import.meta.url)('playwright'); // globally installed in this environment
import fs from 'node:fs';
import path from 'node:path';

const dir = path.dirname(new URL(import.meta.url).pathname);
const out = path.join(dir, 'out');
fs.mkdirSync(path.join(out, 'pages'), {recursive: true});

const browser = await chromium.launch();
const page = await browser.newPage({viewport: {width: 794, height: 1123}, deviceScaleFactor: 2});
await page.goto('file://' + path.join(dir, 'kickstart.html'));
await page.evaluate(() => document.fonts.ready);
await page.pdf({path: path.join(out, 'zmafit-7-day-fat-loss-kickstart.pdf'), format: 'A4', printBackground: true, preferCSSPageSize: true});
const sections = await page.$$('section.page');
for (let i = 0; i < sections.length; i++) {
  await sections[i].screenshot({path: path.join(out, 'pages', `page-${String(i + 1).padStart(2, '0')}.png`)});
}
await browser.close();
console.log(`PDF + ${sections.length} page previews written to ${out}`);
