// STRUTHIO ARCADE · desk mode checks: the ?desk switch (and index.html's
// pre-paint copy of it), a desk run held paused at tick 0 that then plays
// exactly like a web run, desk saves in their own slots, the keyboard dart and
// the starting key, the desk words on the page, the offline worker serving
// ?desk, and the one-time reload when an earlier build's worker serves old code.
import fs from 'node:fs';
import vm from 'node:vm';
import R from '../src/data/rules.mjs';
import { Game } from '../src/sim/game.mjs';
import { newState } from '../src/sim/state.mjs';
import { digest } from '../src/core/canonical.mjs';
import * as CP from '../src/save/checkpoint.mjs';
import schema from '../src/save/save-schema.mjs';
import { InputNormalizer, KEY_MAP } from '../src/input/input.mjs';
import { deskMode, startPaused, deskStorage, DESK_LABEL } from '../src/app/desk.mjs';
let failures = 0;
const check = (ok, m) => { if (!ok) { failures++; console.log('FAIL', m); } else console.log('ok  ', m); };
const input = (t) => ({ left: t % 90 < 30, right: t % 90 > 60, flapEdge: t % 9 === 0, flapHeld: false, flapKind: 'STRAIGHT' });
const read = (p) => fs.readFileSync(new URL(`../${p}`, import.meta.url), 'utf8');

// 1. the switch, and index.html's inline copy of it agrees on every address
const ADDRESSES = { '': false, '?': false, '?desk': true, '?desk=': true, '?desk=1': true, '?desk=true': true, '?desk=ON': true,
  '?seed=7&desk': true, '?desk&seed=7': true, 'desk=1': true, '?desk=0': false, '?desk=off': false, '?desk=no': false,
  '?desk=2': false, '?deskx': false, '?DESK': false, '?seed=7': false, '?x=desk': false };
const html = read('index.html');
const inline = /<script>([^<]*desk[^<]*)<\/script>/.exec(html)?.[1];
check(!!inline && html.indexOf(inline) < html.indexOf('id="boot"'), 'index.html sets the desk class before the boot card is parsed (first paint)');
let agree = true, right = true;
for (const [search, want] of Object.entries(ADDRESSES)) {
  if (deskMode(search) !== want) { right = false; console.log('   deskMode', JSON.stringify(search), '->', deskMode(search)); }
  const added = [];
  vm.runInNewContext(inline || '', { URLSearchParams, location: { search }, document: { body: { classList: { add: (c) => added.push(c) } } } });
  if (added.includes('is-desk') !== want) { agree = false; console.log('   index.html', JSON.stringify(search), '->', added); }
}
check(right && deskMode() === false && deskMode(undefined) === false, '?desk and ?desk=1 switch desk mode on; no switch (or desk=0/off) leaves it off');
check(agree, 'index.html and deskMode read the address the same way');

// 2. a desk run starts paused at tick 0: nothing in the world has advanced
const desk = new Game(R, { seed: 7 });
startPaused(desk);
const s = desk.state;
check(s.sim.tick === 0 && s.sim.shell === 'PAUSE', 'a new desk run is at tick 0 on the PAUSE shell');
check(s.sim.score === 0 && s.sim.lives === R.scoring.startLives && s.tower.round === 1, 'score 0, full Joust Marks, round 1');
const fresh = newState(7, R);
check(s.player.x === fresh.player.x && s.player.y === fresh.player.y && s.player.vx === 0 && s.player.vy === 0, 'the player is at the opening position, at rest');
check(digest(s.actors) === digest(fresh.actors) && digest(s.rng) === digest(fresh.rng), 'no rival has moved and no random number has been drawn');
const web = new Game(R, { seed: 7 });
web.start();
check(digest({ ...desk.payload(), sim: { ...s.sim, shell: 'PLAY' } }) === digest(web.payload()), 'apart from the shell, the desk start is the web start');
const w = CP.writeCheckpoint(CP.memoryStorage(), schema, desk.payload());
check(w.committed, 'the paused tick-0 run is a valid save');
// a flap key resumes (the session sets the shell back to PLAY); from there it plays tick for tick like a web run
s.sim.shell = 'PLAY';
for (let t = 0; t < 1200; t++) { desk.tick(input(t)); web.tick(input(t)); }
check(desk.chain === web.chain && desk.state.sim.tick === 1200, 'after resuming, 1200 ticks match the web run digest for digest');

// 3. desk saves use their own slots: a run the web game saved mid-climb is untouched; records are shared
const raw = CP.memoryStorage();
const mid = new Game(R, { seed: 5 });
mid.start();
for (let t = 0; t < 900; t++) mid.tick(input(t));
CP.writeCheckpoint(raw, schema, mid.payload());
raw.setItem(CP.KEYS.RECORDS, '{"best":{"score":1500,"round":2}}');
const webBefore = Object.fromEntries(raw.keys().map((k) => [k, raw.getItem(k)]));
const deskStore = deskStorage(raw);
check(CP.restoreCheckpoint(deskStore, schema).status === 'NONE', 'desk mode sees no saved run (it starts fresh)');
check(deskStore.getItem(CP.KEYS.RECORDS) === raw.getItem(CP.KEYS.RECORDS), 'desk mode reads the web high-score table');
let commits = 0;
for (let i = 0; i < 3; i++) { desk.tick(input(i)); if (CP.writeCheckpoint(deskStore, schema, desk.payload()).committed) commits++; }
check(commits === 3 && CP.restoreCheckpoint(deskStore, schema).record.payload.sim.tick === 1203, 'desk checkpoints commit and restore in desk mode');
deskStore.setItem(CP.KEYS.WARNING, 'SAVE NOT UPDATED');
CP.clearRun(deskStore);
const webAfter = Object.fromEntries(Object.keys(webBefore).map((k) => [k, raw.getItem(k)]));
check(digest(webAfter) === digest(webBefore), 'the web save (both slots, the pointer, the records) is untouched, even by clearing the desk run');
const after = CP.restoreCheckpoint(raw, schema);
check(after.status === 'RESTORE' && after.record.payload.sim.tick === 900, 'the web game still resumes its mid-climb run');
check(raw.keys().every((k) => k in webBefore || k.startsWith(`${CP.SAVE_NAMESPACE}.desk.`)), 'every key desk mode wrote lies under struthio.arcade.v1.desk.');
check(digest(deskStore.keys().sort()) === digest([CP.KEYS.RECORDS, CP.KEYS.WARNING].sort()), 'desk mode lists only its own keys and the shared records');
deskStore.setItem(CP.KEYS.RECORDS, '{"best":null}');
check(raw.getItem(CP.KEYS.RECORDS) === '{"best":null}', 'a desk high score is written to the shared table');

// 4. keyboard dart (desk mode): towards a held arrow, else the bird's facing
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
check(!KEY_MAP.ArrowDown && !KEY_MAP.KeyS, 'the shared key map is unchanged (Down and S are not flap keys)');
// the key that starts (or resumes) a desk run: the session resumes first (PAUSE -> PLAY clears every
// held key), then hands the key to the input, so it is held and flaps on the first tick
const startKey = new InputNormalizer(R.input);
startKey.setMode('PAUSE');
startKey.setMode('PLAY');
startKey.keyDown('ArrowRight');
f = startKey.frame();
check(f.right && f.flapEdge, 'the key that starts a desk run is held and flaps on the first tick');
check(/if \(resume\('KEY'\)&&app\.desk&&KEY_MAP\[ev\.code\]\) input\.keyDown\(ev\.code\);/.test(read('src/app/session.mjs')), 'session: at the desk the resuming flap key goes to the input after resume()');
check(/else if \(app\.desk&&ev\.code==='Escape'&&isPaused\(\)&&!game\.state\.sim\.tick\) return;/.test(read('src/app/session.mjs')), 'session: Esc does not leave the desk start pause (tick 0)');

// 5. the words on the page speak of keys, and the web words are unchanged
const scene = read('src/render/scene.mjs'), session = read('src/app/session.mjs'), css = read('assets/arcade-frame.css');
check(!/\btap|wing/i.test(DESK_LABEL) && /Escape pauses/.test(DESK_LABEL), 'the desk canvas label names keys, not taps or wings');
check(/'BOTH WINGS TO RESUME'/.test(scene) && /'A FLAP KEY TO START'/.test(scene) && /'A FLAP KEY TO RESUME'/.test(scene), 'the pause screen: BOTH WINGS on the web, a flap key at the desk');
check(/GAMEOVER_ITEMS=Object\.freeze\(\['NEW RUN','TITLE'\]\)/.test(session) && /DESK_GAMEOVER_ITEMS=Object\.freeze\(\['NEW RUN'\]\)/.test(session), 'game over: NEW RUN and TITLE on the web, NEW RUN only at the desk');
check(/body\.is-desk #controls[^{]*\{display:none!important;pointer-events:none\}/.test(css) && /body\.is-desk #title-screen/.test(css), 'desk CSS: the wing controller and the title screen are not displayed');

// 6. release: one version everywhere, and the offline worker precaches desk.mjs and serves its page for any search
const build = /BUILD_ID='([^']+)'/.exec(read('src/app/boot.mjs'))[1];
const sw = read('sw.js');
check(html.includes(`<meta name="build" content="${build}">`) && sw.includes(`const BUILD='${build}';`), `index.html, boot.mjs and sw.js agree on ${build}`);
const core = JSON.parse(/const CORE=(\[[^\]]*\]);/.exec(sw)[1]);
check(core.includes('./src/app/desk.mjs') && core.includes('./'), 'sw.js precaches src/app/desk.mjs and the page');
check(/const offlinePage=async\(cache\)=>\{const hit=\(await cache\.match\('\.\/'\)\)/.test(sw), 'offline, a navigation (?desk included) gets the cached page, matched without its search string');
const sums = Object.fromEntries(read('SHA256SUMS.txt').trim().split('\n').map((l) => l.split(/\s+/).reverse()));
check('src/app/desk.mjs' in sums && 'sw.js' in sums, 'SHA256SUMS.txt lists src/app/desk.mjs and sw.js');

// 7. after an update, a desk page whose code came from the earlier build's worker does not boot that
// code: it waits for the new worker and reloads once (at most once per tab); the web page boots as before
const mod = /<script type="module">([\s\S]*?)<\/script>/.exec(html)[1];
const [importLine] = /^import \{[^}]*\} from '\.\/src\/app\/boot\.mjs';$/m.exec(mod) || [''];
check(/\bBUILD_ID\b/.test(importLine), 'index.html takes BUILD_ID from the code it loaded (src/app/boot.mjs)');
const pageBuild = /<meta name="build" content="([^"]+)">/.exec(html)[1];
function runPage({ code = pageBuild, desk = true, controller = true, reloadedFor = null, reg = { installing: null, waiting: null } } = {}) {
  const out = { booted: 0, reloads: 0, timers: [], listeners: {}, status: 'LOADING', updates: 0, messages: [], store: new Map(reloadedFor ? [['struthio.arcade.reloadedFor', reloadedFor]] : []) };
  const registration = { ...reg, update: async () => { out.updates++; } };
  if (reg.waiting) registration.waiting = { postMessage: (m) => out.messages.push(m.type) };
  const ctx = {
    BUILD_ID: code, boot: () => { out.booted++; return Promise.resolve({ updateReady: false, game: null }); }, showFatal: () => {},
    location: { hostname: 'example.org', search: desk ? '?desk' : '', reload: () => { out.reloads++; } }, URLSearchParams,
    document: {
      querySelector: (sel) => (sel === 'meta[name="build"]' ? { content: pageBuild } : sel === '[data-boot-status]' ? { set textContent(v) { out.status = v; } } : null),
      getElementById: () => ({ hidden: true }), body: { classList: { contains: (c) => c === 'is-desk' && desk } },
    },
    navigator: { serviceWorker: { controller: controller ? {} : null, addEventListener: (t, f) => { out.listeners[t] = f; }, getRegistration: async () => registration } },
    sessionStorage: { getItem: (k) => out.store.get(k) ?? null, setItem: (k, v) => out.store.set(k, v) },
    setTimeout: (f, ms) => out.timers.push(ms), setInterval: () => {}, window: { addEventListener: () => {} },
  };
  vm.runInNewContext(mod.replace(importLine, ''), ctx);
  return out;
}
const settle = () => new Promise((r) => setTimeout(r, 0));
const OLD = 'STRUTHIO-ARCADE-1.8.0';
let p = runPage();
check(p.booted === 1 && p.reloads === 0 && !p.listeners.controllerchange, 'code and page agree: the game boots at once');
p = runPage({ code: OLD, desk: false });
check(p.booted === 1 && p.reloads === 0, 'web page on the earlier build\'s code: boots at once, exactly as before');
p = runPage({ code: OLD, controller: false });
check(p.booted === 1 && p.reloads === 0, 'no worker controls the page: boots at once');
p = runPage({ code: OLD, reg: { installing: {}, waiting: null } });
await settle();
check(p.booted === 0 && p.reloads === 0 && p.status === 'UPDATING' && p.store.get('struthio.arcade.reloadedFor') === pageBuild && p.timers.includes(15000), 'desk page on the earlier build\'s code: does not boot; says UPDATING while the new worker installs');
p.listeners.controllerchange();
check(p.reloads === 1 && p.booted === 0, 'the new worker takes over: the page reloads');
p = runPage({ code: OLD, reg: { installing: null, waiting: {} } });
await settle();
check(p.messages.join() === 'SKIP_WAITING' && p.reloads === 0, 'a new worker waiting: it is asked to take over');
p = runPage({ code: OLD });
await settle(); await settle();
check(p.updates === 1 && p.reloads === 1 && p.booted === 0, 'no newer worker on the way (the new one already took over): an update check, then reload at once');
p = runPage({ code: OLD, reloadedFor: pageBuild });
check(p.booted === 1 && p.reloads === 0, 'already reloaded once in this tab for this build: boots as is (no loop)');

console.log(failures ? `DESK FAILURES: ${failures}` : 'desk: all checks pass');
process.exitCode = failures ? 1 : 0;
