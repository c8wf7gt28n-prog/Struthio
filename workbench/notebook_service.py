"""Checked notebook references use actual caller reads; prose cannot write them."""
import csv, io, os, stat
from pathlib import Path
from sdk.cli.arc1cli import notebook as core
from sdk.cli.arc1cli.concern_catalog import Catalog
from .session import config_dir
from . import record_access

ID={'type':'string','pattern':'^owner:[a-f0-9]{32}$'}
UUID={'type':'string','pattern':'^[a-f0-9]{32}$'}
SHA={'type':'string','pattern':'^[a-f0-9]{64}$'}
PATH={'type':'string','minLength':1,'maxLength':4096}
DOC={'type':'object'};NB={'id':ID};BOUND={**NB,'expected_revision':SHA}
FIELDS={
 'notebook.list':({},[]),
 'notebook.create':({'title':{'type':'string','minLength':1,'maxLength':240},'parent':{'type':'string','minLength':1,'maxLength':100}},['title']),
 'notebook.get':(NB,['id']),
 'notebook.original':(NB,['id']),
 'notebook.save':({**BOUND,'document':DOC},[*BOUND,'document']),
 'notebook.draft.save':({**NB,'writer':UUID,'base_revision':SHA,'document':DOC},['id','writer','base_revision','document']),
 'notebook.drafts':(NB,['id']),
 'notebook.draft.discard':({**NB,'writer':UUID},['id','writer']),
 'notebook.reference.preview':({'kind':{'type':'string','enum':list(core.KINDS[1:-1])},'target':DOC},['kind','target']),
 'notebook.resolve':({**NB,'block':ID},['id','block']),
 'notebook.query.run':({**BOUND,'block':ID},[*BOUND,'block']),
 'notebook.import.preview':({'path':PATH,'parent':{'type':'string','minLength':1,'maxLength':100}},['path']),
 'notebook.import.commit':({'plan':UUID,'expected_digest':SHA},['plan','expected_digest'])}
READS={'notebook.list','notebook.get','notebook.original','notebook.drafts','notebook.resolve','notebook.query.run'}
SCOPES={op:'read' if op in READS else 'approve' for op in FIELDS}
def path():return config_dir()/'concern/catalog.sqlite3'
def store():return core.Notebook(Catalog(path()))
def call(kernel,op,args,p):
    r=kernel.dispatch(op,args,p)
    if not r['ok']:raise ValueError('NOTEBOOK_REFERENCE_UNAVAILABLE')
    value=r['result']
    if isinstance(value,dict) and value.get('status')=='PROJECT_NOT_ATTACHED':raise ValueError('NOTEBOOK_PROJECT_NOT_ATTACHED')
    return value
def bounded_file(path_value,maximum):
    p=Path(path_value).absolute()
    if any(x.is_symlink() for x in (p,*p.parents)):raise ValueError('NOTEBOOK_SOURCE_SYMLINK')
    fd=os.open(p,os.O_RDONLY|getattr(os,'O_NOFOLLOW',0)|getattr(os,'O_NONBLOCK',0))
    try:
        s=os.fstat(fd)
        if not stat.S_ISREG(s.st_mode) or s.st_size>maximum:raise ValueError('NOTEBOOK_SOURCE_SIZE_OR_TYPE')
        with os.fdopen(fd,'rb',closefd=False) as f:raw=f.read(maximum+1)
        if len(raw)!=s.st_size or len(raw)>maximum:raise ValueError('NOTEBOOK_SOURCE_CHANGED')
        return raw
    finally:os.close(fd)
def snapshot(kernel,kind,t,p,notebooks):
    core.target(kind,t);typ=t['type']
    if kind=='query':return {'authority':'SAVED_READ_ONLY_QUERY_DEFINITION','definition':t,'query_id':core.digest(t),'executed':False}
    if typ=='catalog':
        row=notebooks.catalog.get(t['object_id'])
        return {'id':row['id'],'title':row['title'],'summary':row['summary'],'version':row['version'],'note':row['note'],'state':row['state'],
            'authority':'WORKING_REQUIREMENT_NOTE' if kind=='requirement' else 'SAVED_CONCERN_NOTE','accepted_requirement':False}
    if typ=='office':
        from sdk.cli.arc1cli import office_tables as tables
        value=call(kernel,'office.get',{'id':t['object_id']},p);doc=value['document']
        if doc['schema']!=tables.SCHEMA:raise ValueError('NOTEBOOK_OFFICE_WORKBOOK_REQUIRED')
        sheet=next((s for s in doc['sheets'] if s['id']==t['sheet']),None)
        if sheet is None:raise ValueError('NOTEBOOK_OFFICE_SHEET_UNAVAILABLE')
        cells={a:c for a,c in sheet['cells'].items() if tables.xy(a)[0]<=100 and tables.xy(a)[1]<=32};rows=[]
        end=max((tables.xy(a)[0] for a in cells),default=0);columns=max((tables.xy(a)[1] for a in cells),default=0)
        for r in range(1,end+1):
            row=[]
            for c in range(1,columns+1):
                v=cells.get(tables.address(r,c));row.append('' if v is None else v['formula'] if v['formula'] is not None else v['value'])
            rows.append(row)
        return {'id':value['id'],'revision':value['revision'],'title':doc['title'],'sheet':sheet['name'],'sheet_id':sheet['id'],'rows':rows,'typed_cells':cells,'source_state':value['source_state'],'preview_truncated':len(cells)!=len(sheet['cells']),'formula_state':'DEFINITIONS_AND_STORED_CACHES_NOT_RECALCULATION_EVIDENCE','authority':'OWNER_WORKING_OFFICE_TABLE','engineering_acceptance':False}
    if typ=='register':
        value=call(kernel,'register.record',{'record_id':t['record_id']},p)
        return {'record':value['record'],'authority':'EXISTING_ENGINEERING_REGISTER','notice':'Referencing changes no acceptance state'}
    if typ=='intake':
        value=call(kernel,'intake.read',{'id':t['item']},p)
        return {**value,'authority':'ADMITTED_ORIGINAL_REFERENCE_NOT_ENGINEERING_ACCEPTANCE'}
    if typ in ('file','csv'):
        name=t['path'];source=record_access.file_read(kernel,name,p);raw=bounded_file(source,1024*1024)
        value={'path':name,'sha256':core.digest(raw),'bytes':len(raw),'authority':'SAVED_SOURCE_FILE','unsaved_editor_is_separate':True}
        if typ=='csv':
            if source.suffix.lower()!='.csv':raise ValueError('NOTEBOOK_TABLE_CSV_PROFILE')
            rows=[]
            reader=csv.reader(io.StringIO(raw.decode('utf-8-sig')))
            try:
                for i,row in enumerate(reader):
                    if len(row)>32 or any(len(c)>2000 for c in row):raise ValueError('NOTEBOOK_TABLE_CELL_LIMIT')
                    if i==100:value['preview_truncated']=True;break
                    rows.append(row)
            except csv.Error:raise ValueError('NOTEBOOK_TABLE_CSV_PROFILE') from None
            value.update(rows=rows,formula_state='NOT_EVALUATED',type_state='LITERAL_STRINGS_P20_TYPED_TABLES_PENDING')
        else:
            text=raw[:16384].decode('utf-8',errors='replace');value.update(text=text,preview_truncated=len(raw)>16384)
        return value
    if typ=='marginalia':
        if 'path' not in t:raise ValueError('NOTEBOOK_MARGINALIA_REBIND_REQUIRED')
        source=Path(t['path'])
        if not source.is_absolute() or source.suffix.lower() not in ('.html','.htm','.json','.md','.org','.txt'):raise ValueError('NOTEBOOK_MARGINALIA_LINK_PROFILE')
        raw=bounded_file(source,4*1024*1024)
        return {'name':t['name'],'sha256':core.digest(raw),'bytes':len(raw),'authority':'LINKED_MARGINALIA_ORIGINAL','text':raw[:16384].decode('utf-8',errors='replace'),'preview_truncated':len(raw)>16384,'mode':'LINK_ONLY_INERT_ORIGINAL_NOT_EXECUTED'}
    if typ=='job':return {'record':call(kernel,'workspace.job',{'id':t['id']},p),'authority':'RECORDED_KERNEL_JOB_AND_EVIDENCE','physical_qualification':False}
    if typ=='query_read':
        value=notebooks.read_record(t['id'])
        for ref in value['references']:
            now=snapshot(kernel,ref['kind'],ref['target'],p,notebooks)
            if core.digest(now)!=ref['binding']:raise ValueError('NOTEBOOK_QUERY_READ_DEPENDENCY_CHANGED')
        return {'record':value,'authority':'HISTORICAL_READ_ONLY_QUERY_SNAPSHOT','engineering_acceptance':False}
    raise ValueError('NOTEBOOK_REFERENCE_PROFILE')
def preview(kernel,kind,t,p,notebooks):
    first=snapshot(kernel,kind,t,p,notebooks);second=snapshot(kernel,kind,t,p,notebooks)
    if core.digest(first)!=core.digest(second):raise ValueError('NOTEBOOK_REFERENCE_CHANGED_DURING_READ')
    return {'kind':kind,'target':t,'binding':core.digest(first),'record':first,'effects':['read'],'accepted_facts_created':0}
def resolve(kernel,notebooks,doc,block_id,p):
    b=next((b for b in doc['document']['blocks'] if b['id']==block_id),None)
    if not b:raise ValueError('NOTEBOOK_BLOCK_UNAVAILABLE')
    if b['kind'] in ('text','unsupported'):return {'state':'WORKING_PROSE','block':b,'record':None,'authority':'WORKING_NOTEBOOK'}
    try:value=preview(kernel,b['kind'],b['target'],p,notebooks)
    except (ValueError,OSError,KeyError,TypeError):return {'state':'UNAVAILABLE','record':None,'block':b,'message':'Reference unavailable. The saved locator remains; no cached record is substituted.'}
    if value['binding']!=b['binding']:return {'state':'STALE','record':None,'block':b,'message':'Referenced bytes or record changed. Review and explicitly refresh this binding.'}
    current=notebooks.get(doc['id'])
    if current['revision']!=doc['revision']:raise ValueError('NOTEBOOK_CHANGED_DURING_REFERENCE_READ')
    return {'state':'AVAILABLE','block':b,**value}
def query(kernel,notebooks,doc,block_id,p):
    b=next((b for b in doc['document']['blocks'] if b['id']==block_id),None)
    if not b or b['kind']!='query':raise ValueError('NOTEBOOK_SAVED_QUERY_REQUIRED')
    core.target('query',b['target']);t=b['target'];limit=t.get('limit',20);references=[]
    if core.digest(snapshot(kernel,'query',t,p,notebooks))!=b['binding']:raise ValueError('NOTEBOOK_QUERY_DEFINITION_CHANGED')
    if t['type']=='catalog.search':
        before=notebooks.catalog.snapshot()['generation']
        rows=notebooks.catalog.search(t['query'],limit)
        for row in rows:
            spec={'type':'catalog','object_id':row['id']};value=preview(kernel,'note',spec,p,notebooks)
            if any(row[k]!=value['record'][k] for k in ('id','title','summary','version','state')):raise ValueError('NOTEBOOK_QUERY_DEPENDENCY_CHANGED')
            references.append({'kind':'note','target':spec,'binding':value['binding']})
        if notebooks.catalog.snapshot()['generation']!=before:raise ValueError('NOTEBOOK_QUERY_DEPENDENCY_CHANGED')
    else:
        rows=call(kernel,'jobs.list',{},p)[:limit]
        for row in rows:
            spec={'type':'job','id':row['id']};value=preview(kernel,'result',spec,p,notebooks)
            if core.digest(row)!=core.digest(value['record']['record']['job']):raise ValueError('NOTEBOOK_QUERY_DEPENDENCY_CHANGED')
            references.append({'kind':'result','target':spec,'binding':value['binding']})
    # The returned rows and bound records must describe the same observation.
    for ref in references:
        if core.digest(snapshot(kernel,ref['kind'],ref['target'],p,notebooks))!=ref['binding']:raise ValueError('NOTEBOOK_QUERY_DEPENDENCY_CHANGED')
    payload={'definition':t,'query_id':core.digest(t),'rows':rows,'references':references,'qualification':'RECORDED_READING_NOT_TOOL_EXECUTION_OR_FACT_ACCEPTANCE'}
    return notebooks.record_read(doc['id'],block_id,doc['revision'],payload)
def dispatch(kernel,op,a,p):
    if p.identity!='desktop-owner' or 'read' not in p.scopes:raise ValueError('NOTEBOOK_OWNER_PROFILE_REQUIRED')
    n=store()
    if op=='notebook.list':return {'notebooks':n.listing(),'schema':core.SCHEMA}
    if op=='notebook.create':return n.create(a['title'],a.get('parent','inbox'))
    if op=='notebook.get':return n.get(a['id'])
    if op=='notebook.original':return n.original(a['id'])
    if op=='notebook.save':return n.save(a['id'],a['expected_revision'],a['document'])
    if op=='notebook.draft.save':return n.draft(a['id'],a['writer'],a['base_revision'],a['document'])
    if op=='notebook.drafts':return {'drafts':n.drafts(a['id'])}
    if op=='notebook.draft.discard':return n.discard(a['id'],a['writer'])
    if op=='notebook.reference.preview':return preview(kernel,a['kind'],a['target'],p,n)
    if op=='notebook.import.preview':return n.import_preview(a['path'],a.get('parent','inbox'))
    if op=='notebook.import.commit':return n.import_commit(a['plan'],a['expected_digest'])
    if op in ('notebook.resolve','notebook.query.run'):
        doc=n.get(a['id'])
        if op.endswith('.resolve'):return resolve(kernel,n,doc,a['block'],p)
        if doc['revision']!=a['expected_revision']:raise ValueError('NOTEBOOK_QUERY_CHANGED')
        return query(kernel,n,doc,a['block'],p)
    raise ValueError('NOTEBOOK_OPERATION_UNAVAILABLE')
