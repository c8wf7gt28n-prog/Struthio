from pathlib import Path
import time
from PIL import ImageGrab
from workbench.app import Workbench
w=Workbench();w.geometry('1440x900+0+0')
w.update_idletasks();w.update();time.sleep(.7);w.update()
ImageGrab.grab(bbox=(0,0,1450,940)).save('/mnt/data/ARC1_WORKBENCH_R05_ORANGE_AQUA_ACTUAL.png')
w.destroy()
