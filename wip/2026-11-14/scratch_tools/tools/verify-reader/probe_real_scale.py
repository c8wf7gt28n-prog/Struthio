import sys, time, json, os
sys.path.insert(0, '/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/verify-reader')
from wincommon import *
from workbench import field_page
from workbench.engineering_kernel import operator
calls = []
real_dispatch = Kernel.dispatch
def counted(self, operation, params=None, principal=None):
    t = time.perf_counter()
    try: return real_dispatch(self, operation, params, principal)
    finally: calls.append((operation, time.perf_counter() - t))
Kernel.dispatch = counted
open_window(); settle(50, 10)
k = w.ledger_bridge.kernel; p = operator()
def call(op, args=None, quiet=False):
    r = k.dispatch(op, args or {}, p)
    if not r.get('ok'):
        if not quiet: print('   REFUSED', op, r.get('error'))
        return None
    return r['result']
OUT = L / 'out/realscale'; OUT.mkdir(parents=True, exist_ok=True)
def show(tag, png=None):
    best = None
    for _ in range(2):
        field_page.leave_field(w); calls.clear(); t = time.perf_counter(); w.show_field(); dt = (time.perf_counter() - t) * 1000
        if best is None or dt < best[0]: best = (dt, list(calls))
    dt, cs = best; v = w.field_page.view
    by = {}
    for op, s in cs: by.setdefault(op, [0, 0.0]); by[op][0] += 1; by[op][1] += s * 1000
    print('[%s] show_field %.0f ms, %d dispatches | %s' % (tag, dt, len(cs), ', '.join('%s x%d %.0fms' % (op, n, ms) for op, (n, ms) in sorted(by.items()))))
    print('     census: %s | problem/unread: %s | note: %r | status: %r' % (v.field.census(), (w.field_page.problem, sorted(w.field_page.unread)), v.field.note, w.statusBar().currentMessage()))
    settle(20, 3)
    if png: align(); w.grab().save(str(OUT / png), 'PNG')
    return v
ns = call('intake.namespaces')['namespaces']
for n in ns:
    st = call('references.status', {'namespace': n['id']}); print('references.status: current_sources=%s unavailable=%s' % (st['current_sources'], st['unavailable']))
show('worked case as restored')
# 105 more pages
t = time.perf_counter()
for i in range(105): call('documents.create', {'title': 'Bulk page %03d' % i, 'text': 'Page %d.' % i})
print('created 105 pages in %.1f s' % (time.perf_counter() - t))
total = 0; off = 0
while True:
    got = call('documents.list', {'limit': 100, 'offset': off})['documents']; total += len(got); off += 100
    if len(got) < 100: break
print('documents the workspace really holds (paged through documents.list):', total)
v = show('108 documents in the workspace', 'field_108_documents.png')
print('     documents the Field shows:', sum(1 for o in v.field.objects if o.kind in ('document', 'calculation')), '| calculations shown:', sum(1 for o in v.field.objects if o.kind == 'calculation'))
# office sheets up to the store's own limit
made = 0
for i in range(40):
    csv = RUN / ('bulk_%02d.csv' % i); csv.write_text('part,qty\nR%d,2\n' % i)
    plan = call('office.import.preview', {'path': str(csv)}, quiet=True)
    if not plan: break
    r = k.dispatch('office.import.commit', {'plan': plan['id'], 'expected_digest': plan['digest']}, p)
    if not r.get('ok'): print('   office import stopped at %d more sheets: %s' % (made, r['error']['message'])); break
    made += 1
print('office documents now:', len(call('office.list')['documents']))
show('plus office sheets up to the store limit')
# 60 claims in one investigation
mine = call('investigation.create', {'question': 'Bulk probe?'})
for i in range(60): call('investigation.claim', {'id': mine['id'], 'text': 'Bulk claim %02d about the rails.' % i, 'role': 'FINDING'})
v = show('plus one investigation with 60 claims', 'field_at_caps.png')
print('objects %d links %d; surface %.0f px for a body of %.0f px' % (len(v.field.objects), len(v.field.links), v._surface[1], v.body().height()))
from PySide6.QtGui import QImage
img = QImage(v.size(), QImage.Format_ARGB32_Premultiplied)
def t_ms(fn, n=3):
    out = []
    for _ in range(n):
        t = time.perf_counter(); fn(); out.append((time.perf_counter() - t) * 1000)
    return min(out)
print('view %dx%d scale %.2f: one paint %.0f ms; Down key + repaint %.0f ms' % (v.width(), v.height(), v.scale(), t_ms(lambda: v.render(img)), t_ms(lambda: (QTest.keyClick(v, Qt.Key_Down), v.render(img)))))
w._closing = True; print('DONE')
