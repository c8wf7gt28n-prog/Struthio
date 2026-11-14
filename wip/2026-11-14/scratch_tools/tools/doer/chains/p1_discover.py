exec(open('/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/doer/chains/common.py').read())
print('operator scopes:', sorted(p.scopes), 'identity', p.identity, 'mode', p.mode)
L('ledger.address.kinds', {}, n=3000)
L('files.find', {'limit': 60}, n=3000)
L('documents.list', {}, n=2500) if 'documents.list' in CAPABILITIES else print('no documents.list')
L('stac.status', {}, n=3000)
L('procedures.list', {}, n=1500)
L('work.list', {}, n=1500)
L('methods.list', {}, n=1500)
L('agenda.view', {}, n=2500)
L('matrix.status', {})
L('matrix.patterns', {'limit': 10}, n=2500)
L('investigation.list', {}, n=2000)
L('changes.workspaces', {}, n=2000)
L('assignments.list', {}, n=2000) if 'assignments.list' in CAPABILITIES else None
L('projects.list', {}, n=2000) if 'projects.list' in CAPABILITIES else None
L('stac.history', {}, n=1500)
# every field object's stac line
w.a_field.trigger(); settle(); v = w.field_page.view
for o in v.field.objects: print('FIELD %-10s %-40s %s' % (o.kind, o.title[:40], o.stac))
ops = sorted(CAPABILITIES)
print('operations:', len(ops))
import collections
c = collections.Counter(CAPABILITIES.values()); print('scopes:', dict(c))
for prefix in ('language.', 'stac.', 'procedures.', 'work.', 'methods.', 'agenda.', 'matrix.', 'changes.', 'investigation.', 'files.pro', 'copies.', 'memory.lesson', 'assign', 'agent', 'slate.', 'workers.'):
    print(prefix, [(o, CAPABILITIES[o]) for o in ops if o.startswith(prefix)])
