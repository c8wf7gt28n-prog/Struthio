import sys, time, json; sys.path.insert(0, '/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/objects')
import common; common.setup()
from workbench import locations, host_observations
from workbench.engineering_kernel import Kernel, operator
root = locations.office(common.HOME / 'Concern' / 'Office'); k = Kernel(root); p = operator()
a = host_observations.snapshot(); time.sleep(0.6); b = host_observations.snapshot()
print('host_observations.snapshot() ->'); print(json.dumps(b, indent=1))
print('cpu_percent(prev,cur) ->', host_observations.cpu_percent(a['cpu']['counters'], b['cpu']['counters']))
def call(op, args=None):
    v = k.dispatch(op, args or {}, p)
    if not v['ok']: print('!!', op, v['error']); return None
    return v['result']
n = call('network.observe'); time.sleep(0.5); n = call('network.observe')
print('network.observe keys', sorted(n)); print('interfaces', json.dumps(n['interfaces'], indent=1)[:1500])
print('connections[0:2]', json.dumps(n['connections'][:2], indent=1)[:1500]); print('counts', n['counts'], 'rest', n['rest'], 'capture', common.short(n['capture'], 500)); print('notes', n['notes'], 'filter', n['filter'])
for op in ('ledger.resources', 'ledger.resources.observation', 'ledger.machine', 'ledger.operations'):
    r = call(op); print('=====', op); common.shape(r, depth=2, n=160) if r else None
