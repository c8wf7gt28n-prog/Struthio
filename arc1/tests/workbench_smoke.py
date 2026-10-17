"""Current Workbench R05 graphical smoke test; requires desktop session."""
from pathlib import Path
import runpy
runpy.run_path(str(Path(__file__).with_name('workbench_r05_smoke.py')),run_name='__main__')
