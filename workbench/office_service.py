"""Private working-office service and bounded existing-Kernel workers."""
import argparse, json, os, shutil
from pathlib import Path
from sdk.cli.arc1cli import office_tables as tables,office_documents as docs,office_work as core
from sdk.cli.arc1cli.concern_catalog import Catalog
from .session import config_dir
from . import record_io as io,record_access,office_runtime,datasheet_work

ID={'type':'string','pattern':'^owner:[a-f0-9]{32}$'};UUID={'type':'string','pattern':'^[a-f0-9]{32}$'};SHA={'type':'string','pattern':'^[a-f0-9]{64}$'}
PATH={'type':'string','minLength':1,'maxLength':4096};DOC={'type':'object'};BOUND={'id':ID,'expected_revision':SHA};REVIEW={'plan':UUID,'expected_digest':SHA}
FIELDS={
 **datasheet_work.FIELDS,
 'office.list':({},[]),'office.doctor':({},[]),'office.get':({'id':ID},['id']),
 'office.import.preview':({'path':PATH,'parent':{'type':'string','minLength':1,'maxLength':100},'csv':DOC},['path']),
 'office.import.commit':(REVIEW,list(REVIEW)),
 'office.bom.preview':({'path':PATH,'parent':{'type':'string','minLength':1,'maxLength':100}},['path']),
 'office.bom.compare':(BOUND,list(BOUND)),
 'office.save':({**BOUND,'document':DOC},[*BOUND,'document']),
 'office.draft.save':({'id':ID,'writer':UUID,'base_revision':SHA,'document':DOC},['id','writer','base_revision','document']),
 'office.drafts':({'id':ID},['id']),'office.draft.discard':({'id':ID,'writer':UUID},['id','writer']),
 'office.candidate.preview':({**BOUND,'path':PATH,'csv':DOC},[*BOUND,'path']),
 'office.candidate.commit':(REVIEW,list(REVIEW)),
 'office.operation.preview':({**BOUND,'mode':{'type':'string','enum':['export','recalculate','edit']},'format':{'type':'string','enum':['csv','ods','xlsx','docx','pdf']},'sheet':UUID},[*BOUND,'mode','format']),
 'office.operation.run':({**REVIEW,'request_key':{'type':'string','minLength':1,'maxLength':128}},list(REVIEW)),
 'office.operation.result':({'job':UUID},['job']),
 'office.output.copy':({'job':UUID,'file':{'type':'string','minLength':1,'maxLength':100},'expected_sha256':SHA,'destination':PATH},['job','file','expected_sha256','destination']),
 'office.from.notebook':({'notebook':ID,'expected_revision':SHA},['notebook','expected_revision']),
 'office.from.book':({},[])}
READ={'office.list','office.doctor','office.get','office.drafts','office.bom.compare','office.operation.result',
      'office.datasheet.preview'}
SCOPES={op:'read' if op in READ else 'execute' if op=='office.operation.run' else 'approve' for op in FIELDS}
JOB_TOOLS={'references.office.convert','references.office.edit'}
OPTIONS={'type':'object','additionalProperties':False,'properties':REVIEW,'required':list(REVIEW)}
def path():return config_dir()/'concern/catalog.sqlite3'
def store():return core.Office(Catalog(path()))
def source_state(saved,kernel=None,principal=None):
    if saved['origin'].get('profile')==datasheet_work.SHEET and kernel is not None and principal is not None:
        return datasheet_work.sheet_state(kernel,principal,saved['origin'])
    source=saved['origin'].get('source')
    if not source:
        origin=saved['origin'];expected=origin.get('source_revision')
        if expected and kernel is not None and principal is not None:
            try:
                if origin.get('notebook'):
                    current=call(kernel,'notebook.get',{'id':origin['notebook']},principal)
                    state='UNCHANGED_NOTEBOOK_SNAPSHOT' if current['revision']==expected else 'STALE_NOTEBOOK_SNAPSHOT'
                    if state=='UNCHANGED_NOTEBOOK_SNAPSHOT':
                        for ref in origin.get('references',[]):
                            now=call(kernel,'notebook.resolve',{'id':origin['notebook'],'block':ref['block']},principal)
                            if now['state']!=ref['state'] or now['state']=='AVAILABLE' and now['binding']!=ref['reviewed_binding']:state='STALE_NOTEBOOK_REFERENCE';break
                    return {'state':state,'expected_revision':expected,'current_revision':current['revision']}
                if origin.get('profile')=='orange-book-working-derivative-v1':
                    current=call(kernel,'book.contents',{},principal)['input_fingerprint'];return {'state':'UNCHANGED_BOOK_SNAPSHOT' if current==expected else 'STALE_BOOK_SNAPSHOT','expected_revision':expected,'current_revision':current}
            except (ValueError,OSError):return {'state':'DERIVATIVE_SOURCE_UNAVAILABLE','expected_revision':expected}
        return {'state':'WORKING_COPY_OR_DERIVATIVE','source_sha256':expected}

    try:actual=tables.sha(core.read(source['path']));return {'state':'UNCHANGED_ORIGINAL' if actual==source['sha256'] else 'STALE_ORIGINAL','expected_sha256':source['sha256'],'current_sha256':actual}
    except (OSError,ValueError):return {'state':'ORIGINAL_UNAVAILABLE','expected_sha256':source['sha256'],'current_sha256':None}
def get(key,kernel=None,principal=None):
    saved=store().get(key);return {**saved,'source_state':source_state(saved,kernel,principal),'formula_values':'STORED_VALUES_ARE_NOT_RECALCULATION_EVIDENCE'}
def owner(p,execute=False):
    if p.identity!='desktop-owner' or 'read' not in p.scopes or execute and not {'approve','execute'}<=p.scopes:raise ValueError('OFFICE_ACTUAL_OWNER_PROFILE_REQUIRED')
def environment(doc,mode,fmt):
    value={'renderer':None,'docx_writer':None}
    if doc['schema']==docs.SCHEMA:
        try:
            import docx
            value['docx_writer']=docx.__version__
        except ImportError:raise ValueError('OFFICE_DOCX_DEPENDENCY_MISSING: install requirements-office.txt') from None
    if mode in ('edit','recalculate') or fmt in ('xlsx','pdf'):
        value['renderer']=office_runtime.probe()
        if not value['renderer']['available']:raise ValueError('OFFICE_ENGINE_NOT_INSTALLED')
    return value
def authorize_job(kernel,tool,options,p):
    owner(p,True)
    if set(options)!=set(REVIEW):raise ValueError('OFFICE_JOB_OPTIONS')
    plan=store().plan(options['plan'],options['expected_digest'])
    if plan['mode'] not in ('export','recalculate','edit') or (tool.endswith('.edit'))!=(plan['mode']=='edit'):raise ValueError('OFFICE_JOB_PROFILE')
    if store().get(plan['document_id'])['revision']!=plan['expected_revision']:raise ValueError('OFFICE_CHANGED_AFTER_REVIEW')
    if source_state(store().get(plan['document_id']),kernel,p)!=plan['source_state']:raise ValueError('OFFICE_ORIGINAL_CHANGED_AFTER_REVIEW')
    if store().drafts(plan['document_id']):raise ValueError('OFFICE_RECOVERY_REVIEW_REQUIRED')
    if environment(plan['document'],plan['mode'],plan['format'])!=plan['environment']:raise ValueError('OFFICE_ENVIRONMENT_CHANGED_REVIEW_AGAIN')
def call(kernel,op,args,p):
    r=kernel.dispatch(op,args,p)
    if not r['ok']:raise ValueError('OFFICE_UNDERLYING_RECORD_UNAVAILABLE')
    return r['result']
def from_notebook(kernel,a,p):
    n=call(kernel,'notebook.get',{'id':a['notebook']},p)
    if n['revision']!=a['expected_revision']:raise ValueError('OFFICE_NOTEBOOK_CHANGED')
    blocks=[];refs=[]
    for b in n['document']['blocks']:
        blocks.append(docs.paragraph(b['title'],'Heading2'));blocks.append(docs.paragraph(b['body']))
        if b['kind'] in ('text','unsupported'):continue
        value=call(kernel,'notebook.resolve',{'id':n['id'],'block':b['id']},p);record=value.get('record')
        blocks.append(docs.paragraph('Reference '+value['state'].lower()+'. Working prose changes no original or accepted record.'))
        refs.append({'block':b['id'],'target':b['target'],'reviewed_binding':b['binding'],'state':value['state']})
        if isinstance(record,dict):
            if isinstance(record.get('text'),str):blocks.append(docs.paragraph(record['text'][:32768]))
            if isinstance(record.get('rows'),list) and record['rows']:
                rows=record['rows']
                if all(isinstance(r,list) for r in rows):
                    width=max(map(len,rows));blocks.append(docs.table([[str(v) for v in r]+['']*(width-len(r)) for r in rows]))
            blocks.append(docs.paragraph('Reference identity '+tables.canonical({'target':b['target'],'binding':b['binding']})))
    if call(kernel,'notebook.get',{'id':n['id']},p)['revision']!=n['revision']:raise ValueError('OFFICE_NOTEBOOK_CHANGED_DURING_COPY')
    return store().create(docs.document(n['document']['title'],blocks),origin={'profile':'saved-notebook-derivative-v1','notebook':n['id'],'source_revision':n['revision'],'references':refs,'copy_state':'WORKING_DERIVATIVE_NOT_A_SECOND_CURRENT_NOTEBOOK'})
def from_book(kernel,p):
    value=call(kernel,'book.contents',{},p);pages=[]
    if not isinstance(value.get('pages'),list):raise ValueError('OFFICE_BOOK_UNAVAILABLE: the Orange Book belongs to an attached project')
    for item in value['pages']:
        result=call(kernel,'book.read',{'page':item['id']},p)
        if result['input_fingerprint']!=value['input_fingerprint']:raise ValueError('OFFICE_BOOK_CHANGED_DURING_COPY')
        pages.append(result['page'])
    if call(kernel,'book.contents',{},p)['input_fingerprint']!=value['input_fingerprint']:raise ValueError('OFFICE_BOOK_CHANGED_DURING_COPY')
    return store().create(docs.from_pages('The Orange Book working copy',pages),origin={'profile':'orange-book-working-derivative-v1','source_revision':value['input_fingerprint'],'editorial_and_engineering':'SEPARATE_FROM_ACCEPTED_PROJECT_REVISION','physical_qualification':False})
def result(kernel,key,p):
    owner(p);job=record_access.read(kernel,'jobs',key,p)
    if job['tool'] not in JOB_TOOLS or job['owner']!=p.identity:raise ValueError('OFFICE_JOB_UNAVAILABLE')
    if job['state']!='Completed':return {'state':job['state'],'job':key,'error':job.get('error'),'files':[]}
    folder=kernel.state/'jobs'/core.uid(key);value=io.strict_json(core.read(folder/'office_result.json',4*1024*1024))
    if value['job']!=key:raise ValueError('OFFICE_RESULT_JOB_BINDING')
    for row in value['files']:
        if Path(row['name']).name!=row['name'] or tables.sha(core.read(folder/row['name'],32*1024*1024))!=row['sha256']:raise ValueError('OFFICE_OUTPUT_CHANGED')
    saved=store().get(value['document_id']);current=saved['revision']==value['source_revision'] and source_state(saved,kernel,p)==value['source_state']
    return {**value,'state':'AVAILABLE' if current else 'HISTORICAL_INPUTS_CHANGED','directory':str(folder),'engineering_acceptance':False}
def copy_output(kernel,a,p):
    v=result(kernel,a['job'],p);r=next((r for r in v['files'] if r['name']==a['file']),None)
    if not r or r['sha256']!=a['expected_sha256']:raise ValueError('OFFICE_REVIEWED_OUTPUT_REQUIRED')
    raw=core.read(Path(v['directory'])/r['name'],32*1024*1024);target=Path(a['destination']).absolute()
    if target.suffix.lower()!=Path(r['name']).suffix.lower() or any(q.is_symlink() for q in (target,*target.parents)):raise ValueError('OFFICE_OUTPUT_DESTINATION')
    fd=os.open(target,os.O_CREAT|os.O_EXCL|os.O_WRONLY|getattr(os,'O_NOFOLLOW',0),0o600)
    try:
        with os.fdopen(fd,'wb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
    except BaseException:target.unlink(missing_ok=True);raise
    return {'state':'COPIED_NEW_FILE','path':str(target),'sha256':tables.sha(raw),'source_revision':v['source_revision'],'currency':v['state']}
def dispatch(kernel,op,a,p):
    owner(p,op=='office.operation.run')
    if op in datasheet_work.FIELDS:return datasheet_work.dispatch(kernel,op,a,p)
    n=store()
    if op=='office.list':return {'documents':n.listing()}
    if op=='office.doctor':
        try:
            import docx
            writer='python-docx '+docx.__version__
        except ImportError:writer='NOT_INSTALLED: requirements-office.txt'
        return {'renderer':office_runtime.probe(),'docx_writer':writer,'table_reader':'PYTHON_STANDARD_LIBRARY_INERT_PROFILES','external_editor_host':'ACTUAL_OWNER_DISPLAY_QUALIFICATION_OPEN'}
    if op=='office.get':return get(a['id'],kernel,p)
    if op in ('office.import.preview','office.bom.preview'):return n.preview_import(a['path'],a.get('parent','library'),a.get('csv'),op=='office.bom.preview')
    if op in ('office.import.commit','office.candidate.commit'):
        expected='import' if op=='office.import.commit' else 'candidate'
        if n.plan(a['plan'],a['expected_digest'])['mode']!=expected:raise ValueError('OFFICE_COMMIT_REVIEW_PROFILE_MISMATCH')
        return n.commit(a['plan'],a['expected_digest'])
    if op=='office.save':return n.save(a['id'],a['expected_revision'],a['document'])
    if op=='office.draft.save':return n.draft(a['id'],a['writer'],a['base_revision'],a['document'])
    if op=='office.drafts':return {'drafts':n.drafts(a['id'])}
    if op=='office.draft.discard':return n.discard(a['id'],a['writer'])
    if op=='office.candidate.preview':return n.preview_candidate(a['id'],a['expected_revision'],a['path'],a.get('csv'))
    if op=='office.bom.compare':
        saved=n.get(a['id'])
        if saved['revision']!=a['expected_revision']:raise ValueError('OFFICE_CHANGED_KEEP_DRAFT_AND_REVIEW')
        components=saved['origin'].get('components')
        if components is None:raise ValueError('OFFICE_BOM_NATIVE_COMPONENT_BINDING_REQUIRED')
        state=source_state(saved,kernel,p)
        if state['state']!='UNCHANGED_ORIGINAL':return {'state':'SOURCE_UNAVAILABLE_OR_CHANGED','source_state':state,'changes':[],'link_state':'NOT_CURRENT'}
        return tables.compare_bom(tables.bom_document('Original native BOM',components),saved['document'],components,saved['origin']['source']['sha256'])
    if op=='office.operation.preview':
        saved=n.get(a['id']);plan=n.operation(a['id'],a['expected_revision'],a['mode'],a['format'],a.get('sheet'),source_state(saved,kernel,p),environment(saved['document'],a['mode'],a['format']))
        if a['mode']=='recalculate' and any('UNSUPPORTED_FORMULA' in r['reason'] for r in plan['losses']):raise ValueError('OFFICE_RECALC_UNSUPPORTED_FORMULAS_REVIEW_DEFINITION')
        return plan
    if op=='office.operation.run':
        plan=n.plan(a['plan'],a['expected_digest']);tool='references.office.edit' if plan['mode']=='edit' else 'references.office.convert';options={'plan':plan['id'],'expected_digest':a['expected_digest']}
        if plan['result'] and plan['result'].get('state')=='OPERATION_COMPLETED':
            prior=record_access.read(kernel,'jobs',plan['result']['job'],p)
            if prior['tool']!=tool or prior['request_spec'].get('office')!=options:raise ValueError('OFFICE_RECEIPT_JOB_BINDING')
            return prior
        authorize_job(kernel,tool,options,p)
        n.reserve(plan['id'],a['expected_digest'])
        return kernel.submit({'tool':tool,'office':options,'request_key':'office:'+plan['id'],'timeout':550 if plan['mode']=='edit' else 200},p)
    if op=='office.operation.result':return result(kernel,a['job'],p)
    if op=='office.output.copy':return copy_output(kernel,a,p)
    if op=='office.from.notebook':return from_notebook(kernel,a,p)
    if op=='office.from.book':return from_book(kernel,p)
    raise ValueError('OFFICE_OPERATION_UNAVAILABLE')
def work(kernel,key):
    job=kernel.record('jobs',key);options=job['request_spec']['office'];n=store();plan=n.plan(options['plan'],options['expected_digest'])
    from .engineering_kernel import Principal
    worker_principal=Principal(job['owner'],frozenset({'read','approve','execute'}))
    authorize_job(kernel,job['tool'],options,worker_principal);folder=kernel.state/'jobs'/key;folder.mkdir(mode=0o700,parents=True,exist_ok=True)
    stage=folder/'office-stage';stage.mkdir(mode=0o700);inputs=stage/'input';inputs.mkdir(mode=0o700);doc=plan['document'];table=doc['schema']==tables.SCHEMA;fmt=plan['format'];losses=list(plan['losses']);measurement=[];runtime=None;roundtrip_changes=[]
    if table:
        if fmt=='csv' and plan['mode']=='export':raw,extra=tables.csv_bytes(doc,plan['sheet_id']);target=folder/'Working_table.csv';target.write_bytes(raw);losses+=extra
        else:
            raw,extra=tables.ods_bytes(doc);source=inputs/'Working_table.ods';source.write_bytes(raw);losses+=extra
            if plan['mode']=='recalculate' or fmt=='xlsx':
                converted,runtime=office_runtime.convert(source,stage/'output','ods' if plan['mode']=='recalculate' else 'xlsx','table');target=folder/('Recalculated.ods' if plan['mode']=='recalculate' else 'Working_table.xlsx');shutil.copyfile(converted,target)
                observed=tables.parse(target.read_bytes(),target.name)['document'];expected,_=tables.projection(doc);roundtrip_changes=tables.check_roundtrip(expected,observed)
                if plan['mode']=='recalculate':
                    by_name={s['name']:s for s in observed['sheets']}
                    for sheet in doc['sheets']:
                        for loc,c in sheet['cells'].items():
                            if c['formula'] is None:continue
                            now=by_name.get(sheet['name'],{}).get('cells',{}).get(loc)
                            if now is None or now['formula'] is None or tables.clean_formula(now)!=tables.clean_formula(c):raise ValueError('OFFICE_RECALC_FORMULA_IDENTITY_CHANGED')
                            measurement.append({'sheet_id':sheet['id'],'sheet':sheet['name'],'cell':loc,'formula':c['formula'],'stored_type':c['type'],'stored_value':c['value'],'measured_type':now['type'],'measured_value':now['value'],'state':'FORMULA_ERROR' if now['type']=='error' else 'RESULT_UNAVAILABLE' if now['type']=='blank' else 'MEASURED_BY_ACTUAL_OFFICE_ENGINE','engine':runtime['engine']['version']})
                    losses.append({'path':'calculation','reason':'ACTUAL_CALC_ENGINE_FLOATING_POINT_PRECISION_PROFILE_NOT_EXACT_DECIMAL_ARITHMETIC'})
            else:target=folder/'Working_table.ods';target.write_bytes(raw)
    else:
        origin=plan['origin'];provenance={'working_revision':plan['expected_revision'],'profile':origin['profile'],'original_name':origin.get('source',{}).get('name'),'original_sha256':origin.get('source',{}).get('sha256'),'source_revision':origin.get('source_revision'),'source_state':plan['source_state'],'engineering_acceptance':False}
        raw,runtime=docs.docx_bytes(doc,{k:v for k,v in provenance.items() if v is not None});source=inputs/'Working_document.docx';source.write_bytes(raw)
        if fmt=='pdf':converted,renderer=office_runtime.convert(source,stage/'output','pdf');runtime={**runtime,'render':renderer};target=folder/'Working_document.pdf';shutil.copyfile(converted,target)
        else:target=folder/'Working_document.docx';target.write_bytes(raw)
    # A headless conversion is never a commit of the current working document.
    saved=n.get(plan['document_id'])
    if saved['revision']!=plan['expected_revision'] or source_state(saved,kernel,worker_principal)!=plan['source_state']:raise ValueError('OFFICE_INPUTS_CHANGED_DURING_OPERATION')
    value={'schema':'arc.office-operation-result/1','job':key,'document_id':plan['document_id'],'source_revision':plan['expected_revision'],'source_state':plan['source_state'],'mode':plan['mode'],'format':fmt,'input_model_sha256':tables.sha(doc),'input_original_sha256':plan['origin'].get('source',{}).get('sha256'),'runtime':runtime,'reviewed_environment':plan['environment'],'candidate_state':'READY_FOR_DESKTOP_EDITOR' if plan['mode']=='edit' else None,'losses':list({tables.canonical(r):r for r in losses}.values()),'roundtrip_changes':roundtrip_changes,'measurement':measurement,'files':[{'name':target.name,'bytes':target.stat().st_size,'sha256':tables.sha(target.read_bytes())}],'saved_working_copy_changed':False,'accepted_facts_created':0,'physical_qualification':False,'outcome':'PASS'}
    n.finish(plan['id'],options['expected_digest'],{'state':'OPERATION_COMPLETED','job':key,'files':value['files']});io.write_json(folder/'office_result.json',value);print(json.dumps({'outcome':'PASS','files':len(value['files']),'measured_formula_cells':len(measurement)}))
def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--job',required=True);a=p.parse_args()
    from .engineering_kernel import Kernel
    work(Kernel(a.root),core.uid(a.job))
if __name__=='__main__':main()
