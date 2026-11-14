import json, time, os, sqlite3
from pathlib import Path
k = w.ledger_bridge.kernel; p = operator()
def d(op, a=None): return k.dispatch(op, a or {}, p)
def stamp(t): return time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(t))
# session boundaries in the journal: one ledger.open READY per launch
r = d('ledger.activity', {'query': 'ledger.open', 'limit': 50})['result']['events']
print('ledger.open rows (one per launch):', [(e['seq'], stamp(e['at']), e['origin'], e['state']) for e in r])
last_open = r[-1]['seq']; prev_last = d('ledger.journal.read', {'after': str(last_open - 2), 'limit': 1})['result']['events'][0]
print('last row of the previous session: seq %d %s %s at %s  -> away for %.1f days' % (prev_last['seq'], prev_last['operation'], prev_last['state'], stamp(prev_last['at']), (r[-1]['at'] - prev_last['at']) / 86400))
print('ledger.session.read:', {q: v for q, v in d('ledger.session.read')['result'].items()})
print('what the window publishes about now (ledger.context.desktop), in three places:')
print('   workspace in front:', d('ledger.context')['result']['desktop'])
w.a_field.trigger(); settle(900, 2); print('   Field in front    :', d('ledger.context')['result']['desktop'], '| host._field_active', w._field_active, '| face', w.field_page.face)
v = w.field_page.view; sel = v.selected(); print('   Field selection   :', sel.id if sel else None, '| host.selection_context', w.selection_context)
w.show_start(); settle(900, 2); print('   Home in front     :', d('ledger.context')['result']['desktop'])
w.a_field.trigger(); settle(); doc = next(o for o in v.field.objects if o.kind == 'calculation'); v.field.select(doc.id); v.update(); QTest.keyClick(v, Qt.Key_Return); settle(900, 2)
print('   a page in front   :', d('ledger.context')['result']['desktop'])
print('open tabs (Qt only):', [(type(w.tabs.widget(i)).__name__, w.tabs.tabText(i)) for i in range(w.tabs.count())], '| current', w.tabs.currentIndex())
print('tabs.snapshot() (what save_session writes to session.json workspace):', json.dumps(w.tabs.snapshot()))
tab = w.tabs.currentWidget(); print('current tab attributes naming its record:', {q: getattr(tab, q) for q in ('ident', 'document_id', 'current_id', 'doc_id') if hasattr(tab, q)}, '| property cabinet_node:', tab.property('cabinet_node'))
print('documents.list row keys:', sorted(d('documents.list')['result']['documents'][0].keys()))
print('agenda.view waiting:', json.dumps(d('agenda.view')['result']['waiting'])[:400])
x = d('ledger.organizer')['result']; print('ledger.organizer keys:', sorted(x.keys())); print('   ', json.dumps({q: x[q] for q in x if q not in ('tasks',)})[:700])
x = d('ledger.related', {'text': 'startup pulse rail limit settled power'})['result']; print('ledger.related:', json.dumps(x)[:500])
x = d('ledger.object.current')['result']; print('ledger.object.current:', json.dumps(x)[:200])
x = d('memory.tasks'); print('memory.tasks:', json.dumps(x.get('result') or x.get('error'))[:300])
x = d('ledger.cabinet', {}) if False else None
# what a calm watermark gives: events since the Field last caught up, by program
from workbench import explore
views = [(row[0], row[7]) for row in explore.VIEWS]
d('ledger.awareness.catch_up', {'consumer': 'field', 'limit': 200}); a = d('ledger.awareness', {'consumer': 'field'})['result']; mark = a['cursor']
sid = 'owner:5a43beee28224c4e818af7b985cdb535'; got = d('office.get', {'id': sid})['result']; import copy; new = copy.deepcopy(got['document']); new['sheets'][0]['cells']['A1']['value'] = 'Parameter*'
d('office.save', {'id': sid, 'expected_revision': got['revision'], 'document': new}); d('language.run', {'text': 'jobs | where state=Completed | count'})
a = d('ledger.awareness', {'consumer': 'field'})['result']; print('\nafter two more actions: ledger.awareness {consumer: field} ->', {q: a[q] for q in ('state', 'cursor', 'head', 'backlog')})
new_rows = d('ledger.journal.read', {'after': str(mark), 'limit': 200})['result']['events']
seen = {}
for e in new_rows:
    key = next((key for key, prefixes in views if e['operation'].startswith(prefixes)), None)
    if e['state'] != 'REQUEST_RECEIVED': seen[key or e['operation']] = seen.get(key or e['operation'], 0) + 1
print('   since the mark, by shelf program (or bare operation when no program owns it):', seen)
# per-object rows for Office, straight from the store the service itself uses (no operation reads them)
from workbench import office_service
with office_service.store().catalog.db() as db:
    print('office catalog events (office_service.store().catalog.db()):', [(stamp(r[0]), r[1], r[2]) for r in db.execute("SELECT at,operation,object_id FROM events WHERE object_id LIKE 'owner:%' ORDER BY seq")])
print('office_service.path():', str(office_service.path()).replace(os.environ['ARC1_WORKBENCH_CONFIG_HOME'], '<config>'))
# matrix rows name the objects a staC line read
rows = d('matrix.list', {'limit': 50})['result']['rows']; print('matrix.list rows:', len(rows), '| e.g.', [(stamp(r['created']), r['program'][:70], r['outcome']) for r in rows[:3]])
# session file on disk after a save
w.save_session(); s = json.loads(Path(w.session.path).read_text()); print('session.json after save_session: workspace =', json.dumps(s.get('workspace')), '| recent', s.get('recent'), '| last_surface', s['view_preferences'].get('last_surface'), '| console keys', list((s.get('console') or {}).keys()), '| finder', s.get('finder'), '| selection_context' , s.get('selection_context'))
