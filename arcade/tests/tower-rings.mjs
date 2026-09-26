// STRUTHIO ARCADE · static ring-placement rules (see tower-report for the
// flight-based reachability checks).
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import * as T from '../src/sim/tower.mjs';
const here = path.dirname(fileURLToPath(import.meta.url));
const md = JSON.parse(fs.readFileSync(path.join(here, '../assets/art/islands.json'), 'utf8'));
// Lip-fitted widths of the island masters (measured from the sheet's rim row).
const LIP = { STD_01: 158, STD_02: 154, STD_03: 146, STD_04: 163, STD_05: 167, STD_06: 133, STD_07: 162, STD_08: 228, STD_09: 264 };
const M = Object.fromEntries(md.masters.map((m) => [m.id, m]));
export function islandArt(p) {
  // sim-space boxes of the island art (presentation px / 2).
  const m = M[p.look], lw = LIP[p.look], w = p.rect[2];
  const amp = typeof p.motion === 'object' ? p.motion.amplitude : 0;
  const xAmp = typeof p.motion === 'object' && p.motion.profile === 'DRIFT_X_SOFT' ? amp : 0;
  const yAmp = typeof p.motion === 'object' && p.motion.profile === 'BOB_Y_SOFT' ? amp : 0;
  const body = (m.h - m.capTop) * w / lw / 2, decor = m.topDecorRows * w / lw / 2;
  const [x, y] = p.rect;
  return { x0: x - xAmp, x1: x + w + xAmp, top: y - yAmp, bodyBottom: y + body + yAmp, decorTop: y - decor - yAmp, w };
}
function xOverlap(a0, a1, b0, b1) { for (const s of [-256, 0, 256]) if (a0 + s < b1 && a1 + s > b0) return true; return false; }
export function ringProblems() {
  const out = [];
  const isl = T.TOWER_PLATFORMS.filter((p) => p.look).map((p) => ({ p, a: islandArt(p) }));
  const all = T.RING_SETS.map((set, si) => set.map((r) => ({ ...r, set: si + 1 })));
  for (const set of all) {
    const slots = new Set();
    for (const r of set) {
      const [cx, cy] = r.center, tag = `set ${r.set} ring ${r.order} (${cx},${cy})`;
      if (!Number.isInteger(cx) || cx < 0 || cx > 255) out.push(`${tag}: x outside 0..255`);
      if (cy - 6 < T.TOWER_PLAY_TOP + 4 || cy + 6 > T.TOWER_GROUND - 20) out.push(`${tag}: outside the play column`);
      for (const { p, a } of isl) {
        if (!xOverlap(cx - 12, cx + 12, a.x0, a.x1)) continue;
        if (cy + 6 > a.top - 2 && cy - 6 < a.bodyBottom) out.push(`${tag}: overlaps ${p.id} body`);
        const core0 = a.x0 + a.w * .2, core1 = a.x1 - a.w * .2;
        if (xOverlap(cx - 4, cx + 4, core0, core1) && cy + 6 > a.decorTop * 1 + (a.top - a.decorTop) * .2 && cy - 6 < a.top) out.push(`${tag}: sits in ${p.id} spires`);
      }
      const g = T.GOLD_RING.center;
      if (Math.hypot(((cx - g[0] + 384) % 256) - 128, (cy - g[1]) * 2) < 48) out.push(`${tag}: too close to the gold ring`);
      slots.add(Math.min(5, Math.floor((T.TOWER_GROUND - cy) / ((T.TOWER_GROUND - T.TOWER_TOP) / 6))));
    }
    for (let i = 0; i < set.length; i++) for (let j = i + 1; j < set.length; j++) {
      const a = set[i].center, b = set[j].center;
      const dx = Math.abs(((a[0] - b[0] + 384) % 256) - 128), dy = Math.abs(a[1] - b[1]) * 2;
      if (Math.hypot(dx, dy) < 80) out.push(`set ${set[i].set}: rings ${i + 1} and ${j + 1} too close`);
    }
    if (slots.size < 5) out.push(`set ${set[0].set}: rings only cover ${slots.size} of 6 altitude bands`);
  }
  return out;
}
if (import.meta.url === `file://${process.argv[1]}`) {
  const p = ringProblems();
  console.log(p.length ? p.join('\n') : 'ring placement: all rules pass');
  process.exitCode = p.length ? 1 : 0;
}
