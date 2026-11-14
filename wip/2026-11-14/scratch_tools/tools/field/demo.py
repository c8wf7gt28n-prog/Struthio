"""Orchestrator's standalone render of the Field view with a sample shaped like the After Hours 07 case (for looking at the drawing only)."""
import os, sys
from pathlib import Path
PROGRAM = Path(sys.argv[1]); OUT = Path(sys.argv[2])
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen'); sys.path.insert(0, str(PROGRAM)); sys.dont_write_bytecode = True
from PySide6.QtGui import QFontDatabase, QFont
from PySide6.QtWidgets import QApplication
app = QApplication([])
for f in (PROGRAM / 'branding/fonts/plex').glob('*.ttf'): QFontDatabase.addApplicationFont(str(f))
base = QFont('IBM Plex Sans'); base.setPixelSize(16); app.setFont(base)
from workbench.field_model import Field, FieldObject as O, FieldLink as L
from workbench.field_qt import FieldView
objs = [
 O('bench', 'source', 'Bench measurements', 'what was measured at the load', 'current', ('PDF · 1 page', '12 V · 280 mA settled', '650 mA for 110 ms at start'), 'Sources/Bench.pdf · page 1'),
 O('revb', 'source', 'Current Rail Limits Rev B', 'the limits that apply to this run', 'current', ('PDF · 1 page', '6 W continuous', '8 W for up to 80 ms'), 'Sources/Rail_Limits_Rev_B.pdf · page 1'),
 O('reva', 'source', 'Archived Rail Limits Rev A', 'the previous limits, kept for comparison', 'current', ('PDF · 1 page', '120 ms pulse condition'), 'Sources/Rail_Limits_Rev_A.pdf · page 1'),
 O('sheet', 'sheet', 'Bench rows', 'reviewed table from the bench PDF', 'current', ('2 rows · units kept', 'revision 3'), 'Office/After Hours/Bench rows'),
 O('settled', 'calculation', 'Settled power', '', 'current', ('12 V × 280 mA = 3.36 W',), 'Settled_Calculation'),
 O('startup', 'calculation', 'Startup pulse', '', 'recheck', ('12 V × 650 mA = 7.8 W', '110 ms against 80 ms'), 'Startup_Calculation'),
 O('readout', 'finding', '07 Case conclusion', 'hold the startup clearance', 'held', ('HOLD', 'pulse exceeds duration by 30 ms'), 'Case_Readout'),
 O('q1', 'question', 'What does a repeat pulse capture at the load show about the extra 30 ms?', '', 'open', (), ''),
]
links = [L('bench', 'sheet', 'table'), L('sheet', 'settled'), L('sheet', 'startup', '', True), L('revb', 'startup', 'limit'), L('revb', 'settled', 'limit'),
         L('reva', 'readout', 'compared'), L('settled', 'readout'), L('startup', 'readout'), L('readout', 'q1')]
for name, w, h, sel in (('wide', 1368, 1010, 'startup'), ('wide_readout', 1368, 1010, 'readout'), ('compact', 826, 600, 'startup'), ('empty', 1368, 700, None)):
    v = FieldView(); v.resize(w, h)
    v.set_field(Field(objs if sel else [], links if sel else [], 'After Hours 07 · startup clearance', sel or ''))
    v.show(); v.setFocus(); app.processEvents()
    v.field.select(sel) if sel else None; v.update(); app.processEvents()
    assert v.grab().save(str(OUT / ('field_%s.png' % name))); print('saved', name, w, h, 'focus', v.hasFocus())
