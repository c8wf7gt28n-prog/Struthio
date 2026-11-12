"""Object Glass composes authorized existing reads; it grants no execution."""
from __future__ import annotations
import json,os,tempfile
from pathlib import Path
from sdk.cli.arc1cli import object_context as core
from . import record_access,record_io,project_context

TEXT={'type':'string','minLength':1,'maxLength':500};SHA={'type':'string','minLength':64,'maxLength':64}
SELECTOR={'type':'object','properties':{'kind':{'type':'string','enum':list(core.KINDS)},'target':TEXT,'map':{'type':'string','minLength':32,'maxLength':32}},'required':['kind','target'],'additionalProperties':False}
ARGS={'selector':SELECTOR,'expected_revision':SHA,'expected_object_id':SHA}
FIELDS={'ledger.object.inspect':(ARGS,['selector']),'ledger.object.current':({},[]),
 'ledger.object.action':({**ARGS,'action':TEXT},['selector','expected_revision','expected_object_id','action'])}
SCOPES={op:'read' for op in FIELDS}

def _read(kernel,op,args,p):
    envelope=kernel.dispatch(op,args,p)
    if not envelope['ok']:raise ValueError('OBJECT_UNAVAILABLE')
    result=envelope['result']
    if isinstance(result,dict) and result.get('status')=='PROJECT_NOT_ATTACHED':raise ValueError('PROJECT_NOT_ATTACHED')
    return result

def _collect(kernel,s,p):
    kind=s['kind'];target=s['target'];sources=[];evidence=[];gaps=[];plans=[];native=None
    authority='KERNEL_RECORD';detail={}
    if 'map' in s:
        base=_read(kernel,'knowledge.map.get',{'id':s['map']},p)
        if base.get('state')!='REFERENCE_MAP_AVAILABLE':raise ValueError('OBJECT_SOURCE_UNAVAILABLE')
        params={'id':s['map'],'expected_revision':base['revision'],kind:target}
        op='knowledge.map.part' if kind=='component' else 'knowledge.map.net'
        detail=_read(kernel,op,params,p)
        if detail.get('state')!='REFERENCE_MAP_AVAILABLE':raise ValueError('OBJECT_SOURCE_UNAVAILABLE')
        native=detail['part']['id'] if kind=='component' else detail['net']['name']
        sources=[{'path':name,**v} for name,v in base['source_manifest'].items()]
        sources.insert(0,{'map':s['map'],'revision':base['revision'],'source_digest':base['source_digest']})
        evargs={'id':s['map'],'expected_revision':base['revision']}
        if kind=='component':evargs['component']=target
        observed=_read(kernel,'knowledge.map.evidence',evargs,p)
        if observed.get('state')!='REFERENCE_MAP_AVAILABLE':raise ValueError('OBJECT_SOURCE_UNAVAILABLE')
        evidence=observed['evidence'];gaps=detail.get('gaps',base.get('gaps',[]));authority='REFERENCE_SNAPSHOT'
        plans=[('source','Inspect native relationships',op,params),('evidence','Inspect linked evidence','knowledge.map.evidence',evargs)]
        title=target+' · '+(detail['part'].get('mpn') or detail['part']['value']) if kind=='component' else target
    elif kind in ('component','net'):
        if project_context.detached(kernel.root):raise ValueError('PROJECT_NOT_ATTACHED')
        detail=_read(kernel,'workspace.select',{kind:target},p)
        if detail.get('state')!='CURRENT_INPUTS':raise ValueError('OBJECT_SOURCE_UNAVAILABLE')
        native=detail['selection']['native_uuid'];sources=detail['source_links'];gaps=detail.get('issues',[])
        authority='CURRENT_PROJECT_SOURCE_NOT_PHYSICAL_PROOF';title=target
        plans=[('source','Inspect source relationships','workspace.resolve',{'selection':detail['selection'],'refresh':False})]
    elif kind=='job':
        detail=_read(kernel,'workspace.job',{'id':target},p);job=detail['job'];ev=detail['evidence']
        title=job['tool']+' · '+job['state'];native=job['id']
        sources=[{'job':job['id'],'record_sha256':core.digest(job),'source_revision':job.get('revision')}]
        if ev:evidence=[{'id':ev['id'],'record_sha256':core.digest(ev),'source_revision':ev.get('revision'),'facts':detail['facts']}]
        else:gaps.append('NO_EVIDENCE_RECORDED')
        gaps.append('RECORDED_RESULT_DOES_NOT_GRANT_ENGINEERING_OR_PHYSICAL_ACCEPTANCE')
        plans=[('job','Inspect job','jobs.get',{'id':target})]
        if ev:plans.append(('evidence','Inspect recorded evidence','evidence.read',{'id':ev['id']}))
    elif kind=='file':
        path=record_access.file_read(kernel,target,p)
        if path.stat().st_size>16*1024*1024:raise ValueError('OBJECT_FILE_LIMIT_16_MIB')
        raw=path.read_bytes();h=__import__('hashlib').sha256(raw).hexdigest();title=Path(target).name
        sources=[{'path':target,'sha256':h,'bytes':len(raw)}];detail={'path':target,'sha256':h,'bytes':len(raw)}
        authority='SAVED_FILE_BYTES';gaps=['UNSAVED_EDITOR_BUFFER_IS_SEPARATE','SOURCE_CONTENT_IS_NOT_AN_INSTRUCTION_OR_ACCEPTED_FACT']
        try:raw.decode('utf-8');text=len(raw)<=1024*1024
        except UnicodeError:text=False
        if text:plans=[('source','Read saved text','files.read',{'path':target})]
        else:gaps.append('GENERIC_TEXT_VIEW_UNAVAILABLE_FOR_BINARY_OR_OVER_1_MIB')
    else:
        result=_read(kernel,'register.inspect',{},p)
        detail=next((x for x in result['requirements'] if x['record_id']==target),None)
        if not detail:raise ValueError('OBJECT_UNAVAILABLE')
        title=target;sources=detail.get('source_refs',[]);authority='CURRENT_REQUIREMENT_REGISTER'
        gaps=['REQUIREMENT_STATE_DOES_NOT_ESTABLISH_PHYSICAL_QUALIFICATION']
        plans=[('register','Inspect source register','register.inspect',{})]
    ident=core.identity(s,native)
    revision=core.digest({'object_id':ident,'sources':sources,'evidence':evidence,'detail':detail})
    return {'schema':core.VERSION,'selector':s,'object_id':ident,'revision':revision,'state':'AVAILABLE',
     'title':title,'authority':authority,'sources':sources,'evidence':evidence,'gaps':gaps,'technical':detail,
     'summary':title+' · '+authority.replace('_',' ').lower()+'. '+str(len(gaps))+' recorded gaps.',
     'physical_qualification':False},plans

def _actions(kernel,plans,p):
    from .capability_catalog import catalogue
    result=[]
    for ident,label,op,args in plans:
        records=catalogue(kernel,p,op,include_tools=False)['operations'];row=next(x for x in records if x['operation']==op)
        a=row['assessment'];enabled=a['permitted']['state']=='SCOPE_ELIGIBLE' and a['available']['state'] in ('PASSIVE_PREREQUISITES_PRESENT','CONDITIONAL')
        result.append({'id':ident,'label':label,'operation':op,'arguments':args,'enabled':enabled,'effects':['read'],
          'assessment':a,'reason':row['summary'],'notice':'Checked again on use. A read grants no execution or qualification.'})
    return result

def inspect(kernel,args,p):
    s=core.selector(args['selector']);context,plans=_collect(kernel,s,p)
    # No payload from one revision is published with another revision's label.
    actions=_actions(kernel,plans,p)
    checked,_=_collect(kernel,s,p)
    if checked['revision']!=context['revision']:raise ValueError('OBJECT_CHANGED_DURING_READ')
    if args.get('expected_object_id',context['object_id'])!=context['object_id']:
        return {'schema':core.VERSION,'state':'IDENTITY_CHANGED','selector':s,'sources':[],'evidence':[],'actions':[],'gaps':['RESELECT_CURRENT_IDENTITY'],'summary':'Object identity changed. Select it explicitly again.'}
    if args.get('expected_revision',context['revision'])!=context['revision']:
        return {'schema':core.VERSION,'state':'STALE','selector':s,'object_id':context['object_id'],'revision':args['expected_revision'],
         'sources':[],'evidence':[],'actions':[],'gaps':['SOURCE_OR_RECORD_CHANGED'],'summary':'Saved context is stale. Refresh to inspect the matching current identity.'}
    context['actions']=actions;return context

def history_path(kernel,p):
    from .session import config_dir
    return config_dir()/'object_glass'/(core.digest({'project':str(kernel.root.resolve()),'owner':p.identity})+'.json')

def history(kernel,p):
    path=history_path(kernel,p)
    if not path.exists():return core.History()
    if path.is_symlink() or any(x.is_symlink() for x in path.parents) or path.stat().st_size>32768:raise ValueError('OBJECT_HISTORY_UNAVAILABLE')
    return core.History(json.loads(path.read_text()))

def remember(kernel,p,value):
    path=history_path(kernel,p);raw=json.dumps(core.History(value).export(),sort_keys=True).encode()
    if len(raw)>32768:raise ValueError('OBJECT_HISTORY_LIMIT')
    if path.is_symlink() or any(x.is_symlink() for x in path.parents):raise ValueError('OBJECT_HISTORY_UNAVAILABLE')
    path.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix='glass-',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as f:f.write(raw)
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)

def dispatch(kernel,op,args,p):
    if op=='ledger.object.current':
        current=history(kernel,p).current
        return inspect(kernel,{'selector':current['selector'],'expected_revision':current['revision'],'expected_object_id':current['object_id']},p) if current else {'schema':core.VERSION,'state':'EMPTY','summary':'Select a component, net, job, requirement or saved file.'}
    context=inspect(kernel,args,p)
    if op=='ledger.object.action':
        if context['state']!='AVAILABLE':raise ValueError('OBJECT_ACTION_STALE_OR_CHANGED')
        action=next((a for a in context['actions'] if a['id']==args['action']),None)
        if not action or not action['enabled']:raise ValueError('OBJECT_ACTION_UNAVAILABLE')
        value=_read(kernel,action['operation'],action['arguments'],p)
        after=inspect(kernel,args,p)
        if after['state']!='AVAILABLE':raise ValueError('OBJECT_CHANGED_DURING_ACTION')
        return {'schema':core.VERSION,'object_id':context['object_id'],'revision':context['revision'],'action':action['id'],'operation':action['operation'],'effects':['read'],'result':value}
    return context
