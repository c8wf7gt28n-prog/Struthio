"""Unfinished jobs in the Field (new in the fixed reader): the worked case's own job rows with their state changed in the answer."""
from common import *
from workbench.field_source import read_field
k = Kernel(RUN / 'ws'); hold_processes()
real = Kernel.dispatch
states = ['Failed', 'Running', 'Waiting for Approval', 'Paused', 'Interrupted', 'Queued']
def fake(self, operation, arguments=None, principal=None, *a, **kw):
    answer = real(self, operation, arguments, principal, *a, **kw)
    if operation == 'jobs.list' and answer.get('ok'):
        answer = json.loads(json.dumps(answer, default=str))
        for row, state in zip(answer['result'], states): row['state'] = state
    return answer
with patch.object(Kernel, 'dispatch', fake):
    f, r = read_field(k, P)
    print('census:', f.census(), '| first selected:', f.get(f.selected).kind, f.get(f.selected).title)
    for o in f.objects:
        if o.kind == 'job':
            a = k.dispatch('language.run', {'text': o.stac}, operator())
            print('  JOB title=%r role=%r state=%r lines=%s column=%s | attention=%s | stac ok=%s rows=%s' % (o.title, o.role, o.state, o.lines, f.rank_title(f.rank_of(o.id)), o.needs_attention(), a.get('ok'), json.dumps((a.get('result') or {}).get('rows'))[:90]))
