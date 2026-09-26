// Parity with the console build this game was forked from (STRUTHIO CONSOLE
// 3.6.0 Arcade). Optional: set CONSOLE_APP=/path/to/console/app.mjs (defaults
// to ../../app.mjs when the fork still sits inside the console repo). Both
// sims get identical input; every tick the player, rivals, score, lives,
// round, rings, kills, respawn island and event sequence must match.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import R from '../src/data/rules.mjs';
import { Game } from '../src/sim/game.mjs';
import { RING_SETS, GOLD_RING } from '../src/sim/tower.mjs';
const here = path.dirname(fileURLToPath(import.meta.url));
const consoleApp = process.env.CONSOLE_APP || path.resolve(here, '../../app.mjs');
if (!fs.existsSync(consoleApp)) { console.log('parity: console build not present, skipped'); process.exit(0); }
const root = path.dirname(consoleApp);
const C = (await import(pathToFileURL(consoleApp).href)).__sim;
const raw = JSON.parse(fs.readFileSync(path.join(root, 'episodes/dev-00/authority.json'), 'utf8'));
const ep = JSON.parse(fs.readFileSync(path.join(root, 'episodes/dev-00/episode.json'), 'utf8'));
C.authority.configureCartridge({ id: ep.id, buildId: ep.buildId, saveNamespace: ep.saveNamespace });
const A = await C.authority.loadAuthority(async (n) => raw[n]);

function bot(seed) {
  let r = seed >>> 0 || 1, t = 0;
  const rnd = () => ((r = (r * 1664525 + 1013904223) >>> 0) / 4294967296);
  return (p, mask, round) => {
    t++;
    const set = RING_SETS[(round - 1) % 10];
    let target = (mask & 63) === 63 ? GOLD_RING : set.find((q) => !(mask & (1 << (q.order - 1))));
    const cx = p.x / 256 + 14.5, cy = p.y / 256 + 19.5;
    let dx = target.center[0] - cx; dx -= Math.round(dx / 256) * 256;
    const dy = target.center[1] - cy;
    const jitter = rnd();
    const dir = jitter < 0.08 ? -Math.sign(dx) : Math.abs(dx) > 3 ? Math.sign(dx) : 0;
    const flap = (dy < -3 || jitter > 0.93) && t % 7 === 0;
    return { left: dir < 0, right: dir > 0, flapEdge: flap, flapHeld: false, flapKind: dir < 0 ? 'LEFT' : dir > 0 ? 'RIGHT' : 'STRAIGHT', dartEdge: jitter > 0.997, dartSide: 'LEFT' };
  };
}
const actorsOf = (s) => s.actors.map((a) => [a.id, a.class, a.lifecycle, a.x, a.y, a.vx, a.vy, a.tier, a.ghost]);
function compare(seed, ticks, round = 1, goldAt = -1) {
  const a = new C.Game(A, { mode: 'ARCADE', seed }), b = new Game(R, { seed });
  a.start(); b.start();
  if (round > 1) { C.tower.writeTower(a.state, { round, kills: 0, check: 0, go: false, hold: 0 }); b.state.tower.round = round; }
  const inp = bot(seed * 7 + 3);
  for (let t = 0; t < ticks; t++) {
    const tw = C.tower.parseTower(a.state);
    const f = inp(b.state.player, b.state.tower.ringMask, b.state.tower.round);
    if (a.state.sim.lives < 3) a.state.sim.lives = 3;
    if (b.state.sim.lives < 3) b.state.sim.lives = 3;
    if (t === goldAt) for (const s of [a.state, b.state]) {
      if (s.objectives) s.objectives.ringMask = 63; else s.tower.ringMask = 63;
      Object.assign(s.player, { x: (GOLD_RING.center[0] - 14) * 256, y: (GOLD_RING.center[1] - 19) * 256, vx: 0, vy: 0, groundedPlatformId: null, invulnerableTicks: 0 });
    }
    const ra = a.tick(f), rb = b.tick(f);
    const ta = C.tower.parseTower(a.state), sa = a.state, sb = b.state;
    const pa = sa.player, pb = sb.player;
    const diffs = [];
    if (JSON.stringify(pa) !== JSON.stringify(pb)) diffs.push(['player', pa, pb]);
    if (JSON.stringify(actorsOf(sa)) !== JSON.stringify(actorsOf(sb))) diffs.push(['actors', actorsOf(sa), actorsOf(sb)]);
    if (sa.sim.score !== sb.sim.score || sa.sim.lives !== sb.sim.lives || sa.sim.shell !== sb.sim.shell) diffs.push(['sim', sa.sim, sb.sim]);
    if (ta.round !== sb.tower.round || ta.kills !== sb.tower.kills || ta.check !== sb.tower.check || ta.go !== sb.tower.go || ta.hold !== sb.tower.hold || sa.objectives.ringMask !== sb.tower.ringMask || sa.objectives.spawnCursor !== sb.tower.cooldown) diffs.push(['tower', ta, sb.tower, sa.objectives.ringMask, sa.objectives.spawnCursor]);
    if (sa.rng.gameplayState !== sb.rng.gameplayState) diffs.push(['rng']);
    const ea = ra.events.map((e) => e.type).join(), eb = rb.events.map((e) => e.type).join();
    if (ea !== eb) diffs.push(['events', ea, eb]);
    if (JSON.stringify(sa.world.platforms) !== JSON.stringify(sb.world.platforms)) diffs.push(['platforms']);
    if (diffs.length) { console.log(`PARITY seed ${seed}: first difference at tick ${t}`); for (const d of diffs) console.log('  ', JSON.stringify(d).slice(0, 600)); return false; }
  }
  console.log(`parity seed ${seed}${round > 1 ? ' from round ' + round : ''}: ${ticks} ticks identical (round ${b.state.tower.round}, score ${b.state.sim.score}, kills ${b.state.tower.kills})`);
  return true;
}
let ok = true;
for (const seed of [1, 42, 9001]) ok = compare(seed, 40000) && ok;
for (const [seed, round] of [[7, 2], [8, 5], [9, 9], [10, 11]]) ok = compare(seed, 12000, round, 3000) && ok;
process.exitCode = ok ? 0 : 1;
