// usage: node extract.js SCRIPT KEY... ; writes the builder prompt for each key to briefs/<release>_<KEY>.md
const fs=require('fs'); const [script,...keys]=process.argv.slice(2);
let src=fs.readFileSync(script,'utf8').replace(/^export const meta/m,'const meta');
const tag=script.includes('087')?'087':'086'; const out=__dirname;
const captured=[];
const agent=async(p,o)=>{captured.push([o.label,p]);return null};
const parallel=async(ts)=>Promise.all(ts.map(t=>t()));
const log=()=>{}; const phase=()=>{};
const args={phase:1, only:keys};
const PH=src.match(/const PHASES = \{[\s\S]*?\n\}|const PHASES = \{[^\n]*\}/)[0];
src=src.replace(/const keys = [^\n]*/, 'const keys = args.only');
(async()=>{ await eval('(async()=>{'+src+'})()');
 for(const [l,p] of captured){const k=l.split(':')[1]; if(l.startsWith('build:')) fs.writeFileSync(`${out}/${tag}_${k}.md`,p); console.log(tag,k,p.length);} })();
