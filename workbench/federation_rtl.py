"""Bounded Icarus execution of one existing canonical 12F BRAM command path."""
import hashlib, re, shutil, subprocess, time
from pathlib import Path
from . import record_io as io
FW='hardware/compact-arc1/R10_WORK/fpga12/rtl/'
SOURCES=[FW+'accel_engine.sv',FW+'arc1_transform_ecp5.sv','software/arcos/bsp/virtual_console/rtl/tb_federation.sv','workbench/federation_rtl.py']
ARTIFACT='build/virtual_console/federation_12f.vvp'

def build(root):
    root=Path(root).resolve();tool=shutil.which('iverilog')
    if not tool or not shutil.which('vvp'):raise ValueError('RTL_TOOLS_REQUIRED: install Debian iverilog (iverilog and vvp); no behavioral fallback')
    out=root/ARTIFACT;out.parent.mkdir(parents=True,exist_ok=True)
    argv=[tool,'-g2012','-s','tb_federation','-o',str(out),*[str(root/n) for n in SOURCES if n.endswith('.sv')]]
    p=subprocess.run(argv,cwd=root,capture_output=True,text=True,timeout=30)
    if p.returncode:raise ValueError('RTL_BUILD_FAILED: '+p.stderr[-4000:])
    return {'argv':argv,'stdout':p.stdout,'stderr':p.stderr,'sha256':io.sha(out),'sources':{n:io.sha(root/n) for n in SOURCES},'class':'RTL_SIM','scope':'Canonical accel_engine HAS_FIR=0 and ECP5 transform, BRAM boundary; no board timing/PHY/RGMII'}

def exchange(root,request,folder):
    root=Path(root).resolve();folder=Path(folder).resolve()
    if not folder.is_relative_to(root/'.ledger'):raise ValueError('RTL_SCRATCH_SCOPE')
    if not isinstance(request,bytes) or not 16<=len(request)<=8192:raise ValueError('RTL_REQUEST_BOUND')
    vvp=shutil.which('vvp')
    if not vvp:raise ValueError('RTL_TOOLS_REQUIRED: vvp unavailable; no host-reference substitution')
    folder.mkdir(parents=True,exist_ok=True);req=folder/'request.memh';rsp=folder/'response.memh';wave=folder/'transaction.vcd'
    req.write_text(''.join('%02x\n'%v for v in request));rsp.unlink(missing_ok=True)
    argv=[vvp,str(root/ARTIFACT),'+REQ='+str(req),'+RESP='+str(rsp),'+LEN='+str(len(request)),'+WAVE='+str(wave)]
    start=time.monotonic();p=subprocess.run(argv,cwd=root,capture_output=True,text=True,timeout=10)
    if p.returncode or not rsp.is_file():raise ValueError('RTL_EXCHANGE_FAILED: '+(p.stderr+p.stdout)[-2000:])
    raw=rsp.read_bytes()
    if len(raw)>8192*4:raise ValueError('RTL_RESPONSE_BOUND')
    words=raw.decode().split()
    if not 16<=len(words)<=8192 or any(not re.fullmatch('[0-9a-fA-F]{2}',w) for w in words):raise ValueError('RTL_RESPONSE_SCHEMA')
    response=bytes(int(w,16) for w in words);matched=re.search(r'RTL_RESULT cycles=(\d+) bytes=(\d+) status=(\d+)',p.stdout)
    if not matched or int(matched[2])!=len(response):raise ValueError('RTL_RESULT_RECEIPT')
    receipt={'schema':'arc.federation-rtl-transaction/1','class':'RTL_SIM','source_hashes':{n:io.sha(root/n) for n in SOURCES},
        'artifact_sha256':io.sha(root/ARTIFACT),'request_sha256':hashlib.sha256(request).hexdigest(),
        'response_sha256':hashlib.sha256(response).hexdigest(),'request_hex':request.hex(),'response_hex':response.hex(),
        'simulated_cycles':int(matched[1]),'engine_status':int(matched[3]),'elapsed_host_seconds':time.monotonic()-start,
        'stdout':p.stdout,'stderr':p.stderr,'argv':argv,'physical_hardware':False,'board_timing':None,
        'wave_sha256':io.sha(wave) if wave.is_file() else None}
    io.write_json(folder/'receipt.json',receipt);return response,receipt
