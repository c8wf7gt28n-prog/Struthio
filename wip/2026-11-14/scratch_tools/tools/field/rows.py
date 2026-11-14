import json, os, sys, tempfile, shutil
from pathlib import Path
from unittest.mock import patch
S = Path('/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad')
PROGRAM = Path(sys.argv[1]).resolve()
RUN = Path(tempfile.mkdtemp(prefix='run-', dir=str(S / 'tools/field/run'))); HOME = RUN / 'home'; HOME.mkdir()
shutil.copytree(S / 'work/demo/After_Hours_07', RUN / 'ws'); shutil.copytree(S / 'work/demo/After_Hours_07-profile', RUN / 'prof')
os.environ.update(PYTHONDONTWRITEBYTECODE='1', QT_QPA_PLATFORM='offscreen', ARC_LEDGER_EMBEDDED='1', ARC_LEDGER_DISABLE_BOOK_WATCHER='1', HOME=str(HOME),
                  ARC1_WORKBENCH_CONFIG_HOME=str(RUN / 'prof'), ARC_LEDGER_CONCERN=str(HOME / 'Concern'), ARC_LEDGER_WORKSPACE=str(RUN / 'ws'))
os.chdir(RUN); sys.path.insert(0, str(PROGRAM)); sys.dont_write_bytecode = True
from workbench import clip, session_power
from workbench.engineering_kernel import Kernel, operator
patch.object(Kernel, 'launch', side_effect=AssertionError('No worker launch')).start(); patch.object(Kernel, 'submit', side_effect=AssertionError('No job submission')).start()
k = Kernel(RUN / 'ws'); p = operator()
import subprocess; patch.object(subprocess, 'Popen', side_effect=OSError('held')).start()
for op in ('office.list', 'documents.list', 'investigation.list', 'methods.list', 'jobs.list', 'agenda.view', 'files.list'):
    v = k.dispatch(op, {}, p)
    r = v.get('result') if v.get('ok') else v.get('error')
    rows = r if isinstance(r, list) else next((x for x in (r or {}).values() if isinstance(x, list)), None) if isinstance(r, dict) else None
    print(op, 'ok' if v.get('ok') else 'REFUSED', '| keys:', list(r.keys())[:8] if isinstance(r, dict) else type(r).__name__, '| rows:', len(rows) if rows is not None else None, '| first:', json.dumps(rows[0], default=str)[:330] if rows else None)
