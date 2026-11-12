/* SW-002 inert shared views. No markup evaluation, arbitrary URLs or effects. */
'use strict';
window.SlateDeck=(()=>{
  let epoch=0,current=null,imageURL=null,saveTimer=null;
  const labels={object:'Object',sources:'Sources',evidence:'Evidence',review:'Review',pdf:'PDF page'};
  function el(tag,text='',className=''){const n=document.createElement(tag);n.textContent=text;n.className=className;return n;}
  function clear(all=false){epoch++;current=null;clearTimeout(saveTimer);if(imageURL)URL.revokeObjectURL(imageURL);imageURL=null;document.getElementById('deck-reader')?.replaceChildren();if(all)document.querySelectorAll('.deck-catalog').forEach(n=>n.replaceChildren());}
  function bird(className='slate-symbol'){
    const c=el('canvas','Graphite',className);c.width=530;c.height=468;c.setAttribute('role','img');c.setAttribute('aria-label','Graphite, the Struthio bird');
    const img=new Image();img.onload=()=>{const ctx=c.getContext('2d');ctx.save();ctx.translate(c.width,0);ctx.scale(-1,1);ctx.drawImage(img,98,146,265,234,0,0,c.width,c.height);ctx.restore();};img.src='/slate-sheet.png';return c;
  }
  async function render(parent,api){
    clear();const ticket=epoch;parent.append(el('p','Views reviewed on your ThinkPad and published specifically to this paired device. Refresh checks the current source and grant.','muted'));
    const list=await api.call('ledger.deck.list');if(ticket!==epoch)return;
    if(!list.windows.length){parent.append(el('p','No views published to this device. In desktop Object Glass, keep a view and choose Preview / share content. For a PDF, use Share page view.','empty'));return;}
    const catalog=el('div','','deck-catalog');catalog.setAttribute('aria-label','Published windows');parent.append(catalog);
    const reader=el('section','','deck-reader');reader.id='deck-reader';reader.setAttribute('aria-live','polite');parent.append(reader);
    for(const row of list.windows){
      const card=el('article','','card');card.append(el('h3',row.title||'View needs owner refresh'));
      if(row.state!=='AVAILABLE'){card.append(el('p','The source changed or is unavailable. Ask the desktop owner to refresh and publish again.','notice'));catalog.append(card);continue;}
      card.append(el('p',row.window_id,'mono'),el('p','Revision '+row.source_revision,'mono'));
      const buttons=el('div','','actions');card.append(buttons);
      for(const v of row.views){const b=el('button',labels[v.view]);b.dataset.deckView=v.view;b.dataset.windowId=row.window_id;b.onclick=()=>open(reader,api,{window_id:row.window_id,view:v.view,expected_revision:row.source_revision,content_sha256:v.content_sha256});buttons.append(b);}
      if(!row.views.length)card.append(el('p','Overview only. Reading content needs its own reviewed publication.','muted'));
      catalog.append(card);
    }
  }
  async function open(reader,api,args){
    clear();const ticket=epoch;current={...args};reader.replaceChildren(el('p','Checking original, revision and publication…','muted'));
    try{
      const r=await api.call('ledger.deck.read',args);if(ticket!==epoch)return;
      if(r.state!=='AVAILABLE')throw Error(r.summary||'View is unavailable.');
      const c=r.content;if(c.schema!=='arc.slate-view/1'||c.window_id!==args.window_id||c.view!==args.view||c.source_revision!==args.expected_revision||r.content_sha256!==args.content_sha256)throw Error('Source identity changed. Refresh the Window Deck.');
      reader.replaceChildren(el('h3',c.title),el('p',labels[c.view]+' · read-only · no source acceptance','badge'),el('p',c.notice,'muted'));
      const identity=el('details');identity.append(el('summary','Object, source and reviewed-content identity'),el('pre',JSON.stringify({window_id:c.window_id,object_id:c.object_id,source_revision:c.source_revision,content_sha256:r.content_sha256},null,2)));reader.append(identity);
      const bar=el('div','','actions');const zoom=el('select');zoom.setAttribute('aria-label','Shared view zoom');
      for(const value of [.5,.75,1,1.25,1.5,2,3]){const option=el('option',Math.round(value*100)+'%');option.value=String(value);zoom.append(option);}zoom.value=String(r.presentation.zoom);if(!zoom.value)zoom.value='1';bar.append(zoom);
      const close=el('button','Close view');close.onclick=()=>clear();bar.append(close);reader.append(bar);
      const viewport=el('div','','deck-viewport');viewport.tabIndex=0;viewport.setAttribute('role','region');viewport.setAttribute('aria-label','Shared '+labels[c.view]+' content');const content=el('div','','deck-content');viewport.append(content);reader.append(viewport);
      function scale(){content.className='deck-content zoom-'+Math.round(Number(zoom.value)*100)+(c.image?' has-image':'');}
      function save(){clearTimeout(saveTimer);saveTimer=setTimeout(async()=>{if(ticket!==epoch)return;try{await api.call('ledger.deck.present',{...args,presentation:{zoom:Number(zoom.value),scroll:Math.round(viewport.scrollTop)}});}catch(e){if(ticket===epoch){clear();reader.append(el('p','View closed: current publication could not be confirmed. Refresh before continuing.','notice'));api.error(e);}}},500);}
      zoom.onchange=()=>{scale();save();};viewport.addEventListener('scroll',save,{passive:true});scale();
      if(c.image){
        const status=el('p','Loading the checked page image…','muted');content.append(status);
        const img=el('img');img.alt='Original-bound physical PDF page';img.className='deck-page-image';content.append(img);
        const image=await api.call('ledger.deck.image',args);if(ticket!==epoch)return;
        if(image.state==='STALE'||image.type!=='image/png'||image.sha256!==c.image.sha256)throw Error('Page image is unavailable or changed.');
        const raw=Uint8Array.from(atob(image.image_b64),x=>x.charCodeAt(0));
        const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',raw)),x=>x.toString(16).padStart(2,'0')).join('');if(ticket!==epoch)return;
        if(hash!==image.sha256)throw Error('Page image integrity check failed.');
        imageURL=URL.createObjectURL(new Blob([raw],{type:'image/png'}));img.src=imageURL;status.remove();
      }
      for(const b of c.blocks){const block=el(b.collapsed?'details':'section','','deck-block');block.append(el(b.collapsed?'summary':'h4',b.title));if(b.truncated)block.append(el('p','Excerpt only: the complete source exceeds this bounded view.','notice'));block.append(el('pre',b.text));content.append(block);}
      viewport.scrollTop=r.presentation.scroll;reader.scrollIntoView({block:'start'});
    }catch(e){if(ticket!==epoch)return;clear(true);reader.replaceChildren(el('p','View unavailable. Refresh the deck or ask the desktop owner to review and publish again.','notice'));api.error(e);}
  }
  async function verify(api){
    if(!current)return;const ticket=epoch,args={...current};
    try{const r=await api.call('ledger.deck.read',args);if(ticket===epoch&&(r.state!=='AVAILABLE'||r.content_sha256!==args.content_sha256))throw Error('Published view changed. Refresh to continue.');}
    catch(e){if(ticket===epoch){clear(true);api.error(e);}}
  }
  document.addEventListener('visibilitychange',()=>{if(document.hidden)clear(true);});
  return {render,clear,bird,verify};
})();
