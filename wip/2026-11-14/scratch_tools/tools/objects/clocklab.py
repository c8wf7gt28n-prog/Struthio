import sys, json; sys.path.insert(0, '/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/objects')
import common; common.setup()
from workbench import locations, clock_lab
from workbench.engineering_kernel import Kernel, operator
from collections import Counter
root = locations.office(common.HOME / 'Concern' / 'Office'); k = Kernel(root); p = operator()
def call(op, args=None):
    v = k.dispatch(op, args or {}, p)
    if not v['ok']: print('!!', op, args, v['error']); return None
    return v['result']
src = clock_lab.copy_inputs(common.HOME / 'Clock_Lab_I01'); print('copied inputs', sorted(x.name for x in src.iterdir()))
r = clock_lab.start(k, src, p); print('clock_lab.start keys', sorted(r))
print('project', {x: r['project'][x] for x in ('id', 'kind', 'title', 'revision', 'links')}, '| intent', r['project']['original_intent'][:120])
a = r['assignment']; print('assignment keys', sorted(a)); print('   request', a['original_request'][:100], '| project', a['project'] == r['project']['id'], '| inputs[0]', common.short({x: a['inputs'][0][x] for x in ('address', 'operation', 'arguments', 'revision')}, 300), '| questions', a['questions'][:2])
c = r['copy']; print('copy keys', sorted(c)); print('   ', common.short({x: c.get(x) for x in ('id', 'work', 'state', 'source', 'name', 'profile')}, 400))
pr = r['problem']; print('problem keys', sorted(pr)); print('   sources[0]', common.short(pr['sources'][0], 300), '| variables[0]', common.short(pr['variables'][0], 300), '| n variables', len(pr['variables']))
with k.db() as db: print('desk_records by kind', dict(db.execute('SELECT kind,count(*) FROM desk_records GROUP BY kind').fetchall()))
for op, args in (('projects.list', {}), ('assignments.list', {'project': r['project']['id']}), ('problems.list', {'project': r['project']['id']}), ('documents.list', {'project': r['project']['id']}), ('copies.list', {}), ('changes.workspaces', {})):
    v = call(op, args); print(op, {x: (len(y) if isinstance(y, list) else y) for x, y in v.items()})
g = call('problems.get', {'id': pr['id']}); print('problems.get keys', sorted(g), 'freshness', g['freshness']['state'], [(s['path'], s['state']) for s in g['freshness']['sources']], 'unknowns', g['unknowns'][:4])
ro = call('assignments.reopen', {'id': a['id']}); print('assignments.reopen keys', sorted(ro), '| freshness', ro['freshness']['state'], [(s['address'], s['state']) for s in ro['freshness']['sources']], '| unresolved', ro['unresolved'], '| questions', len(ro['unresolved_questions']))
print('math.list', common.short(call('math.list', {'id': pr['id']}), 300)); print('artifacts.list', common.short(call('artifacts.list', {'problem': pr['id']}), 300)); print('reasons.list', common.short(call('reasons.list', {'id': pr['id']}), 300)); print('methods.list', common.short(call('methods.list'), 200))
cab = call('ledger.cabinet', {'limit': 200}); print('cabinet roles', Counter(n['role'] for n in cab['nodes'])); [print('   ', n['id'][:60], '|', n['label'][:40], '| parent', n['parent']) for n in cab['nodes'] if n['role'] in ('project', 'assignment', 'problem', 'working_copy', 'copy', 'document') or n['id'].split(':')[0] in ('project', 'assignment', 'problem', 'copies')]
print('files under workspace', sorted(str(x.relative_to(root)) for x in root.rglob('*') if x.is_file() and '.ledger' not in x.parts)[:20])
