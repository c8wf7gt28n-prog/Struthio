"""R07 host launcher security, execution and layout tests; no physical hardware."""
from pathlib import Path
import copy
import json
import os
import shutil
import sys
import tempfile
import time
import zipfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from workbench.launcher import HostLauncher, LauncherError, prepare, games_on_shelf
from workbench.workspaces import WorkspaceStore
from workbench.agent import handle,AgentError
ROOT=Path(__file__).resolve().parents[1]

def raises(code,call):
    try:call()
    except LauncherError as exc:assert exc.code==code,(code,exc.code,exc)
    else:raise AssertionError('expected '+code)

def run():
    import subprocess
    subprocess.run([sys.executable,str(ROOT/'arc1'),'build','examples/hello_arc1'],cwd=ROOT,check=True,capture_output=True)
    x=prepare()
    assert x['evidence']=='HOST_TEST' and x['board_observed'] is False
    assert x['executable_in_cartridge'] is False
    assert games_on_shelf()[0]['valid']
    raises('INVALID_PATH',lambda:prepare('../cartridges/hello_arc1.arc1cart'))
    raises('INVALID_PATH',lambda:prepare('examples/hello_arc1/arc1.game.json'))
    with tempfile.TemporaryDirectory() as td:
        temp=Path(td);(temp/'cartridges').mkdir();(temp/'examples'/'hello_arc1').mkdir(parents=True)
        src=ROOT/'examples'/'hello_arc1'/'arc1.game.json'
        shutil.copy2(src,temp/'examples'/'hello_arc1'/'arc1.game.json')
        dest=temp/'cartridges'/'hello_arc1.arc1cart';shutil.copy2(ROOT/'cartridges'/'hello_arc1.arc1cart',dest)
        changed=json.loads(src.read_text());changed['author']='changed'
        (temp/'examples'/'hello_arc1'/'arc1.game.json').write_text(json.dumps(changed))
        raises('CARTRIDGE_SOURCE_MISMATCH',lambda:prepare(root=temp))
        dest.write_bytes(b'not-a-zip')
        raises('CARTRIDGE_INVALID',lambda:prepare(root=temp))
    sim=HostLauncher()
    raises('INVALID_FRAMES',lambda:sim.start(frames=0))
    sim.start(frames=120)
    for _ in range(200):
        status=sim.status()
        if status['state'] not in ('RUNNING','STARTING'):break
        time.sleep(.02)
    assert status['state']=='COMPLETED',status
    assert len(status['result']['preview_frames'])>=3
    assert status['result']['board_observed'] is False
    assert status['result']['trace_sha256']
    sim.start(frames=36000)
    stop=sim.stop()
    assert stop['stopped'] is True,stop
    for _ in range(100):
        if sim.status()['state']=='STOPPED':break
        time.sleep(.02)
    assert sim.status()['state']=='STOPPED',sim.status()
    with tempfile.TemporaryDirectory() as td:
        f=Path(td)/'workspace.json';ws=WorkspaceStore(f)
        ws.set_active('Cartridge',diagnostics=True,file_pane_px=267,output_pane_px=188)
        ws.state['recent_file']='firmware/stage/f133_stage.c';ws.state['editor_index']='14.3';ws.save()
        reread=WorkspaceStore(f)
        assert reread.state['active']=='Cartridge'
        assert reread.state['layouts']['Cartridge']['file_pane_px']==267
        assert reread.state['recent_file']=='firmware/stage/f133_stage.c'
        f.write_text(json.dumps({'schema':'arc1.workspaces/1','active':'Bad','recent_file':'../../etc/passwd',
                                 'layouts':{'Code':{'file_pane_px':500000,'folder':'../bad'}}}))
        assert WorkspaceStore(f).state['recent_file'] is None
    assert any(x['name']=='hello_arc1' for x in handle({'method':'launcher.list'})['games'])
    assert 'launcher.stop_sim' in handle({'method':'capabilities'})['methods']
    for method in ('device.flash','shell.exec'):
        try:handle({'method':method})
        except AgentError:pass
        else:raise AssertionError('Unauthorized method available')
    print('R07 PASS: verified shelf, trusted host binding, actual host execution, stop, security, persisted layouts, agent methods')

if __name__=='__main__':run()
