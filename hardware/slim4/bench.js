/* STRUTHIO Studio · BENCH layer: SYSTEMS, BENCH and DOCS tabs, and the offline status.
   Additive, like eye.js: it reads the studio through window.STRUDIO and window.STRUDIO_EYE and never edits geometry
   or loaded files.
   - SYSTEMS colours or isolates the board by function. The assignment is model.systems / part.system /
     model.netSystems, written and checked by CHECKS/build_pcb_viewer_data.py, not guessed here.
   - BENCH records one board's bring-up, step by step, against LAYERS/01_PCB/BRINGUP_PROCEDURE.md (bench-data.js,
     written by CHECKS/build_bench_data.py). Records are what the person enters: the studio does not talk to the board.
     They stay in this browser (localStorage) until exported.
   - DOCS searches and shows the current package documents (also in bench-data.js), so they work offline. */
(() => {
  'use strict';
  const S = window.STRUDIO, B = window.STRUTHIO_BENCH;
  if (!S || !B) return;
  const $ = s => document.querySelector(s);
  const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const M = S.model();
  const PROC = B.procedure, STEPS = PROC.phases.flatMap(p => p.steps.map(s => ({ ...s, phase: p.id })));
  const STEP = Object.fromEntries(STEPS.map(s => [s.id, s]));
  const PARTREFS = new Set((M.parts || []).map(p => p.ref));
  const eye = () => window.STRUDIO_EYE;

  /* ---------- SYSTEMS ---------- */
  const SYS = M.systems || {}, NETSYS = M.netSystems || {};
  const sysParts = k => (M.parts || []).filter(p => p.system === k);
  const sysLen = k => (M.segments || []).filter(s => NETSYS[s.netName] === k).reduce((a, s) => a + Math.hypot(s.x2 - s.x1, s.y2 - s.y1), 0);
  let sysKey = 'all', sysColour = false;
  function renderSystems() {
    const el = $('#paneSystems'); if (!el) return;
    if (!Object.keys(SYS).length) { el.innerHTML = '<div class="empty">This model has no system map. Rebuild it with CHECKS/build_pcb_viewer_data.py.</div>'; return; }
    const rows = Object.entries(SYS).map(([k, v]) => {
      const parts = sysParts(k), nets = Object.values(NETSYS).filter(x => x === k).length;
      const ics = parts.filter(p => ['ic', 'connector', 'switch'].includes(p.category)).map(p => p.ref).join(' ');
      return `<button class="sysRow${sysKey === k ? ' on' : ''}" data-sys="${k}" style="--sc:${esc(v.color)}"><i aria-hidden="true"></i><b>${esc(v.label)}</b>`
        + `<span>${parts.length} parts · ${nets} nets · ${sysLen(k).toFixed(0)} mm of track${ics ? ' · ' + esc(ics) : ''}</span><small>${esc(v.what || '')}</small></button>`;
    }).join('');
    el.innerHTML = `<p class="lead">Colour the board by function, or tap a system to show only its parts and copper (the rest of the copper is dimmed). From the board's own nets; the table is in CHECKS/build_pcb_viewer_data.py.</p>`
      + `<div class="sendRow"><button type="button" class="go" id="sysAll">${sysKey === 'all' ? 'ALL SYSTEMS' : 'SHOW ALL'}</button>`
      + `<label class="benchToggle"><input type="checkbox" id="sysColour"${sysColour ? ' checked' : ''}> COLOUR BY SYSTEM</label></div>`
      + `<div class="sysList">${rows}</div>`;
    el.querySelectorAll('[data-sys]').forEach(b => b.addEventListener('click', () => setSystem(sysKey === b.dataset.sys ? 'all' : b.dataset.sys)));
    $('#sysAll').addEventListener('click', () => setSystem('all'));
    $('#sysColour').addEventListener('change', e => { sysColour = e.target.checked; S.setSystemColor(sysColour); });
  }
  function setSystem(k) {
    sysKey = SYS[k] ? k : 'all'; S.setSystem(sysKey);
    const chip = $('#sysChip');
    if (chip) { chip.hidden = sysKey === 'all'; if (sysKey !== 'all') { chip.textContent = SYS[sysKey].label + ' ×'; chip.style.setProperty('--sc', SYS[sysKey].color); } }
    renderSystems();
  }

  /* ---------- BENCH: bring-up records ---------- */
  const KEY = 'struthio-bench-v1';
  const FIELDS = [['serial', 'BOARD SERIAL'], ['date', 'DATE'], ['operator', 'OPERATOR'], ['firmware', 'FIRMWARE'], ['notes', 'BOARD NOTES']];
  let store = { schema: 1, records: [], active: null }, saved = true;
  function load() {
    try { const raw = localStorage.getItem(KEY); if (raw) store = validate(JSON.parse(raw)); } catch (_) { saved = false; }
  }
  function validate(raw) {
    if (!raw || raw.schema !== 1 || !Array.isArray(raw.records) || raw.records.length > 200) throw Error('not a STRUTHIO bench file');
    const out = { schema: 1, records: [], active: null };
    for (const r of raw.records) {
      if (!r || typeof r.id !== 'string' || typeof r.fields !== 'object' || typeof r.results !== 'object') throw Error('bad record');
      const rec = { id: r.id.slice(0, 40), procedure: String(r.procedure || '').slice(0, 64), created: String(r.created || '').slice(0, 30), fields: {}, results: {} };
      for (const [k] of FIELDS) rec.fields[k] = String(r.fields[k] || '').slice(0, 2000);
      for (const [id, v] of Object.entries(r.results)) {
        if (!/^[A-H]\d{1,2}$/.test(id) || !v) continue;
        rec.results[id] = { status: ['pass', 'fail', 'skip'].includes(v.status) ? v.status : '', value: String(v.value || '').slice(0, 300), note: String(v.note || '').slice(0, 2000), at: String(v.at || '').slice(0, 30) };
      }
      out.records.push(rec);
    }
    out.active = out.records.some(r => r.id === raw.active) ? raw.active : (out.records[0] || {}).id || null;
    return out;
  }
  function persist() {
    try { localStorage.setItem(KEY, JSON.stringify(store)); saved = true; } catch (_) { saved = false; }
    const s = $('#benchSaved'); if (s) { s.textContent = saved ? 'Saved in this browser. Export a copy before clearing site data or changing phone.' : 'NOT SAVED: this browser refused storage. Export now.'; s.classList.toggle('bad', !saved); }
  }
  const rec = () => store.records.find(r => r.id === store.active) || null;
  function newRecord(serial) {
    const id = 'B' + Date.now().toString(36).toUpperCase();
    const r = { id, procedure: PROC.sha256, created: new Date().toISOString(), fields: { serial: serial || '', date: new Date().toISOString().slice(0, 10), operator: '', firmware: 'R12 (0.11.0)', notes: '' }, results: {} };
    store.records.unshift(r); store.active = id; persist(); renderBench();
  }
  function tally(r, phase) {
    const t = { pass: 0, fail: 0, skip: 0, open: 0 };
    for (const s of STEPS) { if (phase && s.phase !== phase) continue; const st = (r && r.results[s.id] || {}).status; t[st || 'open']++; }
    return t;
  }
  const refsIn = text => [...new Set((String(text).match(/\b[A-Z]{1,2}\d{1,3}\b/g) || []).filter(x => PARTREFS.has(x)))];
  function md(text) { return esc(text).replace(/`([^`]+)`/g, '<code>$1</code>').replace(/\*\*([^*]+)\*\*/g, '<b>$1</b>'); }
  let openPhase = null;
  function renderBench() {
    const el = $('#paneBench'); if (!el) return;
    const r = rec();
    const head = `<p class="lead">${esc(PROC.title)}: ${STEPS.length} steps in ${PROC.phases.length} phases. Record what you measure on each board; a FAIL shows what the reading means. Nothing here talks to the board.</p>`;
    const pick = store.records.length ? `<select id="benchPick" aria-label="Board record">${store.records.map(x => `<option value="${esc(x.id)}"${x.id === store.active ? ' selected' : ''}>${esc(x.fields.serial || 'Board without serial')} · ${esc(x.fields.date || '')}</option>`).join('')}</select>` : '';
    const add = `<div class="benchAdd"><input id="benchSerial" type="text" autocomplete="off" autocapitalize="characters" spellcheck="false" placeholder="Serial, e.g. SLIM4-R27-001" aria-label="New board serial"><button type="button" class="go" id="benchNew">NEW BOARD</button></div>`;
    if (!r) { el.innerHTML = head + add + `<div class="empty">No board recorded yet. Give the first board a serial and start with phase A, which needs no board.</div>` + tools(); wire(el); return; }
    const t = tally(r), done = t.pass + t.fail + t.skip;
    const stale = r.procedure && r.procedure !== PROC.sha256 ? `<div class="benchWarn">The bring-up procedure has changed since this record was started (${esc(r.procedure.slice(0, 8))} → ${esc(PROC.sha256.slice(0, 8))}). Steps may have moved; check before relying on old rows.</div>` : '';
    const fields = FIELDS.map(([k, l]) => k === 'notes'
      ? `<label class="fld">${l}<textarea data-f="${k}" rows="2">${esc(r.fields[k])}</textarea></label>`
      : `<label class="fld benchHalf">${l}<input data-f="${k}" type="${k === 'date' ? 'date' : 'text'}" value="${esc(r.fields[k])}" autocomplete="off"></label>`).join('');
    const bar = ['pass', 'fail', 'skip'].map(k => t[k] ? `<i class="${k}" style="flex:${t[k]}"></i>` : '').join('') + (t.open ? `<i class="open" style="flex:${t.open}"></i>` : '');
    const phases = PROC.phases.map(p => {
      const pt = tally(r, p.id), isOpen = openPhase === p.id;
      const steps = p.steps.map(s => {
        const v = r.results[s.id] || {}, refs = refsIn(s.probe);
        return `<div class="step ${v.status || ''}" data-step="${s.id}"><div class="stepHead"><b>${s.id}</b><span>${md(s.probe)}</span></div>`
          + `<div class="stepExp"><small>EXPECTED</small> ${md(s.expected)}</div>`
          + (v.status === 'fail' ? `<div class="stepWrong"><small>WRONG MEANS</small> ${md(s.wrong)}</div>` : '')
          + `<div class="stepAct"><button type="button" data-st="pass" class="${v.status === 'pass' ? 'on' : ''}">PASS</button><button type="button" data-st="fail" class="${v.status === 'fail' ? 'on' : ''}">FAIL</button><button type="button" data-st="skip" class="${v.status === 'skip' ? 'on' : ''}">SKIP</button>`
          + (refs.length ? `<button type="button" class="see" data-refs="${refs.join(' ')}" title="Show ${esc(refs.join(', '))} on the board">SEE ${esc(refs.slice(0, 3).join(' '))}${refs.length > 3 ? '…' : ''}</button>` : '') + `</div>`
          + `<input class="stepVal" data-v="value" type="text" value="${esc(v.value)}" placeholder="Reading, e.g. 3.31 V" autocomplete="off" aria-label="Reading for ${s.id}">`
          + `<input class="stepVal" data-v="note" type="text" value="${esc(v.note)}" placeholder="Note" autocomplete="off" aria-label="Note for ${s.id}"></div>`;
      }).join('');
      return `<details class="phase"${isOpen ? ' open' : ''} data-phase="${p.id}"><summary><b>${p.id}</b><span>${esc(p.title)}</span><em>${pt.pass}/${p.steps.length}${pt.fail ? ` · <u>${pt.fail} FAIL</u>` : ''}</em></summary>`
        + (p.note ? `<p class="phaseNote">${md(p.note)}</p>` : '') + steps + `</details>`;
    }).join('');
    el.innerHTML = head + `<div class="benchPick">${pick}<button type="button" id="benchDel" class="ghost" title="Delete this record">DELETE</button></div>` + add + stale
      + `<div class="benchProg"><div class="pbar">${bar}</div><span>${done}/${STEPS.length} done · ${t.pass} pass · <u>${t.fail} fail</u> · ${t.skip} skipped</span></div>`
      + `<div class="benchFields">${fields}</div>` + phases + tools();
    wire(el);
  }
  function tools() {
    return `<div class="benchTools"><button type="button" id="benchJson">EXPORT JSON</button><button type="button" id="benchCsv">EXPORT CSV</button><button type="button" id="benchCopy">COPY CSV</button>`
      + `<label class="fileBtn">IMPORT<input id="benchImport" type="file" accept=".json,application/json"></label><button type="button" id="benchKeep">KEEP ON DEVICE</button></div>`
      + `<p class="hint" id="benchSaved">${saved ? 'Saved in this browser. Export a copy before clearing site data or changing phone.' : 'NOT SAVED: this browser refused storage. Export now.'}</p><p class="hint" id="benchMsg"></p>`;
  }
  function msg(t) { const m = $('#benchMsg'); if (m) m.textContent = t; }
  function wire(el) {
    $('#benchNew').addEventListener('click', () => newRecord($('#benchSerial').value.trim()));
    $('#benchSerial').addEventListener('keydown', e => { if (e.key === 'Enter') newRecord(e.target.value.trim()); });
    const pick = $('#benchPick'); if (pick) pick.addEventListener('change', e => { store.active = e.target.value; persist(); renderBench(); });
    const del = $('#benchDel');
    if (del) del.addEventListener('click', () => {
      if (del.dataset.armed !== '1') { del.dataset.armed = '1'; del.textContent = 'TAP AGAIN TO DELETE'; setTimeout(() => { if (del.isConnected) { del.dataset.armed = ''; del.textContent = 'DELETE'; } }, 4000); return; }
      store.records = store.records.filter(x => x.id !== store.active); store.active = (store.records[0] || {}).id || null; persist(); renderBench();
    });
    el.querySelectorAll('[data-f]').forEach(i => i.addEventListener('input', () => {
      const r = rec(); if (!r) return; r.fields[i.dataset.f] = i.value; persist();
      if (['serial', 'date'].includes(i.dataset.f) && pick) pick.selectedOptions[0].textContent = (r.fields.serial || 'Board without serial') + ' · ' + (r.fields.date || '');
    }));
    el.querySelectorAll('details.phase').forEach(d => d.addEventListener('toggle', () => { if (d.open) openPhase = d.dataset.phase; else if (openPhase === d.dataset.phase) openPhase = null; }));
    el.querySelectorAll('.step').forEach(row => {
      const id = row.dataset.step;
      const res = () => { const r = rec(); r.results[id] = r.results[id] || { status: '', value: '', note: '', at: '' }; return r.results[id]; };
      row.querySelectorAll('[data-st]').forEach(b => b.addEventListener('click', () => {
        const v = res(); v.status = v.status === b.dataset.st ? '' : b.dataset.st; v.at = new Date().toISOString(); persist();
        const y = $('#eyeDeck .deckBody').scrollTop; renderBench(); $('#eyeDeck .deckBody').scrollTop = y;
      }));
      row.querySelectorAll('[data-v]').forEach(i => i.addEventListener('input', () => { const v = res(); v[i.dataset.v] = i.value; v.at = new Date().toISOString(); persist(); }));
      const see = row.querySelector('.see');
      if (see) see.addEventListener('click', () => { const e = eye(); if (e && e.focus) e.focus({ refs: see.dataset.refs.split(' ') }, id + ' · ' + see.dataset.refs, STEP[id].expected.replace(/`/g, '')); });
    });
    $('#benchJson').addEventListener('click', () => save(JSON.stringify({ ...store, exported: new Date().toISOString(), procedure: { source: PROC.source, sha256: PROC.sha256 }, board: M.name }, null, 2), 'json', 'application/json'));
    $('#benchCsv').addEventListener('click', () => save(csv(), 'csv', 'text/csv'));
    $('#benchCopy').addEventListener('click', async () => { try { await navigator.clipboard.writeText(csv()); msg('CSV copied.'); } catch (_) { msg('Copy was refused here; use EXPORT CSV.'); } });
    $('#benchKeep').addEventListener('click', async () => {
      try { const ok = navigator.storage && navigator.storage.persist ? await navigator.storage.persist() : false; msg(ok ? 'The browser will keep this data unless you clear it. Keep exporting copies.' : 'The browser did not promise to keep the data: export copies.'); }
      catch (_) { msg('This browser has no persistent-storage request: export copies.'); }
    });
    $('#benchImport').addEventListener('change', async e => {
      const f = e.target.files[0]; e.target.value = ''; if (!f) return;
      if (f.size > 4 * 1024 * 1024) { msg('That file is over 4 MB: not a bench export.'); return; }
      try {
        const inc = validate(JSON.parse(await f.text()));
        const have = new Set(store.records.map(r => r.id)); let added = 0, replaced = 0;
        for (const r of inc.records) { if (have.has(r.id)) { store.records = store.records.map(x => x.id === r.id ? r : x); replaced++; } else { store.records.push(r); added++; } }
        store.active = store.active || (store.records[0] || {}).id || null; persist(); renderBench(); msg(`Imported: ${added} new, ${replaced} replaced (same record id).`);
      } catch (err) { msg('Not imported: ' + err.message + '.'); }
    });
  }
  function csv() {
    const q = v => '"' + String(v == null ? '' : v).replace(/"/g, '""') + '"';
    const rows = [['serial', 'date', 'operator', 'firmware', 'step', 'phase', 'probe', 'expected', 'status', 'reading', 'note', 'recorded', 'procedure_sha256']];
    for (const r of store.records) for (const s of STEPS) {
      const v = r.results[s.id] || {};
      rows.push([r.fields.serial, r.fields.date, r.fields.operator, r.fields.firmware, s.id, s.phase, s.probe, s.expected, v.status || 'open', v.value, v.note, v.at, r.procedure]);
    }
    return rows.map(r => r.map(q).join(',')).join('\r\n') + '\r\n';
  }
  function save(text, ext, type) {
    const r = rec(), name = `STRUTHIO_BENCH_${(r && r.fields.serial || 'boards').replace(/[^A-Za-z0-9_-]+/g, '_')}_${new Date().toISOString().slice(0, 10)}.${ext}`;
    try {
      const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([text], { type })); a.download = name;
      document.body.appendChild(a); a.click(); setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 4000); msg('Saved as ' + name + '.');
    } catch (_) { msg('This browser would not save the file; use COPY CSV.'); }
  }

  /* ---------- DOCS: search and read the package documents ---------- */
  let docOpen = null;
  function mdBlock(text) {   // the subset of Markdown the package documents use; everything is escaped first
    const out = [], lines = text.replace(/\r/g, '').split('\n');
    let i = 0;
    const inline = s => esc(s).replace(/`([^`]+)`/g, '<code>$1</code>').replace(/\*\*([^*]+)\*\*/g, '<b>$1</b>').replace(/(^|[\s(])\*([^*\s][^*]*)\*/g, '$1<i>$2</i>').replace(/\[([^\]]+)\]\(([^)]+)\)/g, '$1');
    while (i < lines.length) {
      const l = lines[i];
      if (/^```/.test(l)) { const buf = []; i++; while (i < lines.length && !/^```/.test(lines[i])) buf.push(lines[i++]); i++; out.push(`<pre>${esc(buf.join('\n'))}</pre>`); continue; }
      const h = l.match(/^(#{1,4})\s+(.*)/); if (h) { out.push(`<h${h[1].length + 2}>${inline(h[2])}</h${h[1].length + 2}>`); i++; continue; }
      if (/^\|/.test(l)) {
        const rows = []; while (i < lines.length && /^\|/.test(lines[i])) rows.push(lines[i++]);
        const cells = r => r.trim().replace(/^\||\|$/g, '').split('|').map(c => c.trim());
        const body = rows.filter(r => !/^\|[\s:|-]+\|$/.test(r.trim()));
        out.push('<div class="docTable"><table>' + body.map((r, k) => '<tr>' + cells(r).map(c => k === 0 ? `<th>${inline(c)}</th>` : `<td>${inline(c)}</td>`).join('') + '</tr>').join('') + '</table></div>');
        continue;
      }
      if (/^\s*([-*]|\d+\.)\s+/.test(l)) {
        const items = []; while (i < lines.length && /^\s*([-*]|\d+\.)\s+/.test(lines[i])) items.push(lines[i++].replace(/^\s*([-*]|\d+\.)\s+/, ''));
        out.push('<ul>' + items.map(x => `<li>${inline(x)}</li>`).join('') + '</ul>'); continue;
      }
      if (!l.trim()) { i++; continue; }
      const para = []; while (i < lines.length && lines[i].trim() && !/^(#{1,4}\s|\||```|\s*([-*]|\d+\.)\s)/.test(lines[i])) para.push(lines[i++]);
      out.push(`<p>${inline(para.join(' '))}</p>`);
    }
    return out.join('');
  }
  function search(q) {
    const toks = q.toLowerCase().split(/\s+/).filter(Boolean);
    if (!toks.length) return [];
    return B.docs.map((d, k) => {
      const t = (d.title + '\n' + d.text).toLowerCase();
      if (!toks.every(x => t.includes(x))) return null;
      const hits = toks.reduce((a, x) => a + t.split(x).length - 1, 0), pos = t.indexOf(toks[0]);
      return { k, hits, snip: d.text.slice(Math.max(0, pos - 60), pos + 140).replace(/\s+/g, ' ') };
    }).filter(Boolean).sort((a, b) => b.hits - a.hits);
  }
  function renderDocs() {
    const el = $('#paneDocs'); if (!el) return;
    if (docOpen != null) {
      const d = B.docs[docOpen];
      el.innerHTML = `<div class="sendRow docHead"><button type="button" class="go" id="docBack">← DOCUMENTS</button><span class="hint">${esc(d.path)} · ${esc(d.sha256.slice(0, 12))}</span></div><article class="docBody">${mdBlock(d.text)}</article>`;
      $('#docBack').addEventListener('click', () => { docOpen = null; renderDocs(); });
      return;
    }
    const q = (window.__benchQ || '');
    const found = search(q);
    const list = q ? (found.length ? found.map(f => `<button class="row net" data-doc="${f.k}"><b>${esc(B.docs[f.k].title)}</b><span>${f.hits} matches · …${esc(f.snip)}…</span></button>`).join('') : '<div class="empty">No document has all of those words.</div>')
      : B.docs.map((d, k) => `<button class="row net" data-doc="${k}"><b>${esc(d.title)}</b><span>${esc(d.path)}</span></button>`).join('');
    el.innerHTML = `<div class="offline" id="offlineState">${offlineText()}</div>`
      + `<input id="docSearch" type="search" autocomplete="off" spellcheck="false" placeholder="Search: C309 · 1V1_HP · display fast · TS" value="${esc(q)}" aria-label="Search the package documents">`
      + `<div class="findCount">${q ? found.length + ' of ' + B.docs.length + ' documents' : B.docs.length + ' current documents, offline. Search or open one.'}</div><div class="findList">${list}</div>`;
    const inp = $('#docSearch');
    inp.addEventListener('input', () => { window.__benchQ = inp.value; const p = inp.selectionStart; renderDocs(); const n = $('#docSearch'); n.focus(); n.setSelectionRange(p, p); });
    el.querySelectorAll('[data-doc]').forEach(b => b.addEventListener('click', () => { docOpen = Number(b.dataset.doc); renderDocs(); $('#eyeDeck .deckBody').scrollTop = 0; }));
  }

  /* ---------- offline status ---------- */
  let offline = 'checking';
  function offlineText() {
    const how = /iPhone|iPad/.test(navigator.userAgent) ? 'On iPhone: Safari → Share → Add to Home Screen.' : 'Install from the browser menu (Install app / Add to Home Screen).';
    if (location.protocol === 'file:') return '<b>OFFLINE: NOT AVAILABLE</b> Opened as a file. Offline use needs the studio served over https, then opened once online.';
    if (offline === 'ready') return `<b class="ok">OFFLINE: READY</b> The studio and these documents open without a connection. ${how}`;
    if (offline === 'none') return '<b>OFFLINE: NOT READY</b> This browser has no offline cache for the studio. Open it once online over https.';
    return '<b>OFFLINE: CHECKING…</b>';
  }
  async function checkOffline() {
    try {
      if (!('caches' in window)) { offline = 'none'; }
      else { const keys = await caches.keys(); offline = keys.some(k => k.startsWith('struthio-studio-')) ? 'ready' : 'none'; }
    } catch (_) { offline = 'none'; }
    const el = $('#offlineState'); if (el) el.innerHTML = offlineText();
  }

  /* ---------- wiring ---------- */
  function init() {
    load(); renderSystems(); renderBench(); renderDocs(); checkOffline();
    if (navigator.serviceWorker) navigator.serviceWorker.addEventListener('controllerchange', checkOffline);
    setTimeout(checkOffline, 4000);
    const chip = $('#sysChip'); if (chip) chip.addEventListener('click', () => setSystem('all'));
    const bt = $('#tabBench'); if (bt) bt.addEventListener('click', () => eye() && eye().openTab('bench'));
    // A tour stop shows the whole board: leave any isolated system.
    const reel = $('#reel'); if (reel) reel.addEventListener('click', () => { if (sysKey !== 'all') setSystem('all'); });
  }
  const boot = () => requestAnimationFrame(() => requestAnimationFrame(() => requestAnimationFrame(init)));
  if (document.readyState === 'complete') boot(); else window.addEventListener('load', boot);
  window.STRUDIO_BENCH = { setSystem, csv };
})();
