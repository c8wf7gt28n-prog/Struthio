// STRUTHIO ARCADE · save tests: A/B slots, checksum and schema rejection,
// torn-write recovery, and a restored run continuing identically.
import R from '../src/data/rules.mjs';
import { Game } from '../src/sim/game.mjs';
import * as CP from '../src/save/checkpoint.mjs';
import schema from '../src/save/save-schema.mjs';
let failures = 0;
const check = (ok, m) => { if (!ok) { failures++; console.log('FAIL', m); } };
const input = (t) => ({ left: t % 90 < 30, right: t % 90 > 60, flapEdge: t % 9 === 0, flapHeld: false, flapKind: 'STRAIGHT' });

const g = new Game(R, { seed: 5 });
g.start();
for (let t = 0; t < 3000; t++) g.tick(input(t));
const store = CP.memoryStorage();
check(CP.restoreCheckpoint(store, schema).status === 'NONE', 'empty storage should be NONE');
const w1 = CP.writeCheckpoint(store, schema, g.payload());
check(w1.committed && w1.slot === 'A', 'first save goes to slot A');
for (let t = 3000; t < 3600; t++) g.tick(input(t));
const w2 = CP.writeCheckpoint(store, schema, g.payload());
check(w2.committed && w2.slot === 'B', 'second save goes to slot B');
const back = CP.restoreCheckpoint(store, schema);
check(back.status === 'RESTORE' && back.slot === 'B', 'restore reads the active slot');

// restored run continues identically
const h = new Game(R, { seed: 5, state: structuredClone(back.record.payload) });
for (let t = 3600; t < 6000; t++) { g.tick(input(t)); h.tick(input(t)); }
check(g.stateDigest() === h.stateDigest(), 'restored run diverged');

// corruption: a flipped score fails the checksum; falls back to slot A
const rec = JSON.parse(store.getItem(CP.KEYS.B));
rec.payload.sim.score += 1000;
store.setItem(CP.KEYS.B, JSON.stringify(rec));
const fb = CP.restoreCheckpoint(store, schema);
check(fb.status === 'RESTORE' && fb.slot === 'A', 'checksum failure should fall back to slot A');
// junk in both slots is rejected, not restored
store.setItem(CP.KEYS.A, '{"format":"struthio-arcade-save","version":1,"payload":{}}');
store.setItem(CP.KEYS.B, 'not json');
check(CP.restoreCheckpoint(store, schema).status === 'REJECTED', 'junk should be REJECTED');
// a save from another game is not ours
store.setItem(CP.KEYS.A, JSON.stringify({ ...rec, format: 'struthio-save' }));
check(CP.restoreCheckpoint(store, schema).reasons?.A === 'UNKNOWN_FORMAT', 'foreign format should be UNKNOWN_FORMAT');
CP.clearRun(store);
check(CP.restoreCheckpoint(store, schema).status === 'NONE', 'clearRun should empty the slots');
console.log(failures ? `SAVE FAILURES: ${failures}` : 'save: all checks pass');
process.exitCode = failures ? 1 : 0;
