// Campaign + VS regression: the 3.6 Arcade Tower must not change any other
// mode. Loads the 3.5.4 sim from git (commit tagged below), drives both sims
// with identical scripted input and compares every per-tick digest.
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import { pathToFileURL } from 'node:url';
import { sim as NEW, A as A_NEW, frame, ROOT } from './harness.mjs';
const BASE_REV = process.env.BASE_REV || '4e6a79f';
async function loadOld() {
  const src = execFileSync('git', ['show', `${BASE_REV}:app.mjs`], { cwd: ROOT, encoding: 'utf8', maxBuffer: 1 << 26 })
    .replace(/from '\.\/console\//g, `from '${pathToFileURL(path.join(ROOT, 'console')).href}/`);
  const file = path.join(fs.mkdtempSync(path.join(os.tmpdir(), 'struthio-base-')), 'app-base.mjs');
  fs.writeFileSync(file, src);
  return (await import(pathToFileURL(file).href)).__sim;
}
const OLD = await loadOld();
const raw = JSON.parse(fs.readFileSync(path.join(ROOT, 'episodes/dev-00/authority.json'), 'utf8'));
const ep = JSON.parse(fs.readFileSync(path.join(ROOT, 'episodes/dev-00/episode.json'), 'utf8'));
OLD.authority.configureCartridge({ id: ep.id, buildId: ep.buildId, saveNamespace: ep.saveNamespace });
const A_OLD = await OLD.authority.loadAuthority(async (n) => raw[n]);

function script(seed) {
  // deterministic pseudo-player: flaps, holds, darts.
  let x = seed >>> 0 || 1;
  const rnd = () => ((x = (x * 1664525 + 1013904223) >>> 0) / 4294967296);
  return (t) => {
    const r = rnd();
    const dir = Math.floor(t / 90) % 3 - 1;
    return frame({ left: dir < 0, right: dir > 0, flapEdge: r < 0.14, flapKind: dir < 0 ? 'LEFT' : dir > 0 ? 'RIGHT' : 'STRAIGHT', dartEdge: r > 0.995, dartSide: 'LEFT' });
  };
}
let failures = 0;
function placeAt(S, A, g, level) {
  // jump both sims to the same level (boss milestones enter their ring trial).
  if (!level || level === 1) return;
  const s = g.state;
  s.circuit.levelCursor = level; s.circuit.waveCursor = level;
  if ([5, 11, 17, 23, 29].includes(level)) { s.boss.phase = 'RINGS'; s.boss.milestone = level; s.boss.ringsMask = 0; }
  S.content.activateArena(A, s, []);
}
function compareCampaign(seed, ticks, level = 1) {
  const a = new OLD.Game(A_OLD, { mode: 'CAMPAIGN', seed }), b = new NEW.Game(A_NEW, { mode: 'CAMPAIGN', seed });
  a.start(); b.start();
  placeAt(OLD, A_OLD, a, level); placeAt(NEW, A_NEW, b, level);
  const inp = script(seed);
  for (let t = 0; t < ticks; t++) {
    const f = inp(t);
    const ra = a.tick(f), rb = b.tick(f);
    if (ra.digest !== rb.digest) { console.log(`CAMPAIGN seed ${seed}: digest differs at tick ${t}`); failures++; return; }
    if (a.state.sim.shell === 'GAMEOVER') { OLD.step.applyUnlimitedContinue(a.state, A_OLD.sim_constants); NEW.step.applyUnlimitedContinue(b.state, A_NEW.sim_constants); }
  }
  if (JSON.stringify(a.payload()) !== JSON.stringify(b.payload())) { console.log(`CAMPAIGN seed ${seed}: final state differs`); failures++; return; }
  console.log(`CAMPAIGN seed ${seed} from L${level}: ${ticks} ticks identical (now L${b.state.circuit.levelCursor} ${b.state.world.contentId}, score ${b.state.sim.score})`);
}
function compareVs(seed, ticks) {
  const va = OLD.vs, vb = NEW.vs;
  const ka = Object.keys(va), kb = Object.keys(vb);
  if (ka.join() !== kb.join()) { console.log('VS exports differ'); failures++; return; }
  const ca = JSON.stringify(va.vsContent(A_OLD), (k, v) => typeof v === 'function' ? undefined : v);
  const cb = JSON.stringify(vb.vsContent(A_NEW), (k, v) => typeof v === 'function' ? undefined : v);
  if (ca !== cb) { console.log('VS content differs'); failures++; return; }
  if (typeof vb.newVsState === 'function' && typeof vb.stepVs === 'function') {
    const sa = va.newVsState(A_OLD, seed), sb = vb.newVsState(A_NEW, seed);
    const inp = script(seed);
    for (let t = 0; t < ticks; t++) {
      const f = inp(t), g = inp(t + 7);
      const e = vb.encodeInput(f), e2 = vb.encodeInput(g);
      const da = va.stepVs(A_OLD, sa, [e, e2]), db = vb.stepVs(A_NEW, sb, [e, e2]);
      if (JSON.stringify(da) !== JSON.stringify(db)) { console.log(`VS seed ${seed}: differs at tick ${t}`); failures++; return; }
    }
    console.log(`VS seed ${seed}: ${ticks} ticks identical`);
  } else console.log('VS: content identical (step API not exported for a tick comparison)');
}
for (const seed of [1, 7, 12345, 99991]) compareCampaign(seed, 12000);
[2, 4, 5, 6, 9, 11, 14, 17, 20, 23, 26, 29].forEach((lv, i) => compareCampaign(1000 + i, 6000, lv));
compareVs(3, 4000);
process.exitCode = failures ? 1 : 0;
console.log(failures ? `REGRESSION FAILURES: ${failures}` : 'regression: Campaign and VS unchanged');
