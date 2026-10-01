// STRUTHIO HANDHELD · reference renderer harness. Loads the browser game's own
// render modules (arcade/src, unmodified), renders a given game state with a
// given render tick, and exposes the frame, the instance list and the textures
// to the capture tool (capture.mjs, Playwright + headless Chromium WebGPU).
import R from '../../../arcade/src/data/rules.mjs';
import { loadArt, buildArcadeGlobe, ARCADE_REAR_HORIZON } from '../../../arcade/src/app/art.mjs';
import { buildAtlas } from '../../../arcade/src/render/atlas.mjs';
import { createRenderer } from '../../../arcade/src/render/renderer.mjs';
import { Scene, buildScene } from '../../../arcade/src/render/scene.mjs';
import { towerContent } from '../../../arcade/src/sim/tower.mjs';
import { withCamera, towerProfile, TowerCamera } from '../../../arcade/src/render/camera.mjs';
import { Game } from '../../../arcade/src/sim/game.mjs';
import { InputNormalizer } from '../../../arcade/src/input/input.mjs';
import { freshFeelState, triggerFeel, sampleFeelState } from '../../../arcade/src/app/feel.mjs';
import { MOON_TURN_PER_TICK } from '../../../arcade/src/app/art.mjs';
import { parseTrace, frameForTick, applyCheats } from '../trace.mjs';

const log = (m) => { (window.__log ||= []).push(m); };
// Headless Chromium cannot present a WebGPU canvas here (the device is lost on
// the first presented frame), so the canvas gets a stand-in context: the
// renderer draws its final post pass into an offscreen texture this harness
// owns and reads back. The game's renderer code itself is untouched.
const offscreen = { device: null, texture: null, format: 'rgba8unorm' };
const realGetContext = HTMLCanvasElement.prototype.getContext;
HTMLCanvasElement.prototype.getContext = function (kind, ...rest) {
  if (kind !== 'webgpu') return realGetContext.call(this, kind, ...rest);
  const canvas = this;
  return {
    configure({ device }) { offscreen.device = device; offscreen.texture = null; },
    getCurrentTexture() {
      const w = canvas.width, h = canvas.height;
      if (!offscreen.texture || offscreen.texture.width !== w || offscreen.texture.height !== h)
        offscreen.texture = offscreen.device.createTexture({ size: [w, h, 1], format: offscreen.format, usage: GPUTextureUsage.RENDER_ATTACHMENT | GPUTextureUsage.COPY_SRC });
      return offscreen.texture;
    },
  };
};
const realPreferred = navigator.gpu && navigator.gpu.getPreferredCanvasFormat.bind(navigator.gpu);
if (navigator.gpu) navigator.gpu.getPreferredCanvasFormat = () => offscreen.format;
async function readTexture(device, texture) {
  const w = texture.width, h = texture.height, bpr = Math.ceil(w * 4 / 256) * 256;
  const buf = device.createBuffer({ size: bpr * h, usage: GPUBufferUsage.COPY_DST | GPUBufferUsage.MAP_READ });
  const enc = device.createCommandEncoder();
  enc.copyTextureToBuffer({ texture }, { buffer: buf, bytesPerRow: bpr, rowsPerImage: h }, [w, h, 1]);
  device.queue.submit([enc.finish()]);
  await buf.mapAsync(GPUMapMode.READ);
  const src = new Uint8Array(buf.getMappedRange()), out = new Uint8Array(w * h * 4);
  for (let y = 0; y < h; y++) out.set(src.subarray(y * bpr, y * bpr + w * 4), y * w * 4);
  buf.unmap(); buf.destroy();
  return { w, h, p: out };
}
const base = '../../../arcade/';
const fetchJson = async (p) => (await fetch(base + p)).json();
const ref = { ready: false, error: null, log: (window.__log ||= []) };
window.__ref = ref;
try {
  const art = await loadArt(base, fetchJson);
  log('art loaded');
  const atlas = buildAtlas(R, art);
  log('atlas built');
  const canvas = document.getElementById('game');
  const renderer = await createRenderer(canvas, {
    atlasPixels: atlas.surface, birdPixels: art.bird,
    onLost: (i) => log('LOST ' + JSON.stringify(i)), onFatal: (e) => { ref.error = e.code + ' ' + e.detail; log('FATAL ' + ref.error); },
  });
  log('renderer created');
  renderer.uploadWorld(atlas.world);
  renderer.setBird(art.bird, true);
  const globe = buildArcadeGlobe(atlas.background.rear);
  renderer.setGlobe(globe, globe.params);
  renderer.setArcadeFx(ARCADE_REAR_HORIZON);
  const scene = new Scene(R, atlas);
  Object.assign(ref, { R, art, atlas, renderer, scene, globe, ready: true });
  // Renders one state. opts: renderTick, quality, cameraTop, effects, popups, feel, ...
  ref.render = async (state, opts = {}) => {
    const content = towerContent(state);
    let ascent = withCamera(towerProfile(state));
    if (Number.isFinite(opts.cameraTop)) {
      const b = ascent.bounds;
      ascent = { ...ascent, cameraTop: opts.cameraTop, backgroundProgress: Math.max(0, Math.min(1, (b.bottom - opts.cameraTop) / (b.bottom - b.top))) };
    }
    const view = { state, prev: null, prevPlayer: null, alpha: 1, renderTick: opts.renderTick ?? 1, screen: 'GAME', content, ascent,
      feel: opts.feel || { active: false, impact: 0, joltX: 0, joltY: 0 }, popups: opts.popups || [], musicDrive: null,
      gameOverItems: ['NEW RUN', 'TITLE'], gameOverIndex: 0, gameOverInfo: opts.gameOverInfo || null };
    buildScene(scene, view);
    if (scene.atlasDirty) { scene.atlasDirty = false; renderer.markAtlasDirty(); }
    renderer.setInstances(scene.list);
    renderer.setQuality(opts.quality ?? 2);
    const ok = renderer.frame(view.renderTick, Object.assign({ ambientTick: view.renderTick, cyan: 1.02, lava: 1.02, violet: 0.96, impact: 0, beat: 0, motion: true, bloomBeat: 0, moonPhase: opts.moonPhase ?? 0 }, opts.effects || {}));
    await renderer.device.queue.onSubmittedWorkDone();
    if (opts.read) ref.lastFrame = await readTexture(renderer.device, offscreen.texture);
    if (opts.readScene) ref.lastScene = await renderer.readScene3x();
    return { ok, instances: scene.list.map((q) => [q.x, q.y, q.w, q.h, q.sx, q.sy, q.sw, q.sh, q.z, q.flags || 0]) };
  };
  // ---- golden replay through the session's per-tick behaviour -------------
  // Mirrors arcade/src/app/session.mjs: one sim step then one render per tick
  // (renderTick = ticks rendered), alpha 1, music off (drive null), motion on.
  const SCORE_POPUP = { EGG: 'GOLD', JOUST: 'WHITE', RING: 'CYAN' };
  const BANNER_TICKS = 150;
  const q = (v) => Math.round(v * 4096) | 0;
  function fnvInts(list) {
    let h = 0x811c9dc5 >>> 0;
    const mix = (v) => { for (let k = 0; k < 4; k++) { h ^= (v >>> (8 * k)) & 255; h = Math.imul(h, 0x01000193) >>> 0; } };
    mix(list.length);
    for (const it of list) { mix(q(it.x)); mix(q(it.y)); mix(q(it.w)); mix(q(it.h)); mix(q(it.sx)); mix(q(it.sy)); mix(q(it.sw)); mix(q(it.sh)); mix(q(it.z)); mix(it.flags | 0); }
    return h >>> 0;
  }
  ref.fnvInts = fnvInts;
  ref.replay = async (url, opts = {}) => {
    const bytes = new Uint8Array(await (await fetch(url)).arrayBuffer());
    const { header, ticks } = parseTrace(bytes);
    const game = new Game(R, { seed: header.seed });
    game.state.tower.round = header.startRound;
    game.start();
    const s = game.state;
    const input = new InputNormalizer(R.input);
    const clock = { now: 0 };
    input.now = () => clock.now;
    input.setMode('PLAY');
    const ptr = { n: 0, L: 0, R: 0 };
    const sc = new Scene(R, atlas);
    const camera = new TowerCamera();
    const feel = freshFeelState();
    const popups = [];
    let banner = null, renderTick = 0, moonPhase = 0, gameOverInfo = null;
    const hashes = new Uint32Array(ticks.length);
    const captures = {}, lists = {};
    const want = new Set(opts.capture || []), wantLists = new Set(opts.lists || []);
    for (let t = 0; t < ticks.length; t++) {
      applyCheats(s, header);
      const frame = frameForTick(ticks[t], t, s, input, ptr, header, clock);
      const prevPlayer = { x: s.player.x, y: s.player.y };
      const contentBefore = towerContent(s);
      const wasGrounded = !!s.player.groundedPlatformId;
      const r = game.tick(frame);
      const playerX = Math.floor(s.player.x / 256) + 14, playerTop = Math.floor(s.player.y / 256);
      for (const e of r.events) {
        if (e.type === 'EXTRA_LIFE') banner = { text: 'EXTRA JOUST MARK', until: renderTick + 100 };
        if (e.type === 'GOLD_RING_OPEN') banner = { text: '6/6 · THE GOLD RING IS AT THE MOON', until: renderTick + BANNER_TICKS };
        if (e.type === 'ROUND_CLEAR') banner = { text: `ROUND ${e.round} CLEAR${e.clean ? ' · NO LOSSES' : ''}`, until: renderTick + BANNER_TICKS };
        if (e.type === 'TOWER_BLAST' && e.amount) { popups.push({ text: String(e.amount), tone: 'GOLD', x: Math.floor(e.x / 256) + 14, y: Math.floor(e.y / 256) + 4, tick: renderTick }); if (popups.length > 12) popups.shift(); }
        if (e.type === 'SCORE_AWARD' && SCORE_POPUP[e.kind]) {
          const ring = e.kind === 'RING' ? contentBefore.rings.find((x) => x.order === e.order) : null;
          popups.push({ text: String(e.amount), tone: SCORE_POPUP[e.kind], x: ring ? ring.center[0] : playerX, y: ring ? ring.center[1] - 14 : playerTop + 4, tick: renderTick, big: e.kind === 'EGG' && e.chain >= 4 });
          if (popups.length > 12) popups.shift();
        }
        if (e.type === 'GAMEOVER') gameOverInfo = { final: s.sim.score, round: s.tower.round, best: { score: s.sim.score, round: s.tower.round }, isNew: s.sim.score > 0 };
        if (e.type === 'FLAP') triggerFeel(feel, { kind: 'FLAP', tick: renderTick, duration: 5, strength: .32, priority: 1, x: playerX, y: playerTop, space: 'PLAYER_CENTER' });
        if (e.type === 'RING') {
          const ring = e.gold ? contentBefore.goldRing : contentBefore.rings.find((x) => x.id === e.ringId);
          triggerFeel(feel, { kind: e.gold ? 'RING_GREEN' : 'RING', tick: renderTick, duration: 22, strength: .92, priority: 3, x: ring?.center[0] ?? playerX, y: ring?.center[1] ?? playerTop, space: ring ? 'WORLD' : 'PLAYER_CENTER' });
        }
        if (e.type === 'JOUST_CLASH' && (e.a === 0 || e.b === 0)) triggerFeel(feel, { kind: 'CLASH', tick: renderTick, duration: 8, shake: 5, strength: .9, priority: 4, x: playerX, y: playerTop, space: 'PLAYER_CENTER' });
        if (e.type === 'JOUST_WIN') triggerFeel(feel, { kind: 'JOUST_WIN', tick: renderTick, duration: 14, shake: 8, strength: 1.35, priority: 5, x: playerX, y: playerTop, space: 'PLAYER_CENTER' });
        if (e.type === 'PLAYER_DEATH') triggerFeel(feel, { kind: 'DEATH', tick: renderTick, duration: 18, shake: 11, strength: 1.45, priority: 6, x: Math.floor(prevPlayer.x / 256) + 14, y: Math.floor(prevPlayer.y / 256), space: 'PLAYER_CENTER' });
      }
      if (!wasGrounded && s.player.groundedPlatformId && !r.events.some((e) => e.type === 'PLAYER_DEATH'))
        triggerFeel(feel, { kind: 'LAND', tick: renderTick, duration: 7, shake: 3, strength: .58, priority: 2, x: playerX, y: playerTop, space: 'PLAYER_FEET' });
      // render
      renderTick += 1;
      moonPhase = (moonPhase + MOON_TURN_PER_TICK) % 1;
      const view = { state: s, prev: null, prevPlayer: null, alpha: 1, renderTick, screen: 'GAME', banner, popups,
        gameOverItems: ['NEW RUN', 'TITLE'], gameOverIndex: 0, gameOverInfo, musicDrive: null,
        content: towerContent(s), ascent: camera.resolve(s), feel: sampleFeelState(feel, renderTick) };
      buildScene(sc, view);
      hashes[t] = fnvInts(sc.list);
      if (wantLists.has(t)) lists[t] = sc.list.map((it) => [it.x, it.y, it.w, it.h, it.sx, it.sy, it.sw, it.sh, it.z, it.flags | 0]);
      if (want.has(t)) {
        if (sc.atlasDirty) { sc.atlasDirty = false; renderer.markAtlasDirty(); }
        renderer.setInstances(sc.list);
        const out = {};
        for (const quality of opts.qualities || [2]) {
          renderer.setQuality(quality);
          renderer.frame(renderTick, { ambientTick: renderTick, cyan: 1.02, lava: 1.02, violet: 0.96,
            impact: Math.max(banner && banner.until > renderTick ? 1 : 0, view.feel.impact || 0), beat: 0, motion: true, bloomBeat: 0, moonPhase });
          await renderer.device.queue.onSubmittedWorkDone();
          out['q' + quality] = await readTexture(renderer.device, offscreen.texture);
          if (opts.scene && !out.scene) out.scene = { w: 768, h: 1152, p: await renderer.readScene3x() };
        }
        out.view = { renderTick, cameraTop: view.ascent.cameraTop, moonPhase, banner: banner && banner.until > renderTick ? banner.text : null,
          impact: Math.max(banner && banner.until > renderTick ? 1 : 0, view.feel.impact || 0) };
        captures[t] = out;
      }
      if (s.sim.shell === 'GAMEOVER') { hashes.fill(0, t + 1); break; }
    }
    return { header, hashes, captures, lists, ticks: ticks.length };
  };
  log('ready');
} catch (e) {
  ref.error = String(e && e.stack || e);
  log('ERROR ' + ref.error);
}
