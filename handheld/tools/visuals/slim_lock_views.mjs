// STRUTHIO ONE SLIM · the design-lock views: the finished unit from every side, plus the inside, exploded and colours.
//   node slim_lock_views.mjs OUT_DIR            (serve the studio folder on 127.0.0.1:8765 first)
let pw;
try { pw = await import('playwright'); } catch { pw = await import('/opt/node22/lib/node_modules/playwright/index.mjs'); }
const { chromium } = pw;
const out = process.argv[2];
const D = (x, y, z) => `view=dir&dx=${x}&dy=${y}&dz=${z}`;
const VIEWS = [   // name, label, query (world: +z = the face, -x = the player's left, +y = the USB-C end)
  ['01_front', 'Front', D(0, 0, 1)],
  ['02_back', 'Back', D(0, 0, -1)],
  ['03_left', 'Left side (power button)', D(-1, 0, 0)],
  ['04_right', 'Right side', D(1, 0, 0)],
  ['05_top', 'Top end (USB-C)', D(0, 1, 0)],
  ['06_bottom', 'Bottom end', D(0, -1, 0)],
  ['07_front_left', 'Front, from the left', D(-0.6, 0.35, 0.75)],
  ['08_front_right', 'Front, from the right', D(0.6, 0.35, 0.75)],
  ['09_front_low', 'Front, from below', D(0.45, -0.45, 0.8)],
  ['10_back_left', 'Back, from the left', D(-0.6, 0.3, -0.75)],
  ['11_back_right', 'Back, from the right', D(0.6, -0.3, -0.75)],
  ['12_edge', 'Edge on: how thin it looks', D(-0.95, 0.05, 0.3)],
  ['13_inside', 'Inside: front shell with the boards', 'view=inside'],
  ['14_exploded', 'Exploded', 'view=exploded'],
  ['17_controls', 'Close-up: the wings and the rocker', D(0.15, -0.35, 0.9) + '&ty=-53&zoom=2.6'],
  ['18_back_name', 'Close-up: the name on the back', D(0, -0.2, -1) + '&ty=-46&zoom=2.6'],
  ['19_left_keys', 'Close-up: power button and the RST / BOOT holes', D(-1, 0.12, 0.25) + '&ty=31&tx=-37&tz=-8&zoom=3.2'],
  ['15_graphite', 'Colour: graphite', 'view=hero&shell=graphite'],
  ['16_ivory', 'Colour: ivory', 'view=hero&shell=ivory'],
];
const b = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
for (const [name, label, query] of VIEWS) {
  const p = await b.newPage({ viewport: { width: 1400, height: 1400 } });
  p.on('pageerror', (e) => console.log('page exception:', e.message));
  const shell = query.includes('shell=') ? '' : '&shell=navy';
  await p.goto(`http://127.0.0.1:8765/one_studio.html?model=slim&${query}${shell}&w=1400&h=1400`);
  await p.waitForFunction('window.DONE === true', null, { timeout: 600000 });
  await p.screenshot({ path: `${out}/${name}.png` });
  await p.close(); console.log('wrote', name, '|', label);
}
await b.close();
