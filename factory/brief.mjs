import{ROLE_LABELS}from '../console/palette-bridge.mjs';
export const FACTORY_VERSION='0.7';
export const QUESTIONS=Object.freeze([
{key:'title',group:'IDENTITY',q:'What is this Episode called?',help:'Working titles are fine. LOCK if the name must survive interpretation.',ph:'e.g. THE WINTER KING'},
{key:'setting',group:'WORLD',q:'Where does this Episode take place?',help:'Describe biome, culture or era, geography, and visual setting.',ph:'e.g. medieval conifer forest, frozen lakes, mountains'},
{key:'time_light',group:'WORLD',q:'What should the light and atmosphere feel like?',help:'Describe time, weather, sky, visibility, and environmental light.',ph:'e.g. moonlit winter night with aurora'},
{key:'mood',group:'DIRECTION',q:'What should the player feel?',help:'Use emotional direction rather than implementation instructions.',ph:'e.g. lonely, dangerous, beautiful, mythic'},
{key:'story',group:'STORY',q:'What kind of story should the Episode use?',help:'Name an inspiration, describe a plot direction, or leave it AUTO.',ph:'e.g. public-domain fairy tale; tragic but hopeful'},
{key:'backgrounds',group:'BACKGROUND',q:'What should dominate behind gameplay?',help:'Describe the world depth. The center flight corridor must remain readable.',ph:'e.g. distant mountains; conifers frame the sides'},
{key:'islands',group:'ISLANDS',q:'What should the playable islands look like?',help:'Describe material and character, not new mechanics.',ph:'e.g. frozen rock, snow caps, restrained old stone'},
{key:'characters',group:'CHARACTERS',q:'How should the world frame the permanent Console bird and rider?',help:'Do not author character sprites. Describe environmental contrast, lighting, and visual framing around the fixed Console cast.',ph:'e.g. cool quiet backgrounds that keep the red, bone, yellow, and cyan silhouettes clear'},
{key:'accent',group:'GAMEPLAY ACCENT',q:'How should the birds, rings, and FLAP accent work together?',help:'These colors are selected as one readability system against the environment. AUTO is recommended without a strong requirement.',ph:'e.g. coherent high-contrast cyan and bone accents'},
{key:'music',group:'AUDIO',q:'What is the musical direction?',help:'Describe style, energy, instrumentation, and emotional function.',ph:'e.g. cold medieval texture with arcade propulsion'},
{key:'forbidden',group:'RESTRICTIONS',q:'What must never appear?',help:'Use LOCK for absolute prohibitions.',ph:'e.g. no flags; no ornate castles'},
{key:'special',group:'DIRECTOR NOTE',q:'What else should the agent understand?',help:'Final creative note. It may guide interpretation but cannot override Console law.',ph:'e.g. ice should feel luminous, not simply blue'},
]);
export const CONSOLE_CONTRACT=Object.freeze({
schema:'STRUTHIO_EPISODE_PACK_API_V1',
console_api_version:1,
compatible_console_build:'STRUTHIO-CONSOLE-3.5.4',
ownership:{
console:['simulation','physics','jousting','AI','scoring','controls','camera','renderer','HUD','save protocol','PWA shell','192-pose full bird atlas with vertical-ascent bank','optional 32-state full Hero rider atlas','192-frame rider registration map','sprite-profile selection'],
episode:['identity','world art','environment palette','music','story','dialogue','cinema','title/manual/icon/share presentation'],
prohibited_episode_authority:['executable game logic','physics changes','AI implementation changes','control changes','collision algorithm changes','scoring algorithm changes','renderer modifications','episode-number conditionals'],
},
packaging:{
archive:'one ZIP using STORE or DEFLATE',
root:'<episode-id>/',
manifest:'episode.json',
paths:'cartridge-relative only; no absolute URLs or path escape',
integrity:'lowercase SHA-256 for every referenced asset',
output:'one ready-to-install cartridge ZIP; no loose production files',
},
identity:{
apiVersion:1,
id:'lowercase letters, numbers, and hyphens; 2–32 characters',
buildId:'immutable release identity; change when cartridge bytes or presentation records change',
saveNamespace:'unique struthio.console.<episode-id>.vN namespace',
},
assets:{
authority:'legacy presentation payload only; the Console ignores all cartridge mechanics and accepts only story/cinema/audio/palette/font records',
bird:{owner:'Console only',size:[1536,1152],grid:[16,12],frames:192,raster_cell:[96,96],logical_cell:[32,32],alpha:true,rule:'automatically supplied to every Slot A cartridge; legacy cartridge bird records are ignored'},
rider:{owner:'Console only',states:32,mapping:192,rule:'player-only presentation option; defaults off in Slot A; cartridges cannot replace it; enemies remain riderless'},
islands:{size:[1920,480],alpha:true,masters:{STANDARD:9,BOSS:5,GROUND:1},rule:'explicit metadata and signal rectangles; STORY mode only'},
backgrounds:{pairs:6,each_layer:[768,2304],rear:'opaque at 0.1×',near:'alpha at 0.5×',islands:'1× in front of both layers',rule:'STORY mode only'},
arcade:{owner:'Console only',rule:'Arcade is built into the Console (1.9): its world plates, island masters and palette ship in console-assets/arcade/ and are drawn whatever cartridge is mounted. A cartridge supplies Story/Campaign world art only; do not author Arcade art.'},
cinemaPanels:{size:[4096,2048],alpha:false},
theaterReel:'valid authored gameplay/cinema reel JSON',
startScreen:{size:[941,1672],alpha:false,safe_zone:'keep the essential subject and action inside the central 75–80% horizontally and below the top ~40% (the Console title drawer covers the top of the art); the bottom band sits above the wing deck and is not guaranteed visible'},
manual:{size:[838,1774],alpha:false},
icons:{icon192:[192,192],icon512:[512,512],appleTouchIcon:[180,180],shareCard:[1200,630]},
audio:'optional authored loop with declared presentation BPM',
},
presentation_law:{
layer_order_back_to_front:['rear background','near background','islands','hazards/rings/rivals/eggs','player','HUD/overlay'],
palette:'environment, gameplay ring color, and FLAP accent are selected around the fixed Console bird/rider palette; none may clash or disappear',
red:'danger/alarm only unless a validated episode palette preserves gameplay readability',
motion:'reduced-motion preferences never disable gameplay or moving geometry',
shell_palette:{
field:'presentation.shellPalette (optional)',
roles:ROLE_LABELS.shell,
format:'#RRGGBB per role',
rule:'text and secondary text on background ink, and text on panel graphite, need 4.5:1; accent, action edge and danger on ink need 3:1; any failing or malformed role falls back to Console identity',
},
controller_palette:{
field:'presentation.controllerPalette (optional)',
roles:ROLE_LABELS.controller,
format:'#RRGGBB per role',
rule:'each must reach 3:1 against the effective shell ink; colours only, never geometry, timing or hit regions',
},
},
acceptance:['schema validation','all paths present','all SHA-256 values match','all declared image dimensions match','empty Console remains bootable','cartridge installs without Console source edits','offline relaunch after installation'],
});
const normalizedAnswer=(answer={})=>{
const mode=['LOCK','GUIDE','AUTO'].includes(answer.mode)?answer.mode:'AUTO';
const value=typeof answer.value==='string'&&answer.value.trim()?answer.value.trim():null;
return{mode:mode==='GUIDE'&&!value?'AUTO':mode,value};
};
export function buildBrief(answers={}){
const creative={};
for (const question of QUESTIONS) creative[question.key]=normalizedAnswer(answers[question.key]);
return{
schema:'STRUTHIO_EPISODE_BRIEF_0.7',
factory_version:FACTORY_VERSION,
status:'CONSOLE_API_V1_READY',
creative_intent:creative,
console_contract:CONSOLE_CONTRACT,
production_sequence:['interpret director brief','produce one coherent proposal','wait for director approval','generate and assemble assets','validate Episode Pack API v1','return one installable cartridge ZIP'],
};
}
export function episodeStem(answers={}){
const raw=normalizedAnswer(answers.title).value||'UNTITLED_EPISODE';
return raw.normalize('NFKD').replace(/[^a-zA-Z0-9]+/g,'_').replace(/^_+|_+$/g,'').toUpperCase().slice(0,48)||'UNTITLED_EPISODE';
}
export function briefFilename(answers={}){
return `STRUTHIO_${episodeStem(answers)}_FACTORY_BRIEF_0.7.json`;
}
export function productionHandoff(answers={}){
return `STRUTHIO EPISODE FACTORY — PRODUCTION HANDOFF

Act as the STRUTHIO Episode production agent.

LOCK = mandatory owner authority.
GUIDE = creative direction with room for expert execution.
AUTO = make the strongest compatible choice.

The Console supplies the game. The Episode supplies the world.
Do not modify Console-owned systems, add executable Episode logic, create Episode-number conditionals, or redesign gameplay, controls, HUD, enemies, missions, scoring, physics, AI, collision, or the renderer.

WORKFLOW
1. Read the complete Director Brief and Console API v1 contract below.
2. First return one coherent Episode design proposal for director review.
3. Do not begin final asset production until the director explicitly approves that proposal.
4. After approval, generate, assemble, hash, and validate the complete cartridge.
5. Return exactly one ready-to-install ZIP containing one cartridge root and one episode.json, plus a short validation summary. Do not return loose production files as the final deliverable.

DIRECTOR BRIEF AND MANUFACTURING CONTRACT
${JSON.stringify(buildBrief(answers),null,2)}`;
}
