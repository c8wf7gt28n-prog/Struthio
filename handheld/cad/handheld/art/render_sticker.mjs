// STRUTHIO HANDHELD · renders the sticker pages at 600 dpi (and the proof at 300 dpi) with headless Chromium.
//   node render_sticker.mjs   (uses the Playwright that the reference capture uses)
import { chromium } from '/opt/node22/lib/node_modules/playwright/index.mjs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const here = path.dirname(fileURLToPath(import.meta.url));
const b = await chromium.launch();
for (const [name, dpi] of [['sticker_front_print', 600], ['sticker_front_proof', 300]]) {
  const p = await b.newPage({ deviceScaleFactor: dpi / 96 });
  await p.goto('file://' + path.join(here, name + '.html'));
  await p.waitForTimeout(400);
  await (await p.$('svg')).screenshot({ path: path.join(here, name + '.png'), omitBackground: name.endsWith('print') });
  console.log(name + '.png', dpi, 'dpi');
  await p.close();
}
await b.close();
