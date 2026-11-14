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
    try: a = k.dispatch(op, args or {}, P)
    except Exception as e: return {'EXC': repr(e)}
    return a.get('result') if a.get('ok') else {'REFUSED': a.get('error')}
ns = call('intake.namespaces')['namespaces'][0]
print('references.status:', json.dumps({k2: v for k2, v in call('references.status', {'namespace': ns['id']}).items() if k2 in ('current_sources', 'unavailable', 'generation')}, default=str)[:1500])
for row in call('office.list')['documents']:
    got = call('office.get', {'id': row['id']})
    pdf = (got.get('origin') or {}).get('pdf') or {}
    print('office', row['id'], row['title'], '| source_state:', json.dumps(got.get('source_state'))[:400], '| origin keys', sorted((got.get('origin') or {}).keys()), '| pdf', {k2: pdf.get(k2) for k2 in ('item', 'page_index', 'page', 'decision', 'layer')}, '| revision', got.get('revision'))
for row in call('documents.list')['documents']:
    got = call('documents.get', {'id': row['id']})
    d = (got.get('document') or {}).get('derivation')
    print('document', row, '\n   source_state:', json.dumps(got.get('source_state'))[:500], '\n   derivation:', json.dumps(d)[:1600] if d else None)
for row in call('investigation.list')['investigations']:
    print('investigation', {k2: row.get(k2) for k2 in ('id', 'question', 'state')})
    sheet = call('investigation.sheet', {'id': row['id']})
    print('  sheet keys', sorted(sheet.keys()))
    for group in ('learned', 'unresolved'):
        for claim in sheet.get(group, ()):
            print('  ', group, json.dumps(claim, default=str)[:700])
            path = call('investigation.path', {'claim': claim['id']})
            for step in path.get('path', ()):
                print('       step', json.dumps(step, default=str)[:600])
print('conditions:', json.dumps(call('conditions.list'), default=str)[:1500])
