"""Shared holds for read-only probes: disposable home/profile, no worker launch, no job submission, no provider request."""
import json, os, sys, tempfile, shutil
from pathlib import Path
from unittest.mock import patch
S = Path('/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad')
PROGRAM = S / 'work/graphite'
RUN = Path(tempfile.mkdtemp(prefix='run-', dir=str(S / 'tools/objects/run'))); HOME = RUN / 'home'; HOME.mkdir()
def setup(profile=None, workspace=None):
    os.environ.update(PYTHONDONTWRITEBYTECODE='1', QT_QPA_PLATFORM='offscreen', ARC_LEDGER_EMBEDDED='1', ARC_LEDGER_DISABLE_BOOK_WATCHER='1', HOME=str(HOME),
                      ARC1_WORKBENCH_CONFIG_HOME=str(profile or RUN / 'profile'), ARC_LEDGER_CONCERN=str(HOME / 'Concern'))
    if workspace: os.environ['ARC_LEDGER_WORKSPACE'] = str(workspace)
    os.environ.pop('ARC_LEDGER_XSESSION', None)
    os.chdir(RUN); sys.path.insert(0, str(PROGRAM)); sys.dont_write_bytecode = True
    from workbench import clip, session_power
    from workbench.engineering_kernel import Kernel
    def held_power(request): raise OSError('no login session (held)')
    patch.object(clip, '_request', side_effect=AssertionError('No provider request')).start()
    patch.object(Kernel, 'launch', side_effect=AssertionError('No worker launch')).start()
    patch.object(Kernel, 'submit', side_effect=AssertionError('No job submission')).start()
    patch.object(session_power, 'system', side_effect=held_power).start()
def copy_case():
    """A disposable copy of the restored After Hours 07 workspace and profile (the restored folders stay as restored)."""
    src = S / 'work/demo'
    shutil.copytree(src / 'After_Hours_07', RUN / 'ws'); shutil.copytree(src / 'After_Hours_07-profile', RUN / 'prof')
    return RUN / 'ws', RUN / 'prof'
def short(v, n=200):
    s = json.dumps(v, default=str, ensure_ascii=False); return s if len(s) <= n else s[:n] + '...<+%d>' % (len(s) - n)
def shape(v, depth=2, ind=0, n=110):
    pad = ' ' * ind
    if isinstance(v, dict):
        for k, x in v.items():
            if isinstance(x, (dict, list)) and depth > 0 and x:
                print('%s%s: %s(%d)' % (pad, k, type(x).__name__, len(x))); shape(x, depth - 1, ind + 2, n)
            else: print('%s%s: %s' % (pad, k, short(x, n)))
    elif isinstance(v, list):
        if v:
            print('%s[0] of %d:' % (pad, len(v)))
            if isinstance(v[0], (dict, list)): shape(v[0], depth - 1, ind + 2, n)
            else: print(pad + '  ' + short(v[0], n))
def hold_processes():
    """Call after the Kernel (or window) exists: no child process may start. references.pdf.info and the PDF tab start a Python
    child (sdk/cli/arc1cli/pdf_evidence.py bounded(), stripped environment) that writes __pycache__ into the program tree."""
    import subprocess
    patch.object(subprocess, 'Popen', side_effect=OSError('No process start (held by the probe)')).start()
