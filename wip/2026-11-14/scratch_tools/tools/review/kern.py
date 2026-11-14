"""A Kernel on a disposable copy of the worked case "After Hours 07", with no window and no Qt.
usage:  kern.py SCRIPT.py     (run it with the scratch venv's python, from any directory)
The script is exec'd with:  k (the Kernel), p (the owner principal), d(op, args) -> result or {'ERROR': message},
                            field() -> the Field of the workspace as read now, root (the disposable workspace)
Every run starts from a fresh copy, so a script may write through the Kernel freely; nothing reaches the repository."""
import json, os, shutil, sys, tempfile
from pathlib import Path
S = Path('/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad')
PROGRAM = Path('/home/user/Struthio')
RUN = Path(tempfile.mkdtemp(prefix='kern-', dir=str(S / 'tools/review/run'))); HOME = RUN / 'home'; HOME.mkdir()
shutil.copytree(S / 'work/demo/After_Hours_07', RUN / 'ws'); shutil.copytree(S / 'work/demo/After_Hours_07-profile', RUN / 'prof')
os.environ.update(PYTHONDONTWRITEBYTECODE='1', ARC_LEDGER_EMBEDDED='1', ARC_LEDGER_DISABLE_BOOK_WATCHER='1', HOME=str(HOME),
                  ARC1_WORKBENCH_CONFIG_HOME=str(RUN / 'prof'), ARC_LEDGER_CONCERN=str(HOME / 'Concern'), ARC_LEDGER_WORKSPACE=str(RUN / 'ws'))
os.environ.pop('ARC_LEDGER_XSESSION', None)
os.chdir(RUN); sys.path.insert(0, str(PROGRAM)); sys.dont_write_bytecode = True
from workbench.engine import engineering
from workbench.engineering_kernel import operator
root = RUN / 'ws'; k = engineering(root); p = operator()
def d(op, args=None):
    r = k.dispatch(op, args or {}, p)
    return r['result'] if r.get('ok') else {'ERROR': (r.get('error') or {}).get('message')}
def field():
    from workbench.field_source import read_field
    return read_field(k, p)[0]
exec(open(sys.argv[1]).read())
print('DONE')
