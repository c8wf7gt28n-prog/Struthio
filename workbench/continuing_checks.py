"""Disposable continuing-work restart, budget/Stop and complete-restore checks."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from unittest.mock import patch


def invoke(kernel,op,args,p):
    result=kernel.dispatch(op,args,p)
    if not result['ok']:raise ValueError(op+': '+result['error']['message'])
    return result['result']


def fixture(base,identity='stage-five-check'):
    from .edit_checks import fixture as imported
    kernel,p,home,source,copy=imported(base,identity)
    project=invoke(kernel,'projects.create',{'title':'Clock','intent':'Prepare the clock proposal'},p)
    a=invoke(kernel,'assignments.create',{'project':project['id'],'request':'Use black hands and preserve the master',
        'interpretation':'Update the assigned working note only','intended_output':'Black-hand working proposal',
        'success':['The working note is exact'],'stop':['Changed source or work hold'],
        'inputs':['files:'+copy['work']+'/note.txt']},p)
    steps=[{'key':'Read','operation':'work.read','arguments':{'copy':copy['id'],'path':'note.txt'},'after':[]},
        {'key':'Draft','operation':'changes.propose','arguments':{'copy':copy['id'],'operations':[{'op':'WRITE','path':'note.txt',
            'base_sha256':{'$step':'Read','path':['sha256']},'text':'Clock needs black hands.\n'}]},'after':['Read']},
        {'key':'Apply','operation':'changes.apply','arguments':{'id':{'$step':'Draft','path':['id']},
            'expected_digest':{'$step':'Draft','path':['content_digest']}},'after':['Draft']},
        {'key':'ReadBack','operation':'work.read','arguments':{'copy':copy['id'],'path':'note.txt'},'after':['Apply'],
            'require':[{'path':['text'],'equals':'Clock needs black hands.\n'}]}]
    order=invoke(kernel,'work.create',{'title':'Clock continuation','assignment':a['id'],'copies':[copy['id']],
        'steps':steps,'budget':{'seconds':300,'steps':10,'tokens':0,'memory_mb':128,'output_bytes':1048576,'files':2},'expires':time.time()+3600},p)
    invoke(kernel,'work.authorize',{'id':order['plan']['id'],'expected_digest':order['content_digest']},p)
    return kernel,p,home,source,copy,order


def child(mode,root,profile,home,expected):
    from .baseline import environment
    from .engineering_kernel import Kernel,operator
    from . import continuing_work as flow,work_trail
    os.environ.update(environment(os.environ,root,profile))
    with patch('pathlib.Path.home',return_value=home):
        kernel=Kernel(root);p=operator('stage-five-check');ident=expected['work']
        if mode=='crash':
            flow.CRASH_AT='EFFECT'
            try:invoke(kernel,'work.advance',{'id':ident},p)
            except flow.Crash:os._exit(78)
            raise ValueError('Interruption was not reached')
        before=invoke(kernel,'work.get',{'id':ident},p)
        if mode=='recover':
            if before['state']['state']!='RUNNING':raise ValueError('No persisted in-flight step')
            flow.pump(kernel)
            paused=invoke(kernel,'work.get',{'id':ident},p)
            if paused['state']['reason']!='INTERRUPTED_STEP_REQUIRES_EXPLICIT_RESUME':raise ValueError('Interrupted work resumed automatically')
            invoke(kernel,'work.resume',{'id':ident},p)
            invoke(kernel,'work.advance',{'id':ident},p)
            done=invoke(kernel,'work.get',{'id':ident},p)
            if done['state']['state']!='REVIEW' or not done['steps'][2].get('recovered') or done['state']['used']['steps']!=4:
                raise ValueError('Completed application was not reconciled exactly once')
            with kernel.db() as db:
                applications=db.execute('SELECT count(*) FROM edit_applications').fetchone()[0]
            if applications!=1:raise ValueError('The application repeated')
            # A work hold persists through another Kernel open and never renews this grant.
            work_trail.hold(kernel,p)
            if not work_trail.execution_held(Kernel(root)):raise ValueError('Persistent work hold was lost')
            return {'state':'PASSED','completed_effect_reconciled':True,'applications':applications,'no_automatic_interrupted_resume':True,
                'attempts':done['state']['used']['steps'],'persistent_hold':True,'review_required':True}
        if before['content_digest']!=expected['digest'] or before['state']['state']!='REVIEW':raise ValueError('Order/result did not survive restore')
        if not work_trail.execution_held(kernel):raise ValueError('Restored work hold was lost')
        if invoke(kernel,'work.advance',{'id':ident},p).get('ran') is not None:raise ValueError('Held restored work ran')
        work=root/'Files'/expected['work_path']
        if (work/'note.txt').read_text()!='Clock needs black hands.\n':raise ValueError('Working result changed during restore')
        return {'state':'PASSED','plan_digest_preserved':True,'grant_and_budget_preserved':True,'completed_steps_preserved':True,
            'working_result_preserved':True,'persistent_hold_preserved':True,'effects_replayed':0}


def self_test():
    from .baseline import environment
    from . import workspace_backup
    with tempfile.TemporaryDirectory(prefix='ledger-stage-five-') as temp:
        base=Path(temp);kernel,p,home,source,copy,order=fixture(base)
        for _ in range(2):invoke(kernel,'work.advance',{'id':order['plan']['id']},p)
        expected={'work':order['plan']['id'],'digest':order['content_digest'],'work_path':copy['work']}
        def restart(root,profile,mode,code=0):
            process=subprocess.run([sys.executable,'-m','workbench.continuing_checks','--child',mode,str(root),str(profile),str(home),json.dumps(expected)],
                env=environment(os.environ,root,profile),capture_output=True,text=True,timeout=60)
            if process.returncode!=code:raise ValueError('Child continuation check failed: '+(process.stderr or process.stdout)[-1500:])
            return {'exit_code':code} if code else json.loads(process.stdout)
        crash=restart(kernel.root,base/'profile','crash',78)
        recovered=restart(kernel.root,base/'profile','recover')
        if (source/'note.txt').read_text()!='Clock needs blue hands.\n':raise ValueError('A continuing task altered the master')
        saved=workspace_backup.create(kernel.root,base/'backup');restored=workspace_backup.restore(base/'backup',base/'Restored')
        readback=restart(Path(restored['workspace']),Path(restored['profile']),'readback')
        return {'state':'PASSED','scope':'Actual process exit after a completed working-file effect, before its work checkpoint',
            'crash':crash,'restart':recovered,'backup':{k:saved[k] for k in ('state','files','databases')},'restored_restart':readback,
            'master_unchanged':True,'model_calls':0,'external_network_calls':0,'native_containment':'SEPARATE_REAL_HOST_QUALIFICATION'}


def worker_test():
    from .baseline import environment
    from .engineering_kernel import Kernel,operator
    from . import locations
    with tempfile.TemporaryDirectory(prefix='ledger-worker-check-') as temp:
        base=Path(temp);root=base/'Office';os.environ.update(environment(os.environ,root,base/'profile'));locations.office(root)
        kernel=Kernel(root);p=operator();results={profile:invoke(kernel,'workers.qualify',{'profile':profile},p) for profile in ('PARSER','CHECK','MODEL')}
        passed=all(r['state']=='QUALIFIED' for r in results.values())
        return {'state':'PASSED' if passed else 'UNAVAILABLE_OR_FAILED','profiles':results,'containment_qualified':passed,
            'meaning':'Only all required real probes establish containment. Unavailable/refused probes establish refusal only.'}


def host_test():
    from .host_client import ensure,HostClient
    from .host_cli import wait_stopped
    with tempfile.TemporaryDirectory(prefix='ledger-stage-five-host-') as temp:
        base=Path(temp);kernel,p,home,source,copy,order=fixture(base,'desktop-owner');client=None
        try:
            client=ensure(kernel.root)
            deadline=time.monotonic()+40
            while time.monotonic()<deadline:
                current=invoke(client,'work.get',{'id':order['plan']['id']},p)
                if current['state']['state']=='REVIEW':break
                if current['state']['state'] not in ('READY','RUNNING'):raise ValueError('Headless work stopped: '+str(current['state'].get('reason')))
                time.sleep(.15)
            else:raise ValueError('Headless Agenda did not complete the permitted steps')
            if current['state']['used']['steps']!=4 or (source/'note.txt').read_text()!='Clock needs blue hands.\n':raise ValueError('Headless task changed its scope or repeated work')
            stopped=client.rpc('master_stop',timeout=20)
            if stopped['result']!='STOPPED' or not stopped['work']['held']:raise ValueError('Headless Master Stop did not confirm its hold')
            return {'state':'PASSED','scope':'Actual authenticated coordinator IPC and automatic Agenda advancement, without Qt',
                'transport':client.transport,'automatic_steps':4,'work_state':'REVIEW','master_unchanged':True,'master_stop_held':True,'model_calls':0}
        finally:
            if client is not None:
                client.rpc('shutdown');wait_stopped(client)


def ui_test():
    from .baseline import environment
    with tempfile.TemporaryDirectory(prefix='ledger-stage-five-ui-') as temp:
        base=Path(temp);root=base/'Office';os.environ.update(environment(os.environ,root,base/'profile'));os.environ['QT_QPA_PLATFORM']='offscreen'
        from .locations import office
        office(root)
        from .qt_app import make_app,WorkbenchWindow
        from .continuing_work_qt import show
        app=make_app(['ledger-stage-five-check']);host=WorkbenchWindow(root=root,restore=False)
        try:
            host.show();tab=show(host);app.processEvents()
            if tab.current is not None:raise ValueError('UI fixture unexpectedly loaded user work')
            return {'state':'PASSED','scope':'Real continuing-work panel opens without a model or grant','owner_display_walkthrough':'PENDING'}
        finally:host.close();app.processEvents()


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--child',nargs=5);parser.add_argument('--ui',action='store_true');parser.add_argument('--workers',action='store_true');parser.add_argument('--host',action='store_true');args=parser.parse_args()
    try:
        if args.child:
            mode,root,profile,home,expected=args.child;result=child(mode,Path(root),Path(profile),Path(home),json.loads(expected))
        else:result=ui_test() if args.ui else worker_test() if args.workers else host_test() if args.host else self_test()
        print(json.dumps(result,indent=2));return 0 if result['state']=='PASSED' else 2
    except (ValueError,OSError,ImportError,subprocess.SubprocessError) as exc:
        print(json.dumps({'state':'FAILED','error':str(exc)},indent=2));return 1


if __name__=='__main__':raise SystemExit(main())
