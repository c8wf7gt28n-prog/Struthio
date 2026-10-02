// STRUTHIO ONE · the build manual's step pictures, from one_studio.html?view=step.
//   node one_steps.mjs OUT_DIR            (serve the studio folder on 127.0.0.1:8765 first)
// Each picture shows the parts fitted so far; the parts that step adds glow orange.
let pw;
try { pw = await import('playwright'); } catch { pw = await import('/opt/node22/lib/node_modules/playwright/index.mjs'); }
const { chromium } = pw;
const out = process.argv[2];
const FRONT = 'one_front';
const CAPS = 'one_wing_left,one_wing_right';            // (the engraving is on the far side in these views)
const ONE = 'ref_one,ref_switches';
const STEPS = [
  ['step02_wing_buttons', `show=${FRONT},${CAPS}&hl=${CAPS}&cam=inside`],
  ['step03_rocker', `show=${FRONT},${CAPS},one_rocker&hl=one_rocker&cam=inside`],
  ['step04_waveshare', `show=${FRONT},${CAPS},one_rocker,ref_waveshare&hl=ref_waveshare&cam=inside`],
  ['step05_one_board', `show=${FRONT},${CAPS},one_rocker,ref_waveshare,${ONE}&hl=${ONE}&cam=inside`],
  ['step06_battery', `show=${FRONT},${CAPS},one_rocker,ref_waveshare,${ONE},ref_battery&hl=ref_battery&cam=inside`],
  ['step07_foam', `show=${FRONT},${CAPS},one_rocker,ref_waveshare,${ONE},ref_battery,ref_foam&hl=ref_foam&cam=inside`],
  ['step08_speaker', `show=one_back,ref_speaker&hl=ref_speaker&cam=backshell`],
  ['step09_closed', `show=${FRONT},one_back,${CAPS},one_rocker&hl=one_back&cam=back`],
  ['step10_first_power', `show=${FRONT},one_back,${CAPS},ref_glyphs,one_rocker&cam=front`],
  ['step14_face_panel', `show=ref_panel,${FRONT},one_back,${CAPS},ref_glyphs,one_rocker&hl=&cam=front`],
];
const b = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
for (const [name, query] of STEPS) {
  const p = await b.newPage({ viewport: { width: 1000, height: 1250 } });
  p.on('pageerror', (e) => console.log('page exception:', e.message));
  await p.goto(`http://127.0.0.1:8765/one_studio.html?view=step&${query}&shell=navy&w=1000&h=1250`);
  await p.waitForFunction('window.DONE === true', null, { timeout: 600000 });
  await p.screenshot({ path: `${out}/${name}.png` });
  console.log('wrote', name);
  await p.close();
}
await b.close();
