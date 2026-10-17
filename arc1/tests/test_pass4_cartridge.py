"""Deterministic R06 cartridge and host model tests. No USB/device access."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import zipfile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from workbench.cartridge import package_game,inspect_cartridge,simulate_stream,CartridgeError
from workbench.agent import handle,AgentError

with tempfile.TemporaryDirectory() as tmp:
    tmp=Path(tmp)
    src=ROOT/'examples'/'hello_arc1'
    output=tmp/'hello.arc1cart'
    p=package_game(src,output)
    assert p['asset_count']==1 and p['executable_included'] is False
    d=inspect_cartridge(output)
    assert d['valid'] and d['asset_bytes'] == p['asset_bytes']
    h=hashlib.sha256(output.read_bytes()).hexdigest()
    package_game(src,output)
    assert h==hashlib.sha256(output.read_bytes()).hexdigest(),'not reproducible'
    fast=simulate_stream(output,frames=120,bandwidth_mib_s=20,latency_ms=1)
    assert fast['simulated_stall_frames']==0 and fast['physical_usb_tested'] is False
    slow=simulate_stream(output,frames=120,bandwidth_mib_s=0.001,latency_ms=900,
                         prefetch_frames=0,consumption_bytes_per_frame=100)
    assert slow['simulated_stall_frames']>0
    bad=tmp/'bad.arc1cart'
    with zipfile.ZipFile(bad,'w') as z:
        z.writestr('arc1.game.json',(src/'arc1.game.json').read_bytes())
        z.writestr('../escape.txt','hello')
    try:inspect_cartridge(bad);assert False,'extra entry not rejected'
    except CartridgeError:pass
    corrupted=tmp/'corrupt.arc1cart'
    with zipfile.ZipFile(corrupted,'w') as z:
        z.writestr('arc1.game.json',(src/'arc1.game.json').read_bytes())
        z.writestr('assets/ship.sprite','wrong bytes')
    try:inspect_cartridge(corrupted);assert False,'checksum alteration not rejected'
    except CartridgeError:pass
    try:simulate_stream(output,latency_ms=-1);assert False,'invalid latency not rejected'
    except CartridgeError:pass
    # Larger deterministic fixture stresses several hundred chunk transfers,
    # without distributing a giant archive with this development release.
    stress=tmp/'stress_game';(stress/'assets').mkdir(parents=True)
    payload=bytes(range(256))*4096  # 1 MiB exact; compressible, still models size
    (stress/'assets'/'stream.sprite').write_bytes(payload)
    m=json.loads((src/'arc1.game.json').read_text())
    m['name']='streamstress';m['assets']=[{'path':'assets/stream.sprite','sha256':hashlib.sha256(payload).hexdigest()}]
    (stress/'arc1.game.json').write_text(json.dumps(m))
    big=tmp/'stress.arc1cart'
    package_game(stress,big)
    assert inspect_cartridge(big)['asset_bytes']==1048576
    fast_big=simulate_stream(big,frames=120,bandwidth_mib_s=25,latency_ms=0.05,
                             chunk_bytes=32768,prefetch_frames=30,consumption_bytes_per_frame=7000)
    slow_big=simulate_stream(big,frames=120,bandwidth_mib_s=0.5,latency_ms=10,
                             chunk_bytes=4096,prefetch_frames=0,consumption_bytes_per_frame=7000)
    assert fast_big['simulated_stall_frames']==0 and fast_big['chunk_count']==32
    assert slow_big['simulated_stall_frames']>0 and slow_big['chunk_count']==256
agent_caps=handle({'method':'capabilities'})
assert 'cartridge.stream' in agent_caps['methods']
try:handle({'method':'cartridge.package'});assert False,'agent writes should need permission'
except AgentError:pass
try:handle({'method':'cartridge.inspect','params':{'path':'../../etc/passwd'}});assert False
except AgentError:pass
agent_package=handle({'method':'cartridge.package'},allow_writes=True)
assert agent_package['executable_included'] is False
agent_inspect=handle({'method':'cartridge.inspect'})
assert agent_inspect['valid']
agent_stream=handle({'method':'cartridge.stream','params':{'latency_ms':2000,'prefetch_frames':0}})
assert agent_stream['simulated_stall_frames']>0
print('PASS: deterministic cartridge packaging, integrity, safe paths, latency stalls, agent permissions')
