"""Interactive GUI smoke in Xvfb, also exercises event-only LCD gate."""
import sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from workbench.app import Workbench,AquaButton
app=Workbench();app.update()
assert app.title().startswith('ARC-1 Workbench R07')
assert app.open_file is not None and app.open_file.name=='f133_stage.c'
assert 'POWER' in app.lcd.cget('text')
assert app.boot_model.verified == 0
assert any(isinstance(c,AquaButton) for c in app.toolbar.winfo_children())
app.advance_boot();app.update()
assert app.boot_model.verified==1 and app.boot_model.stage=='f133'
app.inject_fault();app.update()
assert '1203' in app.lcd.cget('text') and app.boot_model.fault_code==0x1203
app.advance_boot();assert app.boot_model.stage=='fault'
app.reset_boot();assert app.boot_model.stage=='power'
app.run_action('Build both stages')
deadline=time.monotonic()+45
while app.busy and time.monotonic()<deadline:app.update();time.sleep(.03)
assert not app.busy and 'PASS' in app.console.get('1.0','end')
app.destroy()
print('PASS R05 Aqua GUI, synthetic boot diagnostics, staged build and fault latch')
