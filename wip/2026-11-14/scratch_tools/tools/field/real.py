"""Orchestrator's probe: read the restored After Hours 07 workspace through the new reader and draw it (no window yet)."""
import json, os, sys, tempfile, shutil
from pathlib import Path
from unittest.mock import patch
S = Path('/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad')
PROGRAM = Path(sys.argv[1]).resolve(); OUT = Path(sys.argv[2]).resolve()
RUN = Path(tempfile.mkdtemp(prefix='run-', dir=str(S / 'tools/field/run'))); HOME = RUN / 'home'; HOME.mkdir()
shutil.copytree(S / 'work/demo/After_Hours_07', RUN / 'ws'); shutil.copytree(S / 'work/demo/After_Hours_07-profile', RUN / 'prof')
os.environ.update(PYTHONDONTWRITEBYTECODE='1', QT_QPA_PLATFORM='offscreen', ARC_LEDGER_EMBEDDED='1', ARC_LEDGER_DISABLE_BOOK_WATCHER='1', HOME=str(HOME),
                  ARC1_WORKBENCH_CONFIG_HOME=str(RUN / 'prof'), ARC_LEDGER_CONCERN=str(HOME / 'Concern'), ARC_LEDGER_WORKSPACE=str(RUN / 'ws'))
os.chdir(RUN); sys.path.insert(0, str(PROGRAM)); sys.dont_write_bytecode = True
from workbench import clip, session_power
from workbench.engineering_kernel import Kernel, operator
patch.object(clip, '_request', side_effect=AssertionError('No provider request')).start()
patch.object(Kernel, 'launch', side_effect=AssertionError('No worker launch')).start()
patch.object(Kernel, 'submit', side_effect=AssertionError('No job submission')).start()
patch.object(session_power, 'system', side_effect=OSError('held')).start()
k = Kernel(RUN / 'ws')
import subprocess; patch.object(subprocess, 'Popen', side_effect=OSError('No process start (held by the probe)')).start()
from workbench.field_source import read_field
import time; t0 = time.time(); field, refused = read_field(k, operator()); dt = time.time() - t0
print('title:', field.title); print('census:', field.census()); print('refused:', refused); print('read in %.2fs' % dt)
for rank in field.ranks():
    print(' ', field.rank_title(rank), [ (field.get(i).kind, field.get(i).title[:34], field.get(i).state) for i in field.column(rank)])
print('links:', [(field.get(l.source).title[:18], l.label, field.get(l.target).title[:18], l.stale) for l in field.links])
from PySide6.QtGui import QFontDatabase, QFont
from PySide6.QtWidgets import QApplication
app = QApplication([])
for f in (PROGRAM / 'branding/fonts/plex').glob('*.ttf'): QFontDatabase.addApplicationFont(str(f))
base = QFont('IBM Plex Sans'); base.setPixelSize(16); app.setFont(base)
from workbench.field_qt import FieldView
for name, w, h in (('real_wide', 1368, 1010), ('real_compact', 826, 600)):
    v = FieldView(); v.resize(w, h); v.set_field(field); v.show(); v.setFocus(); app.processEvents()
    assert v.grab().save(str(OUT / ('field_%s.png' % name))); print('saved', name)
