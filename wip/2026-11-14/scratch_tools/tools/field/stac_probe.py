"""Orchestrator's probe: which staC lines run against the restored worked case (read-only, through language.run)."""
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
from workbench.engineering_kernel import Kernel, operator
patch.object(Kernel, 'launch', side_effect=AssertionError('No worker launch')).start(); patch.object(Kernel, 'submit', side_effect=AssertionError('No job submission')).start()
k = Kernel(RUN / 'ws'); p = operator()
import subprocess; patch.object(subprocess, 'Popen', side_effect=OSError('held')).start()
def call(op, args=None):
    v = k.dispatch(op, args or {}, p); return v['result'] if v.get('ok') else None
sheet = call('office.list')['documents'][0]['id']; docs = call('documents.list')['documents']; calc = docs[0]['id']; page = docs[-1]['id']
inv = call('investigation.list')['investigations'][0]['id']; claim = call('investigation.sheet', {'id': inv})['learned'][0]['id']
ns = call('intake.namespaces')['namespaces'][0]['id']; item = call('intake.items', {'namespace': ns})['items'][0]['id']
calc = next(d['id'] for d in docs if 'power' in d['title']); q = call('investigation.sheet', {'id': inv})['unresolved'][0]['id']; job = call('jobs.list')[0]['id']
lines = [
 'documents.get {"id":"%s"} | pick document.derivation.inputs' % calc, 'documents.get {"id":"%s"} | pick document.derivation | select sheet,expression,unit' % calc,
 'documents.get {"id":"%s"} | select revision,source_state.state' % calc, 'documents.get {"id":"%s"} | pick document | select title,derivation.expression' % page,
 'office.get {"id":"%s"} | select revision,source_state.state,origin.pdf.page_index' % sheet, 'office.list | pick documents | where id=%s' % sheet,
 'investigation.path {"claim":"%s"} | pick path | select kind,address,direction,source_state,outcome' % claim,
 'investigation.sheet {"id":"%s"} | pick unresolved | select text,evidence_state,review' % inv,
 'intake.items {"namespace":"%s"} | pick items | where id=%s | select name,admission,bytes' % (ns, item),
 'jobs | where id=%s | select tool,state,goal' % job, 'jobs | where state is not Completed | select tool,state',
 'network.observe | pick connections | where process=claude | select remote,rport,state | take 3', 'network.observe | pick connections | where remote=160.79.104.10 | select process,rport,state | take 3',
 'network.observe | pick connections | where lport=2024 | select process,local,state', 'network.observe | pick interfaces | where name=eth0 | select name,up,rx_bps,tx_bps',
]
for text in lines:
    v = k.dispatch('language.run', {'text': text}, p)
    if v.get('ok'):
        r = v['result']; out = r.get('value', r.get('rows', r)) if isinstance(r, dict) else r
        print('OK   ', text[:96]); print('        ->', json.dumps(out, default=str)[:230], '| keys:', list(r.keys())[:8] if isinstance(r, dict) else '')
    else: print('REFUSED', text[:96], '|', str(v.get('error'))[:160])
