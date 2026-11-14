import sys; sys.path.insert(0, '/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/objects')
import common; ws, prof = common.copy_case(); common.setup(profile=prof, workspace=ws)
from workbench.engineering_kernel import Kernel, operator
k = Kernel(ws); p = operator(); common.hold_processes()
print('principal', p.identity, sorted(p.scopes), p.mode)
def call(op, args=None, quiet=False):
    v = k.dispatch(op, args or {}, p)
    if not v['ok']:
        print('!!', op, args, v['error']); return None
    return v['result']
for op, args in [('documents.list', {}), ('office.list', {}), ('investigation.list', {}), ('conditions.list', {}), ('methods.list', {}), ('jobs.list', {}),
                 ('evidence.list', {}), ('intake.namespaces', {}), ('assignments.list', {}), ('agenda.view', {}), ('copies.list', {}), ('changes.workspaces', {}),
                 ('references.packets', {}), ('ledger.project.status', {}), ('problems.list', {}) if False else ('ledger.context', {})]:
    r = call(op, args); print('=====', op, type(r).__name__, (len(r) if hasattr(r, '__len__') else ''))
    common.shape(r, depth=3, n=170)
