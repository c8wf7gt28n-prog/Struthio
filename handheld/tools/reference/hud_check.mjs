// STRUTHIO HANDHELD · checks that chrome + HUD layers recompose the browser's
// own HUD (the truth frame hud_capture.mjs renders with the DOM).
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { encodePng } from '../png.mjs';
const dir = path.join(path.dirname(fileURLToPath(import.meta.url)), '..', '..', 'build', 'reference', 'hud');
const meta = JSON.parse(fs.readFileSync(path.join(dir, 'hud.json')));
const W = meta.panel.w, H = meta.panel.h;
const img = new Uint8Array(fs.readFileSync(path.join(dir, 'chrome.rgba')));
const byName = new Map(meta.layers.map((l) => [l.name, l]));
function over(name) {
  const l = byName.get(name);
  if (!l || !l.w) return;
  const p = fs.readFileSync(path.join(dir, name + '.rgba'));
  for (let y = 0; y < l.h; y++) for (let x = 0; x < l.w; x++) {
    const s = (y * l.w + x) * 4, d = ((y + l.y) * W + x + l.x) * 4, a = p[s + 3] / 255;
    for (let c = 0; c < 3; c++) img[d + c] = Math.round(p[s + c] + img[d + c] * (1 - a));
  }
}
// The C compositor's rules (render/struthio_hud.c): the frame, the static HUD
// for the layout variant, then each value's layers.
export function compose(t, draw) {
  const v = t.lives === 11 ? 'a' : 'b';
  draw(`static_${v}`);
  [...t.score].forEach((d, i) => draw(`score_${i}_${d}`));
  [...t.round].forEach((d, i) => draw(`round_${i}_${d}`));
  draw(t.due ? `ring_${v}_due` : `ring_${v}_${+t.rings.slice(0, 2)}`);
  draw(`swords_${v}_${t.kills.length}`);
  [...t.kills].forEach((d, i) => draw(`kills${t.kills.length}_${v}_${i}_${d}`));
  draw(`joust_b_${t.lives}`); draw(`joust_i_${t.lives}`);
  if (t.toast) draw(`toast_${t.toast}`);
}
let fails = 0;
meta.truths.forEach((t, n) => {
  img.set(fs.readFileSync(path.join(dir, 'chrome.rgba')));
  compose(t, over);
  const truth = fs.readFileSync(path.join(dir, `truth_${n}.rgba`));
  const top = Math.ceil(meta.layout.canvas[1] + 30);
  let se = 0, worst = 0, off = 0;
  for (let i = 0; i < W * top; i++) { let m = 0; for (let c = 0; c < 3; c++) { const d = img[i * 4 + c] - truth[i * 4 + c]; se += d * d; m = Math.max(m, Math.abs(d)); } worst = Math.max(worst, m); if (m > 4) off++; }
  const psnr = 10 * Math.log10(255 * 255 / (se / (W * top * 3) + 1e-12));
  console.log(`HUD truth ${n} (score ${t.score}, lives ${t.lives}${t.due ? ', gold due' : ''}): PSNR ${psnr.toFixed(1)} dB, worst ${worst}, pixels off >4: ${off}`);
  if (psnr < 40) fails++;
  if (process.argv[2]) {
    const both = new Uint8Array(W * 2 * top * 4);
    for (let y = 0; y < top; y++) for (let x = 0; x < W; x++) for (let c = 0; c < 4; c++) { both[(y * W * 2 + x) * 4 + c] = img[(y * W + x) * 4 + c]; both[(y * W * 2 + x + W) * 4 + c] = truth[(y * W + x) * 4 + c]; }
    fs.writeFileSync(process.argv[2].replace('.png', `_${n}.png`), encodePng(both, W * 2, top));
  }
});
process.exitCode = fails ? 1 : 0;
