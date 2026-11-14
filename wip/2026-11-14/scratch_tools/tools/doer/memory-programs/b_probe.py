# B: the 33 programs; staging a native launch as the room's "Full app" button does; the Office hand-over.
import json, time, os, io, zipfile, stat, sys
from pathlib import Path
from PySide6.QtWidgets import QPushButton
k = w.ledger_bridge.kernel; p = operator()
def d(op, a=None): return k.dispatch(op, a or {}, p)
def show(tag, r, n=420): print('  %-34s %s %s' % (tag, 'ok' if r['ok'] else 'REFUSED', json.dumps(r.get('result') if r['ok'] else r['error'])[:n]))
# ---- the shelf, as ledger.explore says it
rows = d('ledger.explore', {'kind': 'INSTRUMENT'})['result']['instruments']
print('instruments:', len(rows))
for r in rows:
    print('  %-14s %-10s %-18s dest=%-18s tool_status=%-24s setup=%s ops=%d jobtools=%d' % (r['key'], r['presentation_kind'], r['view_class'], r['destination'], r['tool_status'], r['setup_needed'], r['operations'], r['job_tools']))
# ---- material in the throwaway Files folder
files = Path(k.root) / 'Files' / 'probe'; files.mkdir(parents=True, exist_ok=True)
buf = io.BytesIO()
with zipfile.ZipFile(buf, 'w') as z:
    z.writestr('Document.xml', '<?xml version="1.0" encoding="utf-8"?><Document SchemaVersion="4" ProgramVersion="0.21R0" FileVersion="1"><Properties Count="1"><Property name="Label" type="App::PropertyString"><String value="Probe part"/></Property></Properties><Objects Count="0"/><ObjectData Count="0"/></Document>')
(files / 'part.FCStd').write_bytes(buf.getvalue())
(files / 'panel.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" width="100" height="50" viewBox="0 0 100 50"><rect width="100" height="50" fill="#222"/></svg>')
(files / 'scene.blend').write_bytes(b'BLENDER-v300' + b'\0' * 64)
(files / 'game').mkdir(exist_ok=True); (files / 'game' / 'project.godot').write_text('config_version=5\n\n[application]\n\nconfig/name="Probe game"\n')
(files / 'note.eml').write_text('From: a@example.org\nTo: b@example.org\nSubject: probe\nDate: Thu, 12 Nov 2026 10:00:00 +0000\nMessage-ID: <1@example.org>\n\nhello\n')
(files / 'cart.nes').write_bytes(b'NES\x1a\x01\x01\x00\x00' + b'\0' * 8 + b'\0' * (16384 + 8192))
print('\nDISPLAY=%r WAYLAND_DISPLAY=%r' % (os.environ.get('DISPLAY'), os.environ.get('WAYLAND_DISPLAY')))
head = d('ledger.journal.status')['result']['head']
print('\n== native programs through their operations (nothing installed here) ==')
for key, path, extra in (('freecad', 'probe/part.FCStd', {}), ('inkscape', 'probe/panel.svg', {}), ('blender', 'probe/scene.blend', {}), ('godot', 'probe/game/project.godot', {}), ('mail', 'probe/note.eml', {}), ('cartridge', 'probe/cart.nes', {'core': 'fceumm'})):
    r = d('programs.%s.inspect' % key, {'path': path}); res = r.get('result') or {}
    print(' %s.inspect -> %s state=%s tool=%s %s' % (key, 'ok' if r['ok'] else r['error'], res.get('state'), json.dumps(res.get('tool') or {q: res.get(q) for q in ('emulator', 'cores', 'launch_ready', 'reason')}), {q: res[q] for q in ('editor_safe', 'render_ready', 'reason') if q in res}))
    if not r['ok']: continue
    verb = 'launch' if key == 'cartridge' else 'open'
    show('programs.%s.%s' % (key, verb), d('programs.%s.%s' % (key, verb), {'path': path, 'expected_sha256': res['sha256'], **extra}))
print('journal rows these left:')
for e in d('ledger.journal.read', {'after': str(head), 'limit': 200})['result']['events']: print('     ', e['seq'], e['operation'], e['state'])
# ---- the room, as the owner meets it: shelf -> Enter -> Inspect -> Full app
print('\n== the FreeCAD room from the shelf ==')
w.a_field.trigger(); settle(); v = w.field_page.view; QTest.keyClick(v, Qt.Key_P); settle(30, 4)
fc = next(o for o in v.field.objects if o.id == 'app:freecad'); v.field.select(fc.id); v.update(); settle(5, 2)
print('sheet:', fc.title, '| state', repr(fc.state), '| role', fc.role, '| where', fc.where, '| target keys', sorted(fc.target), '| stac', fc.stac)
QTest.keyClick(v, Qt.Key_Return); settle(60, 5); room = w.tabs.currentWidget(); where('Enter on FreeCAD'); print('room:', type(room).__name__, '| native_app', room.native_app, '| key', room.key)
full = next(b for b in room.findChildren(QPushButton) if b.accessibleName() == 'Open in FreeCAD')
print('  before a source: status=%r | Full app text=%r enabled=%s tip=%r' % (room.status.text(), full.text(), full.isEnabled(), full.toolTip()))
room.source.setText('probe/part.FCStd'); settle(20, 2); room.inspect()
t = time.time()
while room.busy and time.time() - t < 20: settle(50, 2)
print('  after Inspect: status=%r | Full app enabled=%s | tool_ready()=%s' % (room.status.text(), full.isEnabled(), room.tool_ready()))
print('  details:', room.details.toPlainText().replace('\n', ' / ')[:400])
room.bound('open'); t = time.time()
while room.busy and time.time() - t < 20: settle(50, 2)
print('  if the button could be pressed (room.bound("open")): status=%r tooltip=%r' % (room.status.text(), room.status.toolTip()))
save('doer_freecad_room_not_installed.png')
# ---- a stand-in executable named freecad, to see the receipt the owner gets when the program is there
print('\n== with a stand-in executable named "freecad" on PATH and DISPLAY set ==')
bindir = Path(k.root).parent / 'standin-bin'; bindir.mkdir(exist_ok=True)
(bindir / 'freecad').write_text('#!/bin/sh\n# stand-in editor: waits, then "saves" the file it was given (last argument)\nfor a in "$@"; do f="$a"; done\necho "$@" > "%s/args.txt"\nsleep 1.5\nprintf "edited-by-standin" >> "$f"\nsleep 1\n' % bindir)
(bindir / 'freecad').chmod(0o755)
os.environ['PATH'] = str(bindir) + os.pathsep + os.environ['PATH']; os.environ['DISPLAY'] = ':99'
head = d('ledger.journal.status')['result']['head']
r = d('programs.freecad.inspect', {'path': 'probe/part.FCStd'}); res = r['result']; print('  inspect: state', res['state'], 'tool', res['tool'], 'sha', res['sha256'][:12])
r = d('programs.freecad.open', {'path': 'probe/part.FCStd', 'expected_sha256': res['sha256']}); show('programs.freecad.open', r, 600)
pid = (r.get('result') or {}).get('pid')
print('  journal:', [(e['seq'], e['operation'], e['state'], e.get('detail', '')) for e in d('ledger.journal.read', {'after': str(head)})['result']['events']])
print('  jobs.list has a job for it:', any('freecad' in str(j.get('tool')) for j in (d('jobs.list')['result'] if isinstance(d('jobs.list')['result'], list) else [])), '| ledger.context.active_jobs:', d('ledger.context')['result']['active_jobs'])
print('  process alive:', os.path.exists('/proc/%s' % pid), '| stand-in saw args:', (bindir / 'args.txt').read_text().strip() if (bindir / 'args.txt').exists() else None)
room.inspect(); t = time.time()
while room.busy and time.time() - t < 20: settle(50, 2)
print('  the room now (Inspect again): Full app enabled=%s status=%r' % (full.isEnabled(), room.status.text()))
QTest.mouseClick(full, Qt.LeftButton); t = time.time()
while room.busy and time.time() - t < 20: settle(50, 2)
print('  CLICK on Full app: status=%r' % room.status.text()); print('  details tail:', room.details.toPlainText().replace('\n', ' / ')[-260:])
save('doer_freecad_room_started.png')
settle(200, 20)
r2 = d('programs.freecad.inspect', {'path': 'probe/part.FCStd'}); print('  after the stand-in "saved": inspect ->', r2['ok'], (r2.get('result') or {}).get('sha256', '')[:12] if r2['ok'] else r2['error'])
r3 = d('programs.freecad.open', {'path': 'probe/part.FCStd', 'expected_sha256': res['sha256']}); show('open again with the old hash', r3)
print('  files.story:', json.dumps(d('files.story', {'path': 'probe/part.FCStd'}).get('result'))[:300])
print('  room status without re-inspecting:', repr(room.status.text()), '| room.current sha == file now:', (room.current or {}).get('sha256') == (r2.get('result') or {}).get('sha256'))
# shelf marks
w.a_field.trigger(); settle(); QTest.keyClick(v, Qt.Key_P); settle(30, 4)
print('\nshelf states now:', {o.id: o.state for o in v.field.objects if o.state})
