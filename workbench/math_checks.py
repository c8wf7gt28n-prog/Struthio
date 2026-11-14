"""One connected I02 fixture: exact IR, real solvers, native Calc and Writer."""
import argparse,json,os,subprocess,sys,tempfile,time
from pathlib import Path
from unittest.mock import patch
from . import clock_lab,locations,math_model as core,math_backend
from .baseline import environment
from .problem_checks import invoke,bound


def clock_model(problem):
    variables={v['name']:{'unit':v['unit'],'value':v['value']} for v in problem['variables'] if v['type']=='quantity' and v['state']=='KNOWN'}
    memory=core.compile_expression('buffer_A + buffer_B + workspace <= memory_limit',variables,['All three allocations are concurrent.'])['model']
    power=core.compile_expression('voltage * assumed_typical_current',variables,['Declared typical-current assumptions; not a maximum-current guarantee.'])['model']
    for node in power['nodes']:
        node['id']='p'+node['id']
        for key in ('left','right','argument'):
            if key in node:node[key]='p'+node[key]
    return {**memory,'variables':{**memory['variables'],**power['variables']},'nodes':memory['nodes']+power['nodes'],
        'outputs':memory['outputs']+['p'+i for i in power['outputs']], 'assumptions':memory['assumptions']+power['assumptions']}


def exercise(root,profile,home,office=True):
    from .engineering_kernel import Kernel,operator
    locations.office(root);kernel=Kernel(root);p=operator();source=clock_lab.copy_inputs(home/'Clock_Lab_I02')
    data=clock_lab.start(kernel,source,p);problem=data['problem'];model=clock_model(problem)
    action=invoke(kernel,'math.prepare',{**bound(problem),'model':model,'backend':'EXACT'},p)
    receipt=invoke(kernel,'math.run',{'action':action['id']},p)['receipt'];evaluation=receipt['snapshot']
    if evaluation['state']!='INFEASIBLE' or evaluation['outputs'][0]['left']['rational']!='17' or evaluation['outputs'][1]['value']['rational']!='5/4':
        raise ValueError('Connected exact result disagrees with independently frozen oracle')
    solvers={name:invoke(kernel,'math.solve',{'model':model,'backend':name},p) for name in ('SYMPY','Z3')}
    if any(value['state']!='INFEASIBLE' for value in solvers.values()):raise ValueError('Actual solver did not confirm the all-concurrent constraint')
    power=core.compile_expression('voltage * assumed_typical_current',model['variables'],model['assumptions'])
    for name in ('SYMPY','Z3'):
        result=math_backend.solve(power,name)
        if result['state']!='FEASIBLE' or result['evaluation']['outputs'][0]['value']['rational']!='5/4':raise ValueError('Power backend mismatch')
    memory=invoke(kernel,'math.prepare',{**bound(problem),'expression':'buffer_A + buffer_B + workspace <= memory_limit',
        'assumptions':['All three allocations are concurrent.'],'output_unit':'MiB'},p)
    invoke(kernel,'math.run',{'action':memory['id']},p)
    graph=invoke(kernel,'math.sweep',{'action':memory['id'],'variable':'workspace','start':'0','stop':'10','count':21},p)
    if graph['boundaries'][0]['input']['rational']!='4':raise ValueError('Exact What if boundary differs from the independent 16-6-6 calculation')
    stac=invoke(kernel,'stac.run',{'program':'math problem:'+problem['id']+' | calculate "voltage * assumed_typical_current" | unit W'},p)
    if stac['result']['evaluation']['outputs'][0]['value']['rational']!='5/4':raise ValueError('The line did not use the shared evaluator')
    native=None
    if office:
        plan=invoke(kernel,'math.office.prepare',{'receipt':receipt['id']},p)
        job=invoke(kernel,'math.office.run',{'action':plan['id'],'expected_digest':plan['binding_digest']},p)
        deadline=time.monotonic()+210
        while kernel.record('jobs',job['id'])['state'] in ('Queued','Running') and time.monotonic()<deadline:time.sleep(.5)
        native=invoke(kernel,'math.office.result',{'job':job['id']},p)
        if native['state']!='AVAILABLE':raise ValueError('Actual Office round trip failed: '+str(native))
        if len(native['measurement'])!=8:raise ValueError('Native formula coverage changed')
        if not native['writer_reopened'] or not native['writer_table_reopened']:raise ValueError('Writer output was not verified')
        published=invoke(kernel,'math.office.publish',{'job':job['id']},p)
        native['working_files']=published['files']
        for item in native['working_files']:
            path=root/'Files'/data['copy']['work']/item['path']
            if not path.is_file():raise ValueError('Generated working copy missing')
    # A real fresh interpreter reopens exactly the same saved math result.
    expected={'problem':problem['id'],'action':action['id'],'receipt':receipt};expected_path=Path(profile).parent/'expected-math.json';expected_path.write_text(json.dumps(expected))
    child=subprocess.run([sys.executable,'-m','workbench.math_checks','_resume',str(root),str(profile),str(expected_path)],
        capture_output=True,text=True,env=locations.child_env(root),timeout=20)
    if child.returncode:raise ValueError('Math restart failed: '+(child.stderr or child.stdout)[-1000:])
    if (source/'requirements.md').read_bytes()!=(clock_lab.FIXTURE/'requirements.md').read_bytes():raise ValueError('Original exercise changed')
    return {'state':'PASSED','pass':'I02','problem':problem['id'],'action':action['id'],'math_result':receipt['id'],
        'memory':evaluation['outputs'][0],'power':evaluation['outputs'][1],'actual_solvers':{k:{'state':v['state'],'version':v.get('version')} for k,v in solvers.items()},
        'exact_what_if_boundary':graph['boundaries'][0],'stac_shared_math':True,'fresh_process_reopen':json.loads(child.stdout),
        'native_office':native,'model_calls':0,'target_thinkpad':'NOT_QUALIFIED_ON_THIS_HOST'}


def resume(root,profile,path):
    os.environ.update(environment(os.environ,root,profile))
    from .engineering_kernel import Kernel,operator
    expected=json.loads(Path(path).read_text());value=invoke(Kernel(root),'math.get',{'id':expected['action']},operator())
    if value['receipt']!=expected['receipt']:raise ValueError('Saved calculation changed across restart')
    return {'state':'PASSED','exact_receipt':True,'automatic_execution':False}


def ui_check(screenshot=None):
    from PySide6.QtWidgets import QApplication,QLabel
    from .problem_qt import ProblemPane
    from .engineering_kernel import Kernel,operator
    from types import SimpleNamespace
    with tempfile.TemporaryDirectory(prefix='ledger-i02-ui-') as temp:
        base=Path(temp);home=base/'Home';home.mkdir();root=base/'Office';profile=base/'profile'
        with patch.dict(os.environ,{**environment(os.environ,root,profile),'HOME':str(home),'QT_QPA_PLATFORM':'offscreen'}),patch.object(Path,'home',return_value=home):
            app=QApplication.instance() or QApplication(['ledger-i02-ui']);locations.office(root);kernel=Kernel(root)
            data=clock_lab.start(kernel,clock_lab.copy_inputs(home/'Clock_Lab_I02'),operator())
            desk=SimpleNamespace(host=SimpleNamespace(root=root),project=data['project'],assignment=data['assignment'],message=QLabel())
            pane=ProblemPane(desk)
            try:
                pane.resize(1180,1000);pane.show();pane.reload(data['problem']['id']);pane.pages.setCurrentIndex(3);app.processEvents()
                calc=pane.calculator;calc.calculate();app.processEvents();calc.draw();app.processEvents()
                if not calc.graph.data or calc.graph.data['boundaries'][0]['input']['rational']!='4':raise ValueError('Qt graph does not show the exact boundary')
                if '17 MiB' not in calc.answer.text():raise ValueError('Qt result does not show the declared memory model')
                if screenshot:pane.grab().save(str(screenshot))
                # Editing the displayed problem must not silently calculate old values.
                pane.variables.item(3,4).setText('4');old=calc.action['id'];calc.calculate()
                if calc.action['id']!=old or 'Save the problem' not in calc.answer.text():raise ValueError('Unsaved inputs were silently used')
                pane.save();calc.calculate();app.processEvents()
                if 'True' not in calc.answer.text():raise ValueError('Revised quantity did not change the checked comparison')
                return {'state':'PASSED','scope':'Real Qt calculator and sampled graph, offscreen','exact_boundary':'4 MiB',
                    'unsaved_inputs_refused':True,'saved_revision_changes_result':True,'owner_display':'PENDING'}
            finally:pane.close();app.processEvents()


def cancellation_check():
    from .engineering_kernel import Kernel,operator
    with tempfile.TemporaryDirectory(prefix='ledger-i02-cancel-') as temp:
        base=Path(temp);home=base/'Home';home.mkdir();root=base/'Office';profile=base/'profile'
        with patch.dict(os.environ,{**environment(os.environ,root,profile),'HOME':str(home)}),patch.object(Path,'home',return_value=home):
            locations.office(root);kernel=Kernel(root);p=operator()
            data=clock_lab.start(kernel,clock_lab.copy_inputs(home/'Clock_Lab_I02'),p)
            action=invoke(kernel,'math.prepare',{**bound(data['problem']),'expression':'voltage * assumed_typical_current'},p)
            receipt=invoke(kernel,'math.run',{'action':action['id']},p)['receipt'];plan=invoke(kernel,'math.office.prepare',{'receipt':receipt['id']},p)
            job=invoke(kernel,'math.office.run',{'action':plan['id'],'expected_digest':plan['binding_digest']},p)
            folder=kernel.state/'jobs'/job['id'];deadline=time.monotonic()+15
            while not (folder/'math-office/calc-native/stdout.log').exists() and time.monotonic()<deadline:
                if kernel.record('jobs',job['id'])['state']=='Failed':raise ValueError('Worker failed before cancellation')
                time.sleep(.05)
            if not (folder/'math-office/calc-native/stdout.log').exists():raise ValueError('Owned native stage was never launched')
            time.sleep(.2);invoke(kernel,'jobs.cancel',{'id':job['id']},p);deadline=time.monotonic()+10
            while kernel.record('jobs',job['id'])['state'] in ('Running','Queued') and time.monotonic()<deadline:time.sleep(.05)
            state=kernel.record('jobs',job['id'])['state'];result=invoke(kernel,'math.office.result',{'job':job['id']},p)
            if state!='Cancelled' or result['files'] or (folder/'math_office_result.json').exists():raise ValueError('Cancelled native job became a completed observation')
            with kernel.db() as db:health=db.execute('PRAGMA quick_check').fetchone()[0]
            if health!='ok':raise ValueError('Cancellation left a damaged Kernel DB')
            return {'state':'PASSED','native_stage_started':True,'job_state':state,'completed_receipt':False,'files_published':False,'database':health}


def main(argv=None):
    argv=sys.argv[1:] if argv is None else argv
    if argv and argv[0]=='_resume':print(json.dumps(resume(*argv[1:])));return 0
    parser=argparse.ArgumentParser();parser.add_argument('--no-office',action='store_true');parser.add_argument('--keep',type=Path);parser.add_argument('--output',type=Path)
    parser.add_argument('--ui',action='store_true');parser.add_argument('--screenshot',type=Path)
    parser.add_argument('--cancel',action='store_true')
    args=parser.parse_args(argv)
    if args.ui:
        value=ui_check(args.screenshot);raw=json.dumps(value,indent=2)+'\n'
        if args.output:args.output.write_text(raw)
        print(raw,end='');return 0
    if args.cancel:
        value=cancellation_check();raw=json.dumps(value,indent=2)+'\n'
        if args.output:args.output.write_text(raw)
        print(raw,end='');return 0
    with tempfile.TemporaryDirectory(prefix='ledger-i02-') as temp:
        base=args.keep or Path(temp);base.mkdir(exist_ok=True,parents=True);home=base/'Home';home.mkdir();root=base/'Office';profile=base/'profile'
        with patch.dict(os.environ,{**environment(os.environ,root,profile),'HOME':str(home)}),patch.object(Path,'home',return_value=home):
            result=exercise(root,profile,home,not args.no_office)
        raw=json.dumps(result,indent=2)+'\n'
        if args.output:args.output.write_text(raw)
        print(raw,end='')
    return 0


if __name__=='__main__':raise SystemExit(main())
