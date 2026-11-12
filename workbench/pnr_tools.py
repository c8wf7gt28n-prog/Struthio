"""Bound ECP5 routing and held Trellis bitstream candidates; no programming IO."""
from __future__ import annotations
import argparse
from collections import Counter
from contextlib import closing
import json
import math
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import time
import uuid
from . import record_io as io, yosys_tools as synth, kicad_tools as process

CONTRACT='arc.ecp5-implementation/1'
FIELDS={name:({'id':{'type':'string','pattern':'^[0-9a-f]{32}$','maxLength':32}},[]) if name.endswith('.report') else ({},[])
        for name in ('nextpnr.inspect','nextpnr.report','trellis.inspect','trellis.report')}
SCOPES={name:'read' for name in FIELDS}
BASE=synth.BASE
PROFILES={
 'graphics':{'title':'45F · CABGA381 · graphics','device':'LFE5U-45F','flag':'45k','package':'CABGA381','speed':6,'proxy':False,
             'synthesis':'graphics','top':'r10_raster_mem_top',
             'lpf':[(BASE/n).as_posix() for n in ('fpga45/constraints/r10_45f.lpf','hardware/lpf/r10_45f_sdram.lpf')]},
 'support_proxy':{'title':'12F · CABGA256 PROXY · support','device':'LFE5U-12F','flag':'12k','package':'CABGA256','speed':6,'proxy':True,
                  'synthesis':'support','top':'r10_support_mem_top',
                  'lpf':[(BASE/n).as_posix() for n in ('fpga12/timing/r10_12f_proxy256.lpf','hardware/lpf/r10_12f_mem_proxy256.lpf')]},
}
FIXTURE='module route_fixture(input clk, output reg led=0); always @(posedge clk) led<=~led; endmodule\n'
FIXTURE_LPF='LOCATE COMP "clk" SITE "P3"; LOCATE COMP "led" SITE "A7";\nIOBUF PORT "clk" IO_TYPE=LVCMOS33; IOBUF PORT "led" IO_TYPE=LVCMOS33; FREQUENCY PORT "clk" 25 MHZ;\n'


def discover(which=None):
    lookup=which or shutil.which;programs={}
    for name in ('nextpnr-ecp5','ecppack','ecpunpack'):
        p=lookup(name)
        programs[name]=({'executable':str(Path(p).absolute()),'resolved_executable':str(Path(p).resolve()),
                         'sha256':io.sha(Path(p).resolve())} if p else None)
    router=programs['nextpnr-ecp5'];packer=programs['ecppack']
    # The stock Linux build uses its compiled /usr/share location. A standard
    # prefix installation is also discoverable; qualification must exercise it.
    prefixes=[Path(router['resolved_executable']).parent.parent] if router else []
    chip_candidates=[Path('/usr/share/nextpnr/ecp5')]+[p/'share/nextpnr/ecp5' for p in prefixes]+[Path('/usr/local/share/nextpnr/ecp5')]
    chip=next((p.resolve() for p in chip_candidates if (p/'chipdb-45k.bin').is_file() and (p/'chipdb-25k.bin').is_file()),None)
    prefixes=[Path(packer['resolved_executable']).parent.parent] if packer else []
    db_candidates=[p/'share/trellis/database' for p in prefixes]+[Path('/usr/share/trellis/database'),Path('/usr/local/share/trellis/database')]
    database=next((p.resolve() for p in db_candidates if (p/'devices.json').is_file()),None)
    available=bool(router and chip);trellis=bool(packer and programs['ecpunpack'] and database)
    return {'nextpnr':'DETECTED' if available else 'NOT_AVAILABLE','trellis':'DETECTED' if trellis else 'NOT_AVAILABLE',
            'programs':programs,'chip_directory':str(chip) if chip else None,'trellis_database':str(database) if database else None,
            'qualified':False,'notice':'Install nextpnr-ecp5 plus its matching chip databases, ecppack/ecpunpack and the Trellis database. Operation fixtures repeat each job; programming is never performed.'}


def environment(tools,out):
    p=next(p for p in tools['programs'].values() if p)
    env=synth.environment(p,Path(out)/'environment')
    return env


def dependencies(tools,stage):
    result={}
    for name in (('nextpnr-ecp5',) if stage=='route' else ('nextpnr-ecp5','ecppack','ecpunpack')):
        p=tools['programs'][name]
        if not p:raise ValueError('Missing native runtime: '+name)
        result[p['resolved_executable']]={'sha256':io.sha(Path(p['resolved_executable'])),'bytes':Path(p['resolved_executable']).stat().st_size}
    chip=Path(tools['chip_directory'])
    for name in ('chipdb-25k.bin','chipdb-45k.bin'):
        p=chip/name
        if p.stat().st_size>64*1024*1024:raise ValueError('Native chip database exceeds bound')
        result[str(p)]={'sha256':io.sha(p),'bytes':p.stat().st_size}
    if stage=='pack':
        database=Path(tools['trellis_database']);files=[p for p in database.rglob('*') if p.is_file()]
        if len(files)>10000 or sum(p.stat().st_size for p in files)>128*1024*1024:raise ValueError('Trellis database exceeds bound')
        for p in files:
            if p.is_symlink():raise ValueError('Trellis database file is linked')
            result[str(p)]={'sha256':io.sha(p),'bytes':p.stat().st_size}
    return result


def unchanged(rows):return all(Path(n).is_file() and io.sha(Path(n))==r['sha256'] for n,r in rows.items())


def latest(root,family,profile=None):
    paths=list((Path(root)/'build'/family/'runs').glob('*/record.json'))
    if len(paths)>1000:raise ValueError('Run history exceeds bounded lookup; archive older evidence separately')
    candidates=[]
    for path in paths:
        data=io.load(root,path.relative_to(root).as_posix())
        match=data.get('operation')==profile if family=='yosys' else data.get('profile_key')==profile
        if profile is None or match:candidates.append((data.get('created',0),path.parent.name))
    # The Kernel also records attempts that were cancelled/killed before an
    # adapter could write a final record. They must block an older successful
    # artifact rather than accidentally resurrect it as the latest attempt.
    state=Path(root)/'.ledger/engineering.sqlite3'
    if profile is not None and state.is_file():
        if state.is_symlink() or state.parent.is_symlink():raise ValueError('Linked Kernel state')
        with closing(sqlite3.connect(state.as_uri()+'?mode=ro',uri=True,timeout=10)) as db:
            rows=db.execute('SELECT payload FROM jobs ORDER BY rowid DESC LIMIT 1000').fetchall()
        for raw, in rows:
            job=io.strict_json(raw.encode())
            if job['tool']==family+'.'+profile:
                candidates.append((job['created'],job['id']));break
    return max(candidates)[1] if candidates else None


def parent(root,stage,profile):
    spec=PROFILES[profile];family='yosys' if stage=='route' else 'nextpnr'
    ident=latest(root,family,spec['synthesis'] if stage=='route' else profile)
    if not ident:raise ValueError('Run '+('yosys.'+spec['synthesis'] if stage=='route' else 'nextpnr.'+profile)+' first; no verified parent is available')
    state=Path(root)/'.ledger/engineering.sqlite3'
    if state.is_file():
        with closing(sqlite3.connect(state.as_uri()+'?mode=ro',uri=True,timeout=10)) as db:
            row=db.execute('SELECT state FROM jobs WHERE id=?',(ident,)).fetchone()
        if row and row[0]!='Completed':raise ValueError('Latest Kernel parent did not complete; rerun it explicitly')
    data=synth.report(root,ident) if stage=='route' else report(root,'nextpnr',ident)
    accepted=('SYNTHESIZED',) if stage=='route' else ('ROUTED_CLOCKS_MET','ROUTED_CLOCKS_MISSED')
    if data['status'] not in accepted or data['source_currentness']!='CURRENT':raise ValueError('Latest parent is incomplete or stale; rerun it explicitly')
    if stage=='route':
        native='build/yosys/runs/'+ident+'/attempts/'+data['attempt']+'/native/mapped.json'
    else:native='build/nextpnr/runs/'+ident+'/attempts/'+data['attempt']+'/native/routed.config'
    return {'family':family,'id':ident,'attempt':data['attempt'],'status':data['status'],'file':native,
            'sha256':io.sha(io.project_path(root,native)),'record_sha256':io.sha(io.project_path(root,'build/'+family+'/runs/'+ident+'/record.json')),
            'input_revision':data.get('input_revision'),'top':spec['top']},data


def lpf(root,spec,ports):
    text='\n'.join(io.project_path(root,n).read_text() for n in spec['lpf'])
    clean=re.sub(r'#[^\n]*','',text);pins={};frequencies={}
    allports={name if row['bits']==1 else name+'['+str(i+row.get('offset',0))+']'
              for name,row in ports.items() for i in range(row['bits'])}
    for statement in clean.split(';'):
        statement=statement.strip()
        if not statement:continue
        match=re.fullmatch(r'LOCATE\s+COMP\s+"([A-Za-z0-9_\[\]]+)"\s+SITE\s+"([A-Z]+[0-9]+)"',statement)
        if match:
            name,pin=match.groups()
            if name not in allports or name in pins or pin in pins.values():raise ValueError('Duplicate or unknown LPF pin binding: '+name)
            pins[name]=pin;continue
        match=re.fullmatch(r'FREQUENCY\s+PORT\s+"([A-Za-z0-9_]+)"\s+([0-9.]+)\s+MHZ',statement)
        if match:
            name,value=match.groups()
            if name not in allports or name in frequencies:raise ValueError('Unknown or duplicate clock constraint')
            frequencies[name]=float(value);continue
        if re.fullmatch(r'IOBUF\s+PORT\s+"[A-Za-z0-9_\[\]]+"\s+(?:[A-Z0-9_]+=[A-Z0-9_.]+\s*)+',statement):continue
        if re.fullmatch(r'SYSCONFIG\s+(?:[A-Z0-9_]+=[A-Z0-9_.]+\s*)+',statement):continue
        raise ValueError('LPF statement is outside the fixed profile grammar')
    if set(pins)!=allports:raise ValueError('LPF must bind every top-level IO exactly once: '+str(sorted(allports-set(pins))))
    return text,{'pins':pins,'ports':ports,'clock_inputs_mhz':frequencies,'io_count':len(pins),
                 'scope':'Complete source LPF pin coverage; board CAD electrical equivalence and external IO/CDC timing are not qualified.'}


def route_argv(tool,spec,json_file,lpf_file):
    return [tool,'--'+spec['flag'],'--package',spec['package'],'--speed',str(spec['speed']),
            '--json',str(json_file),'--lpf',str(lpf_file),'--seed','1','--timing-allow-fail',
            '--textcfg','routed.config','--write','routed.json','--report','timing.json','--detailed-timing-report','--log','nextpnr.log']


def parse_route(out,spec,pins,ports=None):
    out=Path(out);timing=synth.read_json(out/'timing.json');routed=synth.read_json(out/'routed.json',128*1024*1024)
    if len(routed['modules'])!=1:raise ValueError('Unexpected routed-module count')
    module=next(iter(routed['modules'].values()));settings=module['settings']
    if ports is not None and synth.interface(module)!=ports:raise ValueError('Implementation changed the top port interface')
    if any(int(settings.get(n,'0'),2)!=1 for n in ('pack','place','route')):raise ValueError('Native pack/place/route stages did not finish')
    if settings['arch.type']!=spec['device'].lower().replace('-','_') or settings['arch.package']!=spec['package'] or settings['arch.speed']!=str(spec['speed']):
        raise ValueError('Routed device/package/speed differs from the fixed profile')
    actual={};counts=Counter(c['type'] for c in module['cells'].values())
    for name,cell in module['cells'].items():
        if not cell['attributes'].get('NEXTPNR_BEL'):raise ValueError('Routed output contains an unplaced cell')
        if cell['type']=='TRELLIS_IO':
            port=name.removesuffix('$tr_io');actual[port]=cell['attributes'].get('LOC')
    if actual!=pins:raise ValueError('Routed IO locations differ from complete LPF bindings')
    clocks={}
    for name,row in timing['fmax'].items():
        achieved=row['achieved'];constraint=row['constraint']
        if any(isinstance(v,bool) or not isinstance(v,(float,int)) or not math.isfinite(v) or v<=0 for v in (achieved,constraint)):
            raise ValueError('Invalid native clock frequency')
        clocks[name]={**row,'met':achieved>=constraint,'margin_mhz':achieved-constraint}
    if not clocks:raise ValueError('No native internal-clock timing results')
    for name,row in timing['utilization'].items():
        if not (isinstance(row['used'],int) and isinstance(row['available'],int) and 0<=row['used']<=row['available']):raise ValueError('Invalid native utilization')
        if counts.get(name,0)!=row['used']:raise ValueError('Native utilization differs from routed cell count: '+name)
    config=(out/'routed.config').read_text()
    if not config.startswith('.device '+spec['device']+'\n') or '.comment Part: '+spec['device']+'-'+str(spec['speed'])+spec['package'] not in config:
        raise ValueError('Text configuration has a different device/package identity')
    if 'Program finished normally.' not in (out/'nextpnr.log').read_text():raise ValueError('Native routing completion receipt absent')
    return {'clocks':clocks,'reported_internal_clocks_met':all(r['met'] for r in clocks.values()),
            'utilization':timing['utilization'],'io_locations':actual,'io_count':len(actual),
            'critical_path_count':len(timing['critical_paths']),'routed_sha256':io.sha(out/'routed.json'),
            'config_sha256':io.sha(out/'routed.config'),'timing_sha256':io.sha(out/'timing.json'),
            'scope':'Reported internal clock fmax only, single seed 1 at speed 6. External IO timing, CDC, board pin/electrical equivalence and hardware remain unqualified.'}


def qualify(tools,out,env,stage):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    y=synth.discover()
    if y['state']!='DETECTED':raise ValueError('Yosys is needed for the independent route fixture')
    yenv=synth.environment(y,out/'environment');y=synth.probe(y,out/'probe',yenv)
    good=out/'fixture';good.mkdir();(good/'fixture.sv').write_text(FIXTURE)
    build=synth.native_run(y,synth.script(['fixture.sv'],'route_fixture'),good,yenv,30)
    if build['exit_status']:raise ValueError('Known route fixture synthesis failed')
    synth.parse_results(good,'route_fixture',y['version']);(good/'fixture.lpf').write_text(FIXTURE_LPF)
    spec=PROFILES['graphics'];route=process.invoke(route_argv(tools['programs']['nextpnr-ecp5']['executable'],spec,'mapped.json','fixture.lpf'),good,env,30)
    if route['exit_status']:raise ValueError('Known two-pin routing fixture failed')
    parsed=parse_route(good,spec,{'clk':'P3','led':'A7'})
    if not parsed['reported_internal_clocks_met']:raise ValueError('Known fixture missed 25 MHz')
    bad=out/'bad_pin';bad.mkdir();(bad/'bad.lpf').write_text(FIXTURE_LPF.replace('A7','NOT_A_PIN'))
    negative=process.invoke(route_argv(tools['programs']['nextpnr-ecp5']['executable'],spec,str(good/'mapped.json'),'bad.lpf'),bad,env,30)
    if not negative['exit_status']:raise ValueError('Native tool accepted deliberately invalid package pin')
    missed=out/'missed_clock';missed.mkdir();(missed/'fast.lpf').write_text(FIXTURE_LPF.replace('25 MHZ','10000 MHZ'))
    missed_receipt=process.invoke(route_argv(tools['programs']['nextpnr-ecp5']['executable'],spec,str(good/'mapped.json'),'fast.lpf'),missed,env,30)
    if missed_receipt['exit_status']:raise ValueError('Deliberately missed-clock fixture did not retain its routed output')
    missed_result=parse_route(missed,spec,{'clk':'P3','led':'A7'})
    if missed_result['reported_internal_clocks_met']:raise ValueError('Parser incorrectly accepted deliberately unattainable clock target')
    if not all(io.sha(Path(p))==sha for p,sha in y['program_files'].items()):raise ValueError('Fixture synthesis runtime changed')
    result={'qualified':True,'reused':False,'yosys':y,'fixture_synthesis':build,'positive':route,'invalid_pin':negative,
            'missed_clock':{'native':missed_receipt,'route':missed_result},
            'route':parsed,'scope':'Known tiny 45F/381 placement/routing and rejected invalid pin; not project function or hardware qualification.'}
    if stage=='pack':result['packing']=pack_checked(tools,good/'routed.config',out/'packing',env)
    return result


def pack_checked(tools,config,out,env):
    out=Path(out);out.mkdir(parents=True,exist_ok=True);shutil.copyfile(config,out/'input.config')
    db=tools['trellis_database'];pack=tools['programs']['ecppack']['executable'];unpack=tools['programs']['ecpunpack']['executable']
    def invoke(name,args):
        folder=out/name;folder.mkdir()
        return process.invoke(args,folder,env,45)
    receipts={}
    receipts['pack']=invoke('pack',[pack,'--db',db,'--compress','--input',str(out/'input.config'),'--bit',str(out/'candidate.bit')])
    if receipts['pack']['exit_status']:raise ValueError('Native bitstream packing failed')
    receipts['unpack']=invoke('unpack',[unpack,'--db',db,'--input',str(out/'candidate.bit'),'--textcfg',str(out/'decoded.config')])
    if receipts['unpack']['exit_status']:raise ValueError('Native bitstream decode/CRC check failed')
    receipts['repack']=invoke('repack',[pack,'--db',db,'--compress','--input',str(out/'decoded.config'),'--bit',str(out/'repacked.bit')])
    if receipts['repack']['exit_status']:raise ValueError('Decoded configuration could not be repacked')
    receipts['redecode']=invoke('redecode',[unpack,'--db',db,'--input',str(out/'repacked.bit'),'--textcfg',str(out/'decoded_again.config')])
    if receipts['redecode']['exit_status'] or (out/'decoded.config').read_bytes()!=(out/'decoded_again.config').read_bytes():raise ValueError('Configuration changed after native decode/repack/decode')
    raw=(out/'candidate.bit').read_bytes()
    if len(raw)<100 or len(raw)>8*1024*1024:raise ValueError('Bitstream size outside bound')
    corrupt=bytearray(raw);corrupt[len(corrupt)//2]^=1;(out/'corrupt.bit').write_bytes(corrupt)
    receipts['corrupt_rejected']=invoke('corrupt',[unpack,'--db',db,'--input',str(out/'corrupt.bit'),'--textcfg',str(out/'invalid.config')])
    if receipts['corrupt_rejected']['exit_status']==0:raise ValueError('Native decoder accepted a deliberately invalid bitstream')
    return {'bytes':len(raw),'sha256':io.sha(out/'candidate.bit'),'decoded_sha256':io.sha(out/'decoded.config'),
            'decoded_roundtrip_equal':True,'receipts':receipts,
            'scope':'Native encode/decode and stable decoded-configuration roundtrip; not functional, board or programming qualification.'}


def run(root,operation,ident):
    root=Path(root).resolve();stage,key=operation.split('-',1);family='nextpnr' if stage=='route' else 'trellis'
    if stage not in ('route','pack') or key not in ('qualify',*PROFILES) or not re.fullmatch('[0-9a-f]{32}',ident):raise ValueError('Invalid implementation operation')
    directory=root/'build'/family/'runs'/ident
    if any(p.is_symlink() for p in (root/'build',root/'build'/family,root/'build'/family/'runs',directory,directory/'attempts')):raise ValueError('Linked implementation output')
    out=directory/'attempts'/uuid.uuid4().hex;out.mkdir(parents=True)
    record={'schema':CONTRACT,'family':family,'id':ident,'attempt':out.name,'created':time.time(),'operation':operation,
            'profile_key':key,'class':'STATIC_CHECK','status':'BLOCKED','reason':'','fabrication':'HOLD','routing_release':'HOLD','programming':'HOLD','physical_hardware':False,'artifacts':{}}
    try:
        tools=discover();record['tools']=tools
        if tools['nextpnr']!='DETECTED' or stage=='pack' and tools['trellis']!='DETECTED':raise ValueError(tools['notice'])
        env=environment(tools,out);bound=dependencies(tools,stage);record['dependencies']=bound
        for name,p in tools['programs'].items():
            if p and (stage=='pack' or name=='nextpnr-ecp5'):
                receipt=process.invoke([p['executable'],'--help' if name=='ecpunpack' else '--version'],out/'versions'/name,env,10)
                output=(receipt['stdout']+' '+receipt['stderr']).strip()
                if name=='ecpunpack':
                    match=re.search(r'\bVersion ([0-9][^\n]*)',output)
                    if not match:raise ValueError('Native decoder version banner absent')
                    p['version']='Project Trellis '+match.group(1)
                else:
                    if receipt['exit_status']:raise ValueError('Native version probe failed: '+name)
                    p['version']=output
        if key!='qualify':
            spec=PROFILES[key];record['profile']=spec
            source=io.manifest(root,spec['lpf']+['workbench/pnr_tools.py']);record['inputs']=source;record['input_revision']=io.digest(source)
            binding,data=parent(root,stage,key);record['parent']=binding
            if stage=='route':
                text,coverage=lpf(root,spec,data['synthesis']['ports']);record['constraints']=coverage
                native=out/'native';native.mkdir();(native/'constraints.lpf').write_text(text)
                shutil.copyfile(io.project_path(root,binding['file']),native/'mapped.json')
            else:
                record['route_summary']=data['route'];record['constraints']=data['constraints']
        record['qualification']=qualify(tools,out/'qualification',env,stage)
        if key=='qualify':record.update(status='QUALIFIED',reason='Native operation-specific capability fixtures reproduced; no project candidate.')
        elif stage=='route':
            native=out/'native';receipt=process.invoke(route_argv(tools['programs']['nextpnr-ecp5']['executable'],spec,'mapped.json','constraints.lpf'),native,env,300)
            record['native']=receipt
            if receipt['exit_status']:raise ValueError('Native routing failed; original log retained (exit '+str(receipt['exit_status'])+')')
            record['route']=parse_route(native,spec,coverage['pins'],coverage['ports'])
            record.update(status='ROUTED_CLOCKS_MET' if record['route']['reported_internal_clocks_met'] else 'ROUTED_CLOCKS_MISSED',
                          reason='Routed single-seed candidate; reported internal clock results are separate from unqualified external IO/CDC and physical hardware timing.')
        else:
            record['packing']=pack_checked(tools,io.project_path(root,binding['file']),out/'native',env)
            record.update(status='PACKED_HELD',reason='Offline bitstream candidate decoded and roundtrip checked. Programming and hardware release remain HOLD.')
        if key!='qualify':
            record['source_unchanged']=io.manifest(root,list(source))==source
            record['snapshot_unchanged']=((out/'native/mapped.json').is_file() and io.sha(out/'native/mapped.json')==binding['sha256'] and (out/'native/constraints.lpf').read_text()==text) if stage=='route' else io.sha(out/'native/input.config')==binding['sha256']
            binding_after,_=parent(root,stage,key)
            if not record['source_unchanged'] or not record['snapshot_unchanged'] or binding_after!=binding:raise ValueError('Implementation input, copy or parent changed during execution')
        record['dependencies_unchanged']=unchanged(bound)
        if not record['dependencies_unchanged']:raise ValueError('Native runtime or database changed during execution')
    except (ValueError,OSError,KeyError,TypeError,subprocess.SubprocessError) as exc:
        record.update(status='INVALID' if 'route' in record or 'packing' in record else 'BLOCKED',reason=str(exc))
    record['finished']=time.time()
    for p in sorted(out.rglob('*')):
        if p.is_file() and not p.is_symlink() and 'environment' not in p.relative_to(out).parts:
            record['artifacts'][p.relative_to(root).as_posix()]={'sha256':io.sha(p),'bytes':p.stat().st_size}
    io.write_json(out/'record.json',record);io.write_json(directory/'record.json',record)
    io.write_json(root/'build'/family/'latest.json',{'id':ident,'record_sha256':io.sha(directory/'record.json')})
    return record


def report(root,family,ident=None):
    root=Path(root).resolve();expected=None
    if family not in ('nextpnr','trellis'):raise ValueError('Invalid implementation family')
    if not ident:
        pointer=root/'build'/family/'latest.json'
        if not pointer.is_file():return {'state':'NOT_RUN','reason':'Run a registered '+family+' job.'}
        row=io.load(root,pointer.relative_to(root).as_posix());ident=row['id'];expected=row['record_sha256']
    if not re.fullmatch('[0-9a-f]{32}',ident):raise ValueError('Invalid implementation job ID')
    path=io.project_path(root,'build/'+family+'/runs/'+ident+'/record.json');data=io.strict_json(path.read_bytes())
    prefix='build/'+family+'/runs/'+ident+'/attempts/'+data['attempt']+'/'
    if expected and io.sha(path)!=expected or io.sha(path)!=io.sha(io.project_path(root,prefix+'record.json')):raise ValueError('Implementation record changed')
    for name,row in data['artifacts'].items():
        if not name.startswith(prefix):raise ValueError('Artifact is outside its attempt')
        p=io.project_path(root,name)
        if io.sha(p)!=row['sha256'] or p.stat().st_size!=row['bytes']:raise ValueError('Original implementation artifact changed: '+name)
    data['source_currentness']='NOT_APPLICABLE'
    if data.get('inputs'):
        try:
            binding,_=parent(root,'route' if family=='nextpnr' else 'pack',data['profile_key'])
            data['source_currentness']='CURRENT' if io.manifest(root,list(data['inputs']))==data['inputs'] and binding==data['parent'] else 'STALE'
        except (ValueError,OSError):data['source_currentness']='MISSING_OR_INVALID_PARENT'
    if data.get('route') and parse_route(root/prefix/'native',PROFILES[data['profile_key']],data['constraints']['pins'],data['constraints']['ports'])!=data['route']:raise ValueError('Routed summary differs from original outputs')
    if data.get('packing'):
        native=root/prefix/'native'
        if io.sha(native/'candidate.bit')!=data['packing']['sha256'] or (native/'decoded.config').read_bytes()!=(native/'decoded_again.config').read_bytes():raise ValueError('Packed summary differs from original outputs')
    return data


def dispatch(kernel,operation,args):
    family=operation.split('.')[0]
    if operation.endswith('.report'):return report(kernel.root,family,args.get('id'))
    return {'schema':CONTRACT,'tools':discover(),'profiles':PROFILES,'latest':report(kernel.root,family),
            'notice':'45F/381 exact package; 12F/256 explicitly a package proxy. Single-seed internal clock results; external IO/CDC/board timing and physical programming unqualified.'}


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('operation');ap.add_argument('--root',type=Path,required=True);ap.add_argument('--job',required=True)
    a=ap.parse_args();result=run(a.root,a.operation,a.job)
    print(json.dumps({k:result[k] for k in ('id','status','reason')}))
    raise SystemExit(0 if result['status'] in ('QUALIFIED','ROUTED_CLOCKS_MET','ROUTED_CLOCKS_MISSED','PACKED_HELD') else 2)
