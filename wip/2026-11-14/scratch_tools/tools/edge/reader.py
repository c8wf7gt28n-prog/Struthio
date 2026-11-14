"""Reviewer probe: raw records vs. the derived Field (no window)."""
import json, os, sys, tempfile, shutil
from pathlib import Path
from unittest.mock import patch
S = Path('/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad')
PROGRAM = Path('/home/user/Struthio')
RUN = Path(tempfile.mkdtemp(prefix='run-', dir=str(S / 'tools/edge/run'))); HOME = RUN / 'home'; HOME.mkdir()
shutil.copytree(S / 'work/demo/After_Hours_07', RUN / 'ws'); shutil.copytree(S / 'work/demo/After_Hours_07-profile', RUN / 'prof')
os.environ.update(PYTHONDONTWRITEBYTECODE='1', QT_QPA_PLATFORM='offscreen', ARC_LEDGER_EMBEDDED='1', ARC_LEDGER_DISABLE_BOOK_WATCHER='1', HOME=str(HOME),
                  ARC1_WORKBENCH_CONFIG_HOME=str(RUN / 'prof'), ARC_LEDGER_CONCERN=str(HOME / 'Concern'), ARC_LEDGER_WORKSPACE=str(RUN / 'ws'))
os.chdir(RUN); sys.path.insert(0, str(PROGRAM)); sys.dont_write_bytecode = True
from workbench import clip, session_power
from workbench.engineering_kernel import Kernel, operator
patch.object(clip, '_request', side_effect=AssertionError('No provider request')).start()
patch.object(Kernel, 'launch', side_effect=AssertionError('No worker launch')).start()
patch.object(Kernel, 'submit', side_effect=AssertionError('No job submission')).start()
patch.object(session_power, 'system', side_effect=OSError('held')).start()
k = Kernel(RUN / 'ws')
import subprocess; patch.object(subprocess, 'Popen', side_effect=OSError('No process start (held by the probe)')).start()
P = operator()
def call(op, args=None):
    try:
        a = k.dispatch(op, args or {}, P)
    except Exception as e:
        return {'EXC': repr(e)}
    return a
def show(tag, value, limit=2500):
    text = json.dumps(value, indent=1, default=str)
    print('\n#### ' + tag); print(text[:limit] + (' …[%d more]' % (len(text) - limit) if len(text) > limit else ''))
mode = sys.argv[1] if len(sys.argv) > 1 else 'raw'
if mode == 'raw':
    ns = call('intake.namespaces'); show('intake.namespaces', ns)
    for space in ns['result']['namespaces']:
        show('references.sources ' + space['id'], call('references.sources', {'namespace': space['id']}), 4000)
        show('intake.items ' + space['id'], call('intake.items', {'namespace': space['id']}), 4000)
    ol = call('office.list'); show('office.list', ol)
    for row in ol['result']['documents']:
        got = call('office.get', {'id': row['id']})['result']
        show('office.get ' + row['id'] + ' keys', sorted(got.keys()))
        show(' origin/source_state/revision', {k2: got.get(k2) for k2 in ('origin', 'source_state', 'revision', 'title', 'state')})
    dl = call('documents.list'); show('documents.list', dl)
    for row in dl['result']['documents']:
        got = call('documents.get', {'id': row['id']})['result']
        show('documents.get ' + row['id'] + ' keys', {'top': sorted(got.keys()), 'document': sorted((got.get('document') or {}).keys())})
        show(' derivation/source_state', {'derivation': (got.get('document') or {}).get('derivation'), 'source_state': got.get('source_state')}, 3000)
    il = call('investigation.list'); show('investigation.list', il)
    for row in il['result']['investigations']:
        sheet = call('investigation.sheet', {'id': row['id']})['result']
        show('investigation.sheet ' + row['id'], sheet, 9000)
        for claim in list(sheet.get('learned', ())) + list(sheet.get('unresolved', ())):
            show('investigation.path ' + claim['id'], call('investigation.path', {'claim': claim['id']}), 3500)
    show('conditions.list', call('conditions.list'), 3000)
else:
    from workbench.field_source import read_field
    field, refused = read_field(k, P)
    print('title:', repr(field.title)); print('census:', field.census()); print('refused:', refused)
    for rank in field.ranks():
        print(' ', rank, field.rank_title(rank))
        for i in field.column(rank):
            o = field.get(i); print('     ', o.id, '|', o.kind, '|', o.title[:50], '|', o.state, '|', o.lines, '|', o.where, '|', o.role[:40], '|', o.target)
    print('links kept:'); [print('   ', l.source, '->', l.target, '|', l.label, '|', l.stale) for l in field.links]
