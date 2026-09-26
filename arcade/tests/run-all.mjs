// STRUTHIO ARCADE · runs the whole test suite: node tests/run-all.mjs
import { spawnSync } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const here = path.dirname(fileURLToPath(import.meta.url));
const suites = ['tower-rings.mjs', 'tower-report.mjs', 'save.mjs', 'parity.mjs', 'tower-sim.mjs'];
let failed = 0;
for (const f of suites) {
  const t0 = Date.now();
  const r = spawnSync(process.execPath, [path.join(here, f)], { stdio: 'inherit' });
  console.log(`--- ${f}: ${r.status === 0 ? 'PASS' : 'FAIL'} (${((Date.now() - t0) / 1000).toFixed(0)} s)\n`);
  if (r.status !== 0) failed++;
}
console.log(failed ? `${failed} suite(s) failed` : 'ALL SUITES PASS');
process.exitCode = failed ? 1 : 0;
