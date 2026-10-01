// STRUTHIO HANDHELD · reference capture: runs the browser game's own renderer
// (WebGPU, headless Chromium with SwiftShader) over the golden traces.
//
//   node handheld/tools/reference/capture.mjs [--frames] [--textures] [--list=trace:tick] [trace names...]
//
// Writes, under handheld/build/reference/ (not committed):
//   <trace>.ihash          u32 per tick: hash of the browser's instance list
//   <trace>_<tick>.json    full instance lists for chosen ticks
//   <trace>_<tick>_q{0,2}.rgba / _scene.rgba   final frames (768x1152 RGBA) and the pre-post scene
//   textures/              atlas, world plates, bird sheet, moon globe (raw RGBA) + metadata.json
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium } from '/opt/node22/lib/node_modules/playwright/index.mjs';

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, '..', '..', '..');
const out = path.join(root, 'handheld', 'build', 'reference');
fs.mkdirSync(path.join(out, 'textures'), { recursive: true });
const args = process.argv.slice(2);
const wantFrames = args.includes('--frames'), wantTextures = args.includes('--textures');
const listArgs = args.filter((a) => a.startsWith('--list')).map((a) => a.split('=')[1] || '');
const names = args.filter((a) => !a.startsWith('--'));
// --list=trace:tick writes that tick's full browser instance list (to diff a scene_check mismatch)
const LISTS = {};
for (const spec of listArgs) { const [n, t] = spec.split(':'); (LISTS[n] ||= []).push(+t); if (!names.includes(n)) names.push(n); }
const TRACES = names.length ? names : ['climb', 'mortal', 'duel', 'raw', 'late'];
// Ticks to capture as frames (and full instance lists) per trace.
export const FRAME_TICKS = {
  mortal: [0, 299, 1479, 2239, 2809, 2849, 7399, 8999, 14142],
  climb: [40, 3000, 6000],
  late: [500, 5000],
  duel: [1200, 9000],
  raw: [700, 15000],
};

const MIME = { '.html': 'text/html', '.mjs': 'text/javascript', '.js': 'text/javascript', '.json': 'application/json', '.webp': 'image/webp', '.css': 'text/css' };
const server = http.createServer((req, res) => {
  const url = new URL(req.url, 'http://x');
  if (req.method === 'POST' && url.pathname.startsWith('/upload/')) {
    const name = path.basename(url.pathname.slice(8));
    const chunks = [];
    req.on('data', (c) => chunks.push(c));
    req.on('end', () => { fs.writeFileSync(path.join(out, name.includes('tex_') ? 'textures' : '', name.replace('tex_', '')), Buffer.concat(chunks)); res.end('ok'); });
    return;
  }
  const file = path.join(root, decodeURIComponent(url.pathname));
  if (!file.startsWith(root) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) { res.statusCode = 404; res.end(); return; }
  res.setHeader('Content-Type', MIME[path.extname(file)] || 'application/octet-stream');
  fs.createReadStream(file).pipe(res);
});
await new Promise((r) => server.listen(0, '127.0.0.1', r));
const port = server.address().port;

const browser = await chromium.launch({ headless: true, executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome', args: ['--enable-unsafe-webgpu'] });
const page = await browser.newPage({ viewport: { width: 768, height: 1152 } });
page.on('pageerror', (e) => console.log('pageerror:', e.message));
await page.goto(`http://127.0.0.1:${port}/handheld/tools/reference/index.html`);
await page.waitForFunction(() => window.__ref && (window.__ref.ready || window.__ref.error), null, { timeout: 180000 });
const err = await page.evaluate(() => window.__ref.error);
if (err) { console.log(err); process.exit(1); }

await page.exposeFunction('__upload', () => {});
const upload = (name) => `fetch('/upload/${name}', { method: 'POST', body: new Blob([__DATA__]) })`;
for (const name of TRACES) {
  const t0 = Date.now();
  const ticks = wantFrames ? FRAME_TICKS[name] || [] : [];
  const lists = [...ticks, ...(LISTS[name] || [])];
  const n = await page.evaluate(async ({ name, ticks, lists }) => {
    const r = await window.__ref.replay(`/handheld/golden/${name}.trace`, { capture: ticks, lists, qualities: [0, 2], scene: true });
    const post = (file, data) => fetch('/upload/' + file, { method: 'POST', body: new Blob([data]) });
    await post(`${name}.ihash`, r.hashes.buffer);
    for (const [t, list] of Object.entries(r.lists)) await post(`${name}_${t}.json`, JSON.stringify(list));
    for (const [t, c] of Object.entries(r.captures)) {
      for (const [k, img] of Object.entries(c)) if (img && img.p) await post(`${name}_${t}_${k}.rgba`, img.p);
      await post(`${name}_${t}_view.json`, JSON.stringify(c.view));
    }
    return r.ticks;
  }, { name, ticks, lists });
  console.log(`${name}: ${n} ticks hashed, ${ticks.length} frames (${((Date.now() - t0) / 1000).toFixed(1)} s)`);
}
if (wantTextures) {
  const meta = await page.evaluate(async () => {
    const { atlas, art, globe } = window.__ref;
    const scene = window.__ref.replayScene;
    const post = (file, data) => fetch('/upload/tex_' + file, { method: 'POST', body: new Blob([data]) });
    await post('atlas.rgba', atlas.surface.p);
    await post('world.rgba', atlas.world.p);
    await post('bird.rgba', art.bird.p);
    await post('globe.rgba', globe.p);
    const plans = scene.islandLayout ? [...scene.islandLayout.entries()].map(([id, p]) => ({ id, master: p.id, mirror: p.mirror, depth: p.depth, ground: p.ground, seed: p.seed, family: p.family })) : null;
    const slots = scene.islandSlots ? [...scene.islandSlots.entries()].map(([id, s]) => ({ id, ...s })) : null;
    const masters = atlas.islands.masters.map((m) => ({ id: m.id, role: m.role, x: m.x, y: m.y, w: m.w, h: m.h, capTop: m.capTop, topDecor: m.topDecor, signalRects: m.signalRects }));
    return { atlas: [atlas.surface.w, atlas.surface.h], world: [atlas.world.w, atlas.world.h], bird: [art.bird.w, art.bird.h], globe: [globe.w, globe.h],
      globeParams: globe.params, swatch: atlas.swatch, fontIndex: [...atlas.fontIndex.entries()], modernFont: atlas.modernFont,
      islandsOrigin: atlas.islands.origin, masters, plans, slots };
  });
  fs.writeFileSync(path.join(out, 'textures', 'metadata.json'), JSON.stringify(meta, null, 1));
  console.log('textures + metadata exported');
}
await browser.close();
server.close();
