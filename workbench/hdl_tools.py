"""Fixed native HDL checks and bound digital traces through the shared Kernel."""
from __future__ import annotations
import argparse
from contextlib import closing
import json
import hashlib
import os
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import time
import uuid
from sdk.cli.arc1cli import hdl_waveforms as wave
from . import record_io as io,kicad_tools as process,yosys_tools

CONTRACT='arc.hdl-native/1'
ID={'type':'string','pattern':'^[0-9a-f]{32}$','maxLength':32}
FIELDS={'hdl.inspect':({},[]),'hdl.report':({'id':ID},[]),'hdl.compare_pump':({},[]),
        'hdl.value':({'id':ID,'signal':{'type':'string','maxLength':512},'tick':{'type':'integer','minimum':0,'maximum':10**15}},['id','signal','tick'])}
SCOPES={name:'read' for name in FIELDS}
BASE=yosys_tools.BASE
PUMP_TB='''`timescale 1ns/1ps
module ledger_pump_tb;
 reg clk=0, txc=0, rst=1, we=0, start=0, f_pop=0;
 reg [12:0] waddr=0; reg [7:0] wdata=0; reg [15:0] len=512;
 wire tx_start_tgl,f_valid; wire [15:0] f_data;
 integer i, received=0; reg consuming=0;
 eth_tx_pump dut(.*);
 always #6.25 clk=~clk; always #4 txc=~txc;
 function automatic [7:0] pattern(input integer n); pattern=(n^165)&255; endfunction
 initial begin
  $dumpfile("trace.vcd"); $dumpvars(0,clk,txc,rst,we,start,f_valid,f_data,f_pop,tx_start_tgl,received);
  repeat(4) @(negedge clk); rst=0;
  for(i=0;i<512;i=i+1) begin @(negedge clk); we=1; waddr=i; wdata=pattern(i); end
  @(negedge clk); we=0; start=1; @(negedge clk); start=0;
  wait(received==256); #1; $display("LEDGER_PUMP_PASS"); $finish;
 end
 always @(negedge txc) begin
  if(tx_start_tgl) consuming=1;
  f_pop=consuming && f_valid && received<256;
 end
 always @(posedge txc) if(f_pop) begin
  if(f_data!=={pattern(received*2+1),pattern(received*2)}) $fatal(1,"LEDGER_PUMP_FAIL data");
  $display("SAMPLE %0d %04x",received,f_data); received=received+1;
 end
 initial begin #20000; $fatal(1,"LEDGER_PUMP_FAIL timeout"); end
endmodule
'''
CAP_TB='''`timescale 1ns/1ps
module ledger_cap;
reg clk=0; reg [1:0] q=0; integer i;
always #1 clk=~clk;
always @(posedge clk) q<=q+1;
initial begin $dumpfile("trace.vcd"); $dumpvars(0,clk,q);
for(i=0;i<4;i=i+1) begin @(posedge clk); #0.001; if(q!==((i+1)&3)) $fatal(1,"CAP_FAIL"); end
$display("LEDGER_CAP_PASS"); $finish; end
endmodule
'''
PROFILES={
 'rgmii':{'title':'RGMII · original bench / RX lint','top':'tb_rgmii','pass':'RGMII_TB_PASS',
          'files':['fpga12/tb/tb_rgmii.sv','fpga12/rtl/rgmii_rx.sv','fpga12/rtl/rgmii_tx.sv','fpga12/rtl/eth_tx_pump.sv','fpga12/sim/ecp5_ddr_sim.v'],
          'signals':['rxc','rxd','rx_ctl','cnt_ok','cnt_crc','cnt_drop','cnt_other','frame_tgl','txc','o_txd','o_ctl','cnt_under'],
          'vtop':'rgmii_rx','vfiles':['fpga12/rtl/rgmii_rx.sv','fpga12/sim/ecp5_ddr_sim.v']},
 'sdram':{'title':'SDRAM · original bench / controller lint','top':'tb_sdram','pass':'SDRAM_TB_PASS',
          'files':['fpga45/tb/tb_sdram.sv','fpga45/rtl/sdram_ctrl.sv','fpga45/rtl/sdram_cal.sv','fpga45/sim/sdram_model.sv'],
          'signals':['clk','rst','init_done','cmd_valid','cmd_ready','cmd_write','cmd_addr','cmd_len','wr_ready','rd_valid','rd_data','cnt_refresh','sd_cs_n','sd_ras_n','sd_cas_n','sd_we_n'],
          'vtop':'sdram_ctrl','vfiles':['fpga45/rtl/sdram_ctrl.sv']},
 'pump':{'title':'TX pump · shared 256-word transport check','top':'ledger_pump_tb','pass':'LEDGER_PUMP_PASS',
         'files':['fpga12/rtl/eth_tx_pump.sv'],'signals':['clk','txc','rst','we','start','f_valid','f_data','f_pop','tx_start_tgl','received'],
         'vtop':'ledger_pump_tb','vfiles':['fpga12/rtl/eth_tx_pump.sv']},
}


def discover(engine,which=None):
    lookup=which or shutil.which;name='iverilog' if engine=='icarus' else 'verilator';path=lookup(name)
    if not path:return {'state':'NOT_AVAILABLE','reason':'Install '+name+' separately and launch Graphite with it on PATH.','engine':engine}
    executable=Path(path).resolve();prefix=executable.parent.parent;programs={str(executable):io.sha(executable)}
    data=None
    if engine=='icarus':
        runner=lookup('vvp');candidates=[prefix/'lib/x86_64-linux-gnu/ivl',prefix/'lib/ivl',prefix/'lib64/ivl']
        data=next((p for p in candidates if (p/'ivl').is_file() and (p/'vvp.tgt').is_file()),None)
        available=bool(runner and data)
        if runner:programs[str(Path(runner).resolve())]=io.sha(Path(runner).resolve())
    else:
        runner=executable.parent/'verilator_bin';data=prefix/'share/verilator'
        compiler=lookup('g++');make=lookup('make');available=runner.is_file() and data.is_dir() and bool(compiler and make)
        for p in (runner,compiler,make):
            if p and Path(p).is_file():programs[str(Path(p).resolve())]=io.sha(Path(p).resolve())
    return {'engine':engine,'state':'DETECTED' if available else 'INCOMPLETE_INSTALL','executable':str(executable),
            'runner':str(Path(runner).resolve()) if runner else None,'program_files':programs,
            'data_directory':str(data.resolve()) if data and data.is_dir() else None,
            'reason':'Each job repeats native capability cases; installed tools alone are not qualification.'}


def environment(tool,out):
    fake={'resolved_executable':tool['executable']};env=yosys_tools.environment(fake,Path(out)/'environment')
    if tool['engine']=='verilator':
        env['VERILATOR_ROOT']=tool['data_directory'];env['VERILATOR_BIN']=os.path.relpath(tool['runner'],tool['data_directory'])
    return env


def dependencies(tool):
    rows={n:{'sha256':sha,'bytes':Path(n).stat().st_size} for n,sha in tool['program_files'].items()}
    files=list(Path(tool['data_directory']).rglob('*'))
    if len(files)>6000:raise ValueError('HDL runtime file count exceeds bound')
    for p in files:
        if p.is_symlink():raise ValueError('HDL runtime data contains a symlink')
        if p.is_file():
            if p.stat().st_size>32*1024*1024:raise ValueError('HDL runtime file exceeds bound')
            rows[str(p)]={'sha256':io.sha(p),'bytes':p.stat().st_size}
    if sum(row['bytes'] for row in rows.values())>128*1024*1024:raise ValueError('HDL runtime capture exceeds bound')
    return rows


def safe_hdl(text):
    if re.search(r'verilator\s+(?:public|cxx|hier_block|sc_)',text,re.I):raise ValueError('Source-supplied native hooks are outside the fixed HDL profile')
    clean=re.sub(r'//[^\n]*|/\*.*?\*/','',text,flags=re.S)
    tasks=set(re.findall(r'\$([A-Za-z_][A-Za-z_0-9]*)',clean));directives=set(re.findall(r'`([A-Za-z_][A-Za-z_0-9]*)',clean))
    if tasks-{'display','finish','time','realtime','random'} or directives-{'timescale','default_nettype','ifdef','ifndef','else','endif'} or re.search(r'\b(?:import|export)\s+"DPI',clean):
        raise ValueError('HDL file/system IO, source includes/macros or foreign-code hooks require separate review')


def source_inputs(root,engine,key):
    spec=PROFILES[key];names=[(BASE/n).as_posix() for n in spec['vfiles' if engine=='verilator' else 'files']]
    context=(BASE/('fpga45/Makefile' if key=='sdram' else 'fpga12/Makefile')).as_posix()
    rows=io.manifest(root,names+[context,'workbench/hdl_tools.py','sdk/cli/arc1cli/hdl_waveforms.py'])
    if any(row.get('sha256') is None or row['bytes']>1024*1024 for row in rows.values()) or sum(row['bytes'] for row in rows.values())>8*1024*1024:raise ValueError('HDL source snapshot absent or exceeds bound')
    for name in names:safe_hdl(io.project_path(root,name).read_text())
    return names,rows


def invoke_compile(tool,files,top,out,env,lint=False):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    if tool['engine']=='icarus':argv=[tool['executable'],'-B',tool['data_directory'],'-g2012','-s',top,'-o','model.vvp',*files]
    else:
        argv=[tool['executable'],'--lint-only' if lint else '--binary','--timing','-Wall','-Wno-fatal','--top-module',top]
        if not lint:argv+=['--trace','--trace-depth','2','--trace-max-array','0','--Mdir','obj','-j','2']
        argv+=files
    return process.invoke(argv,out,env,180 if tool['engine']=='verilator' and not lint else 40)


def invoke_model(tool,out,top,env):
    out=Path(out)
    argv=[tool['runner'],'-M',tool['data_directory'],'-n',str(out/'model.vvp')] if tool['engine']=='icarus' else [str(out/'obj'/('V'+top))]
    return process.invoke(argv,out/'run',env,120)


def diagnostics(out):
    rows=[]
    for line in (Path(out)/'stderr.txt').read_text(errors='replace').splitlines():
        m=re.match(r'%((?:Warning|Error))(?:-([A-Za-z0-9_]+))?:\s*(.*?):(\d+)(?::(\d+))?:\s*(.*)',line)
        if m:rows.append({'severity':m[1].upper(),'code':m[2] or 'GENERAL','file':m[3],'line':int(m[4]),'column':int(m[5]) if m[5] else None,'message':m[6]})
        elif line.startswith(('%Error','%Warning')):rows.append({'severity':'ERROR' if line.startswith('%Error') else 'WARNING','code':'GENERAL','message':line})
    return rows


def parse_run(out,marker,key=None):
    out=Path(out);text=(out/'stdout.txt').read_text(errors='replace')+'\n'+(out/'stderr.txt').read_text(errors='replace')
    if len(text)>2*1024*1024 or text.splitlines().count(marker)!=1:raise ValueError('Exactly one expected native PASS marker is required')
    if re.search(r'(?m)^(?:ERROR\b|TB_ERROR\b|MODEL_VIOLATION\b|.*(?:_FAIL\b))',text):raise ValueError('Native bench reported a failure despite process completion')
    result={'pass_marker':marker,'checks':[line for line in text.splitlines() if line.startswith(('ok ','TEST '))]}
    if key=='pump':
        samples=[(int(a),int(b,16)) for a,b in re.findall(r'(?m)^SAMPLE (\d+) ([0-9a-fA-F]{4})$',text)]
        expected=[(i,(((2*i+1)^165)&255)<<8|((2*i)^165)&255) for i in range(256)]
        if samples!=expected:raise ValueError('Pump sample sequence differs from all 256 independently computed words')
        result.update(samples=[list(row) for row in samples],sample_sha256=io.digest(samples),sample_count=256)
    return result


def qualify(tool,out,env):
    out=Path(out);good=out/'good';good.mkdir(parents=True)
    (good/'fixture.sv').write_text(CAP_TB)
    c=invoke_compile(tool,['fixture.sv'],'ledger_cap',good,env)
    if c['exit_status']:raise ValueError('Native timed capability fixture did not compile')
    r=invoke_model(tool,good,'ledger_cap',env)
    if r['exit_status']:raise ValueError('Native timed capability fixture failed')
    parse_run(good/'run','LEDGER_CAP_PASS');trace=wave.parse_vcd(good/'run/trace.vcd')
    if not any(row['width']==2 and len(row['changes'])>=4 for row in trace['signals'].values()):raise ValueError('Capability trace did not contain the expected counter changes')
    bad=out/'bad';bad.mkdir();(bad/'invalid.sv').write_text('module bad(output y); MISSING_LEDGER_MODULE broken(y); endmodule\n')
    negative=invoke_compile(tool,['invalid.sv'],'bad',bad,env,lint=tool['engine']=='verilator')
    if negative['exit_status']==0:raise ValueError('Native compiler accepted a deliberately missing module')
    return {'qualified':True,'reused':False,'compile':c,'simulation':r,'trace':wave.summary(trace),'missing_module':negative,
            'scope':'Known timed digital fixture, VCD output and rejected module case; not project equivalence or physical hardware qualification.'}


def latest(root,engine,key):
    root=Path(root).resolve();candidates=[];paths=list((root/'build/hdl/runs').glob('*/record.json'))
    if len(paths)>1000:raise ValueError('HDL run lookup exceeds bound')
    for path in paths:
        row=io.load(root,path.relative_to(root).as_posix())
        if row['engine']==engine and row['profile_key']==key:candidates.append((row['created'],row['id']))
    state=root/'.ledger/engineering.sqlite3'
    if state.is_file():
        if state.is_symlink() or state.parent.is_symlink():raise ValueError('Linked Kernel state')
        with closing(sqlite3.connect(state.as_uri()+'?mode=ro',uri=True)) as db:
            for raw, in db.execute('SELECT payload FROM jobs ORDER BY rowid DESC LIMIT 1000'):
                job=io.strict_json(raw.encode())
                # Kernel queue order is authoritative, even if an older worker
                # started late and wrote its adapter record after this request.
                if job['tool']==engine+'.'+key:return job['id']
    return max(candidates)[1] if candidates else None


def kernel_state(root,ident):
    state=Path(root)/'.ledger/engineering.sqlite3'
    if not state.is_file():return None
    if state.is_symlink() or state.parent.is_symlink():raise ValueError('Linked Kernel state')
    with closing(sqlite3.connect(state.as_uri()+'?mode=ro',uri=True)) as db:row=db.execute('SELECT state FROM jobs WHERE id=?',(ident,)).fetchone()
    return row[0] if row else None


def new_attempt(root,family,ident):
    root=Path(root).resolve()
    if family not in ('hdl','surfer') or not re.fullmatch('[0-9a-f]{32}',ident):raise ValueError('Invalid native run identity')
    directory=root/'build'/family/'runs'/ident
    if any(p.is_symlink() for p in (root/'build',root/'build'/family,root/'build'/family/'runs',directory,directory/'attempts')):raise ValueError('Linked native output directory')
    out=directory/'attempts'/uuid.uuid4().hex;out.mkdir(parents=True,exist_ok=False);return out


def commit(root,family,record,out):
    root=Path(root).resolve();record['finished']=time.time();record['artifacts']={}
    for p in sorted(out.rglob('*')):
        if p.is_file() and not p.is_symlink() and 'environment' not in p.relative_to(out).parts:
            record['artifacts'][p.relative_to(root).as_posix()]={'sha256':io.sha(p),'bytes':p.stat().st_size}
    directory=out.parent.parent;io.write_json(out/'record.json',record);io.write_json(directory/'record.json',record)
    io.write_json(root/'build'/family/'latest.json',{'id':record['id'],'record_sha256':io.sha(directory/'record.json')})
    return record


def load_record(root,family,ident=None):
    root=Path(root).resolve();expected=None
    if ident is None:
        pointer=root/'build'/family/'latest.json'
        if not pointer.is_file():return {'state':'NOT_RUN','reason':'Run a registered '+family+' operation.'}
        row=io.load(root,pointer.relative_to(root).as_posix());ident=row['id'];expected=row['record_sha256']
    if not re.fullmatch('[0-9a-f]{32}',ident):raise ValueError('Invalid native job ID')
    path=io.project_path(root,'build/'+family+'/runs/'+ident+'/record.json');data=io.load(root,path.relative_to(root).as_posix())
    if data['id']!=ident or not re.fullmatch('[0-9a-f]{32}',data['attempt']):raise ValueError('Native record identity differs')
    prefix='build/'+family+'/runs/'+ident+'/attempts/'+data['attempt']+'/'
    if expected and io.sha(path)!=expected or io.sha(path)!=io.sha(io.project_path(root,prefix+'record.json')):raise ValueError('Native record changed')
    for name,row in data['artifacts'].items():
        if not name.startswith(prefix):raise ValueError('Native artifact outside its attempt')
        p=io.project_path(root,name)
        if io.sha(p)!=row['sha256'] or p.stat().st_size!=row['bytes']:raise ValueError('Original native artifact changed: '+name)
    data['source_currentness']='NOT_APPLICABLE'
    if data.get('inputs'):
        try:data['source_currentness']='CURRENT' if io.manifest(root,list(data['inputs']))==data['inputs'] else 'STALE'
        except (OSError,ValueError):data['source_currentness']='MISSING_OR_INVALID'
    state=kernel_state(root,ident);data['kernel_state']=state
    if state in ('Cancelled','Interrupted'):
        data['original_status']=data['status'];data['status']=state.upper()
    return data


def trace_path(root,data):return io.project_path(root,data['waveform']['file'])


def report(root,ident=None):
    data=load_record(root,'hdl',ident)
    if data.get('compile'):
        native=Path(root)/'build/hdl/runs'/data['id']/'attempts'/data['attempt']/'native'
        if diagnostics(native)!=data['diagnostics']:raise ValueError('HDL diagnostic summary differs from original output')
    if data.get('waveform'):
        raw=wave.vcd_bytes(trace_path(root,data))
        if hashlib.sha256(raw).hexdigest()!=data['waveform']['vcd_sha256'] or len(raw)!=data['waveform']['vcd_bytes']:raise ValueError('Native VCD bytes differ from retained snapshot')
        parsed=wave.summary(wave.parse_vcd(trace_path(root,data)))
        if parsed!=data['waveform']['summary']:raise ValueError('HDL trace summary differs from original VCD')
    if data.get('simulation'):
        native=Path(root)/'build/hdl/runs'/data['id']/'attempts'/data['attempt']/'native/run'
        parsed=parse_run(native,PROFILES[data['profile_key']]['pass'],data['profile_key'])
        if parsed!=data['simulation']:raise ValueError('HDL simulation summary differs from original output')
    return data


def current_trace(root,engine,key):
    ident=latest(root,engine,key)
    if not ident:raise ValueError('Run '+engine+'.'+key+' first')
    state=kernel_state(Path(root).resolve(),ident)
    if state is not None and state!='Completed':raise ValueError('Latest HDL parent did not complete; no fallback to older results')
    data=report(root,ident)
    if data['status']!='SIMULATED' or data['source_currentness']!='CURRENT' or not data.get('waveform'):raise ValueError('Latest HDL result is incomplete, stale or has no trace')
    return data


def run(root,engine,key,ident):
    root=Path(root).resolve();out=new_attempt(root,'hdl',ident)
    if engine not in ('icarus','verilator') or key not in ('qualify',*PROFILES):raise ValueError('Unknown HDL operation')
    record={'schema':CONTRACT,'id':ident,'attempt':out.name,'engine':engine,'profile_key':key,'created':time.time(),
            'class':'STATIC_CHECK' if engine=='verilator' and key not in ('pump','qualify') else 'HOST_SIM',
            'status':'BLOCKED','reason':'','programming':'HOLD','fabrication':'HOLD','physical_hardware':False}
    try:
        tool=discover(engine);record['tool']=tool
        if tool['state']!='DETECTED':raise ValueError(tool['reason'])
        env=environment(tool,out);deps=dependencies(tool);record['dependencies']=deps
        version=process.invoke([tool['executable'],'-V' if engine=='icarus' else '--version'],out/'version',env,10)
        if version['exit_status']:raise ValueError('Native HDL version probe failed')
        tool['version']=version['stdout'].splitlines()[0];record['qualification']=qualify(tool,out/'qualification',env)
        if key=='qualify':record.update(status='QUALIFIED',reason='Timed native fixture and rejected module case reproduced; no project result.')
        else:
            spec=PROFILES[key];names,inputs=source_inputs(root,engine,key);record.update(inputs=inputs,input_revision=io.digest(inputs),profile=spec)
            for name,row in inputs.items():
                dest=out/'inputs'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(io.project_path(root,name),dest);dest.chmod(0o444)
                if io.sha(dest)!=row['sha256']:raise ValueError('HDL input changed while copying')
            native=out/'native';native.mkdir();lint=engine=='verilator' and key!='pump';record['kind']='LINT' if lint else 'RTL_SIMULATION'
            files=['../inputs/'+name for name in names];top=spec['vtop'] if lint else spec['top']
            if not lint:
                code=PUMP_TB if key=='pump' else '`timescale 1ns/1ps\nmodule ledger_trace; '+top+' tb(); initial begin $dumpfile("trace.vcd"); $dumpvars(0,'+','.join('tb.'+n for n in spec['signals'])+'); end endmodule\n'
                (native/'trace_wrapper.sv').write_text(code);files=['trace_wrapper.sv',*files];top=top if key=='pump' else 'ledger_trace'
            compile_result=invoke_compile(tool,files,top,native,env,lint);record['compile']=compile_result;record['diagnostics']=diagnostics(native)
            if compile_result['exit_status']:raise ValueError('Native HDL compilation/lint failed; complete diagnostics retained')
            if lint:record.update(status='LINT_WARNINGS' if any(d['severity']=='WARNING' for d in record['diagnostics']) else 'LINT_CLEAN',reason='Native lint completed; warnings remain visible. No simulation or functional pass is claimed.')
            else:
                execution=invoke_model(tool,native,top,env);record['native']=execution
                if execution['exit_status']:raise ValueError('Native HDL simulation exited with an error')
                record['simulation']=parse_run(native/'run',spec['pass'],key);original=native/'run/trace.vcd';raw=wave.vcd_bytes(original)
                path=native/'run/trace.vcd.gz';wave.archive_vcd(path,raw);trace=wave.parse_vcd(path)
                if not trace['end_tick']:raise ValueError('Simulation trace has no elapsed time')
                record['waveform']={'file':path.relative_to(root).as_posix(),'sha256':io.sha(path),'vcd_sha256':hashlib.sha256(raw).hexdigest(),
                                    'vcd_bytes':len(raw),'encoding':'gzip, exact original native VCD bytes','summary':wave.summary(trace)}
                original.unlink()
                record.update(status='SIMULATED',reason='Original self-checking bench passed, or the bounded shared pump check matched all 256 words; digital RTL trace retained. No board timing or full-system equivalence claim.')
            record['source_unchanged']=source_inputs(root,engine,key)[1]==inputs
            record['snapshot_unchanged']=all(io.sha(out/'inputs'/name)==row['sha256'] for name,row in inputs.items())
            if not record['source_unchanged'] or not record['snapshot_unchanged']:raise ValueError('HDL source or copied input changed')
        record['dependencies_unchanged']=all(Path(n).is_file() and io.sha(Path(n))==row['sha256'] for n,row in deps.items())
        if not record['dependencies_unchanged']:raise ValueError('HDL runtime changed during execution')
    except (ValueError,OSError,KeyError,TypeError,UnicodeError,subprocess.SubprocessError,sqlite3.Error) as exc:
        record.update(status='INVALID' if 'waveform' in record else 'BLOCKED',reason=str(exc))
    return commit(root,'hdl',record,out)


def dispatch(kernel,operation,args):
    if operation=='hdl.report':return report(kernel.root,args.get('id'))
    if operation=='hdl.value':
        data=report(kernel.root,args['id']);trace=wave.parse_vcd(trace_path(kernel.root,data));signal=trace['signals'].get(args['signal'])
        if signal is None or not 0<=args['tick']<=trace['end_tick']:raise ValueError('Signal or cursor tick is outside this recorded trace')
        bits=wave.value_at(signal,args['tick'])
        return {'id':data['id'],'source_currentness':data['source_currentness'],'signal':args['signal'],'tick':args['tick'],
                'tick_fs':trace['tick_fs'],'bits':bits,'value':wave.display_value(bits),'trace_sha256':data['waveform']['sha256']}
    if operation=='hdl.compare_pump':
        a=current_trace(kernel.root,'icarus','pump');b=current_trace(kernel.root,'verilator','pump')
        equal=a['simulation']['samples']==b['simulation']['samples']
        return {'status':'MATCH' if equal else 'MISMATCH','words':256,'icarus':a['id'],'verilator':b['id'],
                'sha256':a['simulation']['sample_sha256'] if equal else None,'class':'HOST_SIM','programming':'HOLD',
                'scope':'Initialized pump output words only. Not four-state equivalence, cycle-by-cycle whole-design equivalence or board timing.'}
    return {'schema':CONTRACT,'tools':{engine:discover(engine) for engine in ('icarus','verilator')},'profiles':PROFILES,'latest':report(kernel.root),
            'notice':'Icarus runs original RGMII/SDRAM benches. Verilator lints RX/controller RTL and runs the shared pump check. Native warnings, state-model differences and physical limits remain explicit.'}


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('operation');ap.add_argument('--root',type=Path,required=True);ap.add_argument('--job',required=True)
    a=ap.parse_args();engine,key=a.operation.split('-',1);result=run(a.root,engine,key,a.job)
    print(json.dumps({k:result[k] for k in ('id','status','reason')}))
    raise SystemExit(0 if result['status'] in ('QUALIFIED','SIMULATED','LINT_CLEAN','LINT_WARNINGS') else 2)
