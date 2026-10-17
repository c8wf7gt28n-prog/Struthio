from pathlib import Path
import os,sys,tempfile,time
from PIL import ImageGrab
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from workbench.app import Workbench
with tempfile.TemporaryDirectory() as cfg:
 os.environ['ARC1_WORKBENCH_CONFIG_HOME']=cfg
 app=Workbench()
 app.geometry('1440x900+0+0')
 app.update_idletasks();app.update()
 app.show_directory(ROOT/'firmware'/'stage')
 app.update_idletasks();app.update()
 ImageGrab.grab(bbox=(0,0,1440,900)).save('/mnt/data/ARC1_WORKBENCH_R08_CLASSIC_ACTUAL.png')
 app.on_close()
 print('Actual Tk fallback screenshot captured')
