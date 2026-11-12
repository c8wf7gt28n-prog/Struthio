"""Bounded native ngspice checks of explicitly reduced R10 passive circuits.

Project netlists are data, never ngspice scripts. Only adapter-owned decks run.
Ideal stimuli and omitted devices remain explicit; physical gates stay HOLD.
"""
from __future__ import annotations
import argparse
import csv
import json
import math
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import time
import uuid
from xml.etree.ElementTree import ParseError
from . import brain_link, cad_export, kicad_tools as process, record_io as io
from sdk.cli.arc1cli.relations import NetGraph

CONTRACT='arc.ngspice-passive/1'
FIELDS={'spice.inspect':({},[]),'spice.report':({'id':{'type':'string','pattern':'^[0-9a-f]{32}$','maxLength':32}},[])}
SCOPES={name:'read' for name in FIELDS}
PROFILES={'dividers':'R10 · six rail-monitor dividers','clock':'R10 · LCD clock RC edge'}
DIVIDERS=[('f45_core','R179','R180','1V1_F45','F45_SENSE_CORE'),
          ('f45_aux','R181','R182','2V5_F45','F45_SENSE_AUX'),
          ('f45_io','R183','R184','3V3_F45','F45_SENSE_IO'),
          ('f12_core','R189','R190','1V1_F12','F12_SENSE_CORE'),
          ('f12_aux','R191','R192','2V5_F12','F12_SENSE_AUX'),
          ('f12_io','R193','R194','3V3_F12','F12_SENSE_IO')]
INIT='* Ledger isolated startup: no external models or plugins.\nset filetype=ascii\n'
OPTIONS='.options reltol=1e-6 abstol=1e-12 vntol=1e-9 numdgt=15\n'


def discover(which=None):
    path=(which or shutil.which)('ngspice')
    if not path:return {'state':'NOT_AVAILABLE','executable':None,'qualified':False,
                        'reason':'Install the ngspice console executable separately and add it to PATH.'}
    resolved=Path(path).resolve()
    return {'state':'DETECTED','executable':str(Path(path).absolute()),'resolved_executable':str(resolved),
            'sha256':io.sha(resolved),'qualified':False,
            'reason':'Presence only. Each job repeats the relevant numerical and rejected-input fixtures.'}


def environment(out):
    out=Path(out);home=out/'home';scripts=out/'scripts'
    home.mkdir(parents=True,exist_ok=True);scripts.mkdir(parents=True,exist_ok=True)
    (scripts/'spinit').write_text(INIT)
    env={k:v for k,v in os.environ.items() if k in ('PATH','SystemRoot','WINDIR','TEMP','TMP','LD_LIBRARY_PATH','DYLD_LIBRARY_PATH')}
    env.update(HOME=str(home),USERPROFILE=str(home),SPICE_USERINIT_DIR=str(home),SPICE_SCRIPTS=str(scripts),
               SPICE_ASCIIRAWFILE='1',NGSPICE_INPUT_DIR=str(out),OMP_NUM_THREADS='1',LC_ALL='C',LANG='C')
    return env


def probe(tool,out,env):
    result=process.invoke([tool['executable'],'-n','--version'],out,env,10)
    match=re.search(r'\bngspice-(\d+(?:\.\d+)*)\b',result['stdout']+result['stderr'])
    if result['exit_status'] or not match:raise ValueError('ngspice version probe failed; inspect the retained logs')
    if int(match[1].split('.')[0])<40:raise ValueError('This adapter requires ngspice 40 or newer plus successful operation fixtures')
    return {**tool,'version':match[1],'probe':result}


def inputs(root):
    root=Path(root).resolve();rows=cad_export.inputs(root)
    rows.update(io.manifest(root,['project/brain_link_export.json','workbench/spice_tools.py']))
    if any(r.get('sha256') is None for r in rows.values()):raise ValueError('A required native source/export binding is missing')
    if sum(r['bytes'] for r in rows.values())>32*1024*1024:raise ValueError('Circuit input snapshot exceeds 32 MiB')
    return dict(sorted(rows.items()))


def value_si(text,kind):
    # Fixed passive values, never expressions, directives or paths from source data.
    units={'R':{'':1,'R':1,'k':1e3,'M':1e6},'C':{'pF':1e-12,'nF':1e-9,'uF':1e-6,'F':1}}
    match=re.fullmatch(r'([0-9]+(?:\.[0-9]+)?)('+ '|'.join(re.escape(k) for k in units[kind])+')',text)
    if not match:raise ValueError('Unsupported passive '+kind+' value: '+repr(text))
    result=float(match[1])*units[kind][match[2]]
    low,high=(1e-3,1e9) if kind=='R' else (1e-15,1)
    if not math.isfinite(result) or not low<=result<=high:raise ValueError('Passive value is outside the model bounds')
    return result


def component(graph,ref,nets,kind):
    item=graph.components[ref];pins=item['pins']
    if len(pins)!=2 or {p['pin'] for p in pins}!={'1','2'} or {p['net'] for p in pins}!=set(nets):
        raise ValueError('Native topology no longer matches the reduced model: '+ref)
    return {**item,'si_value':value_si(item['value'],kind),'model': 'ideal resistor' if kind=='R' else 'ideal capacitor'}


def rc_deck(resistance,capacitance,stimulus):
    a,start,rise,fall,stop,step=[stimulus[k] for k in ('volts','start','rise','fall','stop','step')]
    points=[(0,0),(start,0),(start+rise,a),(fall,a),(fall+rise,0),(stop,0)]
    pwl=' '.join(f'{t:.15g} {v:.15g}' for t,v in points)
    return ('Ledger reduced RC edge\n'+f'Vdrive src 0 PWL({pwl})\nRseries src clk {resistance:.15g}\nCshunt clk 0 {capacitance:.15g}\n'+
            f'.tran {step:.15g} {stop:.15g} 0 {step:.15g}\n.save v(src) v(clk)\n'+OPTIONS+'.end\n')


def model(root,profile):
    if profile not in PROFILES:raise ValueError('Unknown circuit profile')
    export=cad_export.status(root)
    if export.get('state')!='VERIFIED_EXPORT':raise ValueError('Current saved netlist correspondence is not verified; run links.export first')
    graph=NetGraph(io.project_path(root,brain_link.NETLIST).read_bytes())
    description={'profile':profile,'title':PROFILES[profile],'source_kind':'SAVED_KICAD_NETLIST',
                 'export_binding':export,'components':[],'source_nodes':{},'assumptions':[],
                 'omitted':'All other devices, IC input/driver models, leakage, tolerances, temperature, PCB/interconnect parasitics and physical behaviour.'}
    if profile=='dividers':
        deck='Ledger six R10 passive monitor dividers\nVrail rail 0 0\n';channels=[];gains={}
        for node,top,bottom,rail,sense in DIVIDERS:
            upper=component(graph,top,(rail,sense),'R');lower=component(graph,bottom,(sense,'GND'),'R')
            description['components'] += [upper,lower]
            gain=lower['si_value']/(upper['si_value']+lower['si_value']);gains['v('+node+')']=gain
            description['source_nodes'][node]={'native_rail':rail,'native_sense':sense,'references':[top,bottom]}
            deck+=f'{top} rail {node} {upper["si_value"]:.15g}\n{bottom} {node} 0 {lower["si_value"]:.15g}\n'
            channels.append('v('+node+')')
        deck+='.dc Vrail 0 3.6 0.01\n.save v(rail) '+' '.join(channels)+'\n'+OPTIONS+'.end\n'
        description.update(analysis='DC',channels=['v(rail)']+channels,axis_unit='V',axis_label='Ideal supply sweep',
                           gains=gains,start=0,end=3.6,expected_points=361)
        description['assumptions']=['Each isolated divider is driven by the same ideal 0–3.6 V test sweep; real rails are not interconnected.',
                                    'Rail-monitor IC inputs are open circuits. No supervisor trip/release, hysteresis or regulation model is claimed.']
    else:
        resistor=component(graph,'R80',('LCD_DCLK_D','LCD_DCLK'),'R');cap=component(graph,'C129',('LCD_DCLK','GND'),'C')
        description['components']=[resistor,cap]
        stimulus={'volts':3.3,'start':1e-9,'rise':1e-9,'fall':12e-9,'stop':15e-9,'step':1e-11}
        deck=rc_deck(resistor['si_value'],cap['si_value'],stimulus)
        description.update(analysis='TRANSIENT',channels=['v(src)','v(clk)'],axis_unit='s',axis_label='Time',
                           tau_seconds=resistor['si_value']*cap['si_value'],stimulus=stimulus,start=0,end=stimulus['stop'])
        description['source_nodes']={'src':'LCD_DCLK_D','clk':'LCD_DCLK','0':'GND'}
        description['assumptions']=['Ideal 0–3.3 V source; 1 ns rising/falling ramps are test stimulus, not measured D213 clock edges.',
                                    'Only R80 and C129 are modeled. D213 output impedance and TFP410 input capacitance/timing are omitted.']
    # Model decks consist entirely of numeric passive elements and fixed directives.
    if any(word in deck.casefold() for word in ('.control','.include','.lib','.model','shell','source ')):
        raise ValueError('Unexpected executable content in generated deck')
    return description,deck


def parse_raw(path):
    path=Path(path)
    if not path.is_file() or not 0<path.stat().st_size<=8*1024*1024:raise ValueError('Native raw output absent or exceeds 8 MiB')
    try:lines=path.read_text(encoding='ascii').splitlines()
    except UnicodeError as exc:raise ValueError('Native output is not the required ASCII raw format') from exc
    try:
        variables_index=lines.index('Variables:');values_index=lines.index('Values:')
        header={}
        for line in lines[:variables_index]:
            key,sep,val=line.partition(':')
            if not sep or key in header:raise ValueError('Invalid/duplicate raw header')
            header[key]=val.strip()
        count=int(header['No. Variables']);points=int(header['No. Points'])
        if header['Flags']!='real' or not 2<=count<=16 or not 2<=points<=10000:raise ValueError('Unsupported native vector/point bounds')
        variables=[]
        for index,line in enumerate(lines[variables_index+1:values_index]):
            number,name,unit=line.split()
            if int(number)!=index or unit not in ('time','voltage','current'):raise ValueError('Unexpected raw variable definition')
            variables.append({'name':name,'unit':unit})
        if len(variables)!=count or len({v['name'] for v in variables})!=count:raise ValueError('Missing or duplicate native vectors')
        values=[line.split() for line in lines[values_index+1:] if line.strip()]
        if len(values)!=points*count:raise ValueError('Truncated or extra native samples')
        rows=[]
        for point in range(points):
            group=values[point*count:(point+1)*count]
            if len(group[0])!=2 or int(group[0][0])!=point or any(len(v)!=1 for v in group[1:]):raise ValueError('Native point ordering/width changed')
            row=[float(group[0][1])]+[float(v[0]) for v in group[1:]]
            if not all(math.isfinite(v) for v in row):raise ValueError('Non-finite native waveform')
            if rows and row[0]<=rows[-1][0]:raise ValueError('Native scale is not strictly increasing')
            rows.append(row)
        return {'plot':header['Plotname'],'variables':variables,'points':points,'rows':rows,'sha256':io.sha(path)}
    except (KeyError,IndexError,TypeError) as exc:raise ValueError('Incomplete native ASCII raw structure') from exc


def ramp(t,start,tau):
    dt=t-start
    return 0.0 if dt<=0 else dt+tau*math.expm1(-dt/tau)


def analytic_rc(t,tau,stimulus):
    a,start,rise,fall=[stimulus[k] for k in ('volts','start','rise','fall')]
    return a/rise*(ramp(t,start,tau)-ramp(t,start+rise,tau)-ramp(t,fall,tau)+ramp(t,fall+rise,tau))


def crossing(rows,column,level,start,stop):
    for before,after in zip(rows,rows[1:]):
        if start<=before[0]<=stop and before[column]<=level<=after[column] and after[column]>before[column]:
            return before[0]+(after[0]-before[0])*(level-before[column])/(after[column]-before[column])
    raise ValueError('Expected waveform crossing absent')


def validate_waveform(data,description):
    names=[v['name'] for v in data['variables']];rows=data['rows'];kind=description['analysis']
    expected_axis='v(v-sweep)' if kind=='DC' else 'time'
    if names!=[expected_axis]+description['channels']:raise ValueError('Native vector identities differ from the generated model')
    if data['variables'][0]['unit']!=('voltage' if kind=='DC' else 'time') or any(v['unit']!='voltage' for v in data['variables'][1:]):
        raise ValueError('Native waveform units differ from the model')
    tolerance=1e-9 if kind=='DC' else 1e-15
    if abs(rows[0][0]-description['start'])>tolerance or abs(rows[-1][0]-description['end'])>tolerance:raise ValueError('Native analysis did not cover the full requested interval')
    measurements=[]
    if kind=='DC':
        if data['points']!=description['expected_points']:raise ValueError('DC sweep lost points')
        if max(abs(row[1]-row[0]) for row in rows)>1e-8:raise ValueError('Ideal supply vector differs from the DC sweep')
        for index,(name,gain) in enumerate(description['gains'].items(),2):
            error=max(abs(row[index]-row[0]*gain) for row in rows)
            if error>1e-8:raise ValueError('Native divider curve differs from its independent resistor equation')
            measurements.append({'name':name,'gain_V_per_V':gain,'native_output_at_end_V':rows[-1][index],'sweep_end_V':description['end'],
                                 'max_equation_error_V':error,'agreement':'WITHIN_NUMERICAL_BOUND'})
    else:
        stimulus=description['stimulus'];tau=description['tau_seconds']
        if max(b[0]-a[0] for a,b in zip(rows,rows[1:]))>stimulus['step']*1.001:raise ValueError('Native transient sampling exceeds the requested maximum step')
        start,rise,fall,volts=[stimulus[k] for k in ('start','rise','fall','volts')]
        def drive(t):return volts*(max(0,min(1,(t-start)/rise))-max(0,min(1,(t-fall)/rise)))
        if max(abs(row[1]-drive(row[0])) for row in rows)>1e-8:raise ValueError('Native drive waveform differs from the ideal ramp')
        error=max(abs(row[2]-analytic_rc(row[0],tau,stimulus)) for row in rows)
        if error>1e-3:raise ValueError('Native RC response differs from its independent differential-equation solution')
        t10=crossing(rows,2,volts*.1,start,fall);t90=crossing(rows,2,volts*.9,start,fall)
        delay=crossing(rows,2,volts*.5,start,fall)-crossing(rows,1,volts*.5,start,fall)
        measurements=[{'name':'R80 / C129' if description.get('profile')=='clock' else 'RC fixture',
                       'tau_seconds':tau,'rise_10_90_seconds':t90-t10,'delay_at_50_percent_seconds':delay,
                       'max_equation_error_V':error,'agreement':'WITHIN_NUMERICAL_BOUND'}]
    return measurements


def native_run(tool,deck,out,env,timeout=20):
    out=Path(out);out.mkdir(parents=True,exist_ok=True);source=out/'circuit.cir';source.write_text(deck)
    sha=io.sha(source);raw=out/'waveform.raw'
    result=process.invoke([tool['executable'],'-n','-b','-r',str(raw),str(source)],out,env,timeout)
    if io.sha(source)!=sha:raise ValueError('Generated circuit changed during execution')
    return {**result,'deck_sha256':sha,'deck':str(source),'raw':str(raw)}


def qualify(tool,operation,out,env):
    out=Path(out);cases={}
    if operation in ('qualify','dividers'):
        deck='Ledger known 2:1 divider\nVrail rail 0 0\nR1 rail sense 1000\nR2 sense 0 1000\n.dc Vrail 0 4 0.5\n.save v(rail) v(sense)\n'+OPTIONS+'.end\n'
        case=native_run(tool,deck,out/'dc',env)
        if case['exit_status']:raise ValueError('Native DC positive fixture failed')
        spec={'analysis':'DC','channels':['v(rail)','v(sense)'],'gains':{'v(sense)':.5},'start':0,'end':4,'expected_points':9}
        case['measurements']=validate_waveform(parse_raw(case['raw']),spec);cases['dc']=case
    if operation in ('qualify','clock'):
        stimulus={'volts':1,'start':.001,'rise':.0001,'fall':.008,'stop':.01,'step':.00001}
        case=native_run(tool,rc_deck(1000,1e-6,stimulus),out/'rc',env)
        if case['exit_status']:raise ValueError('Native RC positive fixture failed')
        spec={'analysis':'TRANSIENT','channels':['v(src)','v(clk)'],'tau_seconds':.001,'stimulus':stimulus,'start':0,'end':.01}
        case['measurements']=validate_waveform(parse_raw(case['raw']),spec);cases['rc']=case
    rejected=native_run(tool,'Ledger deliberately missing model\nV1 src 0 1\nD1 src 0 MISSING_LEDGER_MODEL\n.op\n.end\n',out/'rejected',env)
    if rejected['exit_status']==0 or 'missing_ledger_model' not in (rejected['stdout']+rejected['stderr']).casefold():
        raise ValueError('Native tool did not reject the missing-model fixture honestly')
    cases['rejected']=rejected
    return {'qualified':True,'reused':False,'cases':cases,'adapter_sha256':io.sha(Path(__file__)),
            'host':platform.platform(),'scope':'These fixed DC/RC operations and raw parser on this runtime; repeated per job. Not full dependency, IC, board or physical qualification.'}


def run(root,operation,ident):
    root=Path(root).resolve()
    if operation not in ('qualify',*PROFILES) or not re.fullmatch('[0-9a-f]{32}',ident):raise ValueError('Invalid circuit operation or job ID')
    directory=root/'build/spice/runs'/ident
    if any(p.is_symlink() for p in (root/'build',root/'build/spice',root/'build/spice/runs',directory,directory/'attempts')):raise ValueError('Circuit output directory is linked')
    out=directory/'attempts'/uuid.uuid4().hex;out.mkdir(parents=True,exist_ok=False)
    record={'schema':CONTRACT,'id':ident,'attempt':out.name,'operation':operation,'created':time.time(),
            'class':'HOST_SIM','status':'BLOCKED','execution_status':'NOT_RUN','reason':'','source_unchanged':None,
            'target':'R10 · F133-B / D213ECV / ECP5','physical_measurements':False,'fabrication':'HOLD','artifacts':{}}
    before=None
    try:
        tool=discover();record['tool']=tool
        if not tool['executable']:raise ValueError(tool['reason'])
        if operation!='qualify':
            before=inputs(root);record['inputs']=before;record['input_revision']=io.digest(before)
            description,deck=model(root,operation);record['model']=description
            for name,row in before.items():
                dest=out/'inputs'/name;dest.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(io.project_path(root,name),dest)
                if io.sha(dest)!=row['sha256']:raise ValueError('Source changed while capturing the circuit inputs')
                dest.chmod(0o444)
            if inputs(root)!=before:raise ValueError('Source changed while preparing the reduced model')
        env=environment(out/'environment');record['startup_sha256']=io.sha(out/'environment/scripts/spinit')
        tool=probe(tool,out/'probe',env);record['tool']=tool
        record['qualification']=qualify(tool,operation,out/'qualification',env)
        if operation=='qualify':record.update(status='QUALIFIED',execution_status='COMPLETED',reason='DC, RC and rejected-model fixtures reproduced.')
        else:
            record['execution_status']='RUNNING';native=native_run(tool,deck,out/'native',env);record['native']=native
            if native['exit_status']:raise ValueError('Native ngspice execution failed (exit '+str(native['exit_status'])+'); original logs retained')
            data=parse_raw(native['raw']);record['measurements']=validate_waveform(data,description);record['waveform']=data
            with (out/'native/waveform.csv').open('w',newline='') as f:
                writer=csv.writer(f);writer.writerow([v['name'] for v in data['variables']]);writer.writerows(data['rows'])
            record['source_unchanged']=inputs(root)==before
            record['snapshot_unchanged']=all(io.sha(out/'inputs'/name)==row['sha256'] for name,row in before.items())
            if not record['source_unchanged'] or not record['snapshot_unchanged']:raise ValueError('Circuit inputs changed during simulation; result is invalid')
            record.update(status='SIMULATED',execution_status='COMPLETED',reason='Reduced passive model agrees with independent circuit equations. This does not qualify the board or IC behaviour.')
        if io.sha(Path(tool['resolved_executable']))!=tool['sha256'] or io.sha(out/'environment/scripts/spinit')!=record['startup_sha256']:
            raise ValueError('Native executable/startup changed during the operation')
    except (OSError,ValueError,KeyError,TypeError,ParseError,subprocess.SubprocessError) as exc:
        record.update(status='INVALID' if 'waveform' in record else 'TOOL_ERROR' if record['execution_status']=='RUNNING' else 'BLOCKED',
                      execution_status='FAILED',reason=str(exc))
    record['finished']=time.time()
    for p in sorted(out.rglob('*')):
        if p.is_file() and not p.is_symlink() and p.name!='record.json':record['artifacts'][p.relative_to(root).as_posix()]={'sha256':io.sha(p),'bytes':p.stat().st_size}
    io.write_json(out/'record.json',record);io.write_json(directory/'record.json',record)
    io.write_json(root/'build/spice/latest.json',{'id':ident,'record_sha256':io.sha(directory/'record.json')})
    return record


def report(root,ident=None):
    root=Path(root).resolve();expected=None
    if not ident:
        if not (root/'build/spice/latest.json').is_file():return {'state':'NOT_RUN','reason':'Run a registered circuit check.'}
        latest=io.load(root,'build/spice/latest.json');ident=latest['id'];expected=latest['record_sha256']
    if not re.fullmatch('[0-9a-f]{32}',ident):raise ValueError('Invalid circuit job ID')
    path=io.project_path(root,'build/spice/runs/'+ident+'/record.json')
    if expected and io.sha(path)!=expected:raise ValueError('Recorded circuit result changed')
    data=io.strict_json(path.read_bytes());prefix='build/spice/runs/'+ident+'/attempts/'+data['attempt']+'/'
    attempt=io.project_path(root,prefix+'record.json')
    if io.sha(path)!=io.sha(attempt):raise ValueError('Latest circuit record differs from its retained attempt')
    for name,row in data['artifacts'].items():
        if not name.startswith(prefix):raise ValueError('Circuit artifact does not belong to this attempt')
        artifact=io.project_path(root,name)
        if io.sha(artifact)!=row['sha256'] or artifact.stat().st_size!=row['bytes']:raise ValueError('Original circuit artifact changed: '+name)
    try:data['source_currentness']='NOT_APPLICABLE' if not data.get('inputs') else 'CURRENT' if inputs(root)==data['inputs'] else 'STALE'
    except (OSError,ValueError) as exc:
        data['source_currentness']='MISSING_OR_INVALID';data['currentness_reason']=str(exc)
    native=data.get('native')
    if native:
        raw=io.project_path(root,prefix+'native/waveform.raw',False);deck=io.project_path(root,prefix+'native/circuit.cir')
        if native['raw']!=str(raw) or native['deck']!=str(deck):raise ValueError('Native paths differ from their bound attempt')
    if data.get('waveform'):
        parsed=parse_raw(raw)
        if data['waveform']!=parsed:raise ValueError('Recorded samples differ from the original native waveform')
        if data.get('measurements')!=validate_waveform(parsed,data['model']):raise ValueError('Recorded circuit measurements differ from their native samples')
    return data


def dispatch(kernel,operation,args):
    if operation=='spice.report':return report(kernel.root,args.get('id'))
    return {'schema':CONTRACT,'tool':discover(),'profiles':PROFILES,'source_export':cad_export.status(kernel.root),
            'latest':report(kernel.root),'notice':'Reduced passive R10 models with ideal stimuli. No full-board, vendor-IC, timing-closure or physical qualification.'}


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('operation',choices=['qualify',*PROFILES]);ap.add_argument('--root',type=Path,required=True);ap.add_argument('--job',required=True)
    a=ap.parse_args();result=run(a.root,a.operation,a.job)
    print(json.dumps({k:result[k] for k in ('id','status','reason')}))
    raise SystemExit(0 if result['status'] in ('QUALIFIED','SIMULATED') else 2)
