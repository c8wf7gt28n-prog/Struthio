// STRUTHIO HANDHELD · golden trace exporter.
//
// Runs the STRUTHIO ARCADE browser authority (arcade/src, unmodified) headless:
// a bot presses two physical wing buttons, the real InputNormalizer turns the
// presses into frames exactly as the browser session does, and the real Game
// ticks. Every tick records the button timeline, the frame the normalizer
// produced, and the tick's state digest. The C port replays the same button
// timeline and must reproduce every frame and every digest bit for bit.
//
//   node handheld/tools/golden_export.mjs            # write handheld/golden/*.trace
//   node handheld/tools/golden_export.mjs --check    # regenerate and compare
//   node handheld/tools/golden_export.mjs --dump NAME TICK   # canonical state line
//
// Trace format: see trace.mjs.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';
import R from '../../arcade/src/data/rules.mjs';
import { Game } from '../../arcade/src/sim/game.mjs';
import { InputNormalizer } from '../../arcade/src/input/input.mjs';
import * as T from '../../arcade/src/sim/tower.mjs';
import { canonicalOf } from './canonical_line.mjs';
import { OP, tickTimeMs, applyOp, encodeFrame, canAcceptBufferedFlap, applyCheats as applyHeaderCheats } from './trace.mjs';
export { OP };
const applyCheats = (s, sc) => applyHeaderCheats(s, sc);

const here = path.dirname(fileURLToPath(import.meta.url));
const GOLDEN = path.join(here, '..', 'golden');
const SUB = 256;

// Scenarios. cheats: livesFloor keeps lives >= 3, shield keeps the player
// unbeatable in jousts (the arcade tower soak test's harness pokes, applied
// before every tick). startRound pokes tower.round before the run starts.
export const SCENARIOS = [
  { name: 'climb', seed: 11, ticks: 40000, rounds: 3, livesFloor: true, shield: true, startRound: 1, dart: 0.004, chord: 0.05 },
  { name: 'mortal', seed: 77, ticks: 40000, rounds: 99, livesFloor: false, shield: false, startRound: 1, dart: 0.006, chord: 0.08 },
  { name: 'duel', seed: 202, ticks: 20000, rounds: 99, livesFloor: true, shield: false, startRound: 1, dart: 0.03, chord: 0.2 },
  { name: 'raw', seed: 4242, ticks: 20000, rounds: 99, livesFloor: true, shield: false, startRound: 4, dart: 0.02, chord: 0.3, raw: true },
  { name: 'late', seed: 3003, ticks: 20000, rounds: 2, livesFloor: true, shield: true, startRound: 9, dart: 0.01, chord: 0.1 },
];

// The tower soak test's climbing bot (arcade/tests/tower-sim.mjs), extended
// with chords and darts, deciding what it wants each tick.
function makeBot(seed, sc) {
  let resting = false, r = seed >>> 0 || 7, flapT = 0, side = 0, sideT = 0, bestDy = Infinity, stall = 0, lastTarget = '';
  const rnd = () => ((r = (r * 1103515245 + 12345) >>> 0) / 4294967296);
  const decide = (s, content) => {
    const p = s.player, cx = p.x / SUB + 14.5, cy = p.y / SUB + 19.5;
    const mask = s.tower.ringMask;
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
    if (!target) return { dir: 0, flap: false };
    const key = target.id + content.round;
    if (key !== lastTarget) { lastTarget = key; bestDy = Infinity; stall = 0; }
    let dx = target.center[0] - cx; dx -= Math.round(dx / 256) * 256;
    const dy = target.center[1] - cy;
    const dist = Math.abs(dx) + Math.abs(dy);
    if (dist < bestDy - 2) { bestDy = dist; stall = 0; } else stall++;
    if (stall > 360 && sideT <= 0) { side = rnd() < 0.5 ? -1 : 1; sideT = 50 + Math.floor(rnd() * 60); stall = 200; }
    let dir = Math.abs(dx) > 3 ? Math.sign(dx) : 0;
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
    // extensions: a both-wings chord instead of a sideways flap, and darts.
    const chord = flap && rnd() < sc.chord;
    let dart = 0;
    if (!p.groundedPlatformId && rnd() < sc.dart) dart = rnd() < 0.5 ? -1 : 1;
    return { dir, flap, chord, dart, jitter: Math.floor(rnd() * 17), chordGap: 5 + Math.floor(rnd() * 90) };
  };
  return decide;
}

// Turns what the bot wants into physical button presses with millisecond
// timing inside the tick. Holding a wing steers; a new press of a wing flaps.
function makeHands() {
  let L = false, R = false, pendingR = null;
  return (want, t0, ops) => {
    const at = (ms, op) => ops.push([Math.min(16, Math.max(0, ms)), op]);
    let ms = want.jitter || 0;
    if (pendingR !== null) {                        // second half of a slow chord
      if (!R) { at(0, OP.RIGHT_DOWN); R = true; }
      pendingR = null;
    }
    const wantL = want.dir < 0, wantR = want.dir > 0;
    if (want.flap && want.chord) {
      // tap both: release whatever is held, press LEFT, then RIGHT inside 100 ms
      if (L) { at(ms, OP.LEFT_UP); L = false; }
      if (R) { at(ms, OP.RIGHT_UP); R = false; }
      at(ms + 1, OP.LEFT_DOWN); L = true;
      if (want.chordGap < 16 - ms) { at(ms + 1 + want.chordGap, OP.RIGHT_DOWN); R = true; }
      else pendingR = want.chordGap;
    } else if (want.flap) {
      const down = wantR ? OP.RIGHT_DOWN : OP.LEFT_DOWN, up = wantR ? OP.RIGHT_UP : OP.LEFT_UP;
      const held = wantR ? R : L;
      if (held) at(ms, up);
      at(ms + 2, down);
      if (wantR) R = true; else L = true;
    } else {
      if (L && !wantL) { at(ms, OP.LEFT_UP); L = false; }
      if (R && !wantR) { at(ms, OP.RIGHT_UP); R = false; }
      if (wantL && !L) { at(ms, OP.LEFT_DOWN); L = true; }
      if (wantR && !R) { at(ms, OP.RIGHT_DOWN); R = true; }
    }
    if (want.dart) at(ms + 3, want.dart < 0 ? OP.DART_LEFT : OP.DART_RIGHT);
    ops.sort((a, b) => a[0] - b[0]);
  };
}

export function newScenarioGame(sc) {
  const g = new Game(R, { seed: sc.seed });
  g.state.tower.round = sc.startRound;
  g.start();
  return g;
}

function run(sc, { dumpTick = -1 } = {}) {
  const g = newScenarioGame(sc);
  const s = g.state;
  const input = new InputNormalizer(R.input);
  let clock = 0;
  input.now = () => clock;
  input.setMode('PLAY');
  const decide = makeBot(sc.seed * 31 + 1, sc);
  const hands = makeHands();
  const ptr = { n: 0, L: 0, R: 0 };
  const chunks = [];
  const stats = { rounds: 0, deaths: 0, jousts: 0, clashes: 0, eggs: 0, rings: 0, gold: 0, darts: 0, chords: 0, flapChords: 0, lava: 0, rescues: 0, spawns: 0, extraLives: 0, gameOver: null };
  let cleanupNext = false, dump = null;
  let tick = 0;
  for (; tick < sc.ticks; tick++) {
    applyCheats(s, sc);
    const want = decide(s, T.towerContent(s));
    const ops = [];
    if (cleanupNext) { ops.push([0, OP.CLEANUP]); cleanupNext = false; }
    let accept, frame;
    if (sc.raw) {
      // raw frames straight into the sim, no normalizer and no flap gating:
      // reaches the chord-during-cooldown correction and side-less darts.
      ops.length = 0;
      accept = true;
      const kind = want.chord ? 'STRAIGHT' : want.dir < 0 ? 'LEFT' : want.dir > 0 ? 'RIGHT' : 'STRAIGHT';
      const chordEdge = want.chord || (want.jitter & 7) === 0;
      frame = { left: want.dir < 0, right: want.dir > 0, flapEdge: want.flap || chordEdge && (want.jitter & 1) === 0,
        flapKind: kind, chordEdge, flapHeld: false, dartEdge: !!want.dart, dartSide: want.dart ? (want.dart < 0 ? 'LEFT' : 'RIGHT') : null };
      // a side-less dart (the handheld's both-wings DART): the sim darts toward facing
      if (frame.dartEdge && (want.jitter % 3) === 0) frame.dartSide = null;
      if (!frame.flapEdge) { frame.flapKind = null; frame.chordEdge = false; }
    } else {
      hands(want, tick, ops);
      const base = tickTimeMs(tick);
      for (const [ms, op] of ops) { clock = base + ms; applyOp(input, op, ptr); }
      clock = base + 16;
      accept = canAcceptBufferedFlap(s);
      frame = input.frame({ acceptFlap: accept });
    }
    const r = g.tick(frame);
    if (tick === dumpTick) dump = canonicalOf({ state: s, events: r.events.filter((e) => e.serial !== 0) });
    const rec = Buffer.alloc(1 + ops.length * 2 + 2 + 8);
    let o = 0;
    rec[o++] = ops.length;
    for (const [ms, op] of ops) { rec[o++] = ms; rec[o++] = op; }
    rec[o++] = (accept ? 1 : 0) | (frame.dartEdge && !frame.dartSide ? 2 : 0);   // bit1: raw side-less dart
    rec[o++] = encodeFrame(frame);
    Buffer.from(r.digest.slice(0, 16), 'hex').copy(rec, o);
    chunks.push(rec);
    for (const e of r.events) {
      if (e.type === 'ROUND_START') stats.rounds++;
      if (e.type === 'PLAYER_DEATH') stats.deaths++;
      if (e.type === 'JOUST_WIN') stats.jousts++;
      if (e.type === 'JOUST_CLASH') stats.clashes++;
      if (e.type === 'EGG') stats.eggs++;
      if (e.type === 'RING') e.gold ? stats.gold++ : stats.rings++;
      if (e.type === 'DART') stats.darts++;
      if (e.type === 'FLAP' && e.kind === 'STRAIGHT') stats.chords++;
      if (e.type === 'FLAP_CHORD') stats.flapChords++;
      if (e.type === 'LAVA_CONTACT') stats.lava++;
      if (e.type === 'LAVA_RESCUE') stats.rescues++;
      if (e.type === 'SPAWN') stats.spawns++;
      if (e.type === 'EXTRA_LIFE') stats.extraLives++;
      if (e.type === 'PLAYER_DEATH' || e.type === 'GAMEOVER') cleanupNext = true;
    }
    if (s.sim.shell === 'GAMEOVER') { stats.gameOver = tick; tick++; break; }
    if (stats.rounds >= sc.rounds) { tick++; break; }
  }
  const header = {
    format: 'struthio-golden', version: 1, authority: 'STRUTHIO ARCADE 1.8.0',
    name: sc.name, raw: !!sc.raw, seed: sc.seed, startRound: sc.startRound, livesFloor: sc.livesFloor, shield: sc.shield,
    ticks: tick, chain: g.chain, stateDigest: g.stateDigest(), finalScore: s.sim.score, finalRound: s.tower.round, stats,
  };
  const hb = Buffer.from(JSON.stringify(header));
  const head = Buffer.alloc(12);
  head.write('STRGOLD1', 0, 'latin1');
  head.writeUInt32LE(hb.length, 8);
  return { header, bytes: Buffer.concat([head, hb, ...chunks]), dump };
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const args = process.argv.slice(2);
  if (args[0] === '--dump') {
    const sc = SCENARIOS.find((x) => x.name === args[1]);
    const r = run(sc, { dumpTick: Number(args[2]) });
    process.stdout.write(r.dump + '\n');
  } else {
    const check = args.includes('--check');
    fs.mkdirSync(GOLDEN, { recursive: true });
    let bad = 0;
    const manifest = [];
    for (const sc of SCENARIOS) {
      const t0 = Date.now();
      const { header, bytes } = run(sc);
      const file = path.join(GOLDEN, `${sc.name}.trace`);
      const sha = crypto.createHash('sha256').update(bytes).digest('hex');
      if (check) {
        const same = fs.existsSync(file) && fs.readFileSync(file).equals(bytes);
        if (!same) bad++;
        console.log(`${same ? 'SAME' : 'DIFF'} ${sc.name}`);
      } else fs.writeFileSync(file, bytes);
      manifest.push(`${sha}  ${sc.name}.trace`);
      console.log(`${sc.name}: ${header.ticks} ticks, ${bytes.length} bytes, score ${header.finalScore}, round ${header.finalRound} (${Date.now() - t0} ms)`);
      console.log('   ', JSON.stringify(header.stats));
    }
    if (!check) fs.writeFileSync(path.join(GOLDEN, 'SHA256SUMS.txt'), manifest.join('\n') + '\n');
    process.exitCode = bad ? 1 : 0;
  }
}
