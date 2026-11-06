// STRUTHIO ARCADE · desk mode checks: the ?desk switch (and index.html's
// pre-paint copy of it), a desk run held paused at tick 0 that then plays
// exactly like a web run, desk saves in their own slots, and the keyboard dart.
import fs from 'node:fs';
import vm from 'node:vm';
import R from '../src/data/rules.mjs';
import { Game } from '../src/sim/game.mjs';
import { newState } from '../src/sim/state.mjs';
import { digest } from '../src/core/canonical.mjs';
import * as CP from '../src/save/checkpoint.mjs';
import schema from '../src/save/save-schema.mjs';
import { InputNormalizer } from '../src/input/input.mjs';
import { deskMode, startPaused, deskStorage } from '../src/app/desk.mjs';
let failures = 0;
const check = (ok, m) => { if (!ok) { failures++; console.log('FAIL', m); } else console.log('ok  ', m); };
const input = (t) => ({ left: t % 90 < 30, right: t % 90 > 60, flapEdge: t % 9 === 0, flapHeld: false, flapKind: 'STRAIGHT' });

// the switch, and index.html's inline copy of it agrees on every address
const ADDRESSES = { '': false, '?': false, '?desk': true, '?desk=': true, '?desk=1': true, '?desk=true': true, '?desk=ON': true,
  '?seed=7&desk': true, 'desk=1': true, '?desk=0': false, '?desk=off': false, '?desk=no': false, '?desk=2': false, '?deskx': false,
  '?DESK': false, '?seed=7': false, '?x=desk': false };
const html = fs.readFileSync(new URL('../index.html', import.meta.url), 'utf8');
const inline = /<script>([^<]*desk[^<]*)<\/script>/.exec(html)?.[1];
check(!!inline, 'index.html sets the desk class before the first paint');
let agree = true, right = true;
for (const [search, want] of Object.entries(ADDRESSES)) {
  if (deskMode(search) !== want) { right = false; console.log('   deskMode', JSON.stringify(search), '->', deskMode(search)); }
  const added = [];
  vm.runInNewContext(inline || '', { URLSearchParams, location: { search }, document: { body: { classList: { add: (c) => added.push(c) } } } });
  if (added.includes('is-desk') !== want) { agree = false; console.log('   index.html', JSON.stringify(search), '->', added); }
}
check(right, '?desk and ?desk=1 switch desk mode on; no switch (or desk=0/off) leaves it off');
check(agree, 'index.html and deskMode read the address the same way');

// a desk run starts paused at tick 0: nothing in the world has advanced
const desk = new Game(R, { seed: 7 });
startPaused(desk);
const s = desk.state;
check(s.sim.tick === 0 && s.sim.shell === 'PAUSE', 'a new desk run is at tick 0 on the PAUSE shell');
check(s.sim.score === 0 && s.sim.lives === R.scoring.startLives && s.tower.round === 1, 'score 0, full Joust Marks, round 1');
const fresh = newState(7, R);
check(s.player.x === fresh.player.x && s.player.y === fresh.player.y && s.player.vx === 0 && s.player.vy === 0, 'the player is at the opening position, at rest');
const web = new Game(R, { seed: 7 });
web.start();
check(digest({ ...desk.payload(), sim: { ...s.sim, shell: 'PLAY' } }) === digest(web.payload()), 'apart from the shell, the desk start is the web start');
const w = CP.writeCheckpoint(CP.memoryStorage(), schema, desk.payload());
check(w.committed, 'the paused tick-0 run is a valid save');
// a flap key resumes (the session sets the shell back to PLAY); from there it plays tick for tick like a web run
s.sim.shell = 'PLAY';
for (let t = 0; t < 1200; t++) { desk.tick(input(t)); web.tick(input(t)); }
check(desk.chain === web.chain && desk.state.sim.tick === 1200, 'after resuming, 1200 ticks match the web run digest for digest');

// desk saves use their own slots: a run the web game saved mid-climb is untouched; records are shared
const raw = CP.memoryStorage();
const mid = new Game(R, { seed: 5 });
mid.start();
for (let t = 0; t < 900; t++) mid.tick(input(t));
CP.writeCheckpoint(raw, schema, mid.payload());
const webSum = CP.restoreCheckpoint(raw, schema).record.checksum;
const deskStore = deskStorage(raw);
check(CP.restoreCheckpoint(deskStore, schema).status === 'NONE', 'desk mode sees no saved run (it starts fresh)');
for (let i = 0; i < 3; i++) { desk.tick(input(i)); check(CP.writeCheckpoint(deskStore, schema, desk.payload()).committed, `desk checkpoint ${i + 1} commits`); }
const after = CP.restoreCheckpoint(raw, schema);
check(after.status === 'RESTORE' && after.record.checksum === webSum && after.record.payload.sim.tick === 900, 'the web save is untouched by desk checkpoints');
deskStore.setItem(CP.KEYS.RECORDS, '{"best":null}');
check(raw.getItem(CP.KEYS.RECORDS) === '{"best":null}', 'high scores are shared');
check(deskStore.keys().every((k) => k === CP.KEYS.RECORDS || k.startsWith(`${CP.SAVE_NAMESPACE}.desk.`) || [CP.KEYS.A, CP.KEYS.B, CP.KEYS.ACTIVE].includes(k)), 'desk keys live under the desk namespace');

// keyboard dart: towards a held arrow, else the bird's facing
const inp = new InputNormalizer(R.input);
inp.setMode('PLAY');
inp.keyDart('LEFT_WING');
let f = inp.frame();
check(f.dartEdge && f.dartSide === 'LEFT', 'Down darts towards the facing side');
inp.keyDown('ArrowRight');
inp.frame();
inp.keyDart('LEFT_WING');
f = inp.frame();
check(f.dartEdge && f.dartSide === 'RIGHT', 'Down with Right held darts right');

console.log(failures ? `DESK FAILURES: ${failures}` : 'desk: all checks pass');
process.exitCode = failures ? 1 : 0;
