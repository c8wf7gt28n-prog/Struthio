// STRUTHIO HANDHELD · HUD capture. Renders the real arcade page (index.html,
// its CSS and the browser's own text rendering) at the handheld's 320x480
// screen, touch deck hidden (the physical wings replace it), and captures:
//   - chrome.rgba     the static page (frame, bezels, HUD dividers, R, icons,
//                     J label) with every changing value blank and the game
//                     canvas hidden
//   - layers          every changing HUD element as a premultiplied RGBA layer
//                     (rendered over black and over white to recover alpha):
//                     score / round / kills digits per position, ring field
//                     0..6 and its gold-due state, JOUST count + lives bar
//                     0..11, and the toast banners
//   - hud.json        layer offsets/sizes and the canvas rectangle
// Output: handheld/build/reference/hud/. The asset compiler packs it for C.
//   node handheld/tools/reference/hud_capture.mjs
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium } from '/opt/node22/lib/node_modules/playwright/index.mjs';

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, '..', '..', '..');
const out = path.join(root, 'handheld', 'build', 'reference', 'hud');
fs.mkdirSync(out, { recursive: true });
const PANEL = { w: 320, h: 480 };

const MIME = { '.html': 'text/html', '.mjs': 'text/javascript', '.js': 'text/javascript', '.json': 'application/json', '.webp': 'image/webp', '.css': 'text/css', '.png': 'image/png', '.mp3': 'audio/mpeg', '.webmanifest': 'application/manifest+json' };
const server = http.createServer((req, res) => {
  const url = new URL(req.url, 'http://x');
  const file = path.join(root, decodeURIComponent(url.pathname));
  if (!file.startsWith(root) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) { res.statusCode = 404; res.end(); return; }
  res.setHeader('Content-Type', MIME[path.extname(file)] || 'application/octet-stream');
  fs.createReadStream(file).pipe(res);
});
await new Promise((r) => server.listen(0, '127.0.0.1', r));
const port = server.address().port;

const browser = await chromium.launch({ headless: true, executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome', args: ['--enable-unsafe-webgpu', '--disable-lcd-text'] });  // grayscale text AA, as phones and the panel
const page = await browser.newPage({ viewport: { width: PANEL.w, height: PANEL.h }, deviceScaleFactor: 1 });
await page.addInitScript(() => {
  // the same stand-in WebGPU canvas context as the reference harness
  const off = { device: null, tex: null };
  const real = HTMLCanvasElement.prototype.getContext;
  HTMLCanvasElement.prototype.getContext = function (k, ...r) {
    if (k !== 'webgpu') return real.call(this, k, ...r);
    const c = this;
    return { configure({ device }) { off.device = device; },
      getCurrentTexture() { if (!off.tex || off.tex.width !== c.width) off.tex = off.device.createTexture({ size: [c.width, c.height], format: 'rgba8unorm', usage: GPUTextureUsage.RENDER_ATTACHMENT | GPUTextureUsage.COPY_SRC }); return off.tex; } };
  };
  if (navigator.gpu) navigator.gpu.getPreferredCanvasFormat = () => 'rgba8unorm';
  document.addEventListener('DOMContentLoaded', () => {
    const s = document.createElement('style');
    s.id = 'handheld';
    s.textContent = '#controls{display:none!important} *{transition:none!important;animation:none!important}';
    document.head.appendChild(s);
  });
});
await page.goto(`http://127.0.0.1:${port}/arcade/index.html?seed=1&music=off&quality=0`, { waitUntil: 'load' });
await page.waitForFunction(() => window.__struthio && window.__struthio.session, null, { timeout: 120000 });
await page.waitForTimeout(1500);
await page.keyboard.press('Space');
await page.waitForTimeout(1500);
// Freeze the session: the HUD is now driven only by this script.
await page.evaluate(() => { window.__struthio.stopped = true; });
await page.waitForTimeout(200);

const layout = await page.evaluate(() => {
  const r = (s) => { const e = document.querySelector(s); const b = e.getBoundingClientRect(); return [b.left, b.top, b.width, b.height]; };
  return { canvas: r('#game'), hud: r('#top-hud'), toastTop: r('#hud-toast')[1] };
});

// DOM helpers run in the page
await page.evaluate(() => {
  const st = document.createElement('style');
  st.id = 'cap';
  document.head.appendChild(st);
  window.__cap = {
    css(text) { document.getElementById('cap').textContent = text; },
    set(sel, html) { document.querySelector(sel).innerHTML = html; },
    // text with only position i visible (others keep their layout but do not paint)
    only(text, i) { return [...text].map((ch, k) => k === i ? ch : `<span style="visibility:hidden">${ch}</span>`).join(''); },
  };
});
const shot = async () => new Uint8Array(await page.screenshot({ type: 'png' })).buffer;
const { decodePng } = await import('../png.mjs');
const grab = async () => decodePng(Buffer.from(await shot()));
const BASE_HIDE = '#game{visibility:hidden!important}';
const ISOLATE = `${BASE_HIDE} #frame{display:none!important} #top-hud>span{background:none!important}
  #hud-pos-a,#hud-rival svg,#hud-joust small{visibility:hidden!important}`;
// The changing contents (never the field spans: their backgrounds are the gold dividers).
const DYNAMIC = ['#hud-score b', '#hud-pos-av', '#hud-ring i', '#hud-ring b', '#hud-rival b', '#hud-joust b', '#hud-joust i', '#hud-toast'];
const HIDE_ALL_DYNAMIC = DYNAMIC.join(',') + '{visibility:hidden!important}';

async function setValues({ score = '000000', round = '01', rings = '00/06', kills = '00', joust = '11/11', lives = 11, due = false, low = false }) {
  await page.evaluate((v) => {
    const c = window.__cap;
    c.set('#hud-score b', v.score); c.set('#hud-pos-av', v.round); c.set('#hud-ring b', v.rings); c.set('#hud-rival b', v.kills); c.set('#hud-joust b', v.joust);
    document.querySelector('#hud-joust i').style.setProperty('--joust', String(v.lives / 11));
    document.querySelector('#hud-ring').classList.toggle('is-due', v.due);
    document.querySelector('#top-hud').classList.toggle('is-low', v.low);
    document.querySelector('#top-hud').classList.add('is-live');
  }, { score, round, rings, kills, joust, lives, due, low });
}
// One layer: render over black and white with only `show` painting.
async function layer(name, css, isolate = true) {
  const base = isolate ? ISOLATE : `${BASE_HIDE} #frame{display:none!important}`;
  await page.evaluate((t) => window.__cap.css(t), `${base} ${css} html,body,main{background:#000!important}`);
  const k = await grab();
  await page.evaluate((t) => window.__cap.css(t), `${base} ${css} html,body,main{background:#fff!important}`);
  const w = await grab();
  const n = PANEL.w * PANEL.h;
  let x0 = PANEL.w, y0 = PANEL.h, x1 = -1, y1 = -1;
  const pre = new Uint8Array(n * 4);
  for (let i = 0; i < n; i++) {
    let a = 0;
    for (let c = 0; c < 3; c++) a = Math.max(a, 255 - (w.p[i * 4 + c] - k.p[i * 4 + c]));
    a = Math.max(0, Math.min(255, a));
    if (a > 0) { const x = i % PANEL.w, y = (i / PANEL.w) | 0; x0 = Math.min(x0, x); y0 = Math.min(y0, y); x1 = Math.max(x1, x); y1 = Math.max(y1, y); }
    pre[i * 4] = Math.min(k.p[i * 4], a); pre[i * 4 + 1] = Math.min(k.p[i * 4 + 1], a); pre[i * 4 + 2] = Math.min(k.p[i * 4 + 2], a); pre[i * 4 + 3] = a;
  }
  if (x1 < 0) return { name, x: 0, y: 0, w: 0, h: 0 };
  const lw = x1 - x0 + 1, lh = y1 - y0 + 1, buf = Buffer.alloc(lw * lh * 4);
  for (let y = 0; y < lh; y++) Buffer.from(pre.buffer, ((y + y0) * PANEL.w + x0) * 4, lw * 4).copy(buf, y * lw * 4);
  fs.writeFileSync(path.join(out, `${name}.rgba`), buf);
  return { name, x: x0, y: y0, w: lw, h: lh };
}
const others = (...keep) => DYNAMIC.filter((s) => !keep.includes(s)).map((s) => `${s}{visibility:hidden!important}`).join(' ');

const layers = [];
// chrome: everything static, values blank, canvas hidden
await setValues({});
await page.evaluate((t) => window.__cap.css(t), `${BASE_HIDE} #top-hud>span,#hud-toast{visibility:hidden!important}`);
const chrome = await grab();
fs.writeFileSync(path.join(out, 'chrome.rgba'), Buffer.from(chrome.p));

// Digits per position. Each string is rendered as one unbroken text run
// ("000000", "111111", ...) so glyphs sit exactly where the browser puts them,
// then cut into per-position cells at the midpoints between the glyph boxes.
async function charBoxes(sel) {
  return page.evaluate((sel) => {
    const node = document.querySelector(sel).firstChild, out = [];
    for (let i = 0; i < node.length; i++) { const r = document.createRange(); r.setStart(node, i); r.setEnd(node, i + 1); const b = r.getBoundingClientRect(); out.push([b.left, b.right]); }
    return out;
  }, sel);
}
function cutCells(src, boxes, prefix, d) {
  const cuts = [-Infinity];
  for (let i = 0; i + 1 < boxes.length; i++) cuts.push((boxes[i][1] + boxes[i + 1][0]) / 2);
  cuts.push(Infinity);
  const buf = fs.readFileSync(path.join(out, `${src.name}.rgba`));
  fs.unlinkSync(path.join(out, `${src.name}.rgba`));
  const cells = [];
  for (let i = 0; i < boxes.length; i++) {
    const x0 = Math.max(src.x, Math.round(cuts[i])), x1 = Math.min(src.x + src.w, Math.round(cuts[i + 1]));
    const w = x1 - x0, cell = Buffer.alloc(w * src.h * 4);
    for (let y = 0; y < src.h; y++) buf.copy(cell, y * w * 4, (y * src.w + (x0 - src.x)) * 4, (y * src.w + (x1 - src.x)) * 4);
    const name = `${prefix}_${i}_${d}`;
    fs.writeFileSync(path.join(out, `${name}.rgba`), cell);
    cells.push({ name, x: x0, y: src.y, w, h: src.h });
  }
  return cells;
}
// Each digit d at position i is rendered inside a run of zeros ("00d000"): one
// unbroken run, and '0' kerns with no digit, so the glyph sits where the
// browser puts it in any number without a kerned "11" pair.
for (const [field, sel, len] of [['score', '#hud-score b', 6], ['round', '#hud-pos-av', 2]]) {
  for (let i = 0; i < len; i++) for (let d = 0; d <= 9; d++) {
    const t = Array.from({ length: len }, (_, k) => (k === i ? String(d) : '0')).join('');
    await page.evaluate(({ sel, t }) => { document.querySelector(sel).textContent = t; }, { sel, t });
    const boxes = await charBoxes(sel);
    const whole = await layer(`${field}_run`, others(sel));
    const cells = cutCells(whole, boxes, `tmp_${field}`, d);
    for (let k = 0; k < cells.length; k++) {
      const tmp = path.join(out, `${cells[k].name}.rgba`);
      if (k !== i) { fs.unlinkSync(tmp); continue; }
      const name = `${field}_${i}_${d}`;
      fs.renameSync(tmp, path.join(out, `${name}.rgba`));
      layers.push({ ...cells[k], name });
    }
  }
  await setValues({});
}
// The ring and rival columns stretch into the space the auto-sized JOUST field
// leaves, and "11/11" is narrower than any other count (a kerned "11" pair).
// Everything from the dividers rightwards is therefore captured twice:
// variant a (lives 11) and b (any other).
for (const [v, joust, lives] of [['a', '11/11', 11], ['b', '02/11', 2]]) {
  await setValues({ joust, lives });
  layers.push(await layer(`static_${v}`, `${HIDE_ALL_DYNAMIC} #hud-rival svg{visibility:hidden!important}`, false));
  for (const [field, sel, len] of [['kills2', '#hud-rival b', 2], ['kills3', '#hud-rival b', 3]]) {
    for (let i = 0; i < len; i++) for (let d = 0; d <= 9; d++) {
      const t = Array.from({ length: len }, (_, k) => (k === i ? String(d) : '0')).join('');
      await page.evaluate(({ sel, t }) => { document.querySelector(sel).textContent = t; }, { sel, t });
      const boxes = await charBoxes(sel);
      const whole = await layer(`${field}_run`, others(sel));
      const cells = cutCells(whole, boxes, `tmp_${field}`, d);
      for (let k = 0; k < cells.length; k++) {
        const tmp = path.join(out, `${cells[k].name}.rgba`);
        if (k !== i) { fs.unlinkSync(tmp); continue; }
        const name = `${field}_${v}_${i}_${d}`;
        fs.renameSync(tmp, path.join(out, `${name}.rgba`));
        layers.push({ ...cells[k], name });
      }
    }
    // the crossed swords centre with the count, so they move with its length
    await page.evaluate(({ t }) => { document.querySelector('#hud-rival b').textContent = t; }, { t: '0'.repeat(len) });
    layers.push(await layer(`swords_${v}_${len}`, `${others()} #hud-rival b{visibility:hidden!important} #hud-rival svg{visibility:visible!important}`));
    await setValues({ joust, lives });
  }
  for (let r = 0; r <= 6; r++) { await setValues({ joust, lives, rings: `0${r}/06` }); layers.push(await layer(`ring_${v}_${r}`, others('#hud-ring i', '#hud-ring b'))); }
  await setValues({ joust, lives, rings: '06/06', due: true });
  layers.push(await layer(`ring_${v}_due`, others('#hud-ring i', '#hud-ring b')));
}
// JOUST: count + lives bar for 0..11 (red count at 2 or fewer)
for (let v = 0; v <= 11; v++) {
  const low = v <= 2;
  await setValues({ joust: `${String(v).padStart(2, '0')}/11`, lives: v, low });
  layers.push(await layer(`joust_b_${v}`, others('#hud-joust b')));
  layers.push(await layer(`joust_i_${v}`, others('#hud-joust i')));
}
// toasts (session.mjs banners; hud.mjs warning / pause)
const TOASTS = [['extra', 'EXTRA JOUST MARK', 'event'], ['gold', '6/6 · THE GOLD RING IS AT THE MOON', 'event'], ['paused', 'PAUSED', 'pause']];
for (let r = 1; r <= 99; r++) { TOASTS.push([`clear_${r}`, `ROUND ${r} CLEAR`, 'event']); TOASTS.push([`clean_${r}`, `ROUND ${r} CLEAR · NO LOSSES`, 'event']); }
await setValues({});
for (const [name, text, kind] of TOASTS) {
  await page.evaluate(({ text, kind }) => { const t = document.getElementById('hud-toast'); t.textContent = text; t.dataset.kind = kind; t.classList.add('is-on'); }, { text, kind });
  layers.push(await layer(`toast_${name}`, others('#hud-toast')));
}
// a truth frame to check the layer composition against
const TRUTHS = [
  { score: '012340', round: '03', rings: '04/06', kills: '17', joust: '02/11', lives: 2, low: true, toast: 'clear_7', toastText: 'ROUND 7 CLEAR' },
  { score: '098765', round: '12', rings: '06/06', due: true, kills: '204', joust: '11/11', lives: 11, low: false, toast: 'gold', toastText: '6/6 · THE GOLD RING IS AT THE MOON' },
];
for (let n = 0; n < TRUTHS.length; n++) {
  const T = TRUTHS[n];
  await setValues(T);
  await page.evaluate(({ text }) => { const t = document.getElementById('hud-toast'); t.textContent = text; t.dataset.kind = 'event'; t.classList.add('is-on'); }, { text: T.toastText });
  await page.evaluate((t) => window.__cap.css(t), BASE_HIDE);
  fs.writeFileSync(path.join(out, `truth_${n}.rgba`), Buffer.from((await grab()).p));
}
fs.writeFileSync(path.join(out, 'hud.json'), JSON.stringify({ panel: PANEL, layout, layers, truths: TRUTHS }, null, 1));
console.log(`HUD: chrome + ${layers.length} layers; canvas at ${layout.canvas.map((v) => v.toFixed(2)).join(', ')}`);
await browser.close();
server.close();
