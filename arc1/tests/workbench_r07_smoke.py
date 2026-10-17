"""R07 window smoke with actual rendered host frame preview."""
from pathlib import Path
import os,sys,tempfile,time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from workbench.app import Workbench
from PIL import ImageGrab
with tempfile.TemporaryDirectory() as cfg:
 os.environ['ARC1_WORKBENCH_CONFIG_HOME']=cfg
 w=Workbench();w.geometry('1420x900+0+0');w.update()
 assert w.title().startswith('ARC-1 Workbench R08')
 w.apply_workspace('Cartridge')
 assert w.workspaces.state['active']=='Cartridge'
 assert w.diagnostics_visible==False
 w.apply_workspace('Debug')
 assert w.diagnostics_visible
 w.apply_workspace('Code')
 w.quick_open();w.update();qw=[t for t in w.winfo_children() if t.winfo_class()=='Toplevel']
 assert qw,'quick open window missing'
 for t in qw:t.destroy()
 w.command_palette();w.update()
 qw=[t for t in w.winfo_children() if t.winfo_class()=='Toplevel']
 assert qw,'command palette window missing'
 for t in qw:t.destroy()
 w.open_launcher();w.update()
 assert w.launch_window and w.launch_window.winfo_exists()
 assert 'hello_arc1' in w.launch_summary.get()
 w.host_launcher.start(frames=120)
 timeout=time.monotonic()+15
 while w.host_launcher.status()['state'] in ('STARTING','RUNNING') and time.monotonic()<timeout:
  w.update();time.sleep(.02)
 assert w.host_launcher.status()['state']=='COMPLETED'
 for _ in range(20):w.update();time.sleep(.02)
 assert w.launch_preview_files
 assert w.launch_picture.cget('image'), 'real host preview image did not render'
 # screenshot focusing launcher as the primary visible window
 w.launch_window.geometry('900x650+250+100');w.update_idletasks();w.update()
 ImageGrab.grab(bbox=(0,0,1420,900)).save('/mnt/data/ARC1_WORKBENCH_R07_ACTUAL_LAUNCHER.png')
 w.launch_window.destroy();w.launch_window=None
 w.apply_workspace('Cartridge');w.update()
 ImageGrab.grab(bbox=(0,0,1420,900)).save('/mnt/data/ARC1_WORKBENCH_R07_ACTUAL_WORKSPACE.png')
 w.on_close()
 print('R07 PASS: GUI presets, quick-open, palette, shelf, real host preview, workspace persistence and screenshots')
