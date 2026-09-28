// STRUTHIO ARCADE · joust rule checks: rising straight up always wins a
// contact; otherwise the higher lance wins (with the tie band and grace).
import R from '../src/data/rules.mjs';
import { Game } from '../src/sim/game.mjs';
let failures = 0;
const check = (ok, m) => { if (!ok) { failures++; console.log('FAIL', m); } else console.log('ok  ', m); };
const EMPTY = { left: false, right: false, flapEdge: false, flapHeld: false };
function contact({ vx, vy, rivalAbovePx }) {
  const g = new Game(R, { seed: 9 }); g.start();
  const s = g.state;
  for (let i = 0; i < 5; i++) g.tick(EMPTY);
  s.actors = [];
  Object.assign(s.player, { x: 120 * 256, y: 100 * 256, vx, vy, groundedPlatformId: null, invulnerableTicks: 0 });
  s.actors.push({ id: 99, kind: 'RIVAL', class: 'HUNTER', ghost: 'BLINKY', tier: 1, lifecycle: 'MOUNTED',
    x: 120 * 256, y: (100 - rivalAbovePx) * 256, vx: 0, vy: vy, facing: -1, phase: 0, timer: 0, rngDraws: 0, joustAwarded: false });
  const r = g.tick(EMPTY);
  return r.events.find((e) => e.type === 'JOUST_WIN') ? 'WIN' : r.events.find((e) => e.type === 'PLAYER_DEATH') ? 'LOSE' : r.events.find((e) => e.type === 'JOUST_CLASH') ? 'CLASH' : 'NONE';
}
check(contact({ vx: 0, vy: -400, rivalAbovePx: 6 }) === 'WIN', 'rising straight up beats a rival 6 px higher');
check(contact({ vx: 0, vy: -400, rivalAbovePx: 9 }) === 'WIN', 'rising straight up beats a rival 9 px higher (boxes just touching)');
check(contact({ vx: 300, vy: -400, rivalAbovePx: 6 }) === 'LOSE', 'rising at an angle still loses to a higher rival');
check(contact({ vx: 0, vy: 200, rivalAbovePx: 6 }) === 'LOSE', 'falling straight down still loses to a higher rival');
check(contact({ vx: 300, vy: 200, rivalAbovePx: -6 }) === 'WIN', 'the higher lance still wins normally');
console.log(failures ? `RULES FAILURES: ${failures}` : 'rules: all checks pass');
process.exitCode = failures ? 1 : 0;
