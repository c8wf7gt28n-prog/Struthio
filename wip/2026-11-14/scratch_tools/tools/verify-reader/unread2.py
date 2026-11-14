"""Records that cannot be read and what the surface says: investigation.sheet refused; investigation.path refused."""
from common import *
from workbench.field_source import read_field, problems
k = Kernel(RUN / 'ws'); hold_processes()
real = Kernel.dispatch
for bad in ('investigation.sheet', 'investigation.path'):
    def fake(self, operation, arguments=None, principal=None, *a, **kw):
        if operation == bad: return {'ok': False, 'error': {'code': 'PROBE', 'message': 'refused'}}
        return real(self, operation, arguments, principal, *a, **kw)
    with patch.object(Kernel, 'dispatch', fake):
        f, r = read_field(k, P)
    print('%s refused -> title %r | census %s | status: %r | unread ids: %s' % (bad, f.title, f.census(), problems(r), [u.split(':')[0] for u in r.unread]))
    print('    objects that say not read:', [o.title for o in f.objects if o.state == 'not read'], '| findings:', [(o.title[:24], o.state, len(f.fed_by(o.id))) for o in f.objects if o.kind in ('finding', 'question')])
    f2, r2 = read_field(k, P, skip=set(r.unread))
    print('    next showing with those remembered (records readable again): census %s | status: %r' % (f2.census(), problems(r2)))
