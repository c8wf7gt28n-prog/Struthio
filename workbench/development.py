"""Source-bound development cases shared by desktop and JSONL agents.

The initial fixed case develops P10 host diagnostic accounting in a separate
candidate directory. Imported hardware and its manifests are never overwritten.
"""
from __future__ import annotations
import hashlib,json,os,shutil,subprocess,tempfile,time
from pathlib import Path
from .project_services import project_path

CASE='diag_ticket_isolation'
WORK='development/'+CASE
BASE='hardware/compact-arc1/R10_WORK/closure_p10/'
FIXTURE='tests/fixtures/development/diag_ticket_isolation.c'
SOURCE_NAMES=('arc1_diag.c','arc1_diag.h')

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write_json(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix='.ledger-',dir=path.parent)
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as f:json.dump(data,f,indent=2);f.write('\n')
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)

def descriptor(root):
    data=json.loads(project_path(root,WORK+'/case.json').read_text())
    if data.get('id')!=CASE:raise ValueError('Unsupported development case')
    return data

def prepare(root):
    """Create once, atomically; never overwrite a developer's working copy."""
    root=Path(root).resolve();target=project_path(root,WORK)
    if target.exists():return inspect(root)
    target.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.prepare-',dir=target.parent) as folder:
        staged=Path(folder)/CASE;(staged/'src').mkdir(parents=True)
        baseline={}
        for name in (*SOURCE_NAMES,'test_arc1_diag.c'):
            source=project_path(root,BASE+name);baseline[BASE+name]=digest(source)
            if name in SOURCE_NAMES:shutil.copyfile(source,staged/'src'/name)
        case={'schema':'arc-ledger.development-case/1','id':CASE,'title':'P10 diagnostic ticket isolation',
              'problem':'A foreign, copied or pre-reset ticket can change the wrong diagnostic counters.',
              'scope':'HOST_SIM diagnostic accounting candidate; no hardware deployment',
              'baseline_sha256':baseline,'working_sources':[WORK+'/src/'+n for n in SOURCE_NAMES],
              'regression':FIXTURE,'acceptance':'Reject foreign, copied and pre-reset tickets without changing counters; preserve existing P10 tests.',
              'review':'PENDING','promotion':'NOT_PROMOTED_TO_HARDWARE'}
        write_json(staged/'case.json',case);os.replace(staged,target)
    return inspect(root)

def inputs(root,variant):
    data=descriptor(root)
    for rel,wanted in data['baseline_sha256'].items():
        if digest(project_path(root,rel))!=wanted:raise ValueError('Imported baseline changed: '+rel)
    source_prefix=BASE if variant=='baseline' else WORK+'/src/'
    paths=[source_prefix+n for n in SOURCE_NAMES]+[BASE+'test_arc1_diag.c',FIXTURE]
    return {p:digest(project_path(root,p)) for p in paths}

def inspect(root):
    root=Path(root).resolve();path=project_path(root,WORK+'/case.json')
    if not path.is_file():return {'id':CASE,'prepared':False,'state':'NOT_PREPARED'}
    data=descriptor(root);latest=root/'build/development'/CASE/'latest.json'
    origin='LOCAL_RUN'
    if not latest.is_file():
        latest=root/WORK/'evidence/review_run.json';origin='PACKAGED_REVIEW_RUN'
    result=None
    if latest.is_file():
        try:
            if latest.stat().st_size>1024*1024:raise ValueError('Oversized result')
            result=json.loads(latest.read_text())
            for run in result.get('runs',[]):
                run['fresh']=run.get('inputs_sha256')==inputs(root,run['variant'])
        except (OSError,ValueError,KeyError):result={'state':'UNAVAILABLE_OR_STALE','runs':[]}
    return {'id':CASE,'prepared':True,'case':data,'latest':result,'result_origin':origin,
            'report_path':latest.relative_to(root).as_posix() if latest.is_file() else None,
            'state':('STALE' if result and any(not x.get('fresh') for x in result.get('runs',[])) else (result or {}).get('state','NOT_RUN')),
            'hardware_release':'HOLD','physical_programming':False}

def run(root,mode='compare'):
    if mode not in ('baseline','working','compare'):raise ValueError('Unknown development run mode')
    root=Path(root).resolve();descriptor(root)
    cc=os.environ.get('CC') or shutil.which('gcc') or shutil.which('clang') or shutil.which('cc')
    if not cc:raise ValueError('A host C compiler is required')
    runs=[]
    for variant in (('baseline','working') if mode=='compare' else (mode,)):
        hashes=inputs(root,variant)
        snapshot={p:project_path(root,p).read_bytes() for p in hashes}
        if any(hashlib.sha256(snapshot[p]).hexdigest()!=h for p,h in hashes.items()):
            raise ValueError('Sources changed during capture; run again')
        prefix=BASE if variant=='baseline' else WORK+'/src/'
        checks=[]
        with tempfile.TemporaryDirectory(prefix='arc-ledger-case-') as temp:
            tmp=Path(temp)
            for name in SOURCE_NAMES:(tmp/name).write_bytes(snapshot[prefix+name])
            for name,relative in [('original',BASE+'test_arc1_diag.c'),('regression',FIXTURE)]:
                test=tmp/(name+'.c');test.write_bytes(snapshot[relative])
                exe=tmp/(name+('.exe' if os.name=='nt' else ''))
                argv=[cc,'-std=c11','-O2','-Wall','-Wextra','-Werror','-pedantic',str(tmp/'arc1_diag.c'),str(test),'-o',str(exe)]
                compiled=subprocess.run(argv,capture_output=True,text=True,timeout=12)
                checked=compiled if compiled.returncode else subprocess.run([str(exe)],capture_output=True,text=True,timeout=6)
                # Attribute temporary-snapshot compiler locations to their
                # source documents so the ordinary Problems/F8 workflow works.
                output,error=checked.stdout,checked.stderr
                mapping={str(tmp/n):prefix+n for n in SOURCE_NAMES}
                mapping[str(test)]=relative
                for temporary,original in mapping.items():
                    output=output.replace(temporary,original);error=error.replace(temporary,original)
                checks.append({'name':name,'status':'PASS' if checked.returncode==0 else 'FAIL',
                               'exit_code':checked.returncode,'stage':'compile' if compiled.returncode else 'execute',
                               'stdout':output[:40000],'stderr':error[:40000]})
                print(variant+' '+name+' '+checks[-1]['status'],flush=True)
                print(output+error,end='',flush=True)
        fresh=hashes==inputs(root,variant)
        runs.append({'variant':variant,'status':'PASS' if all(c['status']=='PASS' for c in checks) and fresh else 'FAIL',
                     'fresh':fresh,'inputs_sha256':hashes,'checks':checks})
    passed=all(r['status']=='PASS' for r in runs)
    if mode=='compare':
        baseline,working=runs
        reproduced=all('CASE '+name+' FAIL' in baseline['checks'][1]['stdout'] for name in (
            'foreign_state_rejected_without_accounting','copied_ticket_rejected_without_accounting',
            'pre_reset_ticket_rejected_without_accounting'))
        passed=(baseline['fresh'] and baseline['checks'][0]['status']=='PASS' and baseline['checks'][1]['stage']=='execute'
                and baseline['checks'][1]['status']=='FAIL' and reproduced and working['status']=='PASS')
    result={'schema':'arc-ledger.development-run/1','case_id':CASE,'mode':mode,'created_unix':time.time(),
            'state':'CANDIDATE_PASS' if passed else 'NEEDS_WORK','evidence':'HOST_SIM','runs':runs,
            'compiler':str(cc),'hardware_tested':False,'review':'PENDING','promotion':'NOT_PROMOTED_TO_HARDWARE'}
    dest=root/'build/development'/CASE;dest.mkdir(parents=True,exist_ok=True)
    write_json(dest/('run-'+str(time.time_ns())+'.json'),result);write_json(dest/'latest.json',result)
    return result

def brief(root):
    data=inspect(root)
    if not data['prepared']:raise ValueError('Prepare the development case first')
    case=data['case'];lines=['Graphite development brief',case['title'],case['problem'],
          'Acceptance: '+case['acceptance'],'Evidence: HOST_SIM only. Hardware HOLD; candidate not promoted.',
          'State: '+data['state'],'Editable sources: '+', '.join(case['working_sources'])]
    if data.get('latest'):
        for run in data['latest'].get('runs',[]):
            lines.append(run['variant']+': '+run['status']+(' (source current)' if run.get('fresh') else ' (STALE)'))
            for check in run['checks']:lines.append(check['name']+': '+check['stdout'][-3000:]+check['stderr'][-1500:])
            lines.append('Input SHA-256: '+json.dumps(run['inputs_sha256'],sort_keys=True))
    lines.append('Review the failure and propose a focused source fix. Do not infer board timing or physical success.')
    return '\n'.join(lines)
