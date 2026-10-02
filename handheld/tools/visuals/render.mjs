// STRUTHIO HANDHELD · drives studio.html in headless Chromium (WebGL) and saves PNGs.
//   node render.mjs OUT_DIR name:view:shell:WxH ...
// Serve this folder first (python3 -m http.server 8765) with assets/ and node_modules/three.
import { chromium } from '/opt/node22/lib/node_modules/playwright/index.mjs';
import fs from 'fs';
const [out, ...jobs] = process.argv.slice(2);
const b = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
for (const j of jobs) {
  const [name, view, shell, size] = j.split(':');
  const [w, h] = size.split('x').map(Number);
  const p = await b.newPage({ viewport: { width: w, height: h } });
  p.on('console', (m) => { if (m.type() === 'error') console.log('page error:', m.text()); });
  p.on('pageerror', (e) => console.log('page exception:', e.message));
  await p.goto(`http://127.0.0.1:8765/studio.html?view=${view}&shell=${shell}&w=${w}&h=${h}`);
  await p.waitForFunction('window.DONE === true', null, { timeout: 600000 });
  await p.screenshot({ path: `${out}/${name}.png` });
  fs.writeFileSync(`${out}/${name}.labels.json`, JSON.stringify(await p.evaluate('window.LABELS')));
  console.log('wrote', name);
  await p.close();
}
await b.close();
