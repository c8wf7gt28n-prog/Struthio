// STRUTHIO HANDHELD · renders svg/*.svg to png/*.png at 2x with headless Chromium.
//   node render_schematics.mjs   (Playwright; PLAYWRIGHT path may need adjusting)
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const pw = await import(process.env.PLAYWRIGHT_MODULE || '/opt/node22/lib/node_modules/playwright/index.mjs');
const here = path.dirname(fileURLToPath(import.meta.url));
fs.mkdirSync(path.join(here, 'png'), { recursive: true });
const b = await pw.chromium.launch();
const p = await b.newPage({ deviceScaleFactor: 2 });
for (const f of fs.readdirSync(path.join(here, 'svg')).filter((f) => f.endsWith('.svg')).sort()) {
  await p.setContent('<html><body style="margin:0">' + fs.readFileSync(path.join(here, 'svg', f), 'utf8') + '</body></html>');
  await (await p.$('svg')).screenshot({ path: path.join(here, 'png', f.replace('.svg', '.png')) });
  console.log('png/' + f.replace('.svg', '.png'));
}
await b.close();
