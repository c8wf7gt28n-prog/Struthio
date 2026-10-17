"""R04 GUI + agent protocol smoke, safe and nondestructive."""
import hashlib
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from workbench.agent import handle,AgentError
from workbench.app import Workbench, ACTION
assert 'flash' not in str(ACTION).lower() and 'deploy' not in str(ACTION).lower()
a=handle({'id':1,'method':'hello'})
assert a['flash_enabled'] is False and a['source_writes_enabled'] is False
names=handle({'method':'files.list','params':{'path':'firmware'}})
assert names['entries']
try:
    handle({'method':'files.write','params':{'path':'firmware/stage/f133_stage.c','expected_sha256':'0'*64,'content':'x'}})
    raise AssertionError('write should be forbidden')
except AgentError: pass
orig=(ROOT/'firmware/stage/f133_stage.c').read_text()
sha=hashlib.sha256(orig.encode()).hexdigest()
try:
    handle({'method':'files.write','params':{'path':'firmware/stage/f133_stage.c','expected_sha256':'0'*64,'content':'x'}},True)
    raise AssertionError('stale write should be forbidden')
except AgentError: pass
ack=handle({'method':'files.write','params':{'path':'firmware/stage/f133_stage.c','expected_sha256':sha,'content':orig}},True)
assert ack['written'] and (ROOT/'firmware/stage/f133_stage.c').read_text()==orig
app=Workbench()
app.update()
assert app.open_file and app.open_file.name=='f133_stage.c'
assert 'RAILS CHECK' in app.lcd.cget('text')
assert 'Directory' in app.addr.get() or app.addr.get().startswith('C:')
assert app.dir_tree.get_children()
app.show_directory(ROOT/'firmware'/'stage')
assert 'firmware' in app.addr.get().lower()
assert any('d213_stage.c' in app.file_tree.item(x,'text') for x in app.file_tree.get_children())
app.run_action('Build both stages')
deadline=time.monotonic()+40
while app.busy and time.monotonic()<deadline:
    app.update();time.sleep(.03)
assert not app.busy,'GUI build timed out'
assert 'arc1 firmware image' in app.console.get('1.0','end')
assert 'PASS' in app.console.get('1.0','end')
app.advance_boot()
assert 'F133 BOOT' in app.lcd.cget('text') and app.boot_model.verified==1
app.destroy()
print('R05 backward-compatible agent+GUI smoke PASS; staged builds PASS; no physical deploy')
