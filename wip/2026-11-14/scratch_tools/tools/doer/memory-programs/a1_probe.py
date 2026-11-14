# A1: what is recorded for each thing the owner does; read back through operations. Throwaway workspace.
import json, time, sqlite3, copy
k = w.ledger_bridge.kernel; p = operator()
def d(op, a=None): return k.dispatch(op, a or {}, p)
def ok(op, a=None):
    r = d(op, a)
    if not r['ok']: print('   REFUSED', op, r['error']); return None
    return r['result']
def brief(e): return {x: (round(e[x],3) if x=='at' else e[x]) for x in ('seq','at','origin','operation','state','detail','correlation_id','job_id','evidence_id','candidate_id','source_generation') if e.get(x) not in (None,'')}
def since(seq, say):
    r = ok('ledger.journal.read', {'after': str(seq), 'limit': 200})
    print('  -- journal rows after seq %s (%s): %d' % (seq, say, len(r['events'])))
    for e in r['events']: print('     ', json.dumps(brief(e)))
    return int(r['cursor'])
st = ok('ledger.journal.status'); head = st['head']; T0 = time.time()
print('journal head at start:', head, '| T0 =', round(T0,3))
# ---- (a) open a page, then a sheet, from the Field with Enter
w.a_field.trigger(); settle(); v = w.field_page.view
doc = next(o for o in v.field.objects if o.id == 'document:218f9efb3315412099761113f1ef2e5d'); v.field.select(doc.id); v.update(); settle(5,2)
QTest.keyClick(v, Qt.Key_Return); settle(60,5); where('Enter on page')
head = since(head, 'OPEN A PAGE from the Field')
sheet = next(o for o in v.field.objects if o.id == 'office:owner:db5f669f863d4c71b89fa7ba348957da')
w.a_field.trigger(); settle(); v.field.select(sheet.id); v.update(); settle(5,2)
QTest.keyClick(v, Qt.Key_Return); settle(60,5); where('Enter on sheet')
head = since(head, 'OPEN A SHEET from the Field')
# ---- (b) edit a cell: the Office panel's own save operation
sid = sheet.target['id']; got = ok('office.get', {'id': sid}); new = copy.deepcopy(got['document'])
cell = new['sheets'][0]['cells']['B2']; print('   B2 before:', cell.get('value'))
print('   B2 cell:', cell); cell['value'] = '12.5' if isinstance(cell['value'], str) else 12.5
r = d('office.save', {'id': sid, 'expected_revision': got['revision'], 'document': new})
print('office.save ->', r['ok'], (list(r['result'].keys()) if r['ok'] else r['error']))
if r['ok']: print('   version now', r['result'].get('version'), '| keys', {x: str(r['result'][x])[:70] for x in r['result'] if x not in ('document',)})
head = since(head, 'EDIT A CELL (office.save)')
# ---- (c) run staC
line = 'office.get {"id":"%s"} | select source_state.state,origin.pdf.page_index' % sid
r = d('language.run', {'text': line}); print('language.run ->', r['ok'], (r['result'].get('rows') if r['ok'] else r['error']))
head = since(head, 'RUN staC (language.run)')
# ---- (d) save a page (documents.save) the way the Documents room does
dg = ok('documents.get', {'id': doc.target['id']}); dd = dg['document']
blocks = copy.deepcopy(dd['blocks']); blocks[1]['text'] = blocks[1]['text'] + ' (probe)'
r = d('documents.save', {'id': dd['id'], 'expected_revision': dd['revision'], 'blocks': blocks})
print('documents.save ->', r['ok'], (r['result'].get('summary') if r['ok'] and isinstance(r['result'], dict) else r.get('error')))
head = since(head, 'SAVE A PAGE (documents.save)')
# ---- (e) propose a change to a file and approve it (the owner's decision)
r = d('files.write', {'path': 'notes/probe.txt', 'text': 'first line\n'}); print('files.write ->', r['ok'], r.get('error') or {x: r['result'][x] for x in list(r['result'])[:6]})
if not r['ok']:
    print('  mkdir:', d('files.mkdir', {'name': 'notes'}).get('error') or 'ok'); r = d('files.write', {'path': 'notes/probe.txt', 'text': 'first line\n'}); print('files.write ->', r['ok'], r.get('error') or list(r['result']))
r = d('files.propose', {'path': 'notes/probe.txt', 'text': 'first line\nsecond line\n', 'why': 'probe: add a line'}); print('files.propose ->', r['ok'], r.get('error') or {x: str(r['result'][x])[:60] for x in r['result']})
pid = (r.get('result') or {}).get('id')
head = since(head, 'A CHANGE IS PROPOSED (files.write, files.propose)')
if pid:
    r = d('files.decide', {'id': pid, 'apply': True}); print('files.decide ->', r['ok'], r.get('error') or {x: str(r['result'][x])[:60] for x in r['result']})
    head = since(head, 'THE OWNER APPROVES (files.decide apply)')
T1 = time.time()
# ---- reading it back
print('\n== READ BACK ==')
st = ok('ledger.journal.status'); print('head now', st['head'])
N = 6
r = ok('ledger.journal.read', {'after': str(st['head'] - N), 'limit': N}); print('LAST %d  (ledger.journal.read after=head-N): %s' % (N, [(e['seq'], e['operation'], e['state']) for e in r['events']]), '| cursor', r['cursor'], 'has_more', r['has_more'], 'gap', r['gap'])
r = ok('ledger.activity', {'query': 'office.save', 'limit': 5}); print('ledger.activity query=office.save:', [(e['seq'], e['operation'], e['state']) for e in r['events']])
r = ok('ledger.activity', {'query': 'ledger.view', 'limit': 50}); print('ledger.activity query=ledger.view:', [(e['seq'], round(e['at'],1), e['detail']) for e in r['events']])
r = ok('ledger.activity', {'after': 'not-an-event', 'limit': 2}); print('ledger.activity after=<unknown id>: gap', r['gap'], 'cursor', r['cursor'], len(r['events']))
r = ok('ledger.context'); print('ledger.context keys:', sorted(r.keys())); print('   desktop:', r['desktop'], '| connection', r['desktop_connection'], '| active_jobs', r['active_jobs'], '| recent_activity events', len(r['recent_activity']['events']), 'last', brief(r['recent_activity']['events'][-1]))
for line in ('activity {"after":"%d"} | where at over %f | select seq,at,operation,state,detail | take 8' % (0, T0),
             'activity {"after":"%d","limit":200} | where state=REQUEST_COMPLETED | where at over %f | group operation | count' % (head - 60 if head > 60 else 0, T0),
             'activity | where operation=ledger.view | select at,detail'):
    r = d('language.run', {'text': line}); print('staC:', line); print('    ->', r['ok'], json.dumps(r['result'].get('rows') if r['ok'] else r['error'])[:900])
r = ok('ledger.trail.list', {'limit': 8}); print('ledger.trail.list:', {x: r[x] for x in r if x != 'intents'})
for i in r['intents'][:8]: print('    ', {x: (round(i[x],3) if x=='created' else i[x]) for x in ('id','operation','created','request_state','scope_check','work','job_ids')})
r = ok('ledger.trail.inspect', {'id': r['intents'][0]['id']}); print('ledger.trail.inspect:', json.dumps({x: r[x] for x in ('intent','jobs','artifacts','contents')})[:700])
r = ok('ledger.awareness'); print('ledger.awareness:', {x: r[x] for x in ('consumer','state','cursor','head','backlog','jobs')}, '| projection keys', list(r['projection']))
# per-record stores
r = ok('documents.get', {'id': dd['id']}); print('documents.get events:', r['events'][:4], '| summary', r['summary'])
r = ok('office.get', {'id': sid}); print('office.get after save: version', r['version'], '| keys', sorted(r))
r = ok('office.list'); print('office.list rows:', [{x: str(row[x])[:40] for x in row} for row in r['documents']][:3])
r = ok('files.story', {'path': 'notes/probe.txt'}); print('files.story:', json.dumps(r)[:900])
r = ok('files.versions', {'path': 'notes/probe.txt'}); print('files.versions:', json.dumps(r)[:500])
r = ok('matrix.list', {}) if 'matrix.list' in __import__('workbench.engineering_kernel', fromlist=['CAPABILITIES']).CAPABILITIES else None
print('matrix.list:', json.dumps(r)[:1200] if r else r)
r = ok('stac.history'); print('stac.history:', json.dumps(r)[:600])
r = ok('ledger.session.read'); print('ledger.session.read:', r)
# the profile catalog's own event rows for Office objects
import os
from workbench import locations
try:
    cat = sqlite3.connect(str(locations.concern_home() / 'catalog.sqlite3'))
except Exception as exc: cat = None; print('catalog open failed', exc)
print('concern_home:', locations.concern_home())
for cand in (os.environ.get('ARC1_WORKBENCH_CONFIG_HOME','') + '/concern/catalog.sqlite3',):
    try:
        c = sqlite3.connect('file:' + cand + '?mode=ro', uri=True); print('catalog events (%s):' % cand)
        for row in c.execute('select seq,at,operation,object_id,detail from events order by seq'): print('    ', row)
        print('   office_history rows:', c.execute('select id,version from office_history').fetchall())
    except Exception as exc: print('  catalog', cand, exc)
print('session.state keys:', sorted(w.session.state.keys()))
print('session recent:', w.session.state.get('recent'), '| workspace:', w.session.state.get('workspace'), '| _viewer_recent:', getattr(w, '_viewer_recent', None))
