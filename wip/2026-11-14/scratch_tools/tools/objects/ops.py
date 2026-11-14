import sys; sys.path.insert(0, '/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/objects')
import common; common.setup()
from workbench.engineering_kernel import CAPABILITIES
from workbench.engineering_cli import schemas
from collections import Counter
sc = schemas()
print('operations', len(CAPABILITIES), Counter(CAPABILITIES.values()))
pref = Counter(k.split('.')[0] for k in CAPABILITIES); print(sorted(pref.items()))
want = sys.argv[1:] 
for k in sorted(CAPABILITIES):
    if any(k.startswith(w) for w in want):
        s = sc[k]; print('%-44s %-8s req=%s opt=%s' % (k, CAPABILITIES[k], s['required'], sorted(set(s['properties']) - set(s['required']))))
