// STRUTHIO ONE SLIM · renders for docs/renders/slim, from one_studio.html?model=slim.
//   node slim_render.mjs OUT_DIR            (serve the studio folder on 127.0.0.1:8765 first)
// Also renders the ONE from the side, for the side-by-side thickness picture.
let pw;
try { pw = await import('playwright'); } catch { pw = await import('/opt/node22/lib/node_modules/playwright/index.mjs'); }
const { chromium } = pw;
const out = process.argv[2];
const SHOTS = [
  ['slim_hero', 'model=slim&view=hero&w=1600&h=1000'],
  ['slim_front', 'model=slim&view=front&w=1000&h=1250'],
  ['slim_back', 'model=slim&view=back&w=1000&h=1250'],
  ['slim_inside', 'model=slim&view=inside&w=1000&h=1250'],
  ['slim_exploded', 'model=slim&view=exploded&w=1600&h=1000'],
  ['slim_side', 'model=slim&view=side&w=500&h=1100'],
  ['one_side', 'model=one&view=side&w=500&h=1100'],
];
const b = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
for (const [name, query] of SHOTS) {
  const [w, h] = [+query.match(/w=(\d+)/)[1], +query.match(/h=(\d+)/)[1]];
  const p = await b.newPage({ viewport: { width: w, height: h } });
  p.on('pageerror', (e) => console.log('page exception:', e.message));
  await p.goto(`http://127.0.0.1:8765/one_studio.html?${query}&shell=navy`);
  await p.waitForFunction('window.DONE === true', null, { timeout: 600000 });
  await p.screenshot({ path: `${out}/${name}.png` });
  console.log('wrote', name);
  await p.close();
}
await b.close();
