"""Fixed ECP5 synthesis profiles over protected RTL snapshots, via the Kernel."""
from __future__ import annotations
import argparse
from collections import Counter
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import time
import uuid
from . import brain_link, kicad_tools as process, record_io as io

CONTRACT='arc.yosys-ecp5/1'
FIELDS={'yosys.inspect':({},[]),'yosys.report':({'id':{'type':'string','pattern':'^[0-9a-f]{32}$','maxLength':32}},[])}
SCOPES={name:'read' for name in FIELDS}
BASE=Path(brain_link.BASE)
COMMON=['eth_link.sv','eth_tx_pump.sv','rgmii_rx.sv','rgmii_tx.sv']
SUPPORT=['accel_engine.sv','accel_fir.sv','arc1_transform_ecp5.sv','r10_support_mem_top.sv','r10_mem_engine.sv',
         'psram_user_port.sv','psram_qspi_core.sv','psram_bist.sv','arc1_ecp5_pll.v','arc1_eth_pll.v']
GRAPHICS=['r10_raster_mem_top.sv','r10_raster_engine.sv','r10_raster.sv','sdram_ctrl.sv','sdram_bist.sv','sdram_cal.sv','arc1_sd_pll.v']
PROFILES={
 'support':{'title':'ECP5-12F · support + PSRAM','top':'r10_support_mem_top','device':'ECP5-12F',
            'rtl':[(BASE/'fpga12/rtl'/n).as_posix() for n in COMMON+SUPPORT],
            'context':[(BASE/n).as_posix() for n in ('fpga12/Makefile','fpga12/PHYSICAL_PROPERTIES.md',
                        'fpga12/timing/r10_12f_tqfp144.lpf','fpga12/timing/r10_12f_proxy256.lpf',
                        'hardware/lpf/r10_12f_mem_tqfp144.lpf','hardware/lpf/r10_12f_mem_proxy256.lpf')]},
 'graphics':{'title':'ECP5-45F · rasterizer + SDRAM','top':'r10_raster_mem_top','device':'ECP5-45F',
             'rtl':[(BASE/'fpga12/rtl'/n).as_posix() for n in COMMON+['arc1_eth_pll.v']]+
                   [(BASE/'fpga45/rtl'/n).as_posix() for n in GRAPHICS],
             'context':[(BASE/n).as_posix() for n in ('fpga45/Makefile','fpga45/PHYSICAL_PROPERTIES.md',
                         'fpga45/constraints/r10_45f.lpf','hardware/lpf/r10_45f_sdram.lpf')]},
}
ALLOWED_FUNCTIONS={'signed','unsigned','clog2','display'}
ALLOWED_DIRECTIVES={'default_nettype','timescale','ifdef','ifndef','else','elsif','endif'}
FIXTURE='''module ledger_synth(input clk, a, b, output reg q, output y);
always @(posedge clk) q <= a ^ b;
assign y = a & b;
endmodule
'''


def discover(which=None):
    path=(which or shutil.which)('yosys')
    if not path:return {'state':'NOT_AVAILABLE','executable':None,'qualified':False,'reason':'Install Yosys with its yosys-abc helper and ECP5 data files on PATH.'}
    p=Path(path).resolve();suffix='.exe' if p.suffix.lower()=='.exe' else ''
    abc=p.parent/('yosys-abc'+suffix);data=p.parent.parent/'share/yosys'
    programs={str(f):io.sha(f) for f in (p,abc) if f.is_file()}
    available=abc.is_file() and (data/'ecp5/cells_sim.v').is_file() and (data/'ecp5/cells_bb.v').is_file()
    return {'state':'DETECTED' if available else 'INCOMPLETE_INSTALL','executable':str(Path(path).absolute()),
            'resolved_executable':str(p),'sha256':io.sha(p),'program_files':programs,
            'abc':str(abc) if abc.is_file() else None,'data_directory':str(data) if data.is_dir() else None,
            'qualified':False,'reason':'Each job repeats mapped-cell, truth-table and rejected-input fixtures.' if available else 'The matching yosys-abc helper or ECP5 data directory is missing.'}


def environment(tool,out):
    out=Path(out);home=out/'home';temporary=out/'tmp';home.mkdir(parents=True,exist_ok=True);temporary.mkdir(exist_ok=True)
    env={k:v for k,v in os.environ.items() if k in ('PATH','SystemRoot','WINDIR')}
    env.update(HOME=str(home),USERPROFILE=str(home),TMPDIR=str(temporary),TEMP=str(temporary),TMP=str(temporary),
               LC_ALL='C',LANG='C',OMP_NUM_THREADS='1')
    # Also supports a private, unpacked Unix installation without changing Kernel env grants.
    prefix=Path(tool['resolved_executable']).parent.parent
    libraries=[p for p in (prefix/'lib/x86_64-linux-gnu',prefix/'lib') if p.is_dir()]
    if os.name!='nt' and libraries:env['LD_LIBRARY_PATH']=os.pathsep.join(str(p) for p in libraries)
    return env


def capture_data(tool,out):
    source=Path(tool['data_directory']);out=Path(out);files={}
    for p in sorted(source.rglob('*')):
        if p.is_symlink():raise ValueError('Yosys data snapshot rejects symlinks')
        if not p.is_file():continue
        name=p.relative_to(source).as_posix()
        if p.stat().st_size>8*1024*1024:raise ValueError('Yosys data file exceeds the capture bound')
        files[name]={'source':str(p),'sha256':io.sha(p),'bytes':p.stat().st_size}
    if not files or len(files)>5000 or sum(r['bytes'] for r in files.values())>64*1024*1024:
        raise ValueError('Yosys data installation exceeds the bounded snapshot')
    for name,row in files.items():
        dest=out/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(row['source'],dest)
        if io.sha(dest)!=row['sha256']:raise ValueError('Yosys data changed while capturing')
        row['snapshot']=str(dest)
    return files


def probe(tool,out,env):
    result=process.invoke([tool['executable'],'-V'],out,env,10)
    version=result['stdout'].strip()
    if result['exit_status'] or not re.fullmatch(r'Yosys \d+\.\d+[^\n]*',version):raise ValueError('Yosys version probe failed')
    return {**tool,'version':version,'version_probe':result}


def safe_rtl(text):
    # Input is HDL data. No source-supplied includes, macros, file IO or mapping scripts.
    clean=re.sub(r'//[^\n]*|/\*.*?\*/','',text,flags=re.S)
    directives=set(re.findall(r'`([A-Za-z_][A-Za-z0-9_]*)',clean))
    functions=set(re.findall(r'\$([A-Za-z_][A-Za-z0-9_]*)',clean))
    if directives-ALLOWED_DIRECTIVES or functions-ALLOWED_FUNCTIONS:
        raise ValueError('HDL include/macro/system task is outside this fixed synthesis profile')
    if re.search(r'\b(blackbox|whitebox|lib_whitebox|techmap\w*|abc9_script)\b',clean,re.I):
        raise ValueError('Source-supplied blackboxes or mapping hooks require a separate adapter review')


def inputs(root,profile):
    spec=PROFILES[profile];names=spec['rtl']+spec['context']+['workbench/yosys_tools.py']
    rows=io.manifest(root,names)
    if any(r.get('sha256') is None for r in rows.values()):raise ValueError('A required synthesis input is missing')
    if any(r['bytes']>1024*1024 for r in rows.values()) or sum(r['bytes'] for r in rows.values())>8*1024*1024:
        raise ValueError('Synthesis source snapshot exceeds its bound')
    for name in spec['rtl']:safe_rtl(io.project_path(root,name).read_text())
    return rows


def script(sources,top):
    if not re.fullmatch('[A-Za-z_][A-Za-z0-9_]*',top):raise ValueError('Invalid fixed top name')
    if any(not re.fullmatch('[A-Za-z0-9_./-]+',n) or '..' in Path(n).parts for n in sources):raise ValueError('Unsafe synthesis filename')
    return ('read_verilog -sv -noautowire '+ ' '.join(sources)+
            '\nhierarchy -top '+top+'\nproc\nwrite_json elaborated.json\n'+
            'synth_ecp5 -abc9 -top '+top+' -json mapped.json\ncheck -assert -mapped -allow-tbuf\n'+
            'tee -o statistics.json stat -json -top '+top+'\n')


def native_run(tool,recipe,out,env,timeout=180):
    out=Path(out);out.mkdir(parents=True,exist_ok=True);path=out/'synthesis.ys';path.write_text(recipe);sha=io.sha(path)
    result=process.invoke([tool['executable'],'-Q','-T','-s','synthesis.ys','-l','yosys.log'],out,env,timeout)
    if io.sha(path)!=sha:raise ValueError('Synthesis recipe changed during execution')
    return {**result,'script_sha256':sha,'script':str(path)}


def read_json(path,limit=64*1024*1024):
    path=Path(path)
    if not path.is_file() or path.stat().st_size>limit:raise ValueError('Native synthesis output absent or oversized: '+path.name)
    data=io.strict_json(path.read_bytes())
    if not isinstance(data,dict):raise ValueError('Invalid native synthesis JSON')
    return data


def interface(module):
    ports=module['ports'];result={}
    if not isinstance(ports,dict) or not ports:raise ValueError('Native top interface is empty')
    for name,row in ports.items():
        if row['direction'] not in ('input','output','inout') or not row['bits']:raise ValueError('Invalid native top port')
        result[name]={'direction':row['direction'],'bits':len(row['bits']),
                      'offset':row.get('offset',0),'upto':row.get('upto',0),'signed':row.get('signed',0)}
    return result


def parse_results(out,top,version):
    out=Path(out);mapped=read_json(out/'mapped.json');before=read_json(out/'elaborated.json');stats=read_json(out/'statistics.json',1024*1024)
    if mapped.get('creator')!=version or stats.get('creator')!=version:raise ValueError('Native output version differs from its probed executable')
    module=mapped['modules'][top];prior=before['modules'][top];ports=interface(module)
    if ports!=interface(prior):raise ValueError('Synthesis changed the top port names, widths or directions')
    if int(module.get('attributes',{}).get('top','0'),2)!=1:raise ValueError('Native mapped top identity is missing')
    cells=module['cells'];counts=dict(sorted(Counter(row['type'] for row in cells.values()).items()))
    if not cells or len(cells)>200000:raise ValueError('Native mapped cell count is outside the bound')
    for cell in cells.values():
        kind=cell['type']
        if kind.startswith('$') and kind!='$_TBUF_':raise ValueError('An unmapped internal cell remains: '+kind)
        if kind!='$_TBUF_':
            definition=mapped['modules'].get(kind)
            if not definition or not re.search(r'[/\\]ecp5[/\\]cells_(sim|bb)\.v:',definition.get('attributes',{}).get('src','')):
                raise ValueError('Mapped cell is outside the recorded ECP5 primitive library: '+kind)
    key='\\'+top;row=stats['modules'].get(key,stats['modules'].get(top))
    if not row or row['num_cells']!=len(cells) or row['num_cells_by_type']!=counts:
        raise ValueError('Native statistics do not match the mapped netlist cells')
    if row['num_processes'] or row['num_memories']:raise ValueError('Unmapped processes or generic memories remain')
    return {'top':top,'ports':ports,'port_interface_preserved':True,'cell_count':len(cells),'cells_by_type':counts,
            'wire_bits':row['num_wire_bits'],'mapped_sha256':io.sha(out/'mapped.json'),
            'statistics_sha256':io.sha(out/'statistics.json'),'elaborated_sha256':io.sha(out/'elaborated.json'),
            'scope':'ECP5 synthesis primitives, including the stock $_TBUF_ tri-state marker. No placement, routing, pin assignment, timing closure, functional-equivalence or physical verdict.'}


def qualify(tool,out,env):
    out=Path(out);good=out/'mapped';good.mkdir(parents=True);(good/'fixture.sv').write_text(FIXTURE)
    positive=native_run(tool,script(['fixture.sv'],'ledger_synth'),good,env,30)
    if positive['exit_status']:raise ValueError('Known mapped-cell fixture failed')
    parsed=parse_results(good,'ledger_synth',tool['version'])
    if not parsed['cells_by_type'].get('LUT4') or not parsed['cells_by_type'].get('TRELLIS_FF'):
        raise ValueError('Known fixture did not preserve its logic and register cell classes')
    truth=out/'truth';truth.mkdir();(truth/'fixture.sv').write_text('module truth(input a,b,output y); assign y=a^b; endmodule\n')
    proof='read_verilog fixture.sv\nprep -top truth\n'+''.join('sat -verify -prove y '+str(a^b)+' -set a '+str(a)+' -set b '+str(b)+'\n' for a in (0,1) for b in (0,1))
    truth_result=native_run(tool,proof,truth,env,15)
    log=(truth/'yosys.log').read_text()
    if truth_result['exit_status'] or log.count('SAT proof finished - no model found: SUCCESS!')!=4:
        raise ValueError('Known four-case truth-table fixture did not prove')
    cases={}
    bad={'missing_module':'module bad(input a,output y); MISSING_LEDGER_CELL u(a,y); endmodule\n',
         'undriven':'module bad(input a,output y); wire missing; assign y=missing; endmodule\n'}
    for name,text in bad.items():
        folder=out/name;folder.mkdir();(folder/'fixture.sv').write_text(text)
        result=native_run(tool,'read_verilog fixture.sv\nhierarchy -check -top bad\nproc\ncheck -assert\n',folder,env,15)
        if result['exit_status']==0:raise ValueError('Native tool accepted the deliberately broken '+name+' fixture')
        cases[name]=result
    return {'qualified':True,'reused':False,'positive':positive,'mapped_validation':parsed,'truth_table':truth_result,
            'negative_cases':cases,'adapter_sha256':io.sha(Path(__file__)),'host':platform.platform(),
            'scope':'Mapped ECP5/ABC9 output and parser, known truth table and rejected hierarchy/undriven cases; repeated each job. Not project functional equivalence or board qualification.'}


def warnings(path):
    text=Path(path).read_text(errors='replace')
    return [line.strip() for line in text.splitlines() if line.startswith('Warning:')]


def run(root,operation,ident):
    root=Path(root).resolve()
    if operation not in ('qualify',*PROFILES) or not re.fullmatch('[0-9a-f]{32}',ident):raise ValueError('Invalid synthesis operation or job ID')
    directory=root/'build/yosys/runs'/ident
    if any(p.is_symlink() for p in (root/'build',root/'build/yosys',root/'build/yosys/runs',directory,directory/'attempts')):raise ValueError('Synthesis output directory is linked')
    out=directory/'attempts'/uuid.uuid4().hex;out.mkdir(parents=True,exist_ok=False)
    record={'schema':CONTRACT,'id':ident,'attempt':out.name,'operation':operation,'created':time.time(),
            'class':'STATIC_CHECK','status':'BLOCKED','execution_status':'NOT_RUN','reason':'','source_unchanged':None,
            'physical_hardware':False,'fabrication':'HOLD','routing':'NOT_RUN','timing':'NOT_CHECKED','programming':'HOLD',
            'artifacts':{}}
    try:
        tool=discover();record['tool']=tool
        if tool['state']!='DETECTED':raise ValueError(tool['reason'])
        if operation!='qualify':
            spec=PROFILES[operation];before=inputs(root,operation);record['inputs']=before;record['input_revision']=io.digest(before)
            record['profile']={k:v for k,v in spec.items() if k!='rtl'}
            for name,row in before.items():
                dest=out/'native/inputs'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(io.project_path(root,name),dest)
                if io.sha(dest)!=row['sha256']:raise ValueError('Source changed while capturing synthesis inputs')
                dest.chmod(0o444)
            if inputs(root,operation)!=before:raise ValueError('Source changed while preparing synthesis')
        env=environment(tool,out/'environment');tool=probe(tool,out/'probe',env);record['tool']=tool
        dependencies=capture_data(tool,out/'environment/data');record['external_data']=dependencies
        record['library_scope']='Installed mapping data is captured for audit and checked before/after use; Yosys resolves its normal installed +/ data path.'
        record['qualification']=qualify(tool,out/'qualification',env)
        if operation=='qualify':record.update(status='QUALIFIED',execution_status='COMPLETED',reason='Mapped-cell, truth-table and rejected-input capability fixtures reproduced.')
        else:
            record['execution_status']='RUNNING'
            native=native_run(tool,script(['inputs/'+n for n in spec['rtl']],spec['top']),out/'native',env)
            record['native']=native;record['warnings']=warnings(out/'native/yosys.log')
            if native['exit_status']:raise ValueError('Native synthesis failed (exit '+str(native['exit_status'])+'); original diagnostics retained')
            record['synthesis']=parse_results(out/'native',spec['top'],tool['version'])
            record['source_unchanged']=inputs(root,operation)==before
            record['snapshot_unchanged']=all(io.sha(out/'native/inputs'/n)==r['sha256'] for n,r in before.items())
            if not record['source_unchanged'] or not record['snapshot_unchanged']:raise ValueError('Synthesis source identity changed during execution')
            record.update(status='SYNTHESIZED',execution_status='COMPLETED',reason='Mapped ECP5 candidate produced; structural check and native count/interface consistency passed. Routing, timing and programming remain unqualified.')
        record['external_data_unchanged']=all(io.sha(Path(r['source']))==r['sha256'] and io.sha(Path(r['snapshot']))==r['sha256'] for r in dependencies.values())
        record['program_files_unchanged']=all(io.sha(Path(p))==sha for p,sha in tool['program_files'].items())
        if not record['external_data_unchanged'] or not record['program_files_unchanged']:raise ValueError('Captured toolchain data or executable changed during synthesis')
    except (OSError,ValueError,KeyError,TypeError,subprocess.SubprocessError) as exc:
        record.update(status='INVALID' if 'synthesis' in record else 'TOOL_ERROR' if record['execution_status']=='RUNNING' else 'BLOCKED',
                      execution_status='FAILED',reason=str(exc))
    record['finished']=time.time()
    for p in sorted(out.rglob('*')):
        if p.is_file() and not p.is_symlink() and not p.is_relative_to(out/'environment/tmp') and not p.is_relative_to(out/'environment/home'):
            record['artifacts'][p.relative_to(root).as_posix()]={'sha256':io.sha(p),'bytes':p.stat().st_size}
    io.write_json(out/'record.json',record);io.write_json(directory/'record.json',record)
    io.write_json(root/'build/yosys/latest.json',{'id':ident,'record_sha256':io.sha(directory/'record.json')})
    return record


def report(root,ident=None):
    root=Path(root).resolve();expected=None
    if not ident:
        if not (root/'build/yosys/latest.json').is_file():return {'state':'NOT_RUN','reason':'Run a registered Yosys profile.'}
        latest=io.load(root,'build/yosys/latest.json');ident=latest['id'];expected=latest['record_sha256']
    if not re.fullmatch('[0-9a-f]{32}',ident):raise ValueError('Invalid synthesis job ID')
    path=io.project_path(root,'build/yosys/runs/'+ident+'/record.json')
    if expected and io.sha(path)!=expected:raise ValueError('Recorded synthesis result changed')
    data=io.strict_json(path.read_bytes());prefix='build/yosys/runs/'+ident+'/attempts/'+data['attempt']+'/'
    if io.sha(path)!=io.sha(io.project_path(root,prefix+'record.json')):raise ValueError('Synthesis record differs from its retained attempt')
    for name,row in data['artifacts'].items():
        if not name.startswith(prefix):raise ValueError('Artifact does not belong to this synthesis attempt')
        artifact=io.project_path(root,name)
        if io.sha(artifact)!=row['sha256'] or artifact.stat().st_size!=row['bytes']:raise ValueError('Original synthesis artifact changed: '+name)
    try:data['source_currentness']='NOT_APPLICABLE' if not data.get('inputs') else 'CURRENT' if inputs(root,data['operation'])==data['inputs'] else 'STALE'
    except (OSError,ValueError) as exc:data['source_currentness']='MISSING_OR_INVALID';data['currentness_reason']=str(exc)
    if data.get('synthesis'):
        parsed=parse_results(root/prefix/'native',PROFILES[data['operation']]['top'],data['tool']['version'])
        if parsed!=data['synthesis']:raise ValueError('Synthesis summary differs from original native outputs')
    return data


def dispatch(kernel,operation,args):
    if operation=='yosys.report':return report(kernel.root,args.get('id'))
    return {'schema':CONTRACT,'tool':discover(),'profiles':{k:{'title':v['title'],'top':v['top']} for k,v in PROFILES.items()},
            'latest':report(kernel.root),'notice':'Current R10 ECP5 synthesis only. Resource counts do not establish physical fit, routing, timing closure or programming approval.'}


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('operation',choices=['qualify',*PROFILES]);ap.add_argument('--root',type=Path,required=True);ap.add_argument('--job',required=True)
    a=ap.parse_args();result=run(a.root,a.operation,a.job)
    print(json.dumps({k:result[k] for k in ('id','status','reason')}))
    raise SystemExit(0 if result['status'] in ('QUALIFIED','SYNTHESIZED') else 2)
