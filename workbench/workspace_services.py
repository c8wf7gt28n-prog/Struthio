"""Read-only shared selection/search over the existing Kernel adapters."""
from sdk.cli.arc1cli import selection_context as context
from . import brain_link,record_io as io,project_inventory,vendor_adapter,database_rom

S={'type':'string','maxLength':600}
FIELDS={
 'workspace.job':({'id':{'type':'string','minLength':32,'maxLength':32}},['id']),
 'workspace.search':({'query':{'type':'string','maxLength':200},'limit':{'type':'integer','minimum':1,'maximum':100}},['query']),
 'workspace.select':({'component':S,'net':S,'expected_uuid':S,'expected_native_revision':S},[]),
 'workspace.resolve':({'selection':{'type':'object'},'refresh':{'type':'boolean'}},['selection']),
}


def manifest(root,names):
    return {name:{'sha256':row['sha256'],'bytes':row['bytes']} for name,row in io.manifest(root,names).items()}


def selected(kernel,kind,reference):
    root=kernel.root;graph,native_inputs,native_revision=brain_link.bound(root)
    if kind=='component':
        if reference not in graph.components:raise ValueError('UNKNOWN_NATIVE_COMPONENT')
        data=brain_link.dispatch(kernel,'links.inspect',{'component':reference})
        uuid=data['component']['native_uuid'];links=data['source_links'];pins=data['component']['pins']
    else:
        if reference not in graph.nets:raise ValueError('UNKNOWN_NATIVE_NET')
        net=graph.nets[reference];pins=net['pins']
        uuid='net:'+context.digest([[p['reference'],graph.components[p['reference']]['native_uuid'],p['pin']] for p in pins])
        links=[{'kind':'native_netlist','path':brain_link.NETLIST,'locator':reference,
            'available':True,'sha256':native_inputs[brain_link.NETLIST]['sha256']}]
        data={'net':net,'source_links':links,'requirements':[],'issues':[],
            'layers':[{'id':key,'label':label,'state':state} for key,label,state in [
                ('schematic','Native net membership','SOURCE_BOUND'),('copper','Routed copper','NOT_VERIFIED'),
                ('airwire','Unrouted airwire','NOT_COMPUTED_FROM_NETLIST'),('intent','Software intent','NOT_BOUND'),
                ('model','Model event','NO_TRACE_SELECTED'),('physical','Physical measurement','UNAVAILABLE')]]}
    names=set(native_inputs)|{r['path'] for r in links}|{'workbench/workspace_services.py','workbench/cad_export.py','sdk/cli/arc1cli/selection_context.py'}
    if (root/'project/brain_link_export.json').is_file():names.add('project/brain_link_export.json')
    binding=manifest(root,names);selection=context.make(kind,reference,uuid,binding)
    terminals=[]
    for pin in pins:
        name=pin['net'];net=graph.nets[name]
        members=[{'reference':p['reference'],'native_uuid':graph.components[p['reference']]['native_uuid'],'pin':p['pin']} for p in net['pins']]
        terminals.append({'pin':pin['pin'],'net':name,'members':members[:50],'member_count':len(members),
            'relation':'NATIVE_NET_MEMBERSHIP','physical_activity':False})
    from .cad_export import status as export_status
    export=export_status(root)
    return {**data,'selection':selection,'state':'CURRENT_INPUTS','native_revision':native_revision,
        'export_binding':export,'terminals':terminals,'physical_measurements':False,
        'currentness_scope':'The saved identities and bytes; electrical operation remains separate.',
        'knowledge_query':('USB' if kind=='component' and 'USB' in data['component']['value'].upper() else reference)}


def resolve(kernel,value,refresh=False):
    old=context.clean(value)
    try:new=selected(kernel,old['kind'],old['reference'])
    except ValueError as exc:
        if 'UNKNOWN_NATIVE_' not in str(exc):raise
        return {'state':'IDENTITY_CHANGED','selection':old,'source_links':[],'terminals':[],
            'message':'The native object is absent; select a current object explicitly.'}
    state=context.currency(old,new['selection']['source_manifest'],new['selection']['native_uuid'])
    if state=='IDENTITY_CHANGED' or (state=='STALE' and not refresh):
        return {'state':state,'selection':old,'current_revision':new['selection']['revision'],
            'source_links':[],'terminals':[],'message':'Inputs changed; refresh a matching native identity before cross-probing.',
            'changed':[name for name,row in new['selection']['source_manifest'].items() if old['source_manifest'].get(name)!=row]}
    return new


def search(kernel,query,limit,principal=None):
    from .engineering_kernel import Principal
    from . import record_access
    principal=principal or Principal('anonymous')
    root=kernel.root;q=query.strip().casefold();rows=[];unavailable=[]
    def add(kind,title,source,currentness,**values):
        rows.append({'kind':kind,'title':title,'source':source,'currentness':currentness,**values})
    try:
        graph,inputs,revision=brain_link.bound(root)
        from .cad_export import status as export_status
        native_currency=export_status(root)['state']
        for ref,c in graph.components.items():
            if q and q not in (ref+' '+c['value']).casefold():continue
            add('component',ref+' · '+c['value'],brain_link.NETLIST,native_currency,reference=ref,native_uuid=c['native_uuid'],native_revision=revision)
        for name,net in graph.nets.items():
            if not q or q not in name.casefold():continue
            add('net',name,brain_link.NETLIST,native_currency,reference=name,native_revision=revision)
    except (OSError,ValueError) as exc:unavailable.append({'kind':'native','reason':str(exc)})
    if q:
        for path in project_inventory.paths(root):
            rel=path.relative_to(root).as_posix()
            if q in rel.casefold():add('file',rel,rel,'HASHED_CURRENT_FILE',path=rel,sha256=io.sha(path))
    from .engineering_kernel import TOOLS
    for name,(module,*argv) in TOOLS.items():
        if not q or q in (name+' '+module).casefold():
            add('command',name,module,'REGISTERED',tool=name,execution='Open controls; selection never runs a job')
    for job in record_access.listing(kernel,'jobs',principal):
        if q and q not in (job['id']+' '+job['tool']+' '+job.get('goal','')).casefold():continue
        add('job',job['tool']+' · '+job['state'],'Kernel job '+job['id'],'RECORDED',job_id=job['id'])
    if q:
        try:
            hits=vendor_adapter.dispatch(kernel,'vendor.search',{'query':query,'limit':15})['hits']
            for hit in hits:
                add('vendor',hit.get('title') or hit.get('document_id','')+' · page '+str(hit.get('page_index',0)+1),
                    'Vendor original '+hit.get('source_sha256',''),hit.get('source_state','UNASSESSED'),hit=hit)
        except (ValueError,OSError) as exc:unavailable.append({'kind':'vendor','reason':str(exc)})
        except Exception as exc:unavailable.append({'kind':'vendor','reason':type(exc).__name__+': '+str(exc)})
        try:
            result=database_rom.dispatch(kernel,'records.search',{'query':query,'limit':15})
            for hit in result['hits']:add('record',hit.get('title',hit.get('record_id','Sealed record')),'Database ROM','SEALED_RECORD',hit=hit)
        except (ValueError,OSError) as exc:unavailable.append({'kind':'record','reason':str(exc)})
        except Exception as exc:unavailable.append({'kind':'record','reason':type(exc).__name__+': '+str(exc)})
    def rank(row):
        title=row['title'].casefold();ref=row.get('reference','').casefold()
        return (0 if q==ref else 1 if title.startswith(q) else 2,row['kind'],title)
    rows.sort(key=rank)
    return {'schema':'arc.workspace-search/1','query':query,'results':rows[:limit],
        'total':len(rows),'truncated':len(rows)>limit,'unavailable':unavailable,'executes':False}


def dispatch(kernel,op,args,principal=None):
    from .engineering_kernel import Principal
    from . import record_access
    principal=principal or Principal('anonymous')
    if op=='workspace.job':
        from sdk.cli.arc1cli.job_evidence import describe
        job=record_access.read(kernel,'jobs',args['id'],principal);e=record_access.read(kernel,'evidence',job['evidence'],principal) if job.get('evidence') else None
        candidate=kernel.record('candidates',job['candidate']) if job.get('candidate') else None
        root=kernel.candidate_root(candidate['id']) if candidate else kernel.root
        current=e.get('input_hashes')==project_inventory.hashes(root) if e else None
        facts=describe(job,e,current=current,review=candidate['state'] if candidate else 'NOT_SUBMITTED')
        if candidate:facts['accepted_base']='CURRENT_INPUTS' if candidate['base']==project_inventory.hashes(kernel.root) else 'STALE'
        return {'job':job,'evidence':e,'facts':facts}
    if op=='workspace.search':return search(kernel,args['query'],args.get('limit',60),principal)
    if op=='workspace.resolve':return resolve(kernel,args['selection'],args.get('refresh',False))
    if bool(args.get('component'))==bool(args.get('net')):raise ValueError('Select exactly one native component or net')
    result=selected(kernel,'component' if args.get('component') else 'net',args.get('component') or args['net'])
    if (args.get('expected_uuid') and args['expected_uuid']!=result['selection']['native_uuid']) or (args.get('expected_native_revision') and args['expected_native_revision']!=result['native_revision']):
        return {'state':'STALE','message':'Search identity changed; search again before opening.','source_links':[],'terminals':[]}
    return result
