"""Connected I03 observations; native execution, no local-model inference."""
from __future__ import annotations
import argparse,copy,json,os,subprocess,sys,tempfile,time
from pathlib import Path
from unittest.mock import patch
from . import clock_lab,locations,lab_service,reason_service
from .baseline import environment
from .problem_checks import invoke,bound


def wait(kernel,job,p,limit=180):
    until=time.monotonic()+limit
    while kernel.record('jobs',job['id'])['state'] in ('Queued','Running') and time.monotonic()<until:time.sleep(.1)
    value=invoke(kernel,'experiments.result',{'job':job['id']},p)
    if value['state']!='AVAILABLE':
        logs=kernel.state/'jobs'/job['id']/'stderr.log'
        raise ValueError('I03 job did not complete: '+str(value)+'\n'+(logs.read_text()[-2500:] if logs.exists() else ''))
    return value


def write(kernel,copy_id,path,text,p,create=False):
    if create:operation={'op':'CREATE','path':path,'text':text}
    else:
        old=invoke(kernel,'changes.file',{'copy':copy_id,'path':path},p)
        operation={'op':'WRITE','path':path,'text':text,'base_sha256':old['sha256']}
    proposal=invoke(kernel,'changes.propose',{'copy':copy_id,'operations':[operation]},p)
    return invoke(kernel,'changes.apply',{'id':proposal['id'],'expected_digest':proposal['content_digest']},p)


from .reason_service import memory_graph


def exercise(root,profile,home,boards=True):
    from .engineering_kernel import Kernel,operator
    from .stac import chronicle
    locations.office(root);kernel=Kernel(root);p=operator()
    data=clock_lab.start(kernel,clock_lab.copy_inputs(home/'Clock_Lab_I03'),p);problem=data['problem'];copy_id=data['copy']['id']
    qualified=wait(kernel,invoke(kernel,'experiments.qualify',{},p),p)
    stub=invoke(kernel,'experiments.create',{**bound(problem),'copy':copy_id},p)
    def python(path,params=stub['parameters']):
        plan=invoke(kernel,'experiments.prepare',{**bound(problem),'copy':copy_id,'script':path,'parameters':params},p)
        return plan,wait(kernel,invoke(kernel,'experiments.run',{'action':plan['id'],'expected_digest':plan['binding_digest']},p),p)
    action,observed=python(stub['script'])
    if observed['observation']['state']!='OBSERVED':raise ValueError('Real experiment failed: '+str(observed['observation']))
    measured={i['name']:i['value'] for i in observed['observation']['parsed']['measurements']}
    if measured!={'memory_total':'17','memory_fits':False}:raise ValueError('Actual Python output differs from independent 6+6+5 and 16 bound')
    published=invoke(kernel,'experiments.publish',{'job':observed['job']},p)
    if len(published['files'])!=2:raise ValueError('Missing generated Python artifacts')
    calculation=invoke(kernel,'math.prepare',{**bound(problem),'expression':'buffer_A + buffer_B + workspace <= memory_limit','assumptions':['All three allocations are concurrent.']},p)
    exact=invoke(kernel,'math.run',{'action':calculation['id']},p)['receipt']
    graph=invoke(kernel,'reasons.create',{**bound(problem),'graph':memory_graph(exact['id'],observed['job'])},p)
    first=invoke(kernel,'reasons.evaluate',{'id':graph['id'],'expected_revision':graph['revision']},p)
    if first['result']['snapshot']['state']!='SUPPORTED' or len(first['result']['snapshot']['paths']['positive'])!=2:raise ValueError('Alternative joint reasons were not retained')
    # Deleting a source must retain the old result with stale applicability.
    old=invoke(kernel,'changes.file',{'copy':copy_id,'path':stub['script']},p)
    deletion=invoke(kernel,'changes.propose',{'copy':copy_id,'operations':[{'op':'DELETE','path':stub['script'],'base_sha256':old['sha256']}]},p)
    invoke(kernel,'changes.apply',{'id':deletion['id'],'expected_digest':deletion['content_digest']},p)
    missing=invoke(kernel,'experiments.result',{'job':observed['job']},p)
    if missing['state']!='AVAILABLE' or missing['applicability']!='STALE':raise ValueError('Missing script hid a retained historical result')
    # Restore a changed script; the independent exact result remains current.
    write(kernel,copy_id,stub['script'],lab_service.SCRIPT+'\n# retained source revision change\n',p,True)
    second=invoke(kernel,'reasons.evaluate',{'id':graph['id'],'expected_revision':first['graph']['revision']},p)
    if second['result']['snapshot']['state']!='SUPPORTED' or second['result']['change']!={'verdict_changed':False,'reason_paths_changed':True,'has_previous':True}:raise ValueError('Stable verdict concealed changed reasons')
    unavailable=invoke(kernel,'reasons.impact',{'id':graph['id'],'node':'missing_edge'},p)
    if unavailable['coverage']!='UNKNOWN_DEPENDENCY':raise ValueError('Missing dependency was treated as no impact')
    stale=kernel.dispatch('experiments.run',{'action':action['id'],'expected_digest':action['binding_digest']},p)
    if stale['ok']:raise ValueError('A changed script was silently replayed')
    failed_path='Experiments/deliberate_failure.py';write(kernel,copy_id,failed_path,"raise RuntimeError('I03 deliberately retained failed attempt')\n",p,True)
    _,failed=python(failed_path)
    if failed['observation']['state']!='EXECUTION_FAILED' or failed['observation']['execution']['exit_code']!=1:raise ValueError('Failed Python attempt was not retained accurately')
    # A deliberately faulty threshold gives a valid, executed output that
    # disagrees with exact arithmetic. Execution alone cannot certify semantics.
    buggy_path='Experiments/deliberate_threshold_variant.py'
    write(kernel,copy_id,buggy_path,lab_service.SCRIPT.replace("fits = total <= v['memory_limit']","fits = total <= v['memory_limit'] + 2"),p,True)
    _,buggy=python(buggy_path)
    conflict_graph=invoke(kernel,'reasons.create',{**bound(problem),'graph':memory_graph(exact['id'],buggy['job'])},p)
    conflict=invoke(kernel,'reasons.evaluate',{'id':conflict_graph['id'],'expected_revision':conflict_graph['revision']},p)
    if conflict['result']['snapshot']['state']!='CONFLICT':raise ValueError('Disagreeing executed output was overwritten or hidden')
    native={}
    if boards:
        from . import kicad_tools
        for name in ('good','bad'):
            path='Experiments/'+name+'.kicad_pcb';write(kernel,copy_id,path,kicad_tools.FIXTURES[name],p,True)
            plan=invoke(kernel,'boards.prepare',{**bound(problem),'copy':copy_id,'board':path},p)
            native[name]=wait(kernel,invoke(kernel,'boards.run',{'action':plan['id'],'expected_digest':plan['binding_digest']},p),p)
            exported=invoke(kernel,'experiments.publish',{'job':native[name]['job']},p)
            if len(exported['files'])!=2 or {Path(i['path']).name for i in exported['files']}!={'drc.json','board.svg'}:raise ValueError('Board publication included a qualification fixture or lost an output')
            native[name]['published']=exported
        if native['good']['observation']['state']!='NO_REPORTED_VIOLATIONS' or native['bad']['observation']['state']!='VIOLATIONS':raise ValueError('Native board findings did not distinguish good and broken outlines')
        if not all(v['observation']['export']['exit_status']==0 for v in native.values()):raise ValueError('Native SVG export did not complete')
    verified=chronicle.verify(root)
    if verified['event_count']!=3:raise ValueError('Reason snapshots were not appended to existing Chronicle')
    child=subprocess.run([sys.executable,'-m','workbench.lab_checks','_resume',str(root),str(profile),graph['id']],
        capture_output=True,text=True,env=locations.child_env(root),timeout=30)
    if child.returncode:raise ValueError('Fresh-process reason reopen failed: '+child.stderr[-2000:])
    with kernel.db() as db:health=db.execute('PRAGMA quick_check').fetchone()[0]
    if health!='ok':raise ValueError('I03 database health check failed')
    return {'state':'PASSED','pass':'I03','model_calls':0,'runtime_qualification':qualified,
        'python_result':observed,'published':published,'retained_failure':failed,'deliberate_threshold_variant':buggy,
        'alternative_reasons':first,'stable_verdict_changed_reasons':second,'contradiction':conflict,
        'missing_dependency':unavailable,'missing_source_retains_history':True,'stale_script_refused':True,'native_boards':native,'chronicle':verified,
        'fresh_process_reopen':json.loads(child.stdout),'database':health,'thinkpad_qualification':'PENDING'}


def resume(root,profile,ident):
    os.environ.update(environment(os.environ,root,profile))
    from .engineering_kernel import Kernel,operator
    value=invoke(Kernel(root),'reasons.get',{'id':ident},operator())
    if value['latest']['snapshot']['state']!='SUPPORTED' or len(value['preview']['paths']['positive'])!=1 or value['automatic_execution']:raise ValueError('Reopen lost stable reason change or executed work')
    return {'state':'PASSED','retained_verdict':'SUPPORTED','active_alternatives':1,'automatic_execution':False}


def cancellation_check(timeout=False):
    from .engineering_kernel import Kernel,operator,process_token
    with tempfile.TemporaryDirectory(prefix='ledger-i03-stop-') as temp:
        base=Path(temp);home=base/'Home';home.mkdir();root=base/'Office';profile=base/'profile'
        with patch.dict(os.environ,{**environment(os.environ,root,profile),'HOME':str(home)}),patch.object(Path,'home',return_value=home):
            locations.office(root);kernel=Kernel(root);p=operator();data=clock_lab.start(kernel,clock_lab.copy_inputs(home/'Clock_Lab'),p)
            wait(kernel,invoke(kernel,'experiments.qualify',{},p),p)
            path='Experiments/sleep.py';write(kernel,data['copy']['id'],path,"open('/output/started','w').write('executing')\nimport time\ntime.sleep(120)\n",p,True)
            plan=invoke(kernel,'experiments.prepare',{**bound(data['problem']),'copy':data['copy']['id'],'script':path,'parameters':{}},p)
            # A direct submit cannot extend this profile to 600 seconds.
            extended=kernel.dispatch('jobs.submit',{'tool':'lab.python','lab':{'action':plan['id'],'expected_digest':plan['binding_digest']},'request_key':'lab:'+plan['id'],'timeout':600},p)
            if extended['ok']:raise ValueError('Direct submission bypassed the profile wall limit')
            job=invoke(kernel,'experiments.run',{'action':plan['id'],'expected_digest':plan['binding_digest']},p)
            folder=kernel.state/'jobs'/job['id'];until=time.monotonic()+20
            while not (folder/'outputs/started').exists() and time.monotonic()<until:
                if kernel.record('jobs',job['id'])['state']=='Failed':raise ValueError('Guest did not enter sleep')
                time.sleep(.05)
            if not (folder/'outputs/started').exists():raise ValueError('No actual execution marker')
            live=kernel.record('jobs',job['id']);pid=live['tool_pid'];token=live['tool_start']
            if not timeout:invoke(kernel,'jobs.cancel',{'id':job['id']},p)
            until=time.monotonic()+40
            while kernel.record('jobs',job['id'])['state'] in ('Queued','Running') and time.monotonic()<until:time.sleep(.05)
            state=kernel.record('jobs',job['id'])['state'];expected='Failed' if timeout else 'Cancelled'
            value=invoke(kernel,'experiments.result',{'job':job['id']},p)
            with kernel.db() as db:
                found=db.execute('SELECT count(*) FROM desk_records WHERE id=? AND kind=?',(job['id'],'lab_result')).fetchone()[0]
                health=db.execute('PRAGMA quick_check').fetchone()[0]
            if state!=expected or value['files'] or found or process_token(pid)==token:raise ValueError('Stopped experiment retained an active worker or successful observation')
            return {'state':'PASSED','case':'wall_timeout' if timeout else 'cancellation','guest_started':True,'job_state':state,
                'completed_result':False,'worker_terminated':True,'profile_extension_refused':True,'database':health}


def ui_check(screenshot=None):
    from PySide6.QtWidgets import QApplication,QLabel
    from types import SimpleNamespace
    from .engineering_kernel import Kernel,operator
    from .problem_qt import ProblemPane
    with tempfile.TemporaryDirectory(prefix='ledger-i03-ui-') as temp:
        base=Path(temp);home=base/'Home';home.mkdir();root=base/'Office';profile=base/'profile'
        with patch.dict(os.environ,{**environment(os.environ,root,profile),'HOME':str(home),'QT_QPA_PLATFORM':'offscreen'}),patch.object(Path,'home',return_value=home):
            locations.office(root);kernel=Kernel(root);p=operator();data=clock_lab.start(kernel,clock_lab.copy_inputs(home/'Clock_Lab'),p)
            app=QApplication.instance() or QApplication(['ledger-i03-ui'])
            desk=SimpleNamespace(host=SimpleNamespace(root=root),project=data['project'],assignment=data['assignment'],message=QLabel())
            pane=ProblemPane(desk)
            def finish():
                until=time.monotonic()+180
                while pane.lab.active and time.monotonic()<until:app.processEvents();time.sleep(.03)
                if pane.lab.active:raise ValueError('UI active job did not finish')
            try:
                pane.resize(1320,1050);pane.show();pane.reload(data['problem']['id']);pane.pages.setCurrentIndex(4);app.processEvents()
                pane.calculator.calculate();pane.lab.qualify();finish();pane.lab.create();pane.lab.run_python();finish()
                if 'memory_total = 17 MiB' not in pane.lab.output.toPlainText():raise ValueError('UI did not show actual executed output: '+pane.lab.output.toPlainText())
                pane.lab.compare();app.processEvents()
                if pane.lab.paths.rowCount()!=2 or 'SUPPORTED' not in pane.lab.answer.text():raise ValueError('UI missing alternative reasons')
                script=pane.lab.script.text();write(kernel,data['copy']['id'],script,lab_service.SCRIPT+'\n# revision changed from UI fixture\n',p)
                pane.lab.recompute();app.processEvents()
                if 'Verdict stayed the same.' not in pane.lab.answer.text() or 'Reason paths changed.' not in pane.lab.answer.text():raise ValueError('UI concealed changed reasons')
                menu=pane.lab.menu_for_row(0)
                if len(menu.actions())<2:raise ValueError('Context menu lacks selected-record actions')
                menu.actions()[0].trigger();app.processEvents()
                if 'snapshot' not in pane.lab.detail.toPlainText():raise ValueError('Context action did not open the retained observation')
                # Put the Why page in view and show the path/context text, rather
                # than hiding this distinction in debug output.
                pane.lab.findChild(__import__('PySide6.QtWidgets',fromlist=['QTabWidget']).QTabWidget).setCurrentIndex(1)
                pane.lab.impact('experiment');app.processEvents()
                if screenshot:pane.grab().save(str(screenshot))
                return {'state':'PASSED','actual_ui_python_run':True,'alternative_paths':True,'stable_verdict_changed_reasons':True,
                    'context_menu_opens_owned_receipt':True,'scope':'Real Qt widgets with native WASI execution, offscreen','owner_display':'PENDING'}
            finally:pane.close();app.processEvents()


def main():
    if len(sys.argv)>1 and sys.argv[1]=='_resume':print(json.dumps(resume(*sys.argv[2:])));return 0
    parser=argparse.ArgumentParser();parser.add_argument('--no-board',action='store_true');parser.add_argument('--keep',type=Path);parser.add_argument('--output',type=Path)
    parser.add_argument('--cancel',action='store_true');parser.add_argument('--timeout',action='store_true');parser.add_argument('--ui',action='store_true');parser.add_argument('--screenshot',type=Path)
    args=parser.parse_args()
    if args.cancel or args.timeout or args.ui:
        value=ui_check(args.screenshot) if args.ui else cancellation_check(args.timeout)
        raw=json.dumps(value,indent=2)+'\n'
        if args.output:args.output.write_text(raw)
        print(raw,end='');return 0
    with tempfile.TemporaryDirectory(prefix='ledger-i03-') as temp:
        base=args.keep or Path(temp);base.mkdir(parents=True,exist_ok=True);home=base/'Home';home.mkdir();root=base/'Office';profile=base/'profile'
        with patch.dict(os.environ,{**environment(os.environ,root,profile),'HOME':str(home)}),patch.object(Path,'home',return_value=home):value=exercise(root,profile,home,not args.no_board)
        raw=json.dumps(value,indent=2)+'\n'
        if args.output:args.output.write_text(raw)
        print(json.dumps({'state':value['state'],'pass':'I03','board_cases':list(value['native_boards']),'model_calls':0}))
    return 0


if __name__=='__main__':raise SystemExit(main())
