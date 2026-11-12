"""Qualified read-only KiCad DRC over a protected native project snapshot.

No source edits, user plugins, zone refill, board save or release approval.
The command lifecycle and the design findings are separate results.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import time
import uuid
from . import brain_link, record_io as io

CONTRACT='arc.kicad-drc/1'
CAD=Path(brain_link.BASE)/'cad'
BOARD='ARC1_R10.kicad_pcb'
FIELDS={'cad.inspect':({},[]), 'cad.report':({'id':{'type':'string','pattern':'^[0-9a-f]{32}$','maxLength':32}},[])}
SCOPES={name:'read' for name in FIELDS}
HEADER='''(kicad_pcb (version 20241229) (generator "pcbnew") (generator_version "9.0")
(general (thickness 1.6)) (paper "A4")
(layers (0 "F.Cu" signal) (2 "B.Cu" signal) (25 "Edge.Cuts" user))
(setup (pad_to_mask_clearance 0))
'''
FIXTURES={
 'good':HEADER+'(gr_rect (start 10 10) (end 50 40) (stroke (width 0.05) (type default)) (fill none) (layer "Edge.Cuts") (uuid "7b65d471-a47a-4da2-a1dd-a7cb28571c88"))\n)\n',
 'bad':HEADER+'(gr_line (start 10 10) (end 50 10) (stroke (width 0.05) (type default)) (layer "Edge.Cuts") (uuid "7b65d471-a47a-4da2-a1dd-a7cb28571c88"))\n)\n',
}


def discover(which=None):
    path=(which or shutil.which)('kicad-cli')
    if not path:
        candidates=[]
        if os.name=='nt':
            for prefix in ('ProgramFiles','ProgramFiles(x86)'):
                if os.environ.get(prefix):
                    candidates.extend(Path(os.environ[prefix])/'KiCad'/v/'bin/kicad-cli.exe' for v in ('10.0','9.0'))
        elif sys.platform=='darwin':candidates=[Path('/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli')]
        path=next((str(p) for p in candidates if p.is_file()),None)
    if not path:return {'state':'NOT_AVAILABLE','executable':None,'qualified':False,'reason':'Install KiCad 9 or newer with kicad-cli. Graphite still opens without it.'}
    p=Path(path).resolve()
    candidates=[p,p.parent/'_pcbnew.kiface',p.parent.parent/'lib/kicad/_pcbnew.kiface',
                p.parent.parent/'shared/bin/kicad-cli',p.parent.parent/'shared/bin/_pcbnew.kiface']
    program_files={str(f.resolve()):io.sha(f) for f in candidates if f.is_file()}
    return {'state':'DETECTED','executable':str(Path(path).absolute()),'resolved_executable':str(p),'program_files':program_files,
            'sha256':io.sha(p),'qualified':False,'reason':'Presence only; a registered CAD job qualifies DRC before use.'}


def inputs(root):
    root=Path(root).resolve();cad=root/CAD
    names=[]
    for p in sorted(cad.rglob('*')):
        if p.is_symlink():raise ValueError('CAD snapshot rejects symbolic links')
        if p.is_file() and (p.suffix.startswith('.kicad_') or p.name in ('fp-lib-table','sym-lib-table')):
            rel=p.relative_to(root).as_posix();io.project_path(root,rel)
            if p.stat().st_size>32*1024*1024:raise ValueError('Native CAD input exceeds the 32 MiB per-file bound')
            names.append(rel)
    for required in (BOARD,'ARC1_R10.kicad_pro','ARC1_R10.kicad_sch'):
        io.project_path(root,(CAD/required).as_posix())
    if not names or len(names)>5000:raise ValueError('CAD input count is outside the snapshot bound')
    result=io.manifest(root,names)
    if sum(r['bytes'] for r in result.values())>64*1024*1024:raise ValueError('Native CAD snapshot exceeds 64 MiB')
    # Project-local library URIs must stay within this captured directory.
    for table in ('fp-lib-table','sym-lib-table'):
        path=cad/table
        if not path.is_file():continue
        for uri in re.findall(r'\(uri\s+"([^"]+)"',path.read_text()):
            if not uri.startswith('${KIPRJMOD}/'):raise ValueError('External project library URI needs an explicit source binding: '+table)
            target=cad/uri[len('${KIPRJMOD}/'):]
            if not target.resolve().is_relative_to(cad.resolve()) or not target.exists():raise ValueError('Project library is absent or escapes the CAD snapshot')
    return result


def environment(folder,major=9):
    folder=Path(folder);home=folder/'home';config=folder/'config'
    home.mkdir(parents=True,exist_ok=True);config.mkdir(parents=True,exist_ok=True)
    env={k:v for k,v in os.environ.items() if k in ('PATH','SystemRoot','WINDIR','LANG','TEMP','TMP','LD_LIBRARY_PATH','DYLD_LIBRARY_PATH')}
    env.update(HOME=str(home),USERPROFILE=str(home),APPDATA=str(config),XDG_CONFIG_HOME=str(config),
               KICAD_CONFIG_HOME=str(config/'kicad'),QT_QPA_PLATFORM='offscreen')
    return env


def invoke(argv,folder,env,timeout):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    started=time.monotonic()
    with (folder/'stdout.txt').open('wb') as stdout,(folder/'stderr.txt').open('wb') as stderr:
        p=subprocess.Popen(argv,cwd=folder,env=env,stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr)
        try:p.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            from .operation_stop import owned_tree,kill_owned
            kill_owned(owned_tree([p.pid]));p.wait(timeout=5)
            raise
    def tail(name):
        with (folder/name).open('rb') as f:
            f.seek(max(0,(folder/name).stat().st_size-12000));return f.read().decode(errors='replace')
    return {'argv':argv,'exit_status':p.returncode,'duration_seconds':time.monotonic()-started,
            'stdout':tail('stdout.txt'),'stderr':tail('stderr.txt')}


def probe(tool,folder):
    folder=Path(folder);env=environment(folder)
    v=invoke([tool['executable'],'version'],folder/'version',env,10)
    version=v['stdout'].strip()
    if v['exit_status'] or not re.fullmatch(r'\d+\.\d+\.\d+[^\n]*',version):raise ValueError('KiCad version probe did not return a usable version')
    major=int(version.split('.')[0])
    if major<9:raise ValueError('This R10 board requires KiCad 9 or newer')
    help_result=invoke([tool['executable'],'pcb','drc','--help'],folder/'help',env,10)
    if help_result['exit_status'] or any(flag not in help_result['stdout'] for flag in ('--format','--severity-all','--all-track-errors','--exit-code-violations')):
        raise ValueError('Required native DRC/JSON/violation-exit capability is unavailable')
    return {**tool,'version':version,'major':major,'version_probe':v,'capability_probe':help_result}


def parse_report(path):
    path=Path(path)
    if not path.is_file() or path.stat().st_size>64*1024*1024:raise ValueError('Native DRC report absent or larger than 64 MiB')
    data=io.strict_json(path.read_bytes())
    if not isinstance(data,dict) or not all(isinstance(data.get(k),list) for k in ('violations','unconnected_items','schematic_parity')):
        raise ValueError('Native DRC JSON does not have the qualified report structure')
    rows=[];counts={'error':0,'warning':0,'exclusion':0,'other':0}
    for group in ('violations','unconnected_items','schematic_parity'):
        for item in data[group]:
            if not isinstance(item,dict) or not isinstance(item.get('description'),str):raise ValueError('Invalid native DRC finding')
            severity=item.get('severity','other');counts[severity if severity in counts else 'other']+=1
            rows.append({'group':group,**item})
    return {'counts':counts,'total':len(rows),'findings':rows,'ignored_checks':data.get('ignored_checks',[]),
            'included_severities':data.get('included_severities'),'kicad_version':data.get('kicad_version'),
            'native_source':data.get('source'),'sha256':io.sha(path),'bytes':path.stat().st_size}


def native_drc(tool,board,out,env,timeout=90):
    out=Path(out);report=out/'drc.json'
    run=invoke([tool['executable'],'pcb','drc','--format','json','--severity-all','--all-track-errors','--exit-code-violations',
                '--output',str(report),str(board)],out,env,timeout)
    if run['exit_status'] not in (0,5):raise ValueError('Native DRC execution failed (exit '+str(run['exit_status'])+'); inspect its retained stderr')
    parsed=parse_report(report)
    if parsed['kicad_version']!=tool['version']:raise ValueError('Native report version differs from the probed executable')
    if run['exit_status']==0 and any(parsed['counts'][k] for k in ('error','warning','other')):
        raise ValueError('Native exit status contradicts its reported violations')
    if run['exit_status']==5 and not parsed['total']:raise ValueError('Native violation exit without reported findings')
    return {**run,**parsed,'native_report':str(report)}


def qualify(root,tool,out):
    root=Path(root);out=Path(out)
    binding={'contract':CONTRACT,'executable_sha256':tool['sha256'],'version':tool['version'],
             'program_files':tool.get('program_files',{}),
             'adapter_sha256':io.sha(Path(__file__)),'fixtures':{k:hashlib.sha256(v.encode()).hexdigest() for k,v in FIXTURES.items()},
             'platform':{'system':platform.system(),'release':platform.release(),'machine':platform.machine()}}
    cache=root/'.ledger/cad/qualification.json'
    try:
        prior=io.strict_json(cache.read_bytes())
        if prior['binding']==binding and prior['qualified'] and all(Path(r['native_report']).is_file() and io.sha(r['native_report'])==r['sha256'] for r in prior['cases'].values()):
            return {**prior,'reused':True}
    except (OSError,ValueError,KeyError,TypeError,AttributeError):pass
    cases={}
    for name,text in FIXTURES.items():
        directory=out/name;directory.mkdir(parents=True,exist_ok=True)
        board=directory/(name+'.kicad_pcb');board.write_text(text)
        cases[name]=native_drc(tool,board,directory,environment(directory,tool['major']),20)
        if board.read_text()!=text:raise ValueError('Native tool altered a qualification fixture')
    good=cases['good']['exit_status']==0 and cases['good']['total']==0
    bad=cases['bad']['exit_status']==5 and any(r.get('type')=='invalid_outline' and r.get('severity')=='error' for r in cases['bad']['findings'])
    if not good or not bad:raise ValueError('Native DRC qualification did not reproduce the expected positive and negative cases')
    record={'qualified':True,'binding':binding,'created':time.time(),'cases':cases,'reused':False,
            'scope':'Native DRC command and JSON interpretation on this host; no physical or full-design qualification.'}
    io.write_json(cache,record);return record


def resource_directory(tool):
    executable=Path(tool['resolved_executable'])
    candidates=[executable.parent.parent/'share/kicad',executable.parent.parent/'usr/share/kicad',
                executable.parent.parent/'SharedSupport']
    return next((p.resolve() for p in candidates if (p/'footprints').is_dir()),None)


def library_environment(root,tool,out):
    """Bind selected external footprint comparisons; retain missing-library findings."""
    root=Path(root);out=Path(out);cad=root/CAD
    board=(cad/BOARD).read_text()
    references=sorted(set(re.findall(r'^\s*\(footprint\s+"([^"\n]+)"',board,re.M)))
    local=set()
    if (cad/'fp-lib-table').is_file():local=set(re.findall(r'\(name\s+"([^"\n]+)"',(cad/'fp-lib-table').read_text()))
    resources=resource_directory(tool);external=[];missing=[];libraries=set()
    for reference in references:
        nickname,sep,footprint=reference.partition(':')
        if not sep or nickname in local:continue
        if any(c in nickname+footprint for c in '/\\\x00') or '..' in (nickname,footprint):
            raise ValueError('Unsafe external footprint reference')
        source=resources/'footprints'/(nickname+'.pretty')/(footprint+'.kicad_mod') if resources else None
        if source is None or not source.is_file():missing.append(reference);continue
        dest=out/'footprints'/(nickname+'.pretty')/source.name;dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(source,dest);sha=io.sha(source)
        if io.sha(dest)!=sha:raise ValueError('External footprint changed while copying')
        external.append({'reference':reference,'source':str(source),'sha256':sha,'snapshot':str(dest)})
        libraries.add(nickname)
    env=environment(out,tool['major']);variable='KICAD'+str(tool['major'])+'_FOOTPRINT_DIR'
    env[variable]=str(out/'footprints')
    table='(fp_lib_table (version 7)\n'+''.join(' (lib (name '+json.dumps(n)+')(type "KiCad")(uri "${'+variable+'}/'+n+'.pretty")(options "")(descr "Ledger captured native dependency"))\n' for n in sorted(libraries))+')\n'
    for directory in (out/'config/kicad',out/'config/kicad'/f"{tool['major']}.0"):
        directory.mkdir(parents=True,exist_ok=True);(directory/'fp-lib-table').write_text(table)
    return env,{'files':external,'missing_references':missing,'global_fp_table_sha256':io.sha(out/'config/kicad/fp-lib-table'),
                'scope':'Embedded board geometry and captured project files. External footprint comparisons use captured installed library files; unavailable references remain explicit.'}


def run(root,operation,ident):
    root=Path(root).resolve()
    if operation not in ('drc','qualify') or not re.fullmatch('[0-9a-f]{32}',ident):raise ValueError('Invalid CAD operation or run ID')
    run_directory=root/'build/cad/runs'/ident
    if any(p.is_symlink() for p in (root/'build',root/'build/cad',root/'build/cad/runs',run_directory,run_directory/'attempts')):raise ValueError('CAD output path is linked')
    attempt=uuid.uuid4().hex;out=run_directory/'attempts'/attempt
    out.mkdir(parents=True,exist_ok=False)
    record={'schema':CONTRACT,'id':ident,'created':time.time(),'operation':operation,'class':'STATIC_CHECK',
            'target':'R10 · F133-B / D213ECV / ECP5-12F / ECP5-45F','status':'BLOCKED',
            'attempt':attempt,'physical_hardware':False,'fabrication':'HOLD','source_unchanged':None,'reason':'',
            'execution_status':'NOT_RUN',
            'check_scope':'Stored board geometry and zone fills. No refill, schematic-parity check or ERC is performed.'}
    try:
        tool=discover();record['tool']=tool
        if not tool['executable']:raise ValueError(tool['reason'])
        tool=probe(tool,out/'probe');record['tool']=tool
        record['qualification']=qualify(root,tool,out/'qualification')
        if operation=='qualify':record.update(status='QUALIFIED',execution_status='COMPLETED',reason='Native good and deliberately broken outline cases reproduced.')
        else:
            before=inputs(root);record['inputs']=before;record['input_revision']=io.digest(before)
            snapshot=out/'inputs'
            for name,row in before.items():
                relative=Path(name).relative_to(CAD);dest=snapshot/relative;dest.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(io.project_path(root,name),dest)
                if io.sha(dest)!=row['sha256']:raise ValueError('Source changed while preparing the native snapshot')
                dest.chmod(0o444)
            env,dependencies=library_environment(root,tool,out/'environment');record['external_inputs']=dependencies
            record['execution_status']='RUNNING'
            native=native_drc(tool,snapshot/BOARD,out/'native',env)
            native['native_report']=Path(native['native_report']).relative_to(root).as_posix()
            record['native']=native
            record['source_unchanged']=inputs(root)==before
            record['snapshot_unchanged']=all(io.sha(snapshot/Path(n).relative_to(CAD))==r['sha256'] for n,r in before.items())
            record['external_inputs_unchanged']=all(io.sha(r['source'])==r['sha256'] and io.sha(r['snapshot'])==r['sha256'] for r in dependencies['files'])
            record['tool_unchanged']=all(Path(p).is_file() and io.sha(p)==sha for p,sha in tool.get('program_files',{}).items())
            if not all(record[k] for k in ('source_unchanged','snapshot_unchanged','external_inputs_unchanged','tool_unchanged')):
                raise ValueError('Native inputs changed during DRC; the result is stale')
            record.update(status='VIOLATIONS' if native['total'] else 'NO_REPORTED_VIOLATIONS',execution_status='COMPLETED',
                          reason='Native findings preserved. This does not issue ROUTE-GO, FAB-GO or programming approval.')
    except (OSError,ValueError,subprocess.SubprocessError) as exc:
        status='INVALID' if 'native' in record else 'TOOL_ERROR' if record['execution_status']=='RUNNING' else 'BLOCKED'
        record.update(status=status,execution_status='FAILED' if status!='BLOCKED' else 'NOT_RUN',reason=str(exc))
    record['finished']=time.time();io.write_json(out/'record.json',record)
    io.write_json(run_directory/'record.json',record)
    io.write_json(root/'build/cad/latest.json',{'id':ident,'record_sha256':io.sha(run_directory/'record.json')})
    return record


def report(root,ident=None):
    root=Path(root).resolve();expected=None
    if not ident:
        p=root/'build/cad/latest.json'
        if not p.is_file():return {'state':'NOT_RUN','reason':'Run a registered KiCad check.'}
        latest=io.load(root,'build/cad/latest.json');ident=latest['id'];expected=latest['record_sha256']
    if not re.fullmatch('[0-9a-f]{32}',ident):raise ValueError('Invalid CAD run ID')
    path=io.project_path(root,'build/cad/runs/'+ident+'/record.json')
    if expected and io.sha(path)!=expected:raise ValueError('Recorded CAD result changed')
    data=io.strict_json(path.read_bytes());data['source_currentness']='NOT_APPLICABLE'
    if data.get('inputs'):data['source_currentness']='CURRENT' if inputs(root)==data['inputs'] else 'STALE'
    native=data.get('native')
    if native:
        expected_path='build/cad/runs/'+ident+'/attempts/'+data['attempt']+'/native/drc.json'
        if native['native_report']!=expected_path:raise ValueError('Native report path does not match this run')
        original=io.project_path(root,expected_path)
        if io.sha(original)!=native['sha256']:raise ValueError('Original native DRC report changed')
    return data


def qualification_status(root,tool=None):
    root=Path(root);tool=tool or discover();qualified=None
    try:
        cached=io.strict_json((root/'.ledger/cad/qualification.json').read_bytes())
        if cached.get('qualified') and cached['binding']['executable_sha256']==tool.get('sha256') and cached['binding'].get('program_files')==tool.get('program_files') and cached['binding']['adapter_sha256']==io.sha(Path(__file__)) and all(Path(r['native_report']).is_file() and io.sha(r['native_report'])==r['sha256'] for r in cached['cases'].values()):
            qualified={'state':'CACHED_DRC_CAPABILITY','version':cached['binding']['version'],
                       'scope':cached['scope'],'notice':'Executable version and fixture/report binding are checked again on every run.'}
    except (OSError,ValueError,KeyError,TypeError,AttributeError):pass
    return qualified


def dispatch(kernel,operation,args):
    if operation=='cad.report':return report(kernel.root,args.get('id'))
    tool=discover();qualified=qualification_status(kernel.root,tool)
    return {'schema':CONTRACT,'tool':tool,'qualification':qualified,'inputs':inputs(kernel.root),
            'board':(CAD/BOARD).as_posix(),'target':'R10','read_only':True,'latest':report(kernel.root),
            'notice':'Discovery does not execute or qualify a tool. Native checks use protected snapshots; physical gates remain HOLD.'}


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('operation',choices=['drc','qualify'])
    ap.add_argument('--root',type=Path,required=True);ap.add_argument('--job',required=True)
    a=ap.parse_args();result=run(a.root,a.operation,a.job)
    print(json.dumps({'id':result['id'],'status':result['status'],'reason':result['reason'],
                      'native_counts':result.get('native',{}).get('counts')}))
    raise SystemExit(0 if result['status'] in ('QUALIFIED','VIOLATIONS','NO_REPORTED_VIOLATIONS') else 2)
