"""Native Surfer state/capture over verified traces, on a private display."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import socket
import subprocess
import time
from sdk.cli.arc1cli import hdl_waveforms as wave
from . import hdl_tools as hdl,record_io as io,kicad_tools as process

CONTRACT='arc.surfer-native/1'
FIELDS={'surfer.inspect':({},[]),'surfer.report':({'id':hdl.ID},[])}
SCOPES={name:'read' for name in FIELDS}
PROFILES={'icarus_rgmii':('icarus','rgmii'),'icarus_sdram':('icarus','sdram'),
          'icarus_pump':('icarus','pump'),'verilator_pump':('verilator','pump')}
FIXTURE='''$timescale 1 ns $end
$scope module ledger_cap $end
$var wire 1 ! clk $end
$var wire 2 " count $end
$upscope $end
$enddefinitions $end
#0
0!
b00 "
#5
1!
b01 "
#10
0!
b10 "
'''


def discover(which=None):
    lookup=which or shutil.which;programs={}
    for name in ('surfer','Xvfb','xauth'):
        path=lookup(name)
        if path:programs[name]={'executable':str(Path(path).resolve()),'sha256':io.sha(Path(path).resolve())}
    pillow=importlib.util.find_spec('PIL') is not None
    return {'state':'DETECTED' if len(programs)==3 and pillow and os.name=='posix' else 'NOT_AVAILABLE',
            'programs':programs,'pillow':pillow,'qualified':False,
            'reason':'Native capture currently requires Linux Surfer, Xvfb, xauth and Pillow, installed separately. Graphite trace inspection works without these optional capture tools.'}


def environment(tools,out):
    binary=Path(tools['programs']['Xvfb']['executable']);prefix=binary.parent.parent
    env={k:v for k,v in os.environ.items() if k in ('PATH','SystemRoot','WINDIR')}
    home=Path(out)/'environment/home';home.mkdir(parents=True);temporary=Path(out)/'environment/tmp';temporary.mkdir()
    env.update(HOME=str(home),USERPROFILE=str(home),TMPDIR=str(temporary),TEMP=str(temporary),TMP=str(temporary),
               XDG_CONFIG_HOME=str(home/'config'),XDG_CACHE_HOME=str(home/'cache'),XDG_DATA_HOME=str(home/'data'),
               LC_ALL='C',LANG='C',LIBGL_ALWAYS_SOFTWARE='1',RUST_LOG='info')
    library=prefix/'lib/x86_64-linux-gnu'
    if library.is_dir():env['LD_LIBRARY_PATH']=str(library)
    return env


def state_variables(text):
    if len(text)>2*1024*1024 or 'format: Vcd' not in text:raise ValueError('Surfer did not preserve a bounded VCD state')
    result=[]
    for scopes,name in re.findall(r'variable_ref:\s*\(\s*path:\s*\(\s*strs:\s*\[(.*?)\],\s*id:.*?\),\s*name:\s*"([A-Za-z_][A-Za-z_0-9]*)"',text,re.S):
        parts=re.findall(r'"([A-Za-z_][A-Za-z_0-9]*)"',scopes)
        result.append('.'.join(parts+[name]))
    return sorted(result)


def capture(tools,trace_path,selected,start,end,out,env):
    from PIL import ImageGrab,Image
    out=Path(out);out.mkdir(parents=True,exist_ok=True);raw=wave.vcd_bytes(trace_path);(out/'trace.vcd').write_bytes(raw)
    if not selected or len(selected)>10 or any(not re.fullmatch('[A-Za-z_][A-Za-z_0-9.]*',name) for name in selected):raise ValueError('Unsafe or excessive Surfer signal list')
    command='\n'.join(['variable_add '+name for name in selected]+['zoom_to '+str(start)+' '+str(end),'save_state_as surfer_state.ron','dump_tree'])+'\n'
    (out/'view.sucl').write_text(command)
    # Authenticated temporary display. The host chooses a free local X port;
    # no endpoint is published and no owner desktop is ever captured.
    number=None
    for _ in range(20):
        n=secrets.randbelow(1000)+100
        try:
            with socket.socket() as s:s.bind(('127.0.0.1',6000+n))
            number=n;break
        except OSError:continue
    if number is None:raise ValueError('No local display slot available')
    display='127.0.0.1:'+str(number);auth=Path(env['HOME']).parent/'Xauthority'
    auth_env={**env,'DISPLAY':display,'XAUTHORITY':str(auth)}
    cookie=secrets.token_hex(16)
    # Do not retain the cookie or this argument vector in audit receipts.
    result=subprocess.run([tools['programs']['xauth']['executable'],'-f',str(auth),'add',display,'.',cookie],env=auth_env,capture_output=True,timeout=10)
    if result.returncode:raise ValueError('Private native display authentication setup failed')
    auth.chmod(0o600);xvfb=None;viewer=None;started=time.monotonic();identities=[]
    from .operation_stop import owned_tree, kill_owned
    try:
        with (out/'display.log').open('wb') as server_log,(out/'surfer.log').open('wb') as log:
            xvfb=subprocess.Popen([tools['programs']['Xvfb']['executable'],':'+str(number),'-screen','0','1280x800x24',
                                   '-nolisten','unix','-nolisten','local','-listen','tcp','-auth',str(auth)],env=auth_env,stdout=server_log,stderr=server_log,stdin=subprocess.DEVNULL)
            deadline=time.monotonic()+5
            while time.monotonic()<deadline:
                if xvfb.poll() is not None:raise ValueError('Private native display failed; original display log retained')
                try:
                    with socket.create_connection(('127.0.0.1',6000+number),timeout=.1):break
                except OSError:time.sleep(.05)
            argv=[tools['programs']['surfer']['executable'],'trace.vcd','--command-file','view.sucl']
            viewer=subprocess.Popen(argv,cwd=out,env=auth_env,stdout=log,stderr=log,stdin=subprocess.DEVNULL)
            identities=owned_tree([xvfb.pid,viewer.pid]);state=out/'surfer_state.ron';deadline=time.monotonic()+30
            while time.monotonic()<deadline:
                if viewer.poll() is not None:raise ValueError('Surfer exited before creating the requested native state')
                if state.is_file() and state.stat().st_size>100:
                    try:
                        text=state.read_text()
                        if state_variables(text)==sorted(selected):break
                    except (OSError,ValueError):pass
                time.sleep(.05)
            else:raise ValueError('Native Surfer did not confirm the selected signals within the time bound')
            time.sleep(.6)
            text=state.read_text()
            if state_variables(text)!=sorted(selected) or 'source: File("trace.vcd")' not in text:raise ValueError('Surfer state differs from the exact trace/signal request')
            original=os.environ.get('XAUTHORITY');os.environ['XAUTHORITY']=str(auth)
            try:ImageGrab.grab(xdisplay=display).save(out/'surfer.png')
            finally:
                if original is None:os.environ.pop('XAUTHORITY',None)
                else:os.environ['XAUTHORITY']=original
            image=Image.open(out/'surfer.png');colors=image.convert('RGB').getcolors(10000000)
            if image.size!=(1280,800) or colors is None or len(colors)<16:raise ValueError('Native capture is absent or blank')
            native_log=(out/'surfer.log').read_text(errors='replace')
            if 'VCD file loaded' not in native_log or 'dump_tree' not in native_log:raise ValueError('Native file-load / selected-tree receipts absent')
            receipt={'selected':sorted(selected),'start_tick':start,'end_tick':end,'pixels':[1280,800],
                    'state_sha256':io.sha(state),'image_sha256':io.sha(out/'surfer.png'),'trace_sha256':io.sha(out/'trace.vcd'),
                    'duration_seconds':time.monotonic()-started,'native_file_loaded':True,
                    'scope':'Actual native Surfer snapshot and saved state, not embedded Surfer controls. Graphite provides its own separate digital cursor/zoom inspector.'}
            return receipt
    finally:
        refs=owned_tree([p.pid for p in (viewer,xvfb) if p is not None])
        if refs:kill_owned(refs)
        for p in (viewer,xvfb):
            if p is not None:
                try:p.wait(timeout=5)
                except subprocess.TimeoutExpired:p.kill();p.wait(timeout=5)
        auth.unlink(missing_ok=True)
        if 'receipt' in locals():
            wave.archive_vcd(out/'trace.vcd.gz',raw);(out/'trace.vcd').unlink();receipt['retained_gzip_sha256']=io.sha(out/'trace.vcd.gz')


def choose(trace,key):
    preferred={'rgmii':['rxc','rxd','rx_ctl','cnt_ok','cnt_crc','cnt_drop','o_txd','o_ctl'],
               'sdram':['clk','init_done','cmd_valid','cmd_ready','cmd_addr','rd_valid','rd_data','cnt_refresh'],
               'pump':['clk','txc','start','f_valid','f_data','f_pop','received']}
    signals=[next(name for name in trace['signals'] if name.rsplit('.',1)[-1]==leaf) for leaf in preferred[key]]
    lo,hi=(200000000,205000000) if key=='sdram' else (0,15000000)
    if key=='pump':lo,hi=6400000,9500000
    return signals,min(lo,trace['end_tick']),min(hi,trace['end_tick'])


def run(root,key,ident):
    root=Path(root).resolve();out=hdl.new_attempt(root,'surfer',ident)
    if key not in ('qualify',*PROFILES):raise ValueError('Unknown Surfer profile')
    record={'schema':CONTRACT,'id':ident,'attempt':out.name,'profile_key':key,'created':time.time(),'class':'STATIC_CHECK',
            'status':'BLOCKED','reason':'','physical_hardware':False,'fabrication':'HOLD','programming':'HOLD'}
    try:
        tools=discover();record['tools']=tools
        if tools['state']!='DETECTED':raise ValueError(tools['reason'])
        env=environment(tools,out)
        version=process.invoke([tools['programs']['surfer']['executable'],'--version'],out/'version',env,10)
        if version['exit_status']:raise ValueError('Surfer version probe failed')
        record['version']=version['stdout'].strip()
        known=out/'fixture.vcd';known.write_text(FIXTURE);trace=wave.parse_vcd(known)
        record['qualification']=capture(tools,known,['ledger_cap.clk','ledger_cap.count'],0,10,out/'qualification',env)
        if key=='qualify':record.update(status='QUALIFIED',reason='Native Surfer loaded a known digital VCD and retained the requested state/capture; no project trace result.')
        else:
            engine,profile=PROFILES[key];data=hdl.current_trace(root,engine,profile);source=hdl.trace_path(root,data);trace=wave.parse_vcd(source)
            parent={'id':data['id'],'engine':engine,'profile_key':profile,'trace_sha256':data['waveform']['sha256'],
                    'vcd_sha256':data['waveform']['vcd_sha256'],'record_sha256':io.sha(root/'build/hdl/runs'/data['id']/'record.json')};record['parent']=parent
            inputs=io.manifest(root,['workbench/surfer_tools.py','workbench/hdl_tools.py','sdk/cli/arc1cli/hdl_waveforms.py']);record.update(inputs=inputs,input_revision=io.digest(inputs))
            signals,start,end=choose(trace,profile);record['capture']=capture(tools,source,signals,start,end,out/'native',env)
            after=hdl.current_trace(root,engine,profile)
            if after['id']!=data['id'] or io.sha(root/'build/hdl/runs'/data['id']/'record.json')!=parent['record_sha256'] or record['capture']['trace_sha256']!=parent['vcd_sha256']:raise ValueError('Surfer source trace/parent changed')
            record['source_unchanged']=io.manifest(root,list(inputs))==inputs
            if not record['source_unchanged']:raise ValueError('Surfer adapter source changed')
            record.update(status='RENDERED',reason='Verified native Surfer capture and saved state of the bound digital trace. No new simulation or physical-timing verdict.')
        record['tools_unchanged']=all(io.sha(Path(p['executable']))==p['sha256'] for p in tools['programs'].values())
        if not record['tools_unchanged']:raise ValueError('Surfer runtime changed during capture')
    except (OSError,ValueError,KeyError,TypeError,subprocess.SubprocessError,UnicodeError) as exc:record.update(status='INVALID' if 'capture' in record else 'BLOCKED',reason=str(exc))
    return hdl.commit(root,'surfer',record,out)


def report(root,ident=None):
    data=hdl.load_record(root,'surfer',ident)
    if data.get('parent'):
        try:
            parent=hdl.current_trace(root,data['parent']['engine'],data['parent']['profile_key'])
            if parent['id']!=data['parent']['id'] or parent['waveform']['sha256']!=data['parent']['trace_sha256']:data['source_currentness']='STALE_PARENT'
        except (OSError,ValueError):data['source_currentness']='MISSING_OR_INVALID_PARENT'
    if data.get('capture'):
        out=Path(root)/'build/surfer/runs'/data['id']/'attempts'/data['attempt']/'native'
        if state_variables((out/'surfer_state.ron').read_text())!=data['capture']['selected']:raise ValueError('Native Surfer state summary differs')
    return data


def dispatch(kernel,operation,args):
    if operation=='surfer.report':return report(kernel.root,args.get('id'))
    return {'schema':CONTRACT,'tool':discover(),'profiles':PROFILES,'latest':report(kernel.root),
            'notice':'Actual native Surfer snapshots/saved state of verified digital VCDs. Graphite cursor/zoom inspection is a separate portable view; no physical timing claim.'}


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('operation');ap.add_argument('--root',type=Path,required=True);ap.add_argument('--job',required=True)
    a=ap.parse_args();r=run(a.root,a.operation,a.job);print(json.dumps({k:r[k] for k in ('id','status','reason')}))
    raise SystemExit(0 if r['status'] in ('QUALIFIED','RENDERED') else 2)
