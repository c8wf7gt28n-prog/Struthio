/* STRUTHIO Studio · EYE layer ("Shared Sight")
   Additive. Reads the studio through window.STRUDIO and draws callouts on its own canvas.
   It never edits geometry, authority state or loaded files.
   Facts in STOPS are computed from model-data.js (window.STRUTHIO_MODEL, R24; its zones, fab and gates blocks come from
   CHECKS/build_pcb_viewer_data.py); anything not in the files is tagged INFERRED or GAP. */
(() => {
  'use strict';
  const S = window.STRUDIO;
  if (!S) return;
  const $ = s => document.querySelector(s);
  const st = S.state;
  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
  const esc = s => String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  let REAR = (window.STRUDIO_ASSETS && window.STRUDIO_ASSETS.rear) || 'R24_REAR_BOARD.svg';
  if (REAR.startsWith('data:image/svg+xml;base64,')) {
    try { const bin = atob(REAR.split(',')[1]); REAR = URL.createObjectURL(new Blob([Uint8Array.from(bin, c => c.charCodeAt(0))], { type: 'image/svg+xml' })); } catch (_) { /* keep data URI */ }
  }

  const layer = $('#eyeLayer'), lctx = layer.getContext('2d');
  const hl = { refs: [], net: '', note: '' };
  let eyeOn = false, capturing = false, cur = 0, fly = null;
  const thumbs = [];
  const sig = () => { const m = S.model(); return (m.name || '') + '|' + m.parts.length + '|' + (m.pads || []).length; };
  let SIG0 = '';

  /* ---------- computed facts (counts from the loaded model; pours, fab files and gates from their blocks) ---------- */
  const MD = S.model(), n1 = v => Number(v).toLocaleString('en-US', { maximumFractionDigits: 1 });
  const ZONES = MD.zones || [], FAB = MD.fab, GATES = MD.gates;
  const PARTS = MD.parts || [], PADS = MD.pads || [], SEGS = MD.segments || [], VIAS = MD.vias || [];
  const NETS = Object.keys(MD.nets || {}).length;
  const count = (arr, f) => arr.reduce((m, x) => { const k = f(x); m[k] = (m[k] || 0) + 1; return m; }, {});
  const backCat = count(PARTS.filter(p => p.side === 'back'), p => p.category);
  const segLayer = count(SEGS, s => s.layer);
  const netPads = count(PADS, p => p.netName);
  const P_ = r => PARTS.find(p => p.ref === r) || {};
  const at = r => { const p = P_(r); return p.x === undefined ? '?' : `${n1(p.x)}, ${n1(p.y)}`; };
  const front = PARTS.filter(p => p.side === 'front');
  const zoneFacts = ZONES.map(z => [z.layer.replace('.Cu', '') + ' · ' + z.net, n1(z.area) + ' mm²']);
  const inner = ZONES.filter(z => z.layer === 'In2.Cu').sort((a, b) => b.area - a.area);
  const gnd = ZONES.filter(z => z.net === 'GND').map(z => z.layer.replace('.Cu', ''));
  const PLANES_TEXT = ZONES.length ? `The board file stores ${ZONES.length} filled copper pours. ${gnd.join(' and ')} are solid GND planes (${n1(ZONES.find(z => z.net === 'GND').area)} mm² each). In2 is split into power pours: ${inner.map(z => `${z.net} ${n1(z.area)} mm²`).join(', ')}. In3 carries the inner signal tracks. Pours are drawn from the stored fills, simplified to 0.03 mm.` : 'This board file has no copper pours.';
  const vip = FAB ? FAB.vias.in_smd_pads.map(v => v.ref) : [];
  const FAB_TEXT = FAB ? `CHECKS/build_builder_packs.py plots the R24 board with KiCad ${FAB.kicad} into the JLCPCB order: ${FAB.gerber_layers.length} Gerber layers, Excellon drill (${FAB.drill.pth_round_holes} vias, ${FAB.drill.plated_slots} plated USB-C slots, ${FAB.drill.npth_holes} non-plated holes), a ${FAB.bom.lines}-line BOM and a ${FAB.cpl_placements}-part placement file. DRC: ${FAB.drc.violations} violations, ${FAB.drc.unconnected_pads} unconnected. Vias are epoxy filled and capped; ${vip.join(' and ')} have a via in a pad. ${FAB.bom.with_lcsc} of ${FAB.bom.placements} parts carry an LCSC number. Every line was in stock at JLCPCB on 2026-10-07 except U1, the ESP32-P4NRW32X: pre-order it through JLCPCB Global Sourcing or consign v3 chips.` : 'No fab summary in this package (CHECKS/R24_FAB_SUMMARY.json).';
  const openRows = GATES ? GATES.open : [];
  const fails = openRows.filter(g => g.status === 'FAIL');
  const gateFacts = openRows.map(g => [(g.status === 'FAIL' ? '✕ ' : '') + g.id, g.title.length > 64 ? g.title.slice(0, 62) + '…' : g.title]);

  /* ---------- authored tour: what Claude sees in the loaded R24 file ---------- */
  const STOPS = [
    { id: 'board', name: 'WHOLE BOARD', gist: `R24 · ${PARTS.length} footprints · ${PADS.length} pads · order files ready.`, basis: 'FILE', side: 'home',
      text: `The PCB is 99.2 × 125.0 mm and 1.2 mm thick, six copper layers. The file holds ${PARTS.length} footprints, ${PADS.length} pads, ${n1(SEGS.length)} track segments, ${VIAS.length} vias and ${NETS} nets. R24 is R22 (R21 with the electrical and land-pattern review fixed) with four plug-and-play ports: the display tail straight into J1, a JST PH battery socket behind a polarity-protection MOSFET, and two PicoBlade speaker sockets (LAYERS/01_PCB/README_PCB_LAYER.md).`,
      facts: [['SIZE', '99.2 × 125.0 × 1.2 mm'], ['FOOTPRINTS', String(PARTS.length)], ['PADS', String(PADS.length)], ['TRACKS / VIAS', `${n1(SEGS.length)} / ${VIAS.length}`], ['NETS', String(NETS)]] },
    { id: 'front', name: 'FRONT FACE', gist: 'SW1–SW4 and the display socket J1 live on the front.', basis: 'FILE', side: 'front', stack: 'pcb.top', refs: ['SW1', 'SW2', 'SW3', 'SW4', 'J1'],
      text: `Four Omron D2LS-21 switches and the display socket are the only footprints on the front. SW1 and SW2 sit under the flap caps (x ±40.75, y 102); SW3 and SW4 under the DART rocker (x ±16, y 119.3). J1, a top-contact FH12A socket at (${at('J1')}), sits under the panel, just below the battery window, and takes the panel tail folded once behind it.`,
      facts: [['FRONT PARTS', `${front.length} of ${PARTS.length}`], ['SW1 / SW2', `${P_('SW1').value} · flap caps`], ['SW3 / SW4', `${P_('SW3').value} · DART rocker`], ['J1', `${P_('J1').value} · display`]] },
    { id: 'back', name: 'BACK SIDE', gist: `${PARTS.length - front.length} of ${PARTS.length} footprints are on the back.`, basis: 'FILE', side: 'back', stack: 'pcb.bottom',
      text: `The back carries nearly everything: ${backCat.capacitor} capacitors, ${backCat.resistor} resistors, ${backCat.ic} ICs, ${backCat.connector} connectors, ${backCat.inductor} inductors, ${backCat.switch} switches, ${backCat.diode} diodes, ${backCat.transistor} transistor and 1 crystal.`,
      facts: [['CAPACITORS', String(backCat.capacitor)], ['RESISTORS', String(backCat.resistor)], ['ICs', String(backCat.ic)], ['CONNECTORS', String(backCat.connector)], ['SWITCHES', String(backCat.switch)], ['L / D / Q / Y', `${backCat.inductor} / ${backCat.diode} / ${backCat.transistor} / 1`]] },
    { id: 'brain', name: 'PROCESSOR + FLASH', gist: 'U1 ESP32-P4 and U2 flash at y 84.', basis: 'FILE', side: 'back', refs: ['U1', 'U2', 'Y1', 'U14'],
      text: `U1 ESP32-P4NRW32X (chip revision v3, 32 MB PSRAM in package) sits at (${at('U1')}). U2 W25Q512JVEIQ 64 MB flash is at (${at('U2')}). Y1, the 40 MHz crystal, is at (${at('Y1')}) with 12 pF load capacitors. U14 TPS3808G33 at (${at('U14')}) holds the chip in reset until 3.3 V is good.`,
      facts: [['U1', `ESP32-P4NRW32X · ${at('U1')}`], ['U2', `W25Q512JVEIQ · ${at('U2')}`], ['Y1', `40 MHz · ${at('Y1')}`], ['U14', `TPS3808G33 · ${at('U14')}`]] },
    { id: 'power', name: 'POWER AREA', gist: 'Regulators and inductors, net 3V3_SYS.', basis: 'FILE', side: 'back', net: '3V3_SYS', refs: ['U3', 'U4', 'U5', 'U6', 'U7', 'L1', 'L2', 'L3', 'D2'],
      text: `Regulators and inductors cluster at y 97–108: U4 TPS63070 buck-boost (3.3 V system), U3 TLV62569, U5 TLV75518 (panel 1.8 V), U6 ME6211C30 (panel 3.0 V), U7 TPS61165 backlight boost (74 mA, R309 2.7 Ω), inductors L1–L3 and diode D2. 3V3_SYS touches ${netPads['3V3_SYS']} pads, the most after GND (${netPads.GND}).`,
      facts: [['3V3_SYS', `${netPads['3V3_SYS']} pads`], ['SYS_RAW', `${netPads.SYS_RAW} pads`], ['U4', `TPS63070 · ${at('U4')}`], ['U6', `ME6211C30 · ${at('U6')}`], ['U7', `TPS61165 · ${at('U7')}`]] },
    { id: 'usb', name: 'USB-C END', gist: 'J2 USB-C to the chip\'s USB-Serial-JTAG, ESD, CC chip and charger.', basis: 'FILE', side: 'back', net: 'USB_JTAG_DP', refs: ['J2', 'U11', 'U12', 'U13', 'D1', 'U10'],
      text: `J2 USB4105-GF-A is at (${at('J2')}). Its data pair goes to GPIO24/25, the ESP32-P4's USB-Serial-JTAG: one cable flashes, logs and debugs with no firmware support. U11 and U12 (TPD2EUSB30, 1 × 1 mm) and D1 protect the pins; U13 TUSB320 handles CC; U10 BQ24074 at (${at('U10')}) charges the cell.`,
      facts: [['J2', `USB4105-GF-A-120 · ${at('J2')}`], ['DATA', 'USB_JTAG_DP/DM · GPIO25/24'], ['U13', 'TUSB320LAIRWBR'], ['U10', `BQ24074RGTR · ${at('U10')}`]] },
    { id: 'audio', name: 'AUDIO', gist: 'Two MAX98357A amps and speaker sockets.', basis: 'FILE', side: 'back', net: 'SPK_L_P', refs: ['U8', 'U9', 'J4', 'J5'],
      text: `U8 and U9 (MAX98357A) sit mirrored at (±29, 112). J4 (${at('J4')}) and J5 (${at('J5')}) are Molex PicoBlade 2-pin sockets for the left and right speaker (the plug on Adafruit's small speakers), pin 1 positive.`,
      facts: [['U8 / U9', 'MAX98357AETE+T'], ['J4 / J5', '53261-0271 PicoBlade · pin 1 +'], ['NETS', 'SPK_L/R_P/N · I2S_*']] },
    { id: 'link', name: 'PLUG-IN PORTS', gist: 'J1 display (front), J3 battery, J4/J5 speakers.', basis: 'FILE', side: 'home', refs: ['J1', 'J3', 'J4', 'J5'],
      text: `Four parts plug in, no adapter cables. J1 (FH12A-40S-0.5SH, top contact, on the front at ${at('J1')}) takes the Crystalfontz CFAF7201280A0-050TN's own 40-pin tail, folded once behind the panel: DSI clock and two lanes, LCD_RESX, 3.0 V and 1.8 V panel supplies and the backlight, every pin matched to the panel's table (check N1). J3 (${at('J3')}) takes any protected 1-cell pack on a JST PH 2.0 plug, pin 1 BAT+; Q2 (AO3401A) blocks a reversed pack when there is no USB; with USB only the charger's few-mA test current flows. J4 and J5 take the speakers on PicoBlade plugs. The DSI pairs are length-matched (CLK 60.25, D0 56.25, D1 54.84 mm; P = N within 0.01 mm).`,
      facts: [['J1', 'Crystalfontz 5 in tail · 40 pins · direct'], ['J3', 'BAT+ · GND (JST PH 2-pin) · Q2 reverse switch'], ['J4 / J5', 'speakers (Molex PicoBlade 2-pin)'], ['CHARGE', '0.5 A (R412 1.8 k)']] },
    { id: 'rear', name: 'REAR BUTTONS', gist: 'SW5–SW7 on the back at x 25.', basis: 'FILE', side: 'back', refs: ['SW5', 'SW6', 'SW7'],
      text: 'Three B3U-1000P switches are stacked on the back at x 25, y 30, 39 and 48: power/wake, reset and boot.',
      facts: [['SW5', 'B3U-1000P · power / wake'], ['SW6', 'B3U-1000P · reset'], ['SW7', 'B3U-1000P · boot']] },
    { id: 'copper', name: 'ROUTING', gist: `${n1(SEGS.length)} track segments · ${VIAS.length} vias.`, basis: 'FILE', side: 'home', mode: 'COPPER',
      text: `R24 track-segment counts by routed layer: B.Cu ${n1(segLayer['B.Cu'] || 0)}, F.Cu ${n1(segLayer['F.Cu'] || 0)}, In3.Cu ${n1(segLayer['In3.Cu'] || 0)}${segLayer['In1.Cu'] ? `, In1.Cu ${segLayer['In1.Cu']} (the USB D+ hop)` : ''}. There are ${VIAS.length} vias. This is a routing count, not a signal-integrity certification.`,
      facts: [['B.Cu', n1(segLayer['B.Cu'] || 0)], ['F.Cu', n1(segLayer['F.Cu'] || 0)], ['In3.Cu', n1(segLayer['In3.Cu'] || 0)], ['TOTAL SEGMENTS', n1(SEGS.length)], ['VIAS', String(VIAS.length)], ['FAB STATUS', 'ORDER FILES READY']] },
    { id: 'planes', name: 'PLANES', gist: 'GND planes on In1 and In4, power pours on In2.', basis: ZONES.length ? 'FILE' : 'GAP', side: 'home', stack: 'pcb.inner', mode: 'COPPER',
      text: PLANES_TEXT, facts: zoneFacts.length ? zoneFacts : [['POURS', 'none in file']] },
    { id: 'fab', name: 'ORDER FILES', gist: FAB ? `JLCPCB Gerbers, drill, BOM, CPL · DRC ${FAB.drc.violations}/${FAB.drc.unconnected_pads} · U1 stock open.` : 'No fab summary.', basis: FAB ? 'FILE' : 'GAP', side: 'back', refs: FAB ? [...vip, 'U1'] : [],
      text: FAB_TEXT,
      facts: FAB ? [['GERBER', `${FAB.gerber_layers.length} layers · X2`], ['DRILL', `${FAB.drill.pth_round_holes} + ${FAB.drill.plated_slots} slots + ${FAB.drill.npth_holes} NPTH`], ['BOM', `${FAB.bom.lines} lines · ${FAB.bom.with_lcsc}/${FAB.bom.placements} LCSC`], ['DRC', `KiCad ${FAB.kicad} · ${FAB.drc.violations} / ${FAB.drc.unconnected_pads} / ${FAB.drc.footprint_errors}`], ['VIAS', 'filled + capped'], ['VIA IN PAD', vip.join(', ') || 'none'], ['STOCK', 'U1 to pre-order or consign']] : [['FAB', 'not generated']] },
    { id: 'plot', kind: 'plot', name: 'KICAD REAR PLOT', gist: 'The R24 rear SVG plot in this package.', basis: 'FILE', side: 'home',
      text: 'This is the R24_REAR_BOARD.svg plot from the package. It is a mirrored rear view, drawn by KiCad. Tap it to enlarge.',
      facts: [['FILE', 'R24_REAR_BOARD.svg'], ['VIEW', 'rear, mirrored']] },
    { id: 'gap', name: 'WHAT I CANNOT SEE', gist: 'CASE R12 is on hold: drawn for an earlier panel.', basis: 'GAP', side: 'home', stack: 'case.front',
      text: 'CASE R12 (front and rear shell, controls, screen stack with its tape frame, internals) and the clear, unprinted ACRYLIC R2 film are loaded from case-layer-data.js and acrylic-layer-data.js. They were converged on R21 for a HOTHMI-size panel; the owner set the case aside for R24, and the case pass for the 5 in Crystalfontz panel comes after the board is up. The LCD, cell and speakers are envelopes, not supplier models. FPC and harness runs are route reserves. SHOW R3 CASE CAD shows the superseded R3 study for reference only.',
      facts: [['CASE', 'R12 · on hold'], ['ACRYLIC', 'FILM R2 · on hold'], ['PCB', 'R24 · order files ready']] },
    { id: 'gates', name: 'OPEN ITEMS', gist: GATES ? `${fails.length} case fixes, ${GATES.counts.GATE} items needing parts or prints.` : 'No gate list.', basis: 'GAP', side: 'home', stack: 'case.front',
      text: GATES ? `The convergence check reports ${GATES.counts.PASS} PASS, ${GATES.counts.FAIL} FAIL and ${GATES.counts.GATE} GATE. ${fails.length ? `The FAIL rows (${fails.map(g => g.id).join(', ')}) are the case pass, on hold: the plastic was drawn before the 5 in panel and the R24 connectors. ` : ''}Every GATE is something CAD cannot close: a supplier drawing, a measured part, or a test print. Details: ${GATES.source} and PRODUCTION_GATES.md.` : 'No gate list in this model.',
      facts: gateFacts.length ? gateFacts : [['GATES', 'none listed']] }
  ];

  /* ---------- geometry helpers ---------- */
  const M = () => S.model();
  const thick = () => M().board.thickness || 1.2;
  const partTopZ = p => (p.side === 'back' ? -S.partHeight(p) / 2 : thick() + S.partHeight(p) / 2);
  const findPart = r => M().parts.find(p => p.ref.toUpperCase() === String(r).toUpperCase());
  const netCache = new Map();
  function netGeom(n) {
    const m = M(), key = n + '|' + (m.name || '') + (m.pads || []).length;
    if (netCache.has(key)) return netCache.get(key);
    const g = {
      pads: (m.pads || []).filter(p => p.netName === n),
      segs: (m.segments || []).filter(s => s.netName === n),
      vias: (m.vias || []).filter(v => v.netName === n)
    };
    netCache.set(key, g);
    return g;
  }
  const allNets = () => [...new Set(Object.values(M().nets || {}).filter(Boolean))];
  function rotRect(cx, cy, w, h, deg) {
    const a = deg * Math.PI / 180, c = Math.cos(a), s = Math.sin(a), hw = w / 2, hh = h / 2;
    return [[-hw, -hh], [hw, -hh], [hw, hh], [-hw, hh]].map(([x, y]) => [cx + x * c - y * s, cy + x * s + y * c]);
  }

  /* ---------- camera ---------- */
  function camFor(sp) {
    const side = sp.side || 'home';
    const yaw = side === 'back' ? 0 : side === 'front' ? -.25 : -.64;
    const pitch = side === 'back' ? -1.2 : side === 'front' ? 1.15 : .82;
    const pts = [];
    (sp.refs || []).forEach(r => { const p = findPart(r); if (p) pts.push([p.x, p.y, partTopZ(p), Math.max(p.w, p.h)]); });
    if (sp.net && !pts.length) { const g = netGeom(sp.net); g.pads.forEach(p => pts.push([p.x, p.y, 0, 0])); g.segs.forEach(s => { pts.push([s.x1, s.y1, 0, 0]); pts.push([s.x2, s.y2, 0, 0]); }); }
    if (!pts.length) return { yaw, pitch, dist: side === 'home' ? 290 : 260, t: { x: 0, y: 0, z: 0 } };
    const xs = pts.map(p => p[0]), ys = pts.map(p => p[1]);
    const x0 = Math.min(...xs), x1 = Math.max(...xs), y0 = Math.min(...ys), y1 = Math.max(...ys);
    const ext = Math.max(x1 - x0, y1 - y0) + Math.max(...pts.map(p => p[3]));
    return { yaw, pitch, dist: clamp(ext * 1.55 + 85, 125, 300), t: S.world((x0 + x1) / 2, (y0 + y1) / 2, side === 'back' ? -1 : thick() + 1) };
  }
  function setCam(c) { st.yaw = c.yaw; st.pitch = c.pitch; st.dist = c.dist; st.target = { ...c.t }; S.schedule(); }
  function flyTo(c, ms = 650) {
    const from = { yaw: st.yaw, pitch: st.pitch, dist: st.dist, t: { ...st.target } };
    let dy = c.yaw - from.yaw; dy = Math.atan2(Math.sin(dy), Math.cos(dy));
    const t0 = performance.now(), id = fly = {};
    const step = now => {
      if (fly !== id) return;
      const k = clamp((now - t0) / ms, 0, 1), e = k < .5 ? 2 * k * k : 1 - Math.pow(-2 * k + 2, 2) / 2;
      st.yaw = from.yaw + dy * e; st.pitch = from.pitch + (c.pitch - from.pitch) * e; st.dist = from.dist + (c.dist - from.dist) * e;
      st.target = { x: from.t.x + (c.t.x - from.t.x) * e, y: from.t.y + (c.t.y - from.t.y) * e, z: from.t.z + (c.t.z - from.t.z) * e };
      S.schedule();
      if (k < 1) requestAnimationFrame(step); else fly = null;
    };
    requestAnimationFrame(step);
  }
  S.canvas.addEventListener('pointerdown', () => { fly = null; });

  /* ---------- show a view ---------- */
  function show(sp, animate) {
    setStack(sp.stack || 'build.assembled');
    setMode(sp.mode || (['pcb.fcu', 'pcb.inner', 'pcb.bcu', 'pcb.pads'].includes(sp.stack) ? 'COPPER' : 'SOLID'));
    hl.refs = (sp.refs || []).filter(findPart); hl.net = sp.net || ''; hl.note = sp.note || '';
    const c = sp.cam || camFor(sp);
    if (animate) flyTo(c); else { fly = null; setCam(c); }
    S.schedule();
  }

  /* ---------- overlay: callouts drawn above the 3D canvas ---------- */
  window.STRUDIO_AFTER = (w, h, dpr) => {
    const W = Math.round(w * dpr), H = Math.round(h * dpr);
    if (layer.width !== W || layer.height !== H) { layer.width = W; layer.height = H; }
    lctx.setTransform(dpr, 0, 0, dpr, 0, 0); lctx.clearRect(0, 0, w, h);
    if (!eyeOn && !capturing) return;
    drawNet(); drawParts();
  };
  function drawNet() {
    if (!hl.net) return;
    const g = netGeom(hl.net), t = thick(), c = lctx;
    c.save(); c.lineCap = 'round'; c.lineJoin = 'round';
    for (const pass of [0, 1]) {
      for (const s of g.segs) {
        const a = S.project(s.x1, s.y1, S.copperLayerZ(s.layer)), b = S.project(s.x2, s.y2, S.copperLayerZ(s.layer));
        if (!a || !b) continue;
        const lw = Math.max(2, s.w * a.scale * 1.3);
        c.strokeStyle = pass ? '#ffb23e' : 'rgba(0,0,0,.65)'; c.lineWidth = lw + (pass ? 0 : 2.5);
        c.beginPath(); c.moveTo(a.x, a.y); c.lineTo(b.x, b.y); c.stroke();
      }
      for (const p of g.pads) {
        const q = S.project(p.x, p.y, p.side === 'back' ? -.03 : t + .03); if (!q) continue;
        const r = Math.max(2.6, Math.max(p.w, p.h) / 2 * q.scale);
        c.fillStyle = pass ? '#ffb23e' : 'rgba(0,0,0,.65)'; c.beginPath(); c.arc(q.x, q.y, r + (pass ? 0 : 1.6), 0, 7); c.fill();
      }
      for (const v of g.vias) {
        const q = S.project(v.x, v.y, t * .5); if (!q) continue;
        const r = Math.max(2.6, v.size / 2 * q.scale);
        c.strokeStyle = pass ? '#fff4d6' : 'rgba(0,0,0,.65)'; c.lineWidth = pass ? 1.6 : 3.4; c.beginPath(); c.arc(q.x, q.y, r, 0, 7); c.stroke();
      }
    }
    c.restore();
  }
  function drawParts() {
    const c = lctx, placed = [], many = hl.refs.length > 14;
    c.save(); c.font = '700 10px ui-monospace,Menlo,Consolas,monospace'; c.textBaseline = 'middle';
    hl.refs.forEach((ref, i) => {
      const p = findPart(ref); if (!p) return;
      const z = p.side === 'back' ? -S.partHeight(p) : thick() + S.partHeight(p);
      const pts = rotRect(p.x, p.y, p.w + .8, p.h + .8, p.rot || 0).map(q => S.project(q[0], q[1], z));
      if (pts.some(q => !q)) return;
      c.lineJoin = 'round';
      for (const pass of [0, 1]) {
        c.beginPath(); pts.forEach((q, k) => k ? c.lineTo(q.x, q.y) : c.moveTo(q.x, q.y)); c.closePath();
        c.strokeStyle = pass ? '#f4fbfa' : 'rgba(0,0,0,.7)'; c.lineWidth = pass ? 1.8 : 4; c.stroke();
      }
      if (many) return;
      const cx = pts.reduce((s, q) => s + q.x, 0) / 4, top = Math.min(...pts.map(q => q.y));
      const tw = c.measureText(ref).width + 10, bw = tw, bh = 15;
      let x = clamp(cx - bw / 2 + ((i % 3) - 1) * 6, 3, layer.clientWidth - bw - 3), y = top - 15;
      for (let k = 0; k < 8; k++) { if (!placed.some(r => x < r.x + r.w + 2 && x + bw + 2 > r.x && y < r.y + r.h + 1 && y + bh + 1 > r.y)) break; y -= bh + 2; }
      y = clamp(y, 3, layer.clientHeight - bh - 3);
      placed.push({ x, y, w: bw, h: bh });
      c.strokeStyle = 'rgba(255,178,62,.9)'; c.lineWidth = 1; c.beginPath(); c.moveTo(cx, top); c.lineTo(clamp(cx, x + 4, x + bw - 4), y + bh); c.stroke();
      c.fillStyle = '#ffb23e'; c.fillRect(x, y, bw, bh);
      c.fillStyle = '#1b1205'; c.fillText(ref, x + 5, y + bh / 2 + .5);
    });
    c.restore();
  }

  /* ---------- UI: bar, deck, tabs ---------- */
  const app = $('#app'), deck = $('#eyeDeck'), bar = $('#eyeBar');
  function setDeck(open) { deck.classList.toggle('open', open); $('#eyeTitle').setAttribute('aria-expanded', open ? 'true' : 'false'); }
  function openTab(name) {
    document.querySelectorAll('.deckTabs [data-tab]').forEach(x => x.classList.toggle('on', x.dataset.tab === name));
    document.querySelectorAll('.deckBody .pane').forEach(p => p.classList.toggle('on', p.id === 'pane' + name[0].toUpperCase() + name.slice(1)));
    if (name === 'send') $('#codeOut').value = currentCode();
    setDeck(true);
    if (name === 'find') setTimeout(() => $('#findInput').focus({ preventScroll: true }), 300);
  }
  function setEye(on) {
    eyeOn = on; app.classList.toggle('eyeOn', on);
    $('#eyeBtn').setAttribute('aria-pressed', on ? 'true' : 'false');
    if (!on) setDeck(false);
    S.schedule();
  }
  function renderBar() {
    const sp = STOPS[cur];
    $('#eyeIdx').textContent = String(cur + 1).padStart(2, '0') + '/' + String(STOPS.length).padStart(2, '0') + (sp.basis === 'FILE' ? '' : ' · ' + sp.basis);
    $('#eyeName').textContent = sp.name;
    $('#eyeGist').textContent = sp.gist;
    bar.dataset.basis = sp.basis;
    document.querySelectorAll('#reel .frame').forEach((f, i) => f.classList.toggle('on', i === cur));
    const d = $('#stopDetail');
    d.innerHTML = `<div class="sdHead"><span class="basis b-${sp.basis}">${sp.basis === 'FILE' ? 'FROM FILE' : sp.basis === 'GAP' ? 'NOT VISIBLE' : 'INFERRED'}</span><b>${esc(sp.name)}</b></div>
      ${sig() !== SIG0 ? '<p class="stale">A different board is loaded. These tour notes describe the bundled R24 only and may not match what you see.</p>' : ''}
      <p>${esc(sp.text)}</p>
      ${sp.kind === 'plot' ? `<button class="plotBtn" id="plotOpen"><img src="${REAR}" alt="KiCad rear plot of R24"></button>` : ''}
      <dl class="facts">${sp.facts.map(([k, v]) => `<div><dt>${esc(k)}</dt><dd>${esc(v)}</dd></div>`).join('')}</dl>
      <div class="sdActs"><button id="lookBtn" class="go">LOOK</button><button id="codeBtn">COPY VIEW CODE</button></div>`;
    $('#lookBtn').onclick = () => { setDeck(false); };
    $('#codeBtn').onclick = e => copyText(currentCode(), e.currentTarget, 'COPY VIEW CODE');
    const po = $('#plotOpen'); if (po) po.onclick = () => openPlot();
  }
  function centerFrame() {
    const r = $('#reel'), f = r.querySelector('.frame.on'); if (!f) return;
    r.scrollTo({ left: f.offsetLeft - (r.clientWidth - f.offsetWidth) / 2, behavior: 'smooth' });
  }
  function syncWheel(id, value, vertical) {
    const el = $(id), b = el && el.querySelector(`[data-value="${value}"]`); if (!b) return;
    const er = el.getBoundingClientRect(), br = b.getBoundingClientRect();
    if (vertical) el.scrollTo({ top: el.scrollTop + (br.top - er.top) - (er.height - br.height) / 2 });
    else el.scrollTo({ left: el.scrollLeft + (br.left - er.left) - (er.width - br.width) / 2 });
  }
  const setStack = k => { S.setStack(k); if (!capturing) syncWheel('#stackWheel', k, true); };
  const setMode = m => { S.setMode(m); const l = $('#toolModeLbl'); if (l) l.textContent = st.mode; if (!capturing) syncWheel('#modeWheel', st.mode, false); };
  function go(i, animate = true) {
    cur = (i + STOPS.length) % STOPS.length;
    const sp = STOPS[cur];
    if (sp.kind === 'plot') { renderBar(); openPlot(); return; }
    closePlot();
    show(sp, animate); renderBar();
    centerFrame();
  }

  function buildReel() {
    $('#reel').innerHTML = STOPS.map((sp, i) => `<button class="frame" data-i="${i}" aria-label="${esc(sp.name)}">
      <span class="sprock"></span>
      <span class="shot">${sp.kind === 'plot' ? `<img class="plotThumb" src="${REAR}" alt="">` : (thumbs[i] ? `<img src="${thumbs[i]}" alt="">` : '')}<i>${String(i + 1).padStart(2, '0')}</i></span>
      <span class="sprock"></span></button>`).join('');
    document.querySelectorAll('#reel .frame').forEach(f => f.addEventListener('click', () => { go(+f.dataset.i); }));
  }

  /* Render each stop once into a small image so the strip is a real contact sheet. */
  function captureThumbs() {
    const src = S.canvas, TW = 168, TH = 266;
    const tc = document.createElement('canvas'); tc.width = TW; tc.height = TH; const t = tc.getContext('2d');
    capturing = true;
    STOPS.forEach((sp, i) => {
      if (sp.kind === 'plot') return;
      show(sp, false); S.render();
      const g = t.createRadialGradient(TW / 2, TH * .46, 0, TW / 2, TH * .46, TH * .62); g.addColorStop(0, '#0a2425'); g.addColorStop(1, '#010708');
      t.fillStyle = g; t.fillRect(0, 0, TW, TH);
      const ar = TW / TH; let sw = src.width, sh = src.height;
      if (sw / sh > ar) sw = sh * ar; else sh = sw / ar;
      t.drawImage(src, (src.width - sw) / 2, (src.height - sh) / 2, sw, sh, 0, 0, TW, TH);
      t.drawImage(layer, (layer.width - sw * (layer.width / src.width)) / 2, (layer.height - sh * (layer.height / src.height)) / 2, sw * (layer.width / src.width), sh * (layer.height / src.height), 0, 0, TW, TH);
      thumbs[i] = tc.toDataURL('image/jpeg', .82);
    });
    capturing = false;
  }

  /* ---------- FIND ---------- */
  const CATS = [['ALL', null], ['IC', 'ic'], ['CONN', 'connector'], ['SW', 'switch'], ['L', 'inductor'], ['D', 'diode'], ['Q', 'transistor'], ['OTHER', 'other']];
  let cat = null;
  function renderFind() {
    const q = $('#findInput').value.trim();
    const qu = q.toUpperCase();
    const m = M();
    let parts = m.parts.filter(p => !cat || p.category === cat);
    if (qu) parts = parts.filter(p => [p.ref, p.value, p.mpn, p.lcsc, p.package].some(v => (v || '').toUpperCase().includes(qu)));
    else if (!cat) parts = parts.filter(p => ['ic', 'connector', 'switch'].includes(p.category));
    parts.sort((a, b) => (a.ref.toUpperCase() === qu ? -1 : 0) - (b.ref.toUpperCase() === qu ? -1 : 0) || a.ref.localeCompare(b.ref, undefined, { numeric: true }));
    const nets = qu ? allNets().filter(n => n.toUpperCase().includes(qu)).slice(0, 8) : [];
    const rows = [];
    nets.forEach(n => { const g = netGeom(n); rows.push(`<button class="row net" data-net="${esc(n)}"><b>${esc(n)}</b><span>NET · ${g.pads.length} pads · ${g.segs.length} tracks · ${g.vias.length} vias</span></button>`); });
    parts.slice(0, 40).forEach(p => rows.push(`<button class="row" data-ref="${esc(p.ref)}"><b>${esc(p.ref)}</b><span>${esc(p.value || p.category)}${p.lcsc ? ' · ' + esc(p.lcsc) : ''} · ${p.side} · ${p.x.toFixed(1)}, ${p.y.toFixed(1)}</span></button>`));
    $('#findList').innerHTML = rows.join('') || '<div class="empty">Nothing matches. Try a ref (U1), a part number (ESP32) or a net (3V3_SYS).</div>';
    $('#findCount').textContent = qu || cat ? `${parts.length} parts${nets.length ? ' · ' + nets.length + ' nets' : ''}` : 'ICs, connectors and switches. Type to search all 165.';
    document.querySelectorAll('#findList .row').forEach(r => r.addEventListener('click', () => {
      const sp = r.dataset.net ? { net: r.dataset.net, side: netSide(r.dataset.net) } : { refs: [r.dataset.ref], side: (findPart(r.dataset.ref) || {}).side === 'front' ? 'front' : 'back' };
      cur = -1; hl.refs = []; show(sp, true);
      $('#eyeName').textContent = r.dataset.net || r.dataset.ref; $('#eyeIdx').textContent = 'FIND'; $('#eyeGist').textContent = r.querySelector('span').textContent; bar.dataset.basis = 'FILE';
      document.querySelectorAll('#reel .frame').forEach(f => f.classList.remove('on'));
      setDeck(false);
    }));
  }
  function netSide(n) { const g = netGeom(n); const b = g.pads.filter(p => p.side === 'back').length; return b >= g.pads.length / 2 ? 'back' : 'front'; }

  /* ---------- VIEW CODE: text a person or Claude can paste ---------- */
  function currentCode() {
    const f = x => +x.toFixed(3);
    const refs = hl.refs.length ? hl.refs : (st.selected && st.selected.type === 'part' ? [st.selected.ref] : []);
    return ['STR', [f(st.yaw), f(st.pitch), f(st.dist), f(st.target.x), f(st.target.y), f(st.target.z)].join(','), st.mode, st.stackKey, refs.join(','), hl.net, hl.note].join('|');
  }
  function applyCode(txt) {
    const parts = String(txt).trim().split('|');
    if (parts[0] !== 'STR' || parts.length < 4) return false;
    const n = (parts[1] || '').split(',').map(Number);
    if (n.length < 6 || n.some(v => !Number.isFinite(v))) return false;
    const stack = parts[3] || 'build.assembled';
    setStack(stack);
    setMode(['SOLID', 'XRAY', 'WIRE', 'COPPER'].includes(parts[2]) ? parts[2] : 'SOLID');
    hl.refs = (parts[4] || '').split(',').map(s => s.trim()).filter(findPart);
    hl.net = (parts[5] || '').trim(); hl.note = parts.slice(6).join('|');
    flyTo({ yaw: n[0], pitch: n[1], dist: clamp(n[2], 105, 540), t: { x: n[3], y: n[4], z: n[5] } });
    cur = -1; $('#eyeIdx').textContent = 'CODE'; $('#eyeName').textContent = hl.refs.join(' ') || hl.net || 'SHARED VIEW'; $('#eyeGist').textContent = hl.note || 'View applied from a pasted code.';
    bar.dataset.basis = 'FILE'; document.querySelectorAll('#reel .frame').forEach(f => f.classList.remove('on'));
    S.schedule(); return true;
  }
  function copyText(text, btn, label) {
    const done = ok => { if (btn) { btn.textContent = ok ? 'COPIED' : 'SELECT + COPY'; setTimeout(() => { btn.textContent = label; }, 1400); } };
    try { navigator.clipboard.writeText(text).then(() => done(true), () => { fallbackCopy(text); done(false); }); }
    catch (_) { fallbackCopy(text); done(false); }
  }
  function fallbackCopy(text) { const t = $('#codeOut'); if (t) { t.value = text; t.focus(); t.select(); } }

  /* ---------- SEND: snapshot with the facts burned in ---------- */
  function snapshot() {
    S.render();
    const src = S.canvas, cap = 96, W = src.width, H = src.height + cap;
    const c = document.createElement('canvas'); c.width = W; c.height = H; const t = c.getContext('2d');
    const g = t.createRadialGradient(W / 2, src.height * .46, 0, W / 2, src.height * .46, src.height * .7); g.addColorStop(0, '#0a2425'); g.addColorStop(1, '#010708');
    t.fillStyle = g; t.fillRect(0, 0, W, src.height); t.drawImage(src, 0, 0); t.drawImage(layer, 0, 0, W, src.height);
    t.fillStyle = '#050b0d'; t.fillRect(0, src.height, W, cap);
    const k = W / 390, a = S.authority();
    t.font = `700 ${11 * k}px ui-monospace,Menlo,Consolas,monospace`; t.textBaseline = 'top';
    const lines = [
      `STRUTHIO VIS · ${S.stackLabel()} · ${st.mode}`,
      `θ ${Math.round(st.yaw * 57.2958)}°  φ ${Math.round(st.pitch * 57.2958)}°  Z ${Math.round(st.dist)}   ${hl.refs.length ? 'REFS ' + hl.refs.join(' ') : ''}${hl.net ? '  NET ' + hl.net : ''}`,
      `CASE ${a.case ? '✓' : a.reference ? '~ REFERENCE' : '— MISSING'} · PCB ${a.pcb ? ((S.model().name||'').includes('R24') ? 'R24 · ORDER READY' : 'PCB · REVIEW') : '—'} · ART ${a.art ? '✓' : '— MISSING'}`
    ];
    lines.forEach((l, i) => { t.fillStyle = i === 0 ? '#ffb23e' : i === 2 ? '#7fa8aa' : '#d8e6e6'; t.fillText(l, 10 * k, src.height + (9 + i * 16) * k); });
    const url = c.toDataURL('image/png');
    $('#snapOut').innerHTML = `<img src="${url}" alt="Snapshot of the current view with its settings">`;
    $('#snapHint').hidden = false;
    $('#codeOut').value = currentCode();
    const dl = $('#snapSave'); dl.href = url; dl.download = `STRUTHIO_VIS_${Date.now()}.png`; dl.hidden = false;
  }

  /* Tapping a part in the 3D view while Eye is on highlights it and fills the bar. */
  window.STRUDIO_SELECT = item => {
    if (!eyeOn || capturing || !item || item.type !== 'part') return;
    const p = item.data; hl.refs = [p.ref]; hl.net = ''; cur = -1;
    $('#eyeIdx').textContent = 'TAP'; $('#eyeName').textContent = p.ref;
    $('#eyeGist').textContent = `${p.value || p.category} · ${p.side} · ${p.x.toFixed(1)}, ${p.y.toFixed(1)}`; bar.dataset.basis = 'FILE';
    document.querySelectorAll('#reel .frame').forEach(f => f.classList.remove('on'));
  };

  /* ---------- plot overlay ---------- */
  function openPlot() { const i = $('#plotImg'); if (!i.getAttribute('src')) i.src = REAR; $('#plotView').hidden = false; }
  function closePlot() { $('#plotView').hidden = true; }

  /* ---------- wiring ---------- */
  function init() {
    SIG0 = sig();
    captureThumbs();
    buildReel(); renderFind();
    show(STOPS[0], false); renderBar();
    $('#eyeBtn').addEventListener('click', () => { setEye(!eyeOn); if (eyeOn) { show(STOPS[Math.max(cur, 0)], false); setDeck(false); } });
    $('#eyeTitle').addEventListener('click', () => { if (deck.classList.contains('open') && $('.deckTabs [data-tab="tour"]').classList.contains('on')) setDeck(false); else openTab('tour'); });
    $('#tabFind').addEventListener('click', () => openTab('find'));
    $('#tabSend').addEventListener('click', () => openTab('send'));
    $('#deckClose').addEventListener('click', () => setDeck(false));
    document.querySelectorAll('.deckTabs [data-tab]').forEach(b => b.addEventListener('click', () => openTab(b.dataset.tab)));
    S.canvas.addEventListener('pointerdown', () => setDeck(false));
    // floating tools: flip side, cycle mode, home
    const MODES = ['SOLID', 'XRAY', 'COPPER', 'WIRE'];
    $('#toolFlip').addEventListener('click', () => {
      const toBack = st.pitch > 0;
      // Turn the board over like a card: same azimuth, pitch mirrored through the board plane.
      const mag = Math.max(.6, Math.abs(st.pitch));
      flyTo({ yaw: st.yaw, pitch: toBack ? -mag : mag, dist: st.dist, t: { ...st.target } });
    });
    $('#toolMode').addEventListener('click', () => { const m = MODES[(MODES.indexOf(st.mode) + 1) % MODES.length]; setMode(m); $('#toolModeLbl').textContent = m; });
    $('#toolHome').addEventListener('click', () => flyTo({ yaw: -.64, pitch: .82, dist: 290, t: { x: 0, y: 0, z: 0 } }));
    $('#findCats').innerHTML = CATS.map(([l, v], i) => `<button data-c="${v || ''}" class="${i === 0 ? 'on' : ''}">${l}</button>`).join('');
    document.querySelectorAll('#findCats button').forEach(b => b.addEventListener('click', () => {
      cat = b.dataset.c || null; document.querySelectorAll('#findCats button').forEach(x => x.classList.toggle('on', x === b)); renderFind();
    }));
    $('#findInput').addEventListener('input', () => {
      const v = $('#findInput').value; if (v.startsWith('STR|')) { if (applyCode(v)) { $('#findInput').value = ''; setDeck(false); } return; } renderFind();
    });
    $('#snapBtn2').addEventListener('click', snapshot);
    $('#copyCode').addEventListener('click', e => copyText($('#codeOut').value || currentCode(), e.currentTarget, 'COPY'));
    $('#applyCode').addEventListener('click', () => {
      const ok = applyCode($('#pasteIn').value); $('#pasteMsg').textContent = ok ? 'View applied.' : 'That is not a view code. It starts with STR|.';
      if (ok) setDeck(false);
    });
    $('#plotClose').addEventListener('click', closePlot);
    document.querySelectorAll('#plotZoom button').forEach(b => b.addEventListener('click', () => {
      document.querySelectorAll('#plotZoom button').forEach(x => x.classList.toggle('on', x === b)); $('#plotImg').style.width = b.dataset.w + '%';
    }));
    document.addEventListener('keydown', e => { if (e.key === 'Escape') closePlot(); });
    setEye(true); setDeck(false);
  }
  // Wait for the studio's first render and the wheels' initial scroll, then build.
  const boot = () => requestAnimationFrame(() => requestAnimationFrame(init));
  if (document.readyState === 'complete') boot(); else window.addEventListener('load', boot);
  window.STRUDIO_EYE = { go, applyCode, currentCode, stops: STOPS };
})();
