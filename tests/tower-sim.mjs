// Arcade Tower soak test: a bot climbs the tower round after round while
// every tick is checked against the tower's rules (see RULES below).
import { sim, A, frame } from './harness.mjs';
const T = sim.tower;
const CP = sim.checkpoint;
const schema = A['state.schema'];
const SUB = 256;
let failures = 0;
const seen = new Set();
const fail = (m) => { failures++; const k = m.replace(/t\d+/, 't#'); if (!seen.has(k) && seen.size < 40) { seen.add(k); console.log('FAIL', m); } };

function makeBot(seed) {
  let resting = false, r = seed >>> 0 || 7, flapT = 0, side = 0, sideT = 0, bestDy = Infinity, stall = 0, lastTarget = '';
  const rnd = () => ((r = (r * 1103515245 + 12345) >>> 0) / 4294967296);
  return (s, content) => {
    const p = s.player, cx = p.x / SUB + 14.5, cy = p.y / SUB + 19.5;
    const mask = s.objectives.ringMask;
    let target = null;
    if ((mask & 63) === 63) target = content.goldRing;
    else {
      let best = Infinity;
      for (const ring of content.rings) {
        if (mask & (1 << (ring.order - 1))) continue;
        let dx = ring.center[0] - cx; dx -= Math.round(dx / 256) * 256;
        const d = Math.abs(dx) + Math.abs(ring.center[1] - cy) * 1.5;
        if (d < best) { best = d; target = ring; }
      }
    }
    if (!target) return frame();
    const key = target.id + content.round;
    if (key !== lastTarget) { lastTarget = key; bestDy = Infinity; stall = 0; }
    let dx = target.center[0] - cx; dx -= Math.round(dx / 256) * 256;
    const dy = target.center[1] - cy;
    const dist = Math.abs(dx) + Math.abs(dy);
    if (dist < bestDy - 2) { bestDy = dist; stall = 0; } else stall++;
    if (stall > 360 && sideT <= 0) { side = rnd() < 0.5 ? -1 : 1; sideT = 50 + Math.floor(rnd() * 60); stall = 200; }
    let dir = Math.abs(dx) > 3 ? Math.sign(dx) : 0;
    // an island between us and a ring above: go round its nearest end first.
    if (dy < -6) {
      for (const q of s.world.platforms) {
        if (!q.collidable || q.id === 'GROUND') continue;
        const top = q.rect[1], bottom = q.rect[1] + q.rect[3];
        if (!(bottom <= cy - 5 && top >= target.center[1] - 4)) continue;
        let l = q.rect[0] - 10 - cx, rr = q.rect[0] + q.rect[2] + 10 - cx;
        const shift = Math.round(((l + rr) / 2) / 256) * 256; l -= shift; rr -= shift;
        if (l < 0 && rr > 0) { dir = -l < rr ? -1 : 1; break; }
      }
    }
    if (sideT > 0) { sideT--; dir = side; }
    // stamina: out of wing -> land and wait for the recharge.
    if (p.wing < 6) resting = true;
    if (resting && p.groundedPlatformId && p.wing >= 48) resting = false;
    if (p.groundedPlatformId && dy > 8 && Math.abs(dx) < 30 && sideT <= 0) { side = dx >= 0 ? 1 : -1; sideT = 40; dir = side; }
    flapT++;
    let flap = false;
    if (dy < -3 && p.vy > -260 && flapT >= 7) flap = true;
    if (dy > 0 && dy < 20 && p.vy > 520 && flapT >= 7) flap = true;
    if (sideT > 0 && p.groundedPlatformId == null && p.vy > 300 && flapT >= 9) flap = true;
    if (resting) { flap = false; if (p.groundedPlatformId) dir = 0; }
    if (flap) flapT = 0;
    return frame({ left: dir < 0, right: dir > 0, flapEdge: flap, flapKind: dir < 0 ? 'LEFT' : dir > 0 ? 'RIGHT' : 'STRAIGHT' });
  };
}

// RULES checked every tick.
function runTower({ seed, rounds, maxTicks, infiniteLives = true, shielded = infiniteLives, label }) {
  const g = new sim.Game(A, { mode: 'ARCADE', seed });
  g.start();
  const s = g.state;
  const bot = makeBot(seed * 31 + 1);
  const cam = new sim.camera.AscentCamera(A);
  const store = CP.memoryStorage();
  const stats = { rounds: 0, rings: 0, gold: 0, kills: 0, deaths: 0, spawns: 0, despawns: 0, blasts: 0, maxLive: 0, saves: 0, ticks: 0, roundTicks: [] };
  let roundStart = 0, prevRound = 1;
  for (let t = 0; t < maxTicks; t++) {
    if (infiniteLives && s.sim.lives < 3) s.sim.lives = 3;
    // shielded: the bot cannot lose a joust (a loss becomes a clash) but still jousts.
    if (shielded && s.player.invulnerableTicks < 2) s.player.invulnerableTicks = 2;
    const content = sim.content.arenaContent(A, s);
    const inp = bot(s, content);
    const r = g.tick(inp);
    stats.ticks = t + 1;
    if (s.sim.shell === 'GAMEOVER') { stats.gameOver = t; break; }
    const c2 = sim.content.arenaContent(A, s);
    const tw = T.parseTower(s);
    // camera, as presented
    const view = cam.resolve(s, c2);
    const feet = (Math.floor(s.player.y / SUB) + 25) * 2;
    const hidden = s.player.invulnerableTicks > 90;
    if (!hidden && (feet < view.cameraTop + 30 || feet > view.cameraTop + 384)) fail(`${label} t${t}: player feet ${feet} outside view top ${view.cameraTop}`);
    if (view.cameraTop < -2352 || view.cameraTop > 336) fail(`${label} t${t}: camera ${view.cameraTop} outside the tower`);
    for (const e of r.events) {
      if (e.type === 'SPAWN') {
        stats.spawns++;
        const a = s.actors.find((x) => x.id === e.actor);
        if (!a) { if (!r.events.some((q) => q.type === 'ROUND_CLEAR')) fail(`${label} t${t}: spawned rival ${e.actor} vanished`); continue; }
        const ay = (Math.floor(a.y / SUB) + 25) * 2;
        if (ay + 3 >= view.cameraTop && ay - 29 <= view.cameraTop + 384) fail(`${label} t${t}: rival ${a.id} arrived on screen (feet ${ay}, view ${view.cameraTop})`);
        if (!tw.go) fail(`${label} t${t}: rival arrived before the player moved`);
      }
      if (e.type === 'DESPAWN') stats.despawns++;
      if (e.type === 'RING' && !e.gold) stats.rings++;
      if (e.type === 'RING' && e.gold) stats.gold++;
      if (e.type === 'TOWER_BLAST') stats.blasts++;
      if (e.type === 'PLAYER_DEATH') stats.deaths++;
      if (e.type === 'ROUND_START') {
        stats.rounds++; stats.roundTicks.push(t - roundStart); roundStart = t;
        if (e.round !== prevRound + 1) fail(`${label}: round jumped ${prevRound} -> ${e.round}`);
        prevRound = e.round;
        if (process.env.VERBOSE) console.log(`  ${label}: round ${e.round} at tick ${t} (${((t - (stats.roundTicks.length > 1 ? 0 : 0)) / 3600).toFixed(1)} min), deaths ${stats.deaths}, kills ${T.parseTower(s).kills}`);
        if (s.actors.length) fail(`${label}: actors survived the round change`);
        if (s.objectives.ringMask !== 0) fail(`${label}: ring mask not reset`);
        const set = T.RING_SETS[(e.round - 1) % 10];
        if (c2.rings !== set) fail(`${label}: round ${e.round} uses the wrong ring set`);
      }
      if (e.type === 'ROUND_CLEAR' && s.actors.length) fail(`${label}: gold ring left ${s.actors.length} actors`);
    }
    // rules
    const live = s.actors.length;
    stats.maxLive = Math.max(stats.maxLive, live);
    if (live > c2.rules.cap) fail(`${label} t${t}: ${live} rivals (incl. eggs), cap ${c2.rules.cap}`);
    for (const a of s.actors) if (Math.abs(a.y - s.player.y) > T.TOWER_DESPAWN * SUB) fail(`${label} t${t}: actor ${a.id} outside the zone`);
    if (s.player.y < (T.TOWER_TOP - 20) * SUB || s.player.y > T.TOWER_BOTTOM * SUB) fail(`${label} t${t}: player left the tower (${s.player.y / SUB})`);
    if (!/^TWR_R\d+$/.test(s.objectives.routeId) || !/^TWR_K\d+_C\d+_G[01]_H\d+$/.test(s.objectives.waveId)) fail(`${label} t${t}: bad tower ids ${s.objectives.routeId} ${s.objectives.waveId}`);
    if (s.objectives.ringMask > 127) fail(`${label} t${t}: ring mask ${s.objectives.ringMask}`);
    if (r.checkpoint.length || t % 997 === 0) {
      const w = CP.writeCheckpoint(store, schema, g.payload());
      if (!w.committed) fail(`${label} t${t}: checkpoint not committed (${w.reason})`);
      else {
        stats.saves++;
        const back = CP.restoreCheckpoint(store, schema, 'ARCADE');
        if (back.status !== 'RESTORE' || JSON.stringify(back.record.payload) !== JSON.stringify(g.payload())) fail(`${label} t${t}: restore mismatch`);
      }
    }
    if (stats.rounds >= rounds) break;
  }
  stats.kills = T.parseTower(s).kills;
  stats.finalRound = T.parseTower(s).round;
  stats.score = s.sim.score;
  stats.chain = g.chain;
  return stats;
}

// 1. data sanity
{
  const ids = new Set();
  for (const p of T.TOWER_PLATFORMS) {
    if (ids.has(p.id)) fail(`duplicate island ${p.id}`); ids.add(p.id);
    if (!p.rect.every(Number.isInteger)) fail(`${p.id} rect not integer`);
    if (p.rect[1] < T.TOWER_TOP + 40 || p.rect[1] > T.TOWER_GROUND) fail(`${p.id} outside the tower`);
  }
  if (T.RING_SETS.length !== 10) fail('need 10 ring sets');
  T.RING_SETS.forEach((set, i) => { if (set.length !== 6) fail(`set ${i + 1} has ${set.length} rings`); });
  if (T.TOWER_TOP !== 360 - 8 * 192) fail('tower is not 8 screens');
  console.log(`data: ${T.TOWER_PLATFORMS.length - 1} islands + ground, ${T.RING_SETS.length} ring sets`);
}
// 2. rules per round
for (const round of [1, 2, 3, 5, 8, 12]) {
  const R = T.towerRules(round);
  console.log(`round ${round}: cap ${R.cap}, fill ${R.fillGap}t, replace ${R.replaceDelay}t, egg ${R.eggTicks}t, class shift ${R.classShift.toFixed(2)}, tier ${R.tierBase}, set ${R.ringSet + 1}, bonus ${R.clearBonus}`);
}
// 3. soak
const runs = [];
for (const seed of [11, 202, 3003]) {
  const st = runTower({ seed, rounds: 12, maxTicks: 12 * 60 * 60 * 6, label: `seed ${seed}` });
  runs.push(st);
  const mins = st.roundTicks.map((x) => (x / 3600).toFixed(1)).join(' ');
  console.log(`seed ${seed}: rounds ${st.rounds} (final R${st.finalRound}) ticks ${st.ticks} rings ${st.rings} gold ${st.gold} kills ${st.kills} deaths ${st.deaths} spawns ${st.spawns} despawns ${st.despawns} blasts ${st.blasts} maxLive ${st.maxLive} saves ${st.saves} score ${st.score}`);
  console.log(`   minutes per round: ${mins}`);
  if (st.rounds < 12) fail(`seed ${seed}: bot only finished ${st.rounds} rounds`);
}
// 4. determinism
{
  const a = runTower({ seed: 11, rounds: 2, maxTicks: 60000, label: 'det-a' });
  const b = runTower({ seed: 11, rounds: 2, maxTicks: 60000, label: 'det-b' });
  if (a.chain !== b.chain || a.ticks !== b.ticks) fail('tower sim is not deterministic');
  else console.log('determinism: identical digest chains');
}
// 5. real lives: the run ends in GAMEOVER
{
  const st = runTower({ seed: 77, rounds: 99, maxTicks: 60 * 60 * 60, infiniteLives: false, label: 'mortal' });
  console.log(`mortal run: game over at tick ${st.gameOver ?? 'never'} in round ${st.finalRound}, score ${st.score}, deaths ${st.deaths}`);
}
console.log(failures ? `TOWER SIM FAILURES: ${failures}` : 'tower sim: all rules held');
process.exitCode = failures ? 1 : 0;
