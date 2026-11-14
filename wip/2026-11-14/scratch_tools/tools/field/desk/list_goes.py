"""The writing line's results go when the line is left: a line put there (as the right-click's Put it in the writing line
does), then a click in the Field, by pointer and by keys; and they come back when the line is clicked again."""
import sys
sys.path.insert(0, '/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/field/desk')
import harness as H
from harness import act
S = H.start(); w = S['w']; T = S['T']
from workbench import context_menu as cm
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
out = {}
try:
    for by in ('pointer', 'keys'):
        cm.inspect_in_line(w, '@files:x.csv | rows | count'); T.settle(S)
        out[by + ' after put'] = w.type_bar.box.popup.isVisible()
        r = act(S, 'go.field', {'by': by}); T.settle(S)
        out[by + ' after go.field'] = w.type_bar.box.popup.isVisible()
        out[by + ' focus'] = type(w.focusWidget()).__name__ if w.focusWidget() else None
        if by == 'pointer':
            QTest.mouseClick(w.type_bar.box, Qt.LeftButton); T.settle(S)
            out['back in the line'] = w.type_bar.box.popup.isVisible()
        act(S, 'go.back', {'by': 'pointer'}); w.type_bar.box.clear(); T.settle(S)
    print('RESULT', out)
finally:
    H.finish(S)
