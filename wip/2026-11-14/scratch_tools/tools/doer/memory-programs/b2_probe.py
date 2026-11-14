import json, time, os, sys
from pathlib import Path
sys.path.insert(0, '/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/doer/memory-programs')
from full_window import full_window
k = w.ledger_bridge.kernel; p = operator()
def d(op, a=None): return k.dispatch(op, a or {}, p)
files = Path(k.root) / 'Files' / 'probe'; files.mkdir(parents=True, exist_ok=True)
(files / 'panel.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" width="100" height="50" viewBox="0 0 100 50"><rect width="100" height="50" fill="#222"/></svg>')
(files / 'scene.blend').write_bytes(b'BLENDER-v300' + b'\0' * 64)
(files / 'note.eml').write_text('From: a@example.org\nTo: b@example.org\nSubject: probe\nDate: Thu, 12 Nov 2026 10:00:00 +0000\nMessage-ID: <1@example.org>\n\nhello\n')
print('== full_window() with nothing installed and no display ==')
for key, path in (('inkscape', 'probe/panel.svg'), ('blender', 'probe/scene.blend'), ('mail', 'probe/note.eml'), ('office', 'x'), ('blender', '')):
    print('  %-9s %-18s ->' % (key, path), full_window(k, p, key, path))
# a principal that is not the desk owner
from workbench.engineering_kernel import Principal
other = Principal('slate', frozenset({'read', 'execute', 'approve'})) if True else None
try:
    r = k.dispatch('programs.blender.open', {'path': 'probe/scene.blend', 'expected_sha256': '0' * 64}, other); print('  as another principal with approve:', r.get('error'))
    r = k.dispatch('programs.blender.open', {'path': 'probe/scene.blend', 'expected_sha256': '0' * 64}, Principal('desktop-owner', frozenset({'read', 'execute'}))); print('  as desktop-owner without approve:', r.get('error'))
except Exception as exc: print('  principal test:', type(exc).__name__, exc)
bindir = Path(k.root).parent / 'standin-bin'; bindir.mkdir(exist_ok=True)
for name in ('inkscape', 'blender', 'thunderbird'):
    (bindir / name).write_text('#!/bin/sh\necho "$0 $@" >> "%s/args.txt"\nsleep 2\n' % bindir); (bindir / name).chmod(0o755)
os.environ['PATH'] = str(bindir) + os.pathsep + os.environ['PATH']
print('== stand-ins on PATH, still no display ==')
for key, path in (('inkscape', 'probe/panel.svg'), ('blender', 'probe/scene.blend'), ('mail', 'probe/note.eml')): print('  %-9s ->' % key, full_window(k, p, key, path))
os.environ['DISPLAY'] = ':99'
print('== stand-ins on PATH and DISPLAY set ==')
for key, path in (('inkscape', 'probe/panel.svg'), ('blender', 'probe/scene.blend'), ('mail', 'probe/note.eml')): print('  %-9s ->' % key, full_window(k, p, key, path))
settle(100, 5); print('  command lines the stand-ins received:'); print('   ', (bindir / 'args.txt').read_text().replace(str(k.root), '<ws>').replace(str(bindir), '<bin>').strip().replace('\n', '\n    '))
os.environ.pop('DISPLAY')
# ---- Office: the sheet's hand-over to the real spreadsheet, and the way back
print('\n== Office: a reviewed sheet handed to the full spreadsheet ==')
sid = 'owner:db5f669f863d4c71b89fa7ba348957da'; got = d('office.get', {'id': sid})['result']
print('office.doctor:', json.dumps(d('office.doctor')['result'])[:500])
r = d('office.operation.preview', {'id': sid, 'expected_revision': got['revision'], 'mode': 'edit', 'format': 'ods'}); print('office.operation.preview ->', r['ok'], json.dumps({q: (v if q != 'document' else '…') for q, v in (r.get('result') or r.get('error')).items()})[:900])
if r['ok']:
    plan = r['result']; t = time.time()
    r = d('office.operation.run', {'plan': plan['id'], 'expected_digest': plan['digest']}); print('office.operation.run ->', r['ok'], json.dumps({q: r['result'][q] for q in ('id', 'tool', 'state')} if r['ok'] else r['error']))
    if r['ok']:
        job = wait_job(r['result']['id'], 240, 'office edit copy'); print('   took %.1f s' % (time.time() - t))
        res = d('office.operation.result', {'job': job['id']}); print('office.operation.result ->', res['ok'], json.dumps({q: v for q, v in (res.get('result') or res.get('error')).items() if q not in ('measurement',)})[:1100])
        if res['ok'] and res['result'].get('files'):
            from workbench import office_runtime
            path = Path(res['result']['directory']) / res['result']['files'][0]['name']; print('   prepared copy:', str(path).replace(str(k.root), '<ws>'), path.exists())
            try: print('   editor_command:', office_runtime.editor_command(path, Path(res['result']['directory']) / 'desktop-editor'))
            except ValueError as exc: print('   editor_command refused (what the Office panel shows):', exc)
            os.environ['DISPLAY'] = ':99'
            args, env = office_runtime.editor_command(path, Path(res['result']['directory']) / 'desktop-editor'); os.environ.pop('DISPLAY')
            print('   editor_command with a display:', [a.replace(str(k.root), '<ws>') for a in args], '| env keys', list(env))
            # the way back: the saved candidate is reviewed, then committed
            r = d('office.candidate.preview', {'id': sid, 'expected_revision': got['revision'], 'path': str(path)}); print('office.candidate.preview ->', r['ok'], json.dumps({q: v for q, v in (r.get('result') or r.get('error')).items() if q not in ('document', 'candidate')})[:700])
print('jobs now:', [(j['tool'], j['state']) for j in (d('jobs.list')['result'])][:3])
print('journal tail:', [(e['operation'], e['state']) for e in d('ledger.journal.read', {'after': str(d('ledger.journal.status')['result']['head'] - 14)})['result']['events']])
