// STRUTHIO ARCADE · reachability report: every island reachable from the
// grid floor, and every ring and the gold ring reachable in flight.
import * as T from '../src/sim/tower.mjs';
import { analyze } from './tower-layout.mjs';
const P = T.TOWER_PLATFORMS;
const rings = [];
T.RING_SETS.forEach((set, si) => set.forEach((r) => rings.push({ ...r, key: `S${si + 1}.${r.order}` })));
rings.push({ ...T.GOLD_RING, key: 'GOLD' });
const t0 = Date.now();
const { edges, ringBest } = analyze(rings);
console.log('analysis ms', Date.now() - t0);
// BFS from ground
const seen = new Set([0]), q = [0];
while (q.length) { const i = q.shift(); for (const j of (edges.get(i) || new Map()).keys()) if (!seen.has(j)) { seen.add(j); q.push(j); } }
const bad = P.map((p, i) => i).filter((i) => !seen.has(i)).map((i) => P[i].id);
console.log('unreachable islands:', bad.length ? bad.join(',') : 'none');
// cheapest way *up* into each island
for (let j = 1; j < P.length; j++) {
  let best = 99, from = '';
  for (const [i, m] of edges) if (m.has(j) && P[i].rect[1] > P[j].rect[1] && m.get(j) < best) { best = m.get(j); from = P[i].id; }
  const out = [...(edges.get(j) || new Map()).entries()].filter(([k]) => P[k].rect[1] < P[j].rect[1]).length;
  if (best > 10 || out === 0) console.log(`  ${P[j].id} y=${P[j].rect[1]} climb-in ${best} flaps from ${from}; upward exits ${out}`);
}
for (const r of rings) {
  const b = ringBest.get(r.key);
  if (!b || b.flaps > 14) console.log(`ring ${r.key} (${r.center}) ${b ? b.flaps + ' flaps from ' + b.from : 'UNREACHED'}`);
}
const table = T.RING_SETS.map((set, si) => set.map((r) => ringBest.get(`S${si + 1}.${r.order}`)?.flaps ?? 99));
table.forEach((row, i) => console.log(`set ${String(i + 1).padStart(2)} flaps ${row.map((f) => String(f).padStart(2)).join(' ')}  total ${row.reduce((a, b) => a + b, 0)}`));
console.log('gold', ringBest.get('GOLD'));
let bad2 = bad.length;
for (const r of rings) if (!ringBest.get(r.key)) bad2++;
console.log(bad2 ? `LAYOUT FAILURES: ${bad2}` : 'layout: every island and ring is reachable');
process.exitCode = bad2 ? 1 : 0;
