"""Focused real application, method-transfer, revision and takeover qualification."""
from pathlib import Path
from unittest.mock import patch
import argparse, copy, csv, hashlib, json, os, subprocess, sys, time
from . import project_desk as records, locations, checked_methods
from .problem_checks import invoke, bound
from .baseline import environment


def wait(kernel, p, job, endpoint, seconds=230):
    until=time.monotonic()+seconds
    while kernel.record('jobs',job['id'])['state'] in ('Queued','Running') and time.monotonic()<until:
        time.sleep(.1)
    result=invoke(kernel,endpoint,{'job':job['id']} if endpoint!='brain.result' else {'id':job['id']},p)
    if result['state'] not in ('AVAILABLE','Completed'):
        folder=kernel.state/'jobs'/job['id']
        tail='\n'.join((folder/name).read_text(errors='replace')[-1500:] for name in ('stdout.log','stderr.log') if (folder/name).exists())
        raise ValueError('Actual job did not pass: '+str(result)+'\n'+tail)
    return result


def fixture(kernel,p,home,title,current=False):
    source=home/title;source.mkdir();path=source/'resources.csv'
    names=('current_limit','pump','heater','controller') if current else ('memory_limit','buffer_A','buffer_B','workspace')
    amounts=('10','4','3','2') if current else ('16','6','6','5');unit='A' if current else 'MiB'
    lives=[('0','7000','ms'),('0','7','s'),('6','12','s')] if current else [('0','10','s'),('0','10','s'),('10','20','s')]
    variables=[{'name':name,'type':'quantity','unit':unit,'state':'KNOWN','value':value,'basis':'Declared synthetic resources.csv'} for name,value in zip(names,amounts)]
    for name,(start,stop,tu) in zip(names[1:],lives):
        variables.append({'name':name+'_life','type':'interval','unit':tu,'state':'KNOWN',
            'value':records.canonical({'start':start,'stop':stop,'unit':tu}),'basis':'Declared synthetic resources.csv intervals'})
    with path.open('w',newline='') as stream:
        out=csv.writer(stream);out.writerow(['name','type','value','unit'])
        for v in variables:out.writerow([v['name'],v['type'],v['value'],v['unit']])
    preview=invoke(kernel,'imports.preview',{'source':str(source),'profile':'ENGINEERING'},p)
    selected=invoke(kernel,'imports.accept',{'id':preview['id'],'expected_digest':preview['content_digest'],'for_slate':True},p)
    request='Check the declared '+('current envelope' if current else 'memory allocations')+' over the supplied lifetimes; document conditional findings.'
    project=invoke(kernel,'projects.create',{'title':title,'intent':request},p)
    assignment=invoke(kernel,'assignments.create',{'project':project['id'],'request':request,'interpretation':request,
        'intended_output':'Checked conditional application findings','success':['Use actual application outputs.'],
        'stop':['Stop on changed inputs or unsupported assumptions.'],'inputs':[]},p)
    problem=invoke(kernel,'problems.create',{'project':project['id'],'assignment':assignment['id'],'request':request,'title':title,
        'goals':[request],'variables':variables,'assumptions':['Synthetic constant additive demands, fixed capacity, half-open lifetimes.'],
        'questions':[],'candidates':['The specified schedule fits.','Overlap may exceed capacity.'],
        'sources':[{'copy':selected['id'],'path':'resources.csv','label':'Declared source quantities and lifetimes'}]},p)
    return {'problem':problem,'copy':selected,'source':path,'source_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
        'capacity':names[0],'allocations':[{'quantity':name,'lifetime':name+'_life'} for name in names[1:]]}


def chain(kernel,p,case,receipt,method_job=None):
    args={'receipt':receipt,'copy':case['copy']['id']}
    if method_job:args['method_job']=method_job
    action=invoke(kernel,'joined.prepare',args,p)
    job=invoke(kernel,'joined.run',{'action':action['id'],'expected_digest':action['binding_digest']},p)
    result=wait(kernel,p,job,'joined.result')
    assert len(result['receipt']['artifacts'])==4
    assert all(invoke(kernel,'artifacts.get',{'id':r['id']},p)['applicability']=='CURRENT' for r in result['receipt']['artifacts'])
    print(case['problem']['title'],'actual native chain',result['snapshot']['state'],result['snapshot']['peak'],flush=True)
    return job,result


def checkpoint(root,profile,home,job,method):
    from .engineering_kernel import Kernel,operator
    os.environ.update(environment(os.environ,root,profile));os.environ['HOME']=str(home)
    kernel=Kernel(root);p=operator();before=len(kernel.listing('jobs'))
    result=invoke(kernel,'joined.result',{'job':job},p);saved=invoke(kernel,'methods.get',{'id':method},p)
    assert result['state']=='AVAILABLE' and saved['state']=='ACCEPTED'
    assert len(kernel.listing('jobs'))==before
    return {'state':'PASSED','artifacts':result['receipt']['artifacts'],'method_revision':saved['revision'],
            'method_history_revisions':[v['revision'] for v in saved['history']],'automatic_jobs_started':0}


def coordinator_takeover(kernel,p,base,case,mapped_job):
    """Session protocol only. Actual Calc edits/outputs; no visible-window claim."""
    from . import native_sessions,typed_artifacts,joined_work,office_math_runtime
    output=invoke(kernel,'joined.result',{'job':mapped_job['id']},p)
    artifact=typed_artifacts.read(kernel,output['receipt']['artifacts'][0]['id'],p)
    action=joined_work.read(kernel,'joined_action',output['receipt']['action'],p)
    schedule=joined_work.schedule(kernel,action['schedule'],p)
    cells,expected,profile=joined_work.calc_profile(schedule)
    holder=records.new('native_session',p,schema='ledger.owned-calc-session/1',source_job=mapped_job['id'],
        copy=case['copy']['id'],artifact=typed_artifacts.reference(artifact),mode='PAUSED',job=mapped_job['id'],
        expires=time.time()+540,components=joined_work.components(),office=office_math_runtime.probe(),test_only='COORDINATOR_NO_NATIVE_WINDOW')
    holder['binding_digest']=records.digest(holder)
    with kernel.db() as db:records.write(db,holder,p,'TEST_COORDINATOR_SESSION_NO_NATIVE_WINDOW')
    data={'cells':{r['cell']:{**r,'cell_type':3 if r['formula'].startswith('=') else 1,
        'unit':profile['inputs'][r['cell']]['unit'] if r['cell'] in profile['inputs'] else r['unit']}
        for r in artifact['data']['measurements'] if r['phase']=='REOPENED'}}
    def native_command(kernel_arg,value,op,p_arg,cell=None,data_value=None):
        if op=='EDIT':
            cells[cell]={'kind':'number','value':data_value}
            folder=base/'coordinator-owner-edit';folder.mkdir(exist_ok=True)
            target=folder/'Edited.ods'
            _,rows=office_math_runtime.calculate(typed_artifacts.path(kernel,artifact),target,folder/'native',cells,list(expected))
            os.replace(target,typed_artifacts.path(kernel,artifact))
            data['cells']={r['cell']:{**r,'cell_type':3 if r['formula'].startswith('=') else 1,
                'unit':profile['inputs'][r['cell']]['unit'] if r['cell'] in profile['inputs'] else expected[r['cell']]['unit']}
                for r in rows if r['phase']=='REOPENED'}
        return {'cells':data['cells'],'window_id':0,'title':'TEST_COORDINATOR_ONLY_NO_NATIVE_WINDOW','mode':value['mode']}
    ident=holder['id']
    def control(op,**extra):
        live=invoke(kernel,'joined.session.get',{'id':ident},p)['session']
        return invoke(kernel,'joined.session.'+op,{'id':ident,'expected_revision':live['revision'],**extra},p)
    order=invoke(kernel,'work.create',{'assignment':case['problem']['assignment'],'copies':[case['copy']['id']],
        'steps':[{'key':'Read','operation':'work.read','arguments':{'copy':case['copy']['id'],'path':'resources.csv'},'after':[]}],
        'budget':{'seconds':60,'steps':2,'tokens':0,'memory_mb':128,'output_bytes':1048576,'files':0},
        'expires':time.time()+3600,'title':'Coordinator conflicting-copy test'},p)
    invoke(kernel,'work.authorize',{'id':order['plan']['id'],'expected_digest':order['content_digest']},p)
    with patch.object(native_sessions,'command',side_effect=native_command):
        control('takeover');assert invoke(kernel,'work.get',{'id':order['plan']['id']},p)['state']['state']=='PAUSED'
        address=next(a for a,role in profile['inputs'].items() if role['name']=='pump')
        control('edit',cell=address,value='6')
        captured=control('resume');assert captured['refresh_required']
        assert invoke(kernel,'joined.result',{'job':mapped_job['id']},p)['state']=='STALE'
        before=invoke(kernel,'problems.get',{'id':case['problem']['id']},p)['problem']['revision']
        original_write=records.write
        def interrupted(db,value,p_arg,action,expected=None):
            if action=='OWNER_SCENARIO_AND_CONTINUATION_COMMITTED':raise OSError('Injected interruption between source revision and session continuation')
            return original_write(db,value,p_arg,action,expected)
        live=captured['session']
        with patch.object(records,'write',side_effect=interrupted):
            failed=kernel.dispatch('joined.session.refresh',{'id':ident,'expected_revision':live['revision'],'note':'Interrupted owner scenario test.'},p)
        assert not failed['ok'] and invoke(kernel,'problems.get',{'id':case['problem']['id']},p)['problem']['revision']==before
        assert invoke(kernel,'joined.session.get',{'id':ident},p)['session']['revision']==live['revision']
        refreshed=control('refresh',note='Coordinator-only owner participation fixture: actual native Calc input changed from 4 A to 6 A.')
        assert refreshed['schedule']['problem_revision']==before+1 and refreshed['schedule']['snapshot']['peak']['rational']=='11'
        plan=refreshed['prepared'];job=invoke(kernel,'joined.run',{'action':plan['id'],'expected_digest':plan['binding_digest']},p)
        result=wait(kernel,p,job,'joined.result');assert result['snapshot']['state']=='INFEASIBLE'
        control('close')
    return {'state':'PASSED','scope':'COORDINATOR_ONLY_NO_VISIBLE_NATIVE_SESSION','native_window_qualification':'NOT_PERFORMED',
        'actual_headless_Calc_owner_edit':True,'conflicting_work_paused':True,'changed_working_revision_captured':True,
        'dependent_outputs_became_stale':True,'interrupted_source_and_checkpoint_transaction_rolled_back':True,
        'retry_committed_one_problem_revision':True,'actual_rechecked_application_chain':result,
        'original_source_unchanged':hashlib.sha256(case['source'].read_bytes()).hexdigest()==case['source_sha256']}


def visible(kernel,p,base,case,primary_job,mapped_job,method):
    from . import native_sessions
    opened=invoke(kernel,'joined.session.open',{'job':mapped_job['id']},p);ident=opened['session']['id']
    unrelated=invoke(kernel,'joined.session.open',{'job':primary_job['id']},p);other=unrelated['session']['id']
    def get():return invoke(kernel,'joined.session.get',{'id':ident},p)
    def control(op,**extra):
        live=get()['session']
        return invoke(kernel,'joined.session.'+op,{'id':ident,'expected_revision':live['revision'],**extra},p)
    try:
        until=time.monotonic()+40
        while (not get()['native']) and time.monotonic()<until:
            if get()['job_state'] not in ('Queued','Running'):
                job=kernel.record('jobs',get()['session']['job']);folder=kernel.state/'jobs'/job['id']/'session'
                raise ValueError('Visible session failed: '+str(job.get('error'))+' '+((folder/'stderr.log').read_text(errors='replace') if (folder/'stderr.log').exists() else ''))
            time.sleep(.1)
        ready=get();assert ready['native']['window_id']>0
        forbidden=kernel.dispatch('joined.session.recalculate',{'id':ident,'expected_revision':ready['session']['revision']},p)
        assert not forbidden['ok']
        control('resume');observed=control('recalculate');assert observed['observation']['authority']=='ACTUAL_VISIBLE_CALC_RECALCULATION'
        # Exercise the current UI over the real native window and retained files.
        from PySide6.QtWidgets import QApplication,QLabel
        from types import SimpleNamespace
        from .problem_qt import ProblemPane
        app=QApplication.instance() or QApplication(['ledger-i05-visible'])
        pane=ProblemPane(SimpleNamespace(host=SimpleNamespace(root=kernel.root),project=None,assignment=None,message=QLabel()))
        pane.resize(1400,1050);pane.show();pane.reload(case['problem']['id']);app.processEvents()
        pane.pages.setCurrentIndex(pane.pages.indexOf(pane.joined));pane.joined.select_job(mapped_job['id']);app.processEvents()
        pane.joined.attach(ready);app.processEvents()
        pane.grab().save(str(base/'I05_visible_calc.png'))
        order=invoke(kernel,'work.create',{'assignment':case['problem']['assignment'],'copies':[case['copy']['id']],
            'steps':[{'key':'Read','operation':'work.read','arguments':{'copy':case['copy']['id'],'path':'resources.csv'},'after':[]}],
            'budget':{'seconds':60,'steps':2,'tokens':0,'memory_mb':128,'output_bytes':1048576,'files':0},
            'expires':time.time()+3600,'title':'Conflicting copy work'},p)
        invoke(kernel,'work.authorize',{'id':order['plan']['id'],'expected_digest':order['content_digest']},p)
        control('takeover');assert invoke(kernel,'work.get',{'id':order['plan']['id']},p)['state']['state']=='PAUSED'
        calc=invoke(kernel,'artifacts.get',{'id':ready['session']['artifact']['id']},p)['artifact']
        address=next(a for a,role in calc['data']['profile']['inputs'].items() if role['name']=='pump')
        control('edit',cell=address,value='6')
        resumed=control('resume');assert resumed['refresh_required'] and resumed['session']['mode']=='REFRESH_REQUIRED'
        stale=invoke(kernel,'joined.result',{'job':mapped_job['id']},p);assert stale['state']=='STALE'
        refreshed=control('refresh',note='Synthetic owner changed pump from 4 A to 6 A in the actual owned Calc window.')
        assert refreshed['schedule']['snapshot']['peak']['rational']=='11' and refreshed['schedule']['snapshot']['fits'] is False
        prepared=refreshed['prepared'];job=invoke(kernel,'joined.run',{'action':prepared['id'],'expected_digest':prepared['binding_digest']},p)
        completed=wait(kernel,p,job,'joined.result');assert completed['snapshot']['peak']['rational']=='11'
        assert completed['snapshot']['state']=='INFEASIBLE'
        assert hashlib.sha256(case['source'].read_bytes()).hexdigest()==case['source_sha256']
        # Close the foreign container before deleting the parent QWidget.
        pane.joined.detach();pane.close();app.processEvents()
        control('close')
        other_state=invoke(kernel,'joined.session.get',{'id':other},p)
        assert other_state['job_state']=='Running' and other_state['native']['window_id']!=ready['native']['window_id']
        return {'state':'PASSED','native_window_id':ready['native']['window_id'],'actual_visible_recalculation':observed['observation'],
            'unrelated_owned_window_survived':True,'conflicting_order_paused':True,'working_edit_captured':True,
            'dependent_results_stale':True,'original_source_unchanged':True,'rechecked_peak':'11 A','rechecked_verdict':'INFEASIBLE',
            'rechecked_job':job['id'],'source_problem_revision':refreshed['schedule']['problem_revision'],
            'screenshot':'I05_visible_calc.png'}
    finally:
        for session in (ident,other):
            try:
                live=invoke(kernel,'joined.session.get',{'id':session},p)
                if live['session']['mode']!='CLOSED': invoke(kernel,'joined.session.close',{'id':session,'expected_revision':live['session']['revision']},p)
            except (ValueError,OSError):pass


def interface(kernel,p,base,case,job):
    """Inspect current records in Qt; never counts as native Calc qualification."""
    from PySide6.QtWidgets import QApplication,QLabel
    from types import SimpleNamespace
    from .problem_qt import ProblemPane
    app=QApplication.instance() or QApplication(['ledger-i05-interface'])
    pane=ProblemPane(SimpleNamespace(host=SimpleNamespace(root=kernel.root),project=None,assignment=None,message=QLabel()))
    pane.resize(1400,1050);pane.show();pane.reload(case['problem']['id']);app.processEvents()
    pane.pages.setCurrentIndex(pane.pages.indexOf(pane.joined));pane.joined.select_job(job['id']);app.processEvents()
    assert pane.pages.count()==6 and pane.joined.selected==job['id']
    assert '12' in pane.joined.finding.text() and pane.joined.why.topLevelItemCount()==4
    assert pane.joined.methods.count() and pane.joined.method_details.topLevelItemCount()==8
    from .adaptive_qt import operations_for
    from .adaptive_contract import FIELDS,validate_schema,DEFAULT_OPS
    assert pane.lab.adaptive.profile.count()==4
    for index in range(4):validate_schema(operations_for(index),FIELDS['work.investigate'][0]['operations'])
    assert operations_for(0)==operations_for(2)==DEFAULT_OPS
    assert len(operations_for(1))==15 and len(operations_for(3))==8
    pane.lab.adaptive.profile.setCurrentIndex(3)
    assert (pane.lab.adaptive.steps.value(),pane.lab.adaptive.minutes.value(),pane.lab.adaptive.tokens.value())==(32,30,240000)
    screenshots=[]
    for index,label in enumerate(('findings','methods','working-file')):
        pane.joined.tabs.setCurrentIndex(index);app.processEvents()
        target=base/('I05_'+label+'.png');assert pane.grab().save(str(target));screenshots.append(target.name)
    pane.joined.timer.stop();pane.close();app.processEvents()
    return {'state':'PASSED','scope':'CURRENT_QT_RECORDS_ONLY_NOT_NATIVE_CALC_VISIBILITY',
        'existing_problem_pages_retained':6,'current_findings_and_expandable_evidence':True,
        'method_preconditions_evidence_and_history_inspectable':True,'model_calls':0,'screenshots':screenshots}


def checks(base, visible_check=False, coordinator_check=False, ui_check=False):
    from .engineering_kernel import Kernel,operator,Principal
    base.mkdir(exist_ok=False);home=base/'Home';home.mkdir();root=base/'Office';profile=base/'profile'
    with patch.dict(os.environ,{**environment(os.environ,root,profile),'HOME':str(home)}),patch.object(Path,'home',return_value=home):
        locations.office(root);kernel=Kernel(root);p=operator()
        wait(kernel,p,invoke(kernel,'experiments.qualify',{},p),'experiments.result')
        first=fixture(kernel,p,home,'Memory_chain');receipt=invoke(kernel,'math.schedule',{**bound(first['problem']),
            'capacity':first['capacity'],'allocations':first['allocations']},p)
        primary_job,primary=chain(kernel,p,first,receipt['id']);assert primary['snapshot']['peak']['rational']=='12'
        count=len(kernel.listing('jobs'));method=invoke(kernel,'methods.propose',{'job':primary_job['id'],'title':'Capacity over known lifetimes'},p)
        assert method['state']=='PROPOSED' and len(kernel.listing('jobs'))==count
        denied=kernel.dispatch('methods.accept',{'id':method['id'],'expected_revision':method['revision'],'note':'Cannot self-approve.'},Principal(p.identity,frozenset({'read','execute'})))
        assert not denied['ok']
        method=invoke(kernel,'methods.accept',{'id':method['id'],'expected_revision':method['revision'],'note':'Accept the checked additive profile and its explicit limitations.'},p)
        assert invoke(kernel,'procedures.get',{'id':method['id']},p)['checked_method']['revision']==method['revision']
        second=fixture(kernel,p,home,'Current_transfer',True)
        args={'method':method['id'],'method_revision':method['revision'],**bound(second['problem']),
            'capacity':second['capacity'],'allocations':second['allocations'],
            'declarations':{**checked_methods.EXPECTED,'basis':'Synthetic fixed current envelopes with no additional modeled overhead; compatible seconds and milliseconds.'}}
        assert invoke(kernel,'methods.preview',args,p)['state']=='SUPPORTED'
        invalid=copy.deepcopy(args);invalid['declarations']['overhead']='PRESENT';before=len(kernel.listing('jobs'))
        assert invoke(kernel,'methods.preview',invalid,p)['state']=='UNSUPPORTED'
        assert not kernel.dispatch('methods.instantiate',invalid,p)['ok'] and len(kernel.listing('jobs'))==before
        action=invoke(kernel,'methods.instantiate',args,p);assert len(kernel.listing('jobs'))==before
        job=invoke(kernel,'methods.run',{'action':action['id'],'expected_digest':action['binding_digest']},p)
        mapped=wait(kernel,p,job,'methods.result');assert mapped['snapshot']['peak']['rational']=='9' and mapped['snapshot']['peak']['unit']=='A'
        mapped_job,mapped_chain=chain(kernel,p,second,mapped['receipt']['receipt'],job['id'])
        process=subprocess.run([sys.executable,'-m','workbench.joined_checks','--child',str(root),str(profile),str(home),mapped_job['id'],method['id']],
            env=locations.child_env(root),capture_output=True,text=True,timeout=30)
        if process.returncode:raise ValueError('Reopen failed: '+process.stderr[-1500:])
        reopened=json.loads(process.stdout);assert reopened['artifacts']==mapped_chain['receipt']['artifacts']
        result={'state':'PASSED','pass':'I05','model_calls':0,'scope':'Real native Calc/Writer and protected Python with coordinator-selected declared cases, not a new model intelligence measurement.',
            'source_chain':primary,'mapped_chain':mapped_chain,'method':method,'unseen_valid_mapping':'Memory to scheduled current; changed names, quantities, overlap pattern and time units.',
            'invalid_precondition_rejected_without_job':True,'method_save_and_instantiation_do_not_grant_or_start_jobs':True,
            'model_cannot_accept_method':True,'fresh_process_reopen':reopened}
        if visible_check:result['visible_takeover']=visible(kernel,p,base,second,primary_job,mapped_job,method)
        elif coordinator_check:result['takeover_coordinator']=coordinator_takeover(kernel,p,base,second,mapped_job)
        revised=invoke(kernel,'methods.revise',{'id':method['id'],'expected_revision':method['revision'],'title':method['title'],
            'note':'Explicit method version change for dependency qualification; previous observations remain historical.'},p)
        assert revised['state']=='PROPOSED' and invoke(kernel,'methods.result',{'job':job['id']},p)['state']=='STALE'
        assert invoke(kernel,'methods.preview',args,p)['state']=='UNSUPPORTED'
        result['changed_method_invalidates_old_instances']=True
        if ui_check:result['interface']=interface(kernel,p,base,first,primary_job)
        assert all(hashlib.sha256(c['source'].read_bytes()).hexdigest()==c['source_sha256'] for c in [first,second])
        result['originals_unchanged']=True
        with kernel.db() as db:result['database']=db.execute('PRAGMA integrity_check').fetchone()[0]
        assert result['database']=='ok'
        return result


def main():
    if len(sys.argv)>1 and sys.argv[1]=='--child':
        print(json.dumps(checkpoint(*map(Path,sys.argv[2:5]),*sys.argv[5:])));return 0
    parser=argparse.ArgumentParser();parser.add_argument('--keep',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--visible',action='store_true');parser.add_argument('--coordinator-takeover',action='store_true');parser.add_argument('--ui',action='store_true');args=parser.parse_args()
    if args.visible and args.coordinator_takeover:parser.error('Choose either actual visible acceptance or coordinator-only takeover')
    result=checks(args.keep,args.visible,args.coordinator_takeover,args.ui);args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'state':result['state'],'visible':bool(result.get('visible_takeover'))}));return 0

if __name__=='__main__':raise SystemExit(main())
