"""R06 GUI smoke under Xvfb; confirms compact header and cartridge workflow."""
import sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from workbench.app import Workbench
w=Workbench();w.update()
assert w.title().startswith('ARC-1 Workbench R07')
assert w.winfo_children()[0].winfo_height()==51, 'header not compact'
assert w.open_file and w.open_file.name=='f133_stage.c'
assert w.diagnostics_visible
w.toggle_diagnostics();w.update();assert not w.diagnostics_visible
w.toggle_diagnostics();w.update();assert w.diagnostics_visible
w.make_cartridge()
assert (ROOT/'cartridges'/'hello_arc1.arc1cart').exists()
w.advance_boot();assert w.boot_model.verified==1
w.run_action('Build both stages');deadline=time.monotonic()+65
while w.busy and time.monotonic()<deadline:w.update();time.sleep(.03)
assert not w.busy
assert 'PASS' in w.console.get('1.0','end')
w.destroy()
print('PASS: compact Aqua GUI, diagnostics hide/restore, cartridge package, boot status, staged firmware build')
