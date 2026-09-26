import{QUESTIONS,buildBrief,briefFilename,productionHandoff}from './brief.mjs';
import{inspectCartridgeZip}from '../console/cartridge-installer.mjs';
import{validateEpisodePack,episodePaletteReport}from '../console/episode-loader.mjs';
import{installViewportShim}from '../console/viewport-shim.mjs';
const viewportShim=installViewportShim({disabled:new URLSearchParams(location.search).get('shim')==='off'});
const LAST_STEP=QUESTIONS.length-1;
const KEY='struthioFactory07';
const LEGACY_KEY='struthioFactory06';
let state={answers:{},step:0};
const $=(id)=>document.getElementById(id);
function save(){
try{localStorage.setItem(KEY,JSON.stringify(state));}catch{}
}
function load(){
try{
const stored=localStorage.getItem(KEY)||localStorage.getItem(LEGACY_KEY);
const parsed=stored&&JSON.parse(stored);
if (parsed?.answers&&typeof parsed.answers==='object') state={answers:parsed.answers,step:Number.isInteger(parsed.step)?Math.max(0,Math.min(LAST_STEP,parsed.step)):0};
}catch{}
}
function show(id){
document.querySelectorAll('.screen').forEach((screen)=>screen.classList.toggle('active',screen.id===id));
}
const current=()=>QUESTIONS[state.step];
const answerFor=(question)=>state.answers[question.key]||{mode:'GUIDE',value:''};
function persist(){
const question=current(),old=answerFor(question);
state.answers[question.key]={mode:old.mode||'GUIDE',value:$('answer').value.trim()};
save();
}
function render(){
show('wizard');
const question=current(),answer=answerFor(question);
$('stepNo').textContent=String(state.step+1).padStart(2,'0')+' / '+QUESTIONS.length;
$('stepGroup').textContent=question.group;
$('question').textContent=question.q;
$('help').textContent=question.help;
$('answer').placeholder=question.ph;
$('answer').value=answer.value||'';
document.querySelectorAll('[data-mode]').forEach((button)=>button.classList.toggle('selected',button.dataset.mode===(answer.mode||'GUIDE')));
$('answer').disabled=answer.mode==='AUTO';
$('answer').style.opacity=answer.mode==='AUTO'?'.35':'1';
$('bar').style.width=((state.step+1)/QUESTIONS.length*100)+'%';
$('backBtn').style.visibility=state.step?'visible':'hidden';
}
function normalizeBlank(){
const question=current(),answer=answerFor(question);
if (answer.mode==='LOCK'&&!answer.value){
$('wizardStatus').textContent='LOCK REQUIRES AN ANSWER.';
$('answer').focus();
return false;
}
if (answer.mode==='GUIDE'&&!answer.value) state.answers[question.key]={mode:'AUTO',value:''};
$('wizardStatus').textContent='';
save();
return true;
}
function renderReview(){
show('review');
const brief=buildBrief(state.answers),values=Object.values(brief.creative_intent);
$('lockCount').textContent=values.filter((entry)=>entry.mode==='LOCK').length;
$('guideCount').textContent=values.filter((entry)=>entry.mode==='GUIDE').length;
$('autoCount').textContent=values.filter((entry)=>entry.mode==='AUTO').length;
const locked=QUESTIONS.filter((question)=>brief.creative_intent[question.key].mode==='LOCK');
const guided=QUESTIONS.filter((question)=>brief.creative_intent[question.key].mode==='GUIDE');
const picks=[...locked,...guided].slice(0,3);
$('reviewFocusText').textContent=picks.length
?picks.map((question)=>`${question.group}: ${brief.creative_intent[question.key].value}`).join('\n')
:'All creative decisions are delegated to AUTO.';
}
async function copyText(text){
try{await navigator.clipboard.writeText(text);return true;}
catch{
const area=document.createElement('textarea');
area.value=text;
area.style.position='fixed';area.style.opacity='0';
document.body.appendChild(area);area.select();
let ok=false;
try{ok=document.execCommand('copy');}catch{}
area.remove();
return ok;
}
}
function briefFile(){
return new File([JSON.stringify(buildBrief(state.answers),null,2)+'\n'],briefFilename(state.answers),{type:'application/json'});
}
function downloadBrief(){
const file=briefFile(),url=URL.createObjectURL(file),anchor=document.createElement('a');
anchor.href=url;anchor.download=file.name;
document.body.appendChild(anchor);anchor.click();anchor.remove();
setTimeout(()=>URL.revokeObjectURL(url),1000);
$('handoffStatus').textContent='DIRECTOR BRIEF DOWNLOADED.';
}
async function shareBrief(){
const file=briefFile();
if (navigator.canShare?.({files:[file]})){
try{
await navigator.share({title:'STRUTHIO Episode Factory Brief',text:'Open this production brief in ChatGPT and follow its Console API v1 workflow.',files:[file]});
$('handoffStatus').textContent='BRIEF SHARED. SELECT CHATGPT IN THE SHARE SHEET.';
return;
}catch (error){
if (error?.name==='AbortError'){$('handoffStatus').textContent='SHARE CANCELLED.';return;}
}
}
const copied=await copyText(productionHandoff(state.answers));
$('handoffStatus').textContent=copied?'HANDOFF COPIED. OPEN CHATGPT AND PASTE.':'SHARE UNAVAILABLE. USE DOWNLOAD BRIEF.';
}
async function openChatGpt(){
const target=window.open('https://chatgpt.com/','_blank');
const copied=await copyText(productionHandoff(state.answers));
if (!copied){
target?.close?.();
$('handoffStatus').textContent='COPY FAILED. USE SHARE OR DOWNLOAD BRIEF.';
return;
}
$('handoffStatus').textContent='PRODUCTION HANDOFF COPIED. PASTE IT INTO CHATGPT.';
if (!target) location.href='https://chatgpt.com/';
}
function returnToInstaller(){
location.href=new URL('../?cartridge=install&from=factory',location.href).href;
}
document.querySelectorAll('[data-mode]').forEach((button)=>{
button.addEventListener('click',()=>{
const question=current(),old=answerFor(question);
state.answers[question.key]={mode:button.dataset.mode,value:button.dataset.mode==='AUTO'?'':(old.value||$('answer').value)};
save();render();
});
});
$('answer').addEventListener('input',persist);
$('newBtn').addEventListener('click',()=>{state={answers:{},step:0};save();render();});
$('continueBtn').addEventListener('click',()=>{load();render();});
$('installReadyBtn').addEventListener('click',returnToInstaller);
$('nextBtn').addEventListener('click',()=>{persist();if (!normalizeBlank()) return;if (state.step<LAST_STEP){state.step++;save();render();}else renderReview();});
$('backBtn').addEventListener('click',()=>{persist();if (state.step>0){state.step--;save();render();}});
$('reviewBackBtn').addEventListener('click',()=>{state.step=LAST_STEP;save();render();});
$('reviewNextBtn').addEventListener('click',()=>{show('publish');$('handoffStatus').textContent='';});
$('publishBackBtn').addEventListener('click',renderReview);
$('shareBtn').addEventListener('click',shareBrief);
$('publishBtn').addEventListener('click',openChatGpt);
$('downloadBtn').addEventListener('click',downloadBrief);
$('consoleBtn').addEventListener('click',returnToInstaller);
export async function selfTestCartridge(source){
try{
const inspected=await inspectCartridgeZip(source,{validateManifest:validateEpisodePack});
const palette=episodePaletteReport(inspected.manifest);
return{ok:true,id:inspected.manifest.id,title:inspected.manifest.title,buildId:inspected.manifest.buildId,assets:inspected.assetCount,installedBytes:inspected.installedBytes,paletteFallbacks:palette.rejected};
}catch (error){
return{ok:false,error:String(error?.message||error)};
}
}
$('checkZipBtn').addEventListener('click',()=>{$('checkZipFile').value='';$('checkZipFile').click();});
$('checkZipFile').addEventListener('change',async ()=>{
const file=$('checkZipFile').files?.[0];
if (!file) return;
$('checkZipStatus').textContent=`CHECKING ${file.name}…`;
const r=await selfTestCartridge(file);
$('checkZipStatus').textContent=r.ok
?`PASS · SLOT A WILL ACCEPT “${r.title}” (${r.buildId}) · ${r.assets} ASSETS · ${(r.installedBytes/1048576).toFixed(1)} MB${r.paletteFallbacks.length?` · ${r.paletteFallbacks.length} PALETTE ROLE(S) WILL FALL BACK`:''}`
:`FAIL · SLOT A WOULD REJECT THIS ZIP · ${r.error}`;
});
load();
if (Object.keys(state.answers).length) $('continueBtn').textContent='CONTINUE DRAFT';
if ('serviceWorker' in navigator) navigator.serviceWorker.register('../sw.js',{scope:'../'}).catch(()=>{});
window.__struthioFactory={buildBrief:()=>buildBrief(state.answers),productionHandoff:()=>productionHandoff(state.answers),selfTestCartridge,lastStep:LAST_STEP,get viewportShim(){return viewportShim.report;}};
