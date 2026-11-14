import traceback
from workbench import field_page
k = w.ledger_bridge.kernel; p = operator()
w.a_field.trigger(); settle(); v = w.field_page.view
orig = field_page.leave_field
def traced(host):
    if getattr(host, '_field_active', False):
        print('--- leave_field called from:'); print(''.join(traceback.format_stack(limit=9)[:-1])[-1800:])
    return orig(host)
field_page.leave_field = traced
inv = next(o for o in v.field.objects if o.kind == 'finding').target['id']
from workbench.engine import engineering
r = engineering(w.root).dispatch('investigation.claim', {'id': inv, 'text': 'A probe finding.', 'role': 'FINDING'}, p); print('claim ok:', r['ok'])
settle(150, 6); print('after the claim: field in front:', w._field_active, '| tab:', type(w.tabs.currentWidget()).__name__ if w.tabs.currentWidget() else None)
w.field_page.refresh(force=True); settle(150, 6); print('after a refresh: field in front:', w._field_active)
