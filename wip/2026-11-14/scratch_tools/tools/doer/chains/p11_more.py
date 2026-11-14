exec(open('/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/doer/chains/common.py').read())
import os, time
from pathlib import Path
from PySide6.QtWidgets import QLabel
from workbench import context_menu as cm
from workbench.shell2 import to_console
face = w.shell2.face; con = w.console; box = w.type_bar.box
def cards(n=1):
    out = [face.lines.itemAt(i).widget() for i in range(face.lines.count()) if face.lines.itemAt(i).widget() is not None]
    return out[-n:]
def words(card): return ' / '.join(l.text().replace('​', '')[:240].replace('\n', ' ⏎ ') for l in card.findChildren(QLabel)[:8])
def tail(n=3): return [l[:200] for l in con.output.toPlainText().replace('​', '').splitlines() if l.strip()][-n:]
print('=========== A. the functions that run a line')
to_console(w, 'kernel', '/files.write {"path":"notes/t.txt","text":"t"}'); settle(30, 3); print('   to_console kernel (execute scope):', tail(2), '| exists:', (Path(k.root) / 'Files/notes/t.txt').exists())
to_console(w, 'kernel', '/files.trash {"path":"notes/t.txt"}'); settle(30, 3); print('   to_console kernel files.trash [%s]:' % CAPABILITIES['files.trash'], tail(2), '| pending:', con.pending_approval)
to_console(w, 'kernel', '/files.restore {"id":"x"}'); settle(30, 3); print('   to_console kernel files.restore [%s]:' % CAPABILITIES['files.restore'], tail(1), '| pending:', con.pending_approval, '| box:', repr(box.text()))
con.pending_approval = None; box.clear()
try: print('   context_menu.run_stac (a read):', cm.run_stac(w, 'documents.list | pick documents | count')); settle(20, 2)
except Exception as e: print('   run_stac raised', type(e).__name__, e)
try: cm.run_stac(w, 'files.write {"path":"x","text":"y"}')
except Exception as e: print('   context_menu.run_stac (a write) raised %s: %s' % (type(e).__name__, e))
print('   context_menu.dispatch (no UI):', short(cm.dispatch(w, 'files.write', {'path': 'notes/u.txt', 'text': 'u'}), 200))
print('   face.execute (Talk):'); face.execute('files.write', {'path': 'notes/v.txt', 'text': 'v'}, 'files.write {…}'); settle(20, 2); print('      ', words(cards(1)[0])[:200])
print('\n=========== B. a read operation line taken as a step in the Field (D, then a digit)')
w.a_field.trigger(); settle(); v = w.field_page.view; page = w.field_page
src = next(o for o in v.field.objects if o.kind == 'source'); v.field.select(src.id); v.update(); settle(5, 2)
QTest.keyClick(v, Qt.Key_D); settle(60, 4); print('   steps:', [(s.words, s.kind, s.line[:40]) for s in page.steps])
QTest.keyClick(v, Qt.Key_2); settle(80, 5); c = cards(1)[0]; print('   digit 2 (/references.impact, a read) ->', words(c)[:500]); print('      answered:', getattr(c, 'answered', None), '| has Run:', hasattr(c, 'run'))
QTest.keyClick(v, Qt.Key_4); settle(80, 5); c = cards(1)[0]; print('   digit 4 (Watch it, execute) ->', words(c)[:300], '| has Run:', hasattr(c, 'run'))
print('\n=========== C. work orders: what a step may be, and checks')
home = Path(os.environ['HOME']); d = home / 'Clock'; d.mkdir(exist_ok=True); (d / 'note.md').write_text('hands: blue\n')
pre = k.dispatch('imports.preview', {'source': str(d), 'profile': 'CODE'}, p)['result']
ca = k.dispatch('imports.accept', {'id': pre['id'], 'expected_digest': pre['content_digest'], 'for_slate': True}, p)['result']
pre2 = k.dispatch('imports.preview', {'source': str(d), 'profile': 'CODE'}, p)['result']
cn = k.dispatch('imports.accept', {'id': pre2['id'], 'expected_digest': pre2['content_digest']}, p)['result']
proj = k.dispatch('projects.create', {'title': 'Clock', 'intent': 'Make a working clock'}, p)['result']
asg = k.dispatch('assignments.create', {'project': proj['id'], 'request': 'Use black hands', 'interpretation': 'Prepare a revised working note', 'intended_output': 'A reviewed note', 'success': ['Note says black'], 'stop': ['Changed inputs'], 'inputs': []}, p)
print('   assignment with no inputs:', asg['ok'], asg.get('error')); asg = asg['result']
budget = {'seconds': 300, 'steps': 10, 'tokens': 0, 'memory_mb': 128, 'output_bytes': 1048576, 'files': 10}
def create(steps, copies=None, title='t'):
    return L('work.create', {'title': title, 'assignment': asg['id'], 'copies': copies or [ca['id']], 'steps': steps, 'budget': budget, 'expires': time.time() + 3600}, quiet=True)
create([{'key': 'W', 'operation': 'files.write', 'arguments': {'path': 'x', 'text': 'y'}, 'after': []}])
create([{'key': 'Q', 'operation': 'work.query', 'arguments': {'text': 'documents.list | pick documents | count'}, 'after': []}])
create([{'key': 'Q', 'operation': 'work.query', 'arguments': {'text': 'work.read {"copy":"%s","path":"note.md"} | select text,sha256' % ca['id']}, 'after': []}], title='query ok') and print('   work.query over work.read: accepted')
create([{'key': 'R', 'operation': 'work.read', 'arguments': {'copy': cn['id'], 'path': 'note.md'}, 'after': []}], copies=[cn['id']])
steps = [
 {'key': 'Read', 'operation': 'work.read', 'arguments': {'copy': ca['id'], 'path': 'note.md'}, 'after': []},
 {'key': 'Draft', 'operation': 'changes.propose', 'arguments': {'copy': ca['id'], 'operations': [{'op': 'WRITE', 'path': 'note.md', 'base_sha256': {'$step': 'Read', 'path': ['sha256']}, 'text': 'hands: black\n'}]}, 'after': ['Read']},
 {'key': 'Apply', 'operation': 'changes.apply', 'arguments': {'id': {'$step': 'Draft', 'path': ['id']}, 'expected_digest': {'$step': 'Draft', 'path': ['content_digest']}}, 'after': ['Draft']},
 {'key': 'ReadBack', 'operation': 'work.read', 'arguments': {'copy': ca['id'], 'path': 'note.md'}, 'after': ['Apply'], 'require': [{'path': ['text'], 'equals': 'hands: BLACK\n'}]}]
wk = create(steps, title='four steps with a check that will fail')
k.dispatch('work.authorize', {'id': wk['plan']['id'], 'expected_digest': wk['content_digest']}, p)
for i in range(5):
    r = k.dispatch('work.advance', {'id': wk['plan']['id']}, p)['result']; print('   advance ->', r)
got = k.dispatch('work.get', {'id': wk['plan']['id']}, p)['result']
print('   state:', got['state']['state'], got['state']['reason'], '| steps:', [(s['key'], s['state'], s.get('reason')) for s in got['steps']])
print('   working copy file now (the grant covered the apply, no second approval):', repr((Path(k.root) / 'Files' / ca['work'] / 'note.md').read_text()), '| original:', repr((d / 'note.md').read_text()))
L('work.review', {'id': wk['plan']['id'], 'decision': 'ACCEPT', 'note': 'x'}, 'a failed-check order cannot be accepted')
L('work.resume', {'id': wk['plan']['id']}, 'resume a failed step?')
print('   events:', [e['event'] for e in got['events']])
print('   agenda waiting:', [(r['kind'], r.get('state'), r.get('reason'), r['title']) for r in k.dispatch('agenda.view', {}, p)['result']['waiting'] if r['kind'] == 'work'])
S('work.get {"id":"%s"} | pick events | select event,detail' % wk['plan']['id'])
