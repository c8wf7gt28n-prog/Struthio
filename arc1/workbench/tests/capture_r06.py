from pathlib import Path
from PIL import ImageGrab
from workbench.app import Workbench
w=Workbench();w.geometry('1440x900+0+0');w.update_idletasks();w.update()
w.show_directory(Path(__file__).resolve().parents[2]/'cartridges')
w.update_idletasks();w.update()
ImageGrab.grab(bbox=(0,0,1440,900)).save('/mnt/data/ARC1_WORKBENCH_R06_ORANGE_AQUA_ACTUAL.png')
w.destroy()
