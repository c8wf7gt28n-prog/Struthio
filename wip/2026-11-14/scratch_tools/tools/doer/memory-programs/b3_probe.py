import json, time, os, io, zipfile
from pathlib import Path
k = w.ledger_bridge.kernel; p = operator()
def d(op, a=None): return k.dispatch(op, a or {}, p)
def run(line):
    r = d('language.run', {'text': line}); print('  staC> %s\n        -> %s %s' % (line, 'ok' if r['ok'] else 'REFUSED', json.dumps(r['result'].get('rows') if r['ok'] else r['error'])[:500]))
files = Path(k.root) / 'Files' / 'probe'; files.mkdir(parents=True, exist_ok=True)
buf = io.BytesIO()
with zipfile.ZipFile(buf, 'w') as z: z.writestr('Document.xml', '<Document SchemaVersion="4" ProgramVersion="0.21R0" FileVersion="1"><Properties Count="0"/><Objects Count="0"/><ObjectData Count="0"/></Document>')
(files / 'part.FCStd').write_bytes(buf.getvalue()); (files / 'panel.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" width="100" height="50" viewBox="0 0 100 50"><rect width="100" height="50"/></svg>')
(files / 'scene.blend').write_bytes(b'BLENDER-v300' + b'\0' * 64)
print('files.find, the ways a shelf sheet could list what its program can open:')
for a in ({'text': '.fcstd'}, {'text': 'fcstd', 'limit': 5}, {'kind': 'image'}, {'days': 1, 'limit': 10}, {'under': 'probe'}):
    r = d('files.find', a); print('  files.find %s -> %s' % (json.dumps(a), json.dumps(r.get('result') or r.get('error'))[:420]))
r = d('files.list', {'path': 'probe'}); print('  files.list probe ->', [(e['path'], e['kind'], round(e['modified'])) for e in r['result']['entries']])
print('the inspect reads as staC lines:')
run('programs.freecad.inspect {"path":"probe/part.FCStd"} | select state,sha256,tool.available,editor_safe')
run('programs.inkscape.inspect {"path":"probe/panel.svg"} | select state,render_ready,reason')
run('files.find {"days":1} | pick files | select path,kind,modified')
run('files.list {"path":"probe"} | pick entries | where name has .FCStd | select path,modified')
run('activity {"after":"150","limit":200} | where operation has programs. | select at,operation,state')
run('ledger.context | pick desktop')
run('ledger.context | pick active_jobs')
run('ledger.awareness {"consumer":"field"} | select state,cursor,head,backlog')
run('documents.list | pick documents | sort -updated | select title,updated,revision | take 3')
run('ledger.trail.list {"limit":5} | pick intents | select operation,created,request_state,work')
run('matrix.list {"limit":5} | pick rows | select created,program,outcome')
# operation lines the writing strip takes for a write (how field_do writes them)
from workbench.stac_bridge import route_program
for line in ('programs.freecad.inspect {"path":"probe/part.FCStd"}',):
    try: print('  route_program:', route_program(line))
    except Exception as exc: print('  route_program refused:', exc)
# is there any place that lists native sessions?
r = d('joined.session.get', {'id': '0' * 32}); print('joined.session.get unknown ->', r.get('error'))
with k.db() as db: print('desk_records kinds:', db.execute('select kind,count(*) from desk_records group by 1').fetchall())
# candidate.preview on an untouched prepared copy: which field differs
sid = 'owner:db5f669f863d4c71b89fa7ba348957da'; got = d('office.get', {'id': sid})['result']
plan = d('office.operation.preview', {'id': sid, 'expected_revision': got['revision'], 'mode': 'edit', 'format': 'ods'})['result']
job = wait_job(d('office.operation.run', {'plan': plan['id'], 'expected_digest': plan['digest']})['result']['id'], 240, 'edit copy')
res = d('office.operation.result', {'job': job['id']})['result']; path = Path(res['directory']) / res['files'][0]['name']
c = d('office.candidate.preview', {'id': sid, 'expected_revision': got['revision'], 'path': str(path)})['result']
print('candidate.preview of the UNTOUCHED prepared copy: %d changes;' % len(c['changes']), [(x['cell'], x['change'], {q: (x['before'].get(q), x['after'].get(q)) for q in x['before'] if x['before'].get(q) != (x.get('after') or {}).get(q)}) for x in c['changes'] if isinstance(x.get('before'), dict)][:4], '| keys', sorted(c.keys()))
