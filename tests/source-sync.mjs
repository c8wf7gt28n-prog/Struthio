// The Game Source viewer must carry the shipped tower module verbatim and the
// shipped build id.
import fs from 'node:fs';
import path from 'node:path';
import { ROOT } from './harness.mjs';
const app = fs.readFileSync(path.join(ROOT, 'app.mjs'), 'utf8');
const txt = fs.readFileSync(path.join(ROOT, 'source/game-source.txt'), 'utf8');
let bad = 0;
const a = app.indexOf('__modules[42]=(()=>{'), b = app.indexOf('})();', a) + 5;
const parts = app.slice(a, b).replace('__modules[42]=(()=>{', '').split('const{px,mod}=__modules[4];');
if (parts.length !== 2 || !parts.every((part) => txt.includes(part))) { console.log('game-source.txt: tower module is out of date'); bad++; }
const build = /BUILD_ID='([^']+)'/.exec(app)[1];
if (!txt.includes(`Build ${build}`) || !txt.includes(`'${build}'`)) { console.log('game-source.txt: build id is out of date'); bad++; }
for (const f of ['sw.js', 'index.html', 'console.json']) if (!fs.readFileSync(path.join(ROOT, f), 'utf8').includes(build)) { console.log(`${f}: build id is not ${build}`); bad++; }
console.log(bad ? `SOURCE SYNC FAILURES: ${bad}` : `source sync: ${build} everywhere, tower module mirrored`);
process.exitCode = bad ? 1 : 0;
