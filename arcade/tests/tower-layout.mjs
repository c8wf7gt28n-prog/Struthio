// STRUTHIO ARCADE · tower layout analyzer: flies the real sim physics
// (humanIntent + integrateHuman) from every island with a bank of flap
// programs, then reports island reachability, ring reachability and art clearance.
import R from '../src/data/rules.mjs';
import * as T from '../src/sim/tower.mjs';
import { humanIntent, integrateHuman } from '../src/sim/step.mjs';
import { inRing } from '../src/sim/physics.mjs';
import { newState } from '../src/sim/state.mjs';
import { buildPlatforms, stepWorld } from '../src/sim/world.mjs';
const C = { ...R.sim, playTop: T.TOWER_PLAY_TOP };
const P = T.TOWER_PLATFORMS;

export function worldAt(phaseTick = 0) {
  // platforms at a given tick (moving islands use the sim's own motion).
  const s = newState(1, R);
  const content = T.towerContent(s);
  s.world = { platforms: buildPlatforms(content), lavaY: 352 * 256 };
  for (let i = 0; i < phaseTick; i++) stepWorld(s, content);
  return s.world;
}

const PROGRAMS = [];
for (const dir of [-1, 0, 1]) for (const every of [7, 10, 14]) for (const n of [1, 2, 3, 4, 5, 6, 8, 10, 13, 16, 20, 26]) PROGRAMS.push({ dir, every, n });

export function fly(world, fromIdx, startDx, prog, rings, maxTicks = 420) {
  const from = P[fromIdx];
  const [x0, y0, w0] = world.platforms[fromIdx].rect;
  const cx = from.id === 'GROUND' ? 128 + startDx * 40 : x0 + (w0 >> 1) + Math.round(startDx * (w0 / 2 - 8));
  const p = { x: ((cx - 14 + 256) % 256) * 256, y: (y0 - 25) * 256, vx: 0, vy: 0, groundedPlatformId: world.platforms[fromIdx].id, facing: 1, wing: 64, flapCooldown: 0, footingTicks: 0, lavaPhase: 'SAFE', lavaTicks: 0, invulnerableTicks: 0 };
  let flaps = 0, left = false, peak = p.y;
  const hits = new Map();
  for (let t = 0; t < maxTicks; t++) {
    if (p.flapCooldown > 0) p.flapCooldown--;
    const doFlap = flaps < prog.n && t % prog.every === 0;
    const kind = prog.dir < 0 ? 'LEFT' : prog.dir > 0 ? 'RIGHT' : 'STRAIGHT';
    const input = { left: prog.dir < 0, right: prog.dir > 0, flapEdge: doFlap, flapHeld: false, flapKind: kind };
    const ev = [];
    const it = humanIntent(C, p, true, input, ev);
    if (it.flap) flaps++;
    integrateHuman(C, p, it, world, [], ev);
    peak = Math.min(peak, p.y);
    const box = { l: p.x + 8 * 256, r: p.x + 21 * 256, t: p.y + 14 * 256, b: p.y + 25 * 256 };
    for (const r of rings) if (!hits.has(r.key) && inRing(box, r)) hits.set(r.key, flaps);
    if (!p.groundedPlatformId) left = true;
    if (left && p.groundedPlatformId && t > 2) {
      const idx = world.platforms.findIndex((q) => q.id === p.groundedPlatformId);
      return { land: idx, flaps, hits, peak: peak >> 8 };
    }
  }
  return { land: -1, flaps, hits, peak: peak >> 8 };
}

export function analyze(ringList, { phases = [0] } = {}) {
  const edges = new Map(); // from -> Map(to -> minFlaps)
  const ringBest = new Map(); // key -> {flaps, from}
  for (const ph of phases) {
    const world = worldAt(ph);
    for (let i = 0; i < P.length; i++) {
      for (const sdx of [-1, 0, 1]) for (const prog of PROGRAMS) {
        const r = fly(world, i, sdx, prog, ringList);
        if (r.land >= 0 && r.land !== i) {
          if (!edges.has(i)) edges.set(i, new Map());
          const m = edges.get(i);
          m.set(r.land, Math.min(m.get(r.land) ?? 99, r.flaps));
        }
        for (const [k, f] of r.hits) { const b = ringBest.get(k); if (!b || f < b.flaps) ringBest.set(k, { flaps: f, from: P[i].id }); }
      }
    }
  }
  return { edges, ringBest };
}
