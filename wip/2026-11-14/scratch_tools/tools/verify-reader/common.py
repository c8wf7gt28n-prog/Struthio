"""Reviewer probe support: a disposable copy of the case, the holds, a Kernel (no window)."""
import json, os, sys, tempfile, shutil
from pathlib import Path
from unittest.mock import patch
S = Path('/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad')
PROGRAM = S / 'work/wt'
RUN = Path(tempfile.mkdtemp(prefix='run-', dir=str(S / 'tools/verify-reader/run'))); HOME = RUN / 'home'; HOME.mkdir()
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
import subprocess
def hold_processes():
    patch.object(subprocess, 'Popen', side_effect=OSError('No process start (held by the probe)')).start()
P = operator()
def call(k, op, args=None):
    try: a = k.dispatch(op, args or {}, P)
    except Exception as e: return {'EXC': repr(e)}
    return a.get('result') if a.get('ok') else {'REFUSED': a.get('error')}
def dump(field, reader=None):
    print('title:', repr(field.title), '| census:', field.census(), '| note:', repr(field.note), '| refused:', getattr(reader, 'refused', None), '| unread:', getattr(reader, 'unread', None))
    for rank in field.ranks():
        print(' ', rank, field.rank_title(rank))
        for i in field.column(rank):
            o = field.get(i); print('     ', o.kind, '|', (o.tag or '-'), '|', o.title[:46], '| state=%r' % o.state, '|', o.lines, '| where:', o.where, '| role:', o.role[:30])
    for l in field.links: print('    link', field.get(l.source).title[:26], '->', field.get(l.target).title[:30], '|', l.label, '| stale', l.stale)
