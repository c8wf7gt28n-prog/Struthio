"""Fixed KiBot BOM/fabrication recipes over bound R10 copies, via the Kernel.

No project YAML, preflight, downloader, design save or release approval is used.
Native outputs are candidates even when generation and qualification complete.
"""
from __future__ import annotations
import argparse
import csv
import json
import platform
import re
import shutil
import subprocess
import time
import uuid
from pathlib import Path
from xml.etree import ElementTree as ET
from . import kicad_tools as cad, record_io as io

CONTRACT='arc.kibot-outputs/1'
FIELDS={'kibot.inspect':({},[]), 'kibot.report':({'id':{'type':'string','pattern':'^[0-9a-f]{32}$','maxLength':32}},[])}
SCOPES={name:'read' for name in FIELDS}
COLUMNS=['References','Value','Footprint Full','Quantity Per PCB','MPN','Manufacturer','LCSC','Note']
LAYERS=['F.Cu','In1.Cu','In2.Cu','In3.Cu','In4.Cu','B.Cu','F.SilkS','B.SilkS','F.Mask','B.Mask','Edge.Cuts']
GERBERS={'F_Cu','In1_Cu','In2_Cu','In3_Cu','In4_Cu','B_Cu','F_Silkscreen','B_Silkscreen','F_Mask','B_Mask','Edge_Cuts'}


def recipe(operation):
    if operation=='bom':
        outputs=[{'name':'ledger_bom','type':'bom','dir':'bom','options':{
            'format':'CSV','output':'components.csv','columns':COLUMNS,
            'group_fields':['reference'],'parse_value':False,'exclude_filter':'_null',
            'dnf_filter':'_null','ignore_dnf':False,'exclude_marked_in_pcb':False,
            'csv':{'hide_pcb_info':True,'hide_stats_info':True}}}]
    elif operation=='fabrication':
        outputs=[{'name':'ledger_gerbers','type':'gerber','dir':'fabrication',
                  'options':{'output':'%f-%i.%x','create_gerber_job_file':True},'layers':LAYERS},
                 {'name':'ledger_drill','type':'excellon','dir':'fabrication',
                  'options':{'output':'%f-%i.%x','map':'None'}}]
    else:raise ValueError('Unknown KiBot recipe')
    return {'kibot':{'version':1},'outputs':outputs}


def discover(which=None):
    path=(which or shutil.which)('kibot')
    if not path:return {'state':'NOT_AVAILABLE','executable':None,'qualified':False,
                        'reason':'Install KiBot with KiCad Python bindings on PATH. Graphite opens without it.'}
    resolved=Path(path).resolve()
    return {'state':'DETECTED','executable':str(Path(path).absolute()),'resolved_executable':str(resolved),
            'sha256':io.sha(resolved),'qualified':False,
            'reason':'Presence only. Each job runs its own operation fixtures; no cached qualification.'}


def probe(tool,out):
    run=cad.invoke([tool['executable'],'--version'],out,cad.environment(out),15)
    match=re.search(r'KiBot\s+(\d+\.\d+\.\d+)',run['stdout'])
    if run['exit_status'] or not match:raise ValueError('KiBot version probe failed; check its retained logs and pcbnew installation')
    if tuple(map(int,match[1].split('.'))) < (1,9,1):raise ValueError('This adapter requires KiBot 1.9.1 or newer and qualified KiCad bindings')
    return {**tool,'version':match[1],'version_probe':run}


def export_netlist(tool,source,out,env):
    out=Path(out);path=out/'native.xml'
    run=cad.invoke([tool['executable'],'sch','export','netlist','--format','kicadxml','--output',str(path),str(source)],out,env,30)
    if run['exit_status']:raise ValueError('Native KiCad netlist export failed; no BOM equivalence established')
    return {**run,'path':str(path),'sha256':io.sha(path),'model':netlist_model(path)}


def netlist_model(path):
    path=Path(path)
    if path.stat().st_size>32*1024*1024:raise ValueError('Netlist exceeds 32 MiB')
    raw=path.read_bytes()
    if b'<!DOCTYPE' in raw or b'<!ENTITY' in raw:raise ValueError('External netlist entities are not accepted')
    root=ET.fromstring(raw)
    def node(n):return [n.tag,sorted(n.attrib.items()),(n.text or '').strip(),[node(c) for c in n]]
    sections={name:root.find(name) for name in ('components','libparts','nets')}
    if any(n is None for n in sections.values()):raise ValueError('Incomplete native netlist')
    components={}
    for c in sections['components']:
        ref=c.attrib['ref']
        if ref in components:raise ValueError('Duplicate native component reference')
        properties={p.attrib['name']:p.attrib.get('value','') for p in c.findall('property')}
        fields={p.attrib['name']:p.text or '' for p in c.findall('fields/field')}
        components[ref]={'value':c.findtext('value',''),'footprint':c.findtext('footprint',''),
                         'fields':fields,'properties':properties}
    canonical={name:node(n) for name,n in sections.items()}
    return {'semantic_sha256':io.digest(canonical),'components':components,'net_count':len(sections['nets']),
            'scope':'Complete component, library-definition and net sections; generation metadata and library filesystem paths are excluded.'}


def compatibility_copy(snapshot,out,native,env):
    """Omit one known empty library unit only in a separately recorded tool copy."""
    snapshot=Path(snapshot);out=Path(out);effective=out/'inputs'
    shutil.copytree(snapshot,effective)
    edits=[]
    path=effective/'power.kicad_sch'
    if path.is_file():
        text=path.read_text();pattern=r'\(symbol\s+"FID_1_1"\s*\)'
        updated,count=re.subn(pattern,'',text)
        if count>1:raise ValueError('Unexpected duplicate empty FID unit; compatibility requires review')
        if count:
            before=io.sha(path);path.chmod(0o644);path.write_text(updated);path.chmod(0o444)
            edits.append({'file':'power.kicad_sch','before_sha256':before,'after_sha256':io.sha(path),
                          'removed_node':'(symbol "FID_1_1")','count':count,
                          'reason':'KiBot 1.9.1 rejects this empty, pinless library unit; native KiCad accepts it.'})
    before=export_netlist(native,snapshot/'ARC1_R10.kicad_sch',out/'original',env)
    after=export_netlist(native,effective/'ARC1_R10.kicad_sch',out/'effective',env)
    same=before['model']['semantic_sha256']==after['model']['semantic_sha256']
    result={'transforms':edits,'native_equivalent':same,'original':before,'effective':after}
    io.write_json(out/'equivalence.json',compact_compatibility(result))
    if not same:raise ValueError('KiCad netlist changed in the interoperability copy; BOM blocked')
    return effective,result


def compact_compatibility(result):
    def compact(run):
        model=run['model']
        return {**run,'model':{k:v for k,v in model.items() if k!='components'},'component_count':len(model['components'])}
    return {**result,'original':compact(result['original']),'effective':compact(result['effective'])}


def validate_bom(path,model):
    path=Path(path)
    if not path.is_file() or path.stat().st_size>8*1024*1024:raise ValueError('BOM absent or larger than 8 MiB')
    with path.open(newline='',encoding='utf-8-sig') as f:
        reader=csv.DictReader(f)
        if reader.fieldnames!=COLUMNS:raise ValueError('BOM columns differ from the fixed recipe')
        rows=list(reader)
    actual={}
    for row in rows:
        ref=row['References']
        if ref in actual or row['Quantity Per PCB']!='1':raise ValueError('BOM merged, duplicated or changed component quantities')
        actual[ref]=row
    expected=model['components']
    if set(actual)!=set(expected):raise ValueError('BOM references do not match the complete native component set')
    for ref,native in expected.items():
        row=actual[ref]
        if (row['Value'],row['Footprint Full'])!=(native['value'],native['footprint']):raise ValueError('Native value/footprint differs in BOM: '+ref)
        for field in ('MPN','Manufacturer','LCSC','Note'):
            if row[field]!=native['fields'].get(field,''):raise ValueError('Native component field differs in BOM: '+ref+' / '+field)
    return {'rows':rows,'component_count':len(rows),'group_count':len(rows),'sha256':io.sha(path),
            'native_component_match':True,
            'scope':'One row per native reference, including mechanical parts and DNP entries. No purchase or assembly selection; copied source fields are unverified.'}


def validate_fabrication(directory,stem):
    directory=Path(directory);job=directory/(stem+'-job.gbrjob')
    data=io.strict_json(job.read_bytes())
    if data['GeneralSpecs']['LayerNumber']!=6:raise ValueError('Fixed R10 fabrication recipe requires six copper layers')
    expected={stem+'-'+name+'.gbr' for name in GERBERS}
    listed={r['Path'] for r in data['FilesAttributes']}
    if listed!=expected:raise ValueError('Gerber job does not list the exact fixed layer set')
    actual={p.name for p in directory.iterdir() if p.is_file()}
    drill=stem+'-drill.drl'
    if actual!=expected|{job.name,drill}:raise ValueError('Unexpected or missing fabrication outputs')
    for name in sorted(expected):
        raw=(directory/name).read_bytes()
        if not raw or b'%FS' not in raw or not raw.rstrip().endswith(b'M02*'):raise ValueError('Incomplete Gerber: '+name)
    raw=(directory/drill).read_bytes()
    if not raw.startswith(b'M48') or b'METRIC' not in raw or not raw.rstrip().endswith(b'M30'):raise ValueError('Incomplete Excellon drill file')
    return {'copper_layers':6,'gerber_count':len(expected),'drill_count':1,'job_file':job.name,
            'scope':'Native Gerber/Excellon structure and fixed layer set verified. Stored fills; no refill, routing, assembly or manufacture approval.'}


def invoke_outputs(tool,operation,source,out,env,stem='ARC1_R10'):
    source=Path(source);out=Path(out);out.mkdir(parents=True,exist_ok=True)
    config=out/'recipe.kibot.yaml';io.write_json(config,recipe(operation));recipe_sha=io.sha(config)
    argv=[tool['executable'],'-A','-c',str(config),'-b',str(source/(stem+'.kicad_pcb')),'-d',str(out/'outputs')]
    argv+=['-e',str(source/(stem+'.kicad_sch'))]
    run=cad.invoke(argv,out,env,75)
    logs={name:{'path':str(out/name),'sha256':io.sha(out/name)} for name in ('stdout.txt','stderr.txt')}
    warnings={}
    for name in logs:
        for code in re.findall(r'WARNING:\(W(\d+)\)',(out/name).read_text(errors='replace')):
            key='W'+code;warnings[key]=warnings.get(key,0)+1
    return {**run,'logs':logs,'warning_counts':warnings,'warning_count':sum(warnings.values()),
            'recipe':{'path':str(config),'sha256':recipe_sha},
            'recipe_unchanged':io.sha(config)==recipe_sha,'downloads_disabled':True}


def fixture():
    root_uuid='4b596f3b-4db3-48c6-a2fb-bf7fb7debb5a'
    symbol='''(symbol "Ledger:R" (pin_names (offset 0)) (in_bom yes) (on_board yes)
    (property "Reference" "R" (at 0 2 0) (effects (font (size 1 1))))
    (property "Value" "R" (at 0 -2 0) (effects (font (size 1 1))))
    (symbol "R_0_1" (rectangle (start -1 1) (end 1 -1) (stroke (width 0.2) (type default)) (fill (type none))))
    (symbol "R_1_1" (pin passive line (at -3 0 0) (length 2) (name "~" (effects (font (size 1 1)))) (number "1" (effects (font (size 1 1)))))
                    (pin passive line (at 3 0 180) (length 2) (name "~" (effects (font (size 1 1)))) (number "2" (effects (font (size 1 1)))))))'''
    instances=[]
    for n in (1,2,3):
        ident=f'4b596f3b-4db3-48c6-a2fb-bf7fb7debb5{n}'
        props=''.join('(property '+json.dumps(k)+' '+json.dumps(v)+' (at 20 20 0) (effects (font (size 1 1))))' for k,v in
                      [('Reference',f'R{n}'),('Value','10k'),('Footprint','Ledger:R'),('Datasheet',''),('Description',''),('MPN',f'part-{n}'),('Note','DNP review' if n==3 else '')])
        instances.append(f'(symbol (lib_id "Ledger:R") (at {20+n*10} 20 0) (unit 1) (in_bom yes) (on_board yes) (dnp {"yes" if n==3 else "no"}) (uuid "{ident}") '+props+
                         f'(instances (project "fixture" (path "/{root_uuid}" (reference "R{n}") (unit 1)))))')
    sch=f'(kicad_sch (version 20231120) (generator "eeschema") (uuid "{root_uuid}") (paper "A4") (lib_symbols '+symbol+')'+''.join(instances)+')\n'
    board=cad.FIXTURES['good'].replace('(2 "B.Cu" signal)', '(4 "In1.Cu" signal) (6 "In2.Cu" signal) (8 "In3.Cu" signal) (10 "In4.Cu" signal) (2 "B.Cu" signal) (1 "F.Mask" user) (3 "B.Mask" user) (5 "F.SilkS" user) (7 "B.SilkS" user)')
    board=board.rstrip()[:-1]+'''(footprint "Ledger:R" (layer "F.Cu") (at 20 20)
      (property "Reference" "R1" (at 0 2 0) (layer "F.SilkS") (effects (font (size 1 1))))
      (property "Value" "10k" (at 0 -2 0) (layer "F.Fab") (effects (font (size 1 1))))
      (pad "1" thru_hole circle (at 0 0) (size 2 2) (drill 1) (layers "*.Cu" "*.Mask")))\n)\n'''
    return {'fixture.kicad_sch':sch,'fixture.kicad_pcb':board,'fixture.kicad_pro':'{}\n'}


def qualify(tool,native,operation,out,env):
    out=Path(out);source=out/'inputs';source.mkdir(parents=True)
    texts=fixture()
    for name,text in texts.items():(source/name).write_text(text)
    operations=('bom','fabrication') if operation=='qualify' else (operation,)
    cases={};artifacts={}
    for kind in operations:
        positive=invoke_outputs(tool,kind,source,out/(kind+'-good'),env,'fixture')
        if positive['exit_status'] or not positive['recipe_unchanged']:raise ValueError('KiBot '+kind+' positive fixture failed')
        if kind=='bom':
            net=export_netlist(native,source/'fixture.kicad_sch',out/'native-netlist',env)
            parsed=validate_bom(out/'bom-good/outputs/bom/components.csv',net['model'])
            if parsed['component_count']!=3 or {r['MPN'] for r in parsed['rows']}!={'part-1','part-2','part-3'}:
                raise ValueError('BOM fixture lost distinct part identities or DNP component')
        else:
            parsed=validate_fabrication(out/'fabrication-good/outputs/fabrication','fixture')
            drill=(out/'fabrication-good/outputs/fabrication/fixture-drill.drl').read_text()
            if 'C1.000' not in drill:raise ValueError('Fabrication fixture lost its known 1 mm drill')
        broken=out/(kind+'-bad-inputs');broken.mkdir()
        for name,text in texts.items():(broken/name).write_text(text)
        target=broken/('fixture.kicad_sch' if kind=='bom' else 'fixture.kicad_pcb');target.write_text('(deliberately invalid')
        negative=invoke_outputs(tool,kind,broken,out/(kind+'-bad'),env,'fixture')
        if negative['exit_status']==0:raise ValueError('KiBot accepted the deliberately unreadable '+kind+' fixture')
        cases[kind]={'positive':positive,'validation':{k:v for k,v in parsed.items() if k!='rows'},'negative':negative}
    for p in out.rglob('*'):
        if p.is_file() and '/home/' not in str(p) and '/config/' not in str(p):artifacts[str(p)]=io.sha(p)
    if any((source/n).read_text()!=v for n,v in texts.items()):raise ValueError('Tool altered qualification source')
    return {'qualified':True,'reused':False,'operations':list(operations),'cases':cases,'artifacts':artifacts,
            'binding':{'adapter_sha256':io.sha(Path(__file__)),'kibot':tool,'kicad':native,
                       'fixture_sha256':io.digest(texts),'recipe_sha256':io.digest({k:recipe(k) for k in operations}),
                       'platform':platform.platform()},
            'scope':'These fixed operations and artifact parsers on this runtime. Repeated every job; no package/dynamic-library closure or other-host claim.'}


def run(root,operation,ident):
    root=Path(root).resolve()
    if operation not in ('bom','fabrication','qualify') or not re.fullmatch('[0-9a-f]{32}',ident):raise ValueError('Invalid KiBot operation or job ID')
    directory=root/'build/kibot/runs'/ident
    if any(p.is_symlink() for p in (root/'build',root/'build/kibot',root/'build/kibot/runs',directory,directory/'attempts')):raise ValueError('KiBot output path is linked')
    attempt=uuid.uuid4().hex;out=directory/'attempts'/attempt;out.mkdir(parents=True,exist_ok=False)
    record={'schema':CONTRACT,'id':ident,'attempt':attempt,'operation':operation,'created':time.time(),
            'class':'STATIC_CHECK','status':'BLOCKED','execution_status':'NOT_RUN','fabrication':'HOLD',
            'physical_hardware':False,'target':'R10 · F133-B / D213ECV / ECP5-12F / ECP5-45F',
            'reason':'','source_unchanged':None,'artifacts':{}}
    try:
        tool=discover();record['tool']=tool
        if not tool['executable']:raise ValueError(tool['reason'])
        native=cad.discover();record['kicad']=native
        if not native['executable']:raise ValueError(native['reason'])
        tool=probe(tool,out/'probe/kibot');record['tool']=tool
        native=cad.probe(native,out/'probe/kicad');record['kicad']=native
        env=cad.environment(out/'environment',native['major'])
        record['qualification']=qualify(tool,native,operation,out/'qualification',env)
        if operation=='qualify':record.update(status='QUALIFIED',execution_status='COMPLETED',reason='Fixed BOM and fabrication positive/negative fixtures reproduced.')
        else:
            before=cad.inputs(root);record['inputs']=before;record['input_revision']=io.digest(before);snapshot=out/'inputs'
            for name,row in before.items():
                dest=snapshot/Path(name).relative_to(cad.CAD);dest.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(io.project_path(root,name),dest)
                if io.sha(dest)!=row['sha256']:raise ValueError('Source changed while copying')
                dest.chmod(0o444)
            env,dependencies=cad.library_environment(root,native,out/'environment');record['external_inputs']=dependencies
            effective,compat=compatibility_copy(snapshot,out/'compatibility',native,env);record['compatibility']=compat
            effective_before={p.relative_to(effective).as_posix():io.sha(p) for p in effective.rglob('*') if p.is_file()}
            if operation=='fabrication':
                record['drc_qualification']=cad.qualify(root,native,out/'drc-qualification')
                record['drc']=cad.native_drc(native,snapshot/cad.BOARD,out/'drc',env)
            record['execution_status']='RUNNING'
            run_result=invoke_outputs(tool,operation,effective,out/'native',env);record['native']=run_result
            if run_result['exit_status'] or not run_result['recipe_unchanged']:raise ValueError('KiBot output generation failed (exit '+str(run_result['exit_status'])+'); original logs retained')
            if operation=='bom':
                record['bom']=validate_bom(out/'native/outputs/bom/components.csv',record['compatibility']['original']['model'])
            else:record['fabrication_outputs']=validate_fabrication(out/'native/outputs/fabrication','ARC1_R10')
            record['compatibility']=compact_compatibility(record['compatibility'])
            record['source_unchanged']=cad.inputs(root)==before
            record['snapshot_unchanged']=all(io.sha(snapshot/Path(n).relative_to(cad.CAD))==r['sha256'] for n,r in before.items())
            record['effective_inputs_unchanged']=effective_before=={p.relative_to(effective).as_posix():io.sha(p) for p in effective.rglob('*') if p.is_file()}
            record['external_inputs_unchanged']=all(io.sha(r['source'])==r['sha256'] and io.sha(r['snapshot'])==r['sha256'] for r in dependencies['files'])
            record['tool_unchanged']=io.sha(Path(tool['resolved_executable']))==tool['sha256'] and all(io.sha(Path(p))==sha for p,sha in native['program_files'].items())
            if not all(record[k] for k in ('source_unchanged','snapshot_unchanged','effective_inputs_unchanged','external_inputs_unchanged','tool_unchanged')):
                raise ValueError('A bound input changed during generation; outputs are invalid')
            record.update(status='CANDIDATE',execution_status='COMPLETED',reason='Output candidate generated and checked. FAB/ROUTE/programming remain HOLD; source fields and physical design require review.')
    except (OSError,ValueError,KeyError,TypeError,ET.ParseError,csv.Error,subprocess.SubprocessError) as exc:
        record.update(status='TOOL_ERROR' if record['execution_status']=='RUNNING' else 'BLOCKED',
                      execution_status='FAILED',reason=str(exc))
    # Bind all review material, including complete logs, recipes and parity reports.
    for p in sorted(out.rglob('*')):
        if p.is_file() and not p.is_symlink() and not p.is_relative_to(out/'environment') and p.name!='record.json':
            record['artifacts'][p.relative_to(root).as_posix()]={'sha256':io.sha(p),'bytes':p.stat().st_size}
    record['finished']=time.time();io.write_json(out/'record.json',record);io.write_json(directory/'record.json',record)
    io.write_json(root/'build/kibot/latest.json',{'id':ident,'record_sha256':io.sha(directory/'record.json')})
    return record


def report(root,ident=None):
    root=Path(root).resolve();expected=None
    if not ident:
        if not (root/'build/kibot/latest.json').is_file():return {'state':'NOT_RUN','reason':'Run a registered KiBot job.'}
        latest=io.load(root,'build/kibot/latest.json');ident=latest['id'];expected=latest['record_sha256']
    if not re.fullmatch('[0-9a-f]{32}',ident):raise ValueError('Invalid KiBot run ID')
    path=io.project_path(root,'build/kibot/runs/'+ident+'/record.json')
    if expected and io.sha(path)!=expected:raise ValueError('Recorded KiBot result changed')
    data=io.strict_json(path.read_bytes());prefix='build/kibot/runs/'+ident+'/attempts/'+data['attempt']+'/'
    for name,row in data.get('artifacts',{}).items():
        if not name.startswith(prefix):raise ValueError('Artifact does not belong to this run')
        artifact=io.project_path(root,name)
        if io.sha(artifact)!=row['sha256'] or artifact.stat().st_size!=row['bytes']:raise ValueError('Original KiBot review artifact changed: '+name)
    for name,row in data.get('native',{}).get('logs',{}).items():
        if name not in ('stdout.txt','stderr.txt') or row['path']!=str(root/prefix/'native'/name):raise ValueError('Native log path does not belong to this attempt')
        if data['artifacts'][prefix+'native/'+name]['sha256']!=row['sha256']:raise ValueError('Native log binding differs from its artifact')
    data['source_currentness']='CURRENT' if data.get('inputs') and cad.inputs(root)==data['inputs'] else 'STALE' if data.get('inputs') else 'NOT_APPLICABLE'
    return data


def dispatch(kernel,operation,args):
    if operation=='kibot.report':return report(kernel.root,args.get('id'))
    return {'schema':CONTRACT,'tool':discover(),'kicad':cad.discover(),'latest':report(kernel.root),
            'notice':'Fixed BOM and six-layer fabrication candidates on R10. Each job qualifies its operation. Physical gates remain HOLD.'}


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('operation',choices=['bom','fabrication','qualify'])
    ap.add_argument('--root',type=Path,required=True);ap.add_argument('--job',required=True);a=ap.parse_args()
    result=run(a.root,a.operation,a.job)
    print(json.dumps({k:result[k] for k in ('id','status','reason')}))
    raise SystemExit(0 if result['status'] in ('QUALIFIED','CANDIDATE') else 2)
