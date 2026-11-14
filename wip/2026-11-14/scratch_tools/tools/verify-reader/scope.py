"""Is the Field 'this workspace'? Read an EMPTY second workspace folder with the same profile."""
from common import *
from workbench.field_source import read_field
other = RUN / 'other-ws'; other.mkdir()
k2 = Kernel(other); hold_processes()
f, refused = read_field(k2, P)
print('--- Field of an empty second workspace folder, same profile ---'); dump(f, refused)
