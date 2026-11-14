# a survey of the main surfaces as a new owner meets them
from PySide6.QtWidgets import QAbstractButton
def tab(name):
    b = next((b for b in w.findChildren(QAbstractButton) if b.text() == name and b.isVisible()), None)
    if b is not None: b.click(); settle(250, 5)
    return b is not None
w.show_start() if hasattr(w, 'show_start') else None; settle(300, 6); save('Survey_01_Home_%s.png' % tag)
w.a_field.trigger(); settle(); v = w.field_page.view
def open_tile(title):
    o = next((o for o in v.field.objects if o.title.startswith(title)), None)
    if o is None: return False
    w.a_field.trigger(); settle(150, 4); v.field.select(o.id); v._describe(); QTest.keyClick(v, Qt.Key_Return); settle(800, 8); return True
open_tile('07_Bench_Readings.pdf'); save('Survey_02_PDF_%s.png' % tag)
open_tile('Settled draw'); save('Survey_03_Finding_%s.png' % tag)
tab('Talk'); save('Survey_04_Talk_%s.png' % tag)
tab('Context'); save('Survey_05_Context_%s.png' % tag)
tab('Settings'); save('Survey_06_Settings_%s.png' % tag)
tab('Machine'); save('Survey_07_Machine_%s.png' % tag)
tab('Files'); tab('Activity')
open_tile('What stretched'); save('Survey_08_Question_%s.png' % tag)
