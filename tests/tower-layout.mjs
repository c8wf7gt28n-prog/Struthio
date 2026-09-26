// Arcade Tower layout analyzer: flies the real sim physics (humanIntent +
// integrateHuman) from every island with a bank of flap programs, then
// reports island reachability, ring reachability and art clearance.
import { sim, A } from './harness.mjs';
const T = sim.tower;
const { humanIntent, integrateHuman } = sim.step;
const { inRing } = sim.physics;
const C = { ...A.sim_constants, playTop: T.TOWER_PLAY_TOP };
const P = T.TOWER_PLATFORMS;

export function worldAt(phaseTick = 0) {
  // platforms at a given tick (moving islands use the sim's own motion).
  const s = sim.state.newState('ARCADE', 1, A.sim_constants);
  T.writeTower(s, { round: 1, kills: 0, check: 0, go: false, hold: 0 });
  const content = sim.content.arenaContent(A, s);
  const platforms = sim.content.buildPlatforms(content);
  const w = { platforms, lavaY: 352 * 256 };
  s.world = w;
  for (let i = 0; i < phaseTick; i++) sim.content.stepWorld(A, s, content);
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
