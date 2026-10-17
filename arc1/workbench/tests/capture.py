from PIL import ImageGrab
from workbench.app import Workbench
import time
x=Workbench()
x.geometry('1390x840+10+10')
x.update_idletasks();x.update();time.sleep(0.6);x.update()
ImageGrab.grab(bbox=(0,0,1430,875)).save('/mnt/data/ARC1_WORKBENCH_R04_ACTUAL_SCREEN.png')
x.destroy()
