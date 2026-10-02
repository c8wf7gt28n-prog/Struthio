// STRUTHIO ONE SLIM · the build manual's step pictures and the assembly animation, from one_studio.html?model=slim.
//   node slim_steps.mjs OUT_DIR            (serve the studio folder on 127.0.0.1:8765 first)
// Each picture shows the parts fitted so far; the parts that step adds glow orange.
// anim/frame_NN.png: the exploded view closing up (tools/visuals/make_gif.py turns them into a GIF).
let pw;
try { pw = await import('playwright'); } catch { pw = await import('/opt/node22/lib/node_modules/playwright/index.mjs'); }
const { chromium } = pw;
const out = process.argv[2];
const FRONT = 'one_front', CAPS = 'one_wing_left,one_wing_right', ROCK = 'one_rocker', BTN = 'power_button';
const ONE = 'ref_one,ref_switches';
const STEPS = [
  ['s01_wing_buttons', `show=${FRONT},${CAPS}&hl=${CAPS}&cam=inside`],
  ['s02_rocker', `show=${FRONT},${CAPS},${ROCK}&hl=${ROCK}&cam=inside`],
  ['s03_power_button', `show=${FRONT},${CAPS},${ROCK},${BTN}&hl=${BTN}&cam=inside`],
  ['s04_waveshare', `show=${FRONT},${CAPS},${ROCK},${BTN},ref_waveshare&hl=ref_waveshare&cam=inside`],
  ['s05_board', `show=${ONE}&hl=ref_switches&cam=front&screen=0`],
  ['s06_one_slim', `show=${FRONT},${CAPS},${ROCK},${BTN},ref_waveshare,${ONE}&hl=${ONE}&cam=inside`],
  ['s07_back_shell', `show=one_back,ref_speaker,ref_battery,ref_foam&hl=ref_speaker,ref_battery,ref_foam&cam=backshell`],
  ['s08_closed', `show=${FRONT},one_back,${CAPS},${ROCK},${BTN},ref_screws&hl=one_back,ref_screws&cam=back`],
  ['s09_first_power', `show=${FRONT},one_back,${CAPS},ref_glyphs,${ROCK},${BTN}&cam=front`],
  ['s10_panel', `show=ref_panel,${FRONT},one_back,${CAPS},ref_glyphs,${ROCK},${BTN}&hl=ref_panel&cam=front`],
];
const b = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
async function shot(path, query, w, h) {
  const p = await b.newPage({ viewport: { width: w, height: h } });
  p.on('pageerror', (e) => console.log('page exception:', e.message));
  await p.goto(`http://127.0.0.1:8765/one_studio.html?model=slim&${query}&shell=navy&w=${w}&h=${h}`);
  await p.waitForFunction('window.DONE === true', null, { timeout: 600000 });
  await p.screenshot({ path });
  await p.close();
}
const ONLY = process.env.ONLY;
for (const [name, query] of STEPS) {
  if (ONLY && name !== ONLY) continue; await shot(`${out}/${name}.png`, `view=step&${query}`, 1000, 1250); console.log('wrote', name); }
const N = ONLY ? 0 : +(process.env.FRAMES || 16);
for (let i = 0; i < N; i++) {
  const k = 1 - i / (N - 1);                                   // apart -> together
  await shot(`${out}/anim/frame_${String(i).padStart(2, '0')}.png`, `view=exploded&explode=${k.toFixed(3)}`, 800, 600);
}
console.log('wrote', N, 'animation frames');
await b.close();
