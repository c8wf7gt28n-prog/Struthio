import sys
sys.path.insert(0, '/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/field/desk')
import harness as H
from harness import act
S = H.start(); w = S['w']; T = S['T']
from workbench import context_menu as cm
from PySide6.QtWidgets import QApplication
def where(tag):print(tag, 'field' if getattr(w, '_field_active', False) else 'not field', type(QApplication.focusWidget()).__name__, 'list', w.type_bar.box.popup.isVisible(), flush=True)
try:
    where('start')
    cm.inspect_in_line(w, '@files:x.csv | rows | count'); T.settle(S); where('after put')
    r = act(S, 'go.field', {'by': 'keys'}); T.settle(S); print('act', r.get('ok'), r.get('by'), str(r.get('said') or r.get('words'))[:120]); where('after go.field keys')
    w.a_field.trigger(); T.settle(S); where('after a_field.trigger')
finally:
    H.finish(S)
