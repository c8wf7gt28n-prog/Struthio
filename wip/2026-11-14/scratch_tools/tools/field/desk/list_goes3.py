import sys
sys.path.insert(0, '/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/field/desk')
import harness as H
from harness import act
S = H.start(); w = S['w']; T = S['T']
from workbench import context_menu as cm
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
def where(tag):print(tag, 'field' if getattr(w, '_field_active', False) else 'not field', type(QApplication.focusWidget()).__name__, 'list', w.type_bar.box.popup.isVisible(), flush=True)
try:
    cm.inspect_in_line(w, '@files:x.csv | rows | count'); T.settle(S); where('put')
    r = act(S, 'go.field', {'by': 'pointer'}); T.settle(S); where('go.field pointer')
    QTest.mouseClick(w.type_bar.box, Qt.LeftButton); T.settle(S); where('click line')
    r = act(S, 'go.back', {'by': 'pointer'}); T.settle(S); print('back', r.get('ok'), r.get('by'), str(r.get('said'))[:100]); where('go.back')
    w.type_bar.box.clear(); T.settle(S); where('clear')
    cm.inspect_in_line(w, '@files:x.csv | rows | count'); T.settle(S); where('put 2')
    r = act(S, 'go.field', {'by': 'keys'}); T.settle(S); print('act', r.get('ok'), r.get('by'), str(r.get('said'))[:120]); where('go.field keys')
finally:
    H.finish(S)
