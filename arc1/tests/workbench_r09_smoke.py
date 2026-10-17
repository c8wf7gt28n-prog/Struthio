"""R09 real Tk GUI regression; run under virtual display, not Windows qualification."""
from pathlib import Path
import os,sys,time,tempfile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from workbench.app import Workbench
from PIL import ImageGrab
with tempfile.TemporaryDirectory() as preferences:
 os.environ['ARC1_WORKBENCH_CONFIG_HOME']=preferences
 w=Workbench();w.geometry('1420x900+0+0');w.update()
 time.sleep(.28);w.update()
 assert not w.output_visible, 'Code workspace must recover height'
 assert not w.diagnostics_visible
 assert w.editor.winfo_height()>420, 'Editor should gain reclaimed area'
 ImageGrab.grab(bbox=(0,0,1420,900)).save('/mnt/data/ARC1_WORKBENCH_R09_EDITOR_ACTUAL.png')
 w.toggle_output();w.update();assert w.output_visible
 w.toggle_output();w.update();assert not w.output_visible
 w.run_action('Build both stages')
 deadline=time.monotonic()+40
 while w.busy and time.monotonic()<deadline:
  w.update();time.sleep(.035)
 assert not w.busy,'build did not finish'
 assert w.router.exit_code==0,w.router.summary()
 assert 'PASS' in w.build_log.get('1.0','end')
 assert 'No recognized compiler errors' in w.problem_log.get('1.0','end')
 w.reveal_output(1);w.update()
 ImageGrab.grab(bbox=(0,0,1420,900)).save('/mnt/data/ARC1_WORKBENCH_R09_BUILD_ACTUAL.png')
 w.apply_workspace('Code');w.update();assert not w.output_visible
 w.apply_workspace('Debug');w.update();assert w.output_visible
 w.inspect_host_debug();w.update();assert 'HOST GAME SIMULATION' in w.debug_log.get('1.0','end')
 w.apply_workspace('Code');w.update();w.on_close()
 print('R09 PASS: code/editor area, F10 panel, real firmware build, parsed problems, debug pane, workspace persistence, screenshots')
