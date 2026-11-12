"""Private office working copies, reviewed candidates, drafts and immutable input."""
import copy,json,os,re,stat,time,uuid
from pathlib import Path
from . import office_tables as tables,office_documents as documents
from .concern_catalog import MAX_OBJECTS

def validate(doc):
    if not isinstance(doc,dict):raise ValueError('OFFICE_DOCUMENT_SCHEMA')
    return tables.validate(doc) if doc.get('schema')==tables.SCHEMA else documents.validate(doc)
def parse(raw,name,options=None):
    if name.lower().endswith('.docx'):return documents.parse(raw,name)
    return tables.parse(raw,name,**(options or {}))
def rules():return tables.sha({p.name:tables.sha(p.read_bytes()) for p in (Path(__file__),Path(tables.__file__),Path(documents.__file__))})
def read(path,maximum=tables.MAX_INPUT):
    path=Path(path).absolute()
    if any(x.is_symlink() for x in (path,*path.parents)):raise ValueError('OFFICE_SOURCE_SYMLINK')
    fd=os.open(path,os.O_RDONLY|getattr(os,'O_NOFOLLOW',0)|getattr(os,'O_NONBLOCK',0))
    try:
        before=os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_size>maximum:raise ValueError('OFFICE_SOURCE_SIZE_OR_TYPE')
        with os.fdopen(fd,'rb',closefd=False) as f:raw=f.read(maximum+1)
        after=os.fstat(fd)
        if len(raw)>maximum or len(raw)!=before.st_size or (before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns):raise ValueError('OFFICE_SOURCE_CHANGED')
        return raw
    finally:os.close(fd)
def ident(value):
    if not isinstance(value,str) or not re.fullmatch('owner:[a-f0-9]{32}',value):raise ValueError('OFFICE_ID')
    return value
def uid(value):
    if not isinstance(value,str) or not re.fullmatch('[a-f0-9]{32}',value):raise ValueError('OFFICE_TOKEN')
    return value
class Office:
    def __init__(self,catalog):
        self.catalog=catalog
        with catalog.db() as db:db.executescript('''
          CREATE TABLE IF NOT EXISTS office_documents(id TEXT PRIMARY KEY,version INTEGER,payload TEXT,origin TEXT,original BLOB);
          CREATE TABLE IF NOT EXISTS office_history(id TEXT,version INTEGER,payload TEXT,PRIMARY KEY(id,version));
          CREATE TABLE IF NOT EXISTS office_drafts(id TEXT,writer TEXT,base TEXT,payload TEXT,at REAL,PRIMARY KEY(id,writer));
          CREATE TABLE IF NOT EXISTS office_plans(id TEXT PRIMARY KEY,payload TEXT,original BLOB,result TEXT,at REAL);
        ''')
    def _get(self,db,key):
        ident(key);row=db.execute('SELECT * FROM office_documents WHERE id=?',(key,)).fetchone()
        if not row:raise ValueError('OFFICE_DOCUMENT_UNAVAILABLE')
        obj=self.catalog._object(db,key);doc=json.loads(row['payload']);doc['title']=obj['title'];validate(doc)
        return {'id':key,'version':row['version'],'revision':tables.sha([obj,row['version'],doc,row['origin']]),'document':doc,'origin':json.loads(row['origin']),'authority':'OWNER_WORKING_OFFICE_COPY','engineering_acceptance':False}
    def get(self,key):
        with self.catalog.db() as db:db.execute('BEGIN');return self._get(db,key)
    def listing(self):
        rows=[]
        with self.catalog.db() as db:
            for r in db.execute("SELECT d.id,d.version,d.payload,o.title,o.state FROM office_documents d JOIN objects o ON o.id=d.id WHERE o.state!='archived' ORDER BY o.title"):
                row=dict(r);payload=row.pop('payload');row['kind']='table' if json.loads(payload)['schema']==tables.SCHEMA else 'document';rows.append(row)
        return rows
    def _create(self,db,doc,parent,origin,original):
        validate(doc);p=self.catalog._object(db,parent)
        if p['state']=='archived':raise ValueError('OFFICE_DESTINATION_ARCHIVED')
        if db.execute('SELECT count(*) FROM office_documents').fetchone()[0]>=32 or db.execute('SELECT count(*) FROM objects').fetchone()[0]>=MAX_OBJECTS:raise ValueError('OFFICE_DOCUMENT_COUNT_LIMIT')
        key='owner:'+uuid.uuid4().hex
        db.execute('INSERT INTO objects VALUES(?,?,?,?,?,1)',(key,'collection',doc['title'],'Office working copy; original and engineering acceptance are separate.','active'))
        db.execute('INSERT INTO relations VALUES(?,?,?)',(key,'part_of',parent))
        db.execute('INSERT INTO office_documents VALUES(?,1,?,?,?)',(key,tables.canonical(doc),tables.canonical(origin),original));self.catalog._index(db,key);self.catalog._event(db,'office.create',key)
        return self._get(db,key)
    def create(self,doc,parent='library',origin=None,original=None):
        with self.catalog.db() as db:db.execute('BEGIN IMMEDIATE');return self._create(db,doc,parent,origin or {'profile':'authored-working-copy-v1'},original)
    def _save(self,db,key,expected,doc):
        validate(doc);old=self._get(db,key)
        if old['revision']!=expected:raise ValueError('OFFICE_CHANGED_KEEP_DRAFT_AND_REVIEW')
        if old['document']['schema']!=doc['schema']:raise ValueError('OFFICE_DOCUMENT_KIND_CHANGE')
        if old['document']==doc:return old
        if db.execute('SELECT count(*) FROM office_history WHERE id=?',(key,)).fetchone()[0]>=256:raise ValueError('OFFICE_HISTORY_LIMIT')
        db.execute('INSERT INTO office_history VALUES(?,?,?)',(key,old['version'],tables.canonical(old['document'])))
        db.execute('UPDATE office_documents SET payload=?,version=version+1 WHERE id=?',(tables.canonical(doc),key))
        if old['document']['title']!=doc['title']:db.execute('UPDATE objects SET title=?,version=version+1 WHERE id=?',(doc['title'],key))
        self.catalog._index(db,key);self.catalog._event(db,'office.save',key);return self._get(db,key)
    def save(self,key,expected,doc):
        with self.catalog.db() as db:db.execute('BEGIN IMMEDIATE');return self._save(db,key,expected,doc)
    def original(self,key):
        with self.catalog.db() as db:self._get(db,key);row=db.execute('SELECT original FROM office_documents WHERE id=?',(key,)).fetchone();return row['original']
    def drafts(self,key):
        with self.catalog.db() as db:
            self._get(db,key);return [{'writer':r['writer'],'base_revision':r['base'],'document':json.loads(r['payload']),'at':r['at']} for r in db.execute('SELECT * FROM office_drafts WHERE id=? ORDER BY at DESC',(key,))]
    def draft(self,key,writer,base,doc):
        uid(writer);validate(doc)
        if not re.fullmatch('[a-f0-9]{64}',base or ''):raise ValueError('OFFICE_DRAFT_BASE')
        with self.catalog.db() as db:
            db.execute('BEGIN IMMEDIATE');self._get(db,key)
            if db.execute('SELECT count(*) FROM office_drafts WHERE id=?',(key,)).fetchone()[0]>=16 and not db.execute('SELECT 1 FROM office_drafts WHERE id=? AND writer=?',(key,writer)).fetchone():raise ValueError('OFFICE_DRAFT_LIMIT')
            db.execute('INSERT OR REPLACE INTO office_drafts VALUES(?,?,?,?,?)',(key,writer,base,tables.canonical(doc),time.time()))
        return {'state':'DRAFT_ONLY','saved_document_changed':False}
    def discard(self,key,writer):
        uid(writer)
        with self.catalog.db() as db:self._get(db,key);db.execute('DELETE FROM office_drafts WHERE id=? AND writer=?',(key,writer))
        return {'state':'DRAFT_DISCARDED'}
    def _plan(self,db,payload,raw=None):
        now=time.time();db.execute('DELETE FROM office_plans WHERE result IS NULL AND at<?',(now-3600,))
        for row in db.execute('SELECT id,payload FROM office_plans WHERE result IS NULL').fetchall():
            old=json.loads(row['payload'])
            keys=('mode','document_id','parent','path','format')
            if all(old.get(k)==payload.get(k) for k in keys):db.execute('DELETE FROM office_plans WHERE id=?',(row['id'],))
        if db.execute('SELECT count(*) FROM office_plans').fetchone()[0]>=1024 or db.execute('SELECT count(*) FROM office_plans WHERE result IS NULL').fetchone()[0]>=8:raise ValueError('OFFICE_PLAN_LIMIT')
        value={**payload,'id':uuid.uuid4().hex,'rules':rules(),'at':now};db.execute('INSERT INTO office_plans VALUES(?,?,?,NULL,?)',(value['id'],tables.canonical(value),raw,now));return {**value,'digest':tables.sha(value)}
    def preview_import(self,path,parent='library',options=None,bom=False):
        path=Path(path).absolute();raw=read(path)
        if bom:
            if path.suffix.lower()!='.kicad_pcb':raise ValueError('OFFICE_BOM_KICAD_PCB_PROFILE')
            components=tables.pcb_components(raw);parsed={'document':tables.bom_document(path.stem+' BOM',components),'losses':[],'profile':'kicad-pcb-bom-v1'}
        else:components=None;parsed=parse(raw,path.name,options)
        with self.catalog.db() as db:
            db.execute('BEGIN IMMEDIATE');destination=self.catalog._object(db,parent)
            origin={'source':{'path':str(path),'name':path.name,'sha256':tables.sha(raw),'bytes':len(raw)},'profile':parsed['profile'],'losses':parsed['losses']}
            if components is not None:origin['components']=components;origin['physical_qualification']=False
            return self._plan(db,{'mode':'import','parent':parent,'parent_revision':tables.sha(destination),'document':parsed['document'],'origin':origin,'losses':parsed['losses']},raw)
    def plan(self,key,digest=None):
        uid(key)
        with self.catalog.db() as db:
            row=db.execute('SELECT * FROM office_plans WHERE id=?',(key,)).fetchone()
            if not row:raise ValueError('OFFICE_PLAN_UNAVAILABLE')
            p=json.loads(row['payload'])
            if digest is not None and tables.sha(p)!=digest or p['rules']!=rules():raise ValueError('OFFICE_REVIEW_CHANGED')
            if row['result'] is None and time.time()-row['at']>3600:raise ValueError('OFFICE_PLAN_EXPIRED')
            return {**p,'digest':tables.sha(p),'result':json.loads(row['result']) if row['result'] else None}
    def preview_candidate(self,key,expected,path,options=None):
        saved=self.get(key)
        if saved['revision']!=expected:raise ValueError('OFFICE_CHANGED_KEEP_DRAFT_AND_REVIEW')
        if self.drafts(key):raise ValueError('OFFICE_REVIEW_SAVED_WORK_AND_RECOVERY_BEFORE_CANDIDATE')
        path=Path(path).absolute();raw=read(path);parsed=parse(raw,path.name,options)
        if parsed['document']['schema']!=saved['document']['schema']:raise ValueError('OFFICE_CANDIDATE_KIND')
        impl=tables if parsed['document']['schema']==tables.SCHEMA else documents;doc=impl.align(parsed['document'],saved['document']);changes=impl.difference(saved['document'],doc)
        with self.catalog.db() as db:
            db.execute('BEGIN IMMEDIATE')
            if self._get(db,key)['revision']!=expected:raise ValueError('OFFICE_CHANGED_DURING_PREVIEW')
            return self._plan(db,{'mode':'candidate','document_id':key,'expected_revision':expected,'path':str(path),'source_sha256':tables.sha(raw),'document':doc,'losses':parsed['losses'],'changes':changes},raw)
    def commit(self,key,digest):
        # Revalidate inside one transaction. The late source read rolls back all writes.
        with self.catalog.db() as db:
            db.execute('BEGIN IMMEDIATE');row=db.execute('SELECT * FROM office_plans WHERE id=?',(uid(key),)).fetchone()
            if not row:raise ValueError('OFFICE_PLAN_UNAVAILABLE')
            p=json.loads(row['payload'])
            if tables.sha(p)!=digest or p['rules']!=rules():raise ValueError('OFFICE_REVIEW_CHANGED')
            if row['result']:return {**json.loads(row['result']),'replayed':True}
            if time.time()-row['at']>3600:raise ValueError('OFFICE_PLAN_EXPIRED')
            if p['mode']=='import':
                source=p['origin']['source'];path=source['path'];expected_source=source['sha256']
                if tables.sha(self.catalog._object(db,p['parent']))!=p['parent_revision']:raise ValueError('OFFICE_IMPORT_DESTINATION_CHANGED')
            elif p['mode']=='candidate':path=p['path'];expected_source=p['source_sha256']
            else:raise ValueError('OFFICE_COMMIT_PROFILE')
            if tables.sha(read(path))!=expected_source:raise ValueError('OFFICE_SOURCE_CHANGED')
            if p['mode']=='import':saved=self._create(db,p['document'],p['parent'],p['origin'],bytes(row['original']))
            else:
                if db.execute('SELECT 1 FROM office_drafts WHERE id=?',(p['document_id'],)).fetchone():raise ValueError('OFFICE_RECOVERY_REVIEW_REQUIRED')
                saved=self._save(db,p['document_id'],p['expected_revision'],p['document'])
            if tables.sha(read(path))!=expected_source:raise ValueError('OFFICE_SOURCE_CHANGED')
            result={'state':'IMPORTED' if p['mode']=='import' else 'SAVED_CANDIDATE','document_id':saved['id'],'revision':saved['revision'],'replayed':False,'engineering_acceptance':False}
            db.execute('UPDATE office_plans SET result=? WHERE id=?',(tables.canonical(result),key));return result
    def operation(self,key,expected,mode,fmt,sheet_id=None,source_state=None,environment=None):
        saved=self.get(key)
        if saved['revision']!=expected:raise ValueError('OFFICE_CHANGED_KEEP_DRAFT_AND_REVIEW')
        if self.drafts(key):raise ValueError('OFFICE_REVIEW_SAVED_WORK_AND_RECOVERY_BEFORE_EXPORT')
        table=saved['document']['schema']==tables.SCHEMA
        if mode not in ('export','recalculate','edit') or fmt not in (('csv','ods','xlsx') if table else ('docx','pdf')) or mode=='recalculate' and not table:raise ValueError('OFFICE_OPERATION_PROFILE')
        if mode=='edit' and fmt not in ('ods','docx'):raise ValueError('OFFICE_EDIT_PROFILE')
        if table:
            if fmt=='csv':_,losses=tables.csv_bytes(saved['document'],sheet_id)
            else:_,losses=tables.ods_bytes(saved['document'])
            if mode=='recalculate' and any('UNSUPPORTED_FORMULA' in r['reason'] for r in losses):raise ValueError('OFFICE_RECALC_UNSUPPORTED_FORMULAS_REVIEW_DEFINITION')
            tables.loss(losses,'workbook','EXTERNAL_OFFICE_FLOATING_POINT_PRECISION_IS_NOT_EXACT_LEDGER_DECIMAL_STORAGE')
        else:losses=[{'path':'document','reason':'PLAIN_EDITABLE_PARAGRAPH_TABLE_EXPORT_PROFILE'}]
        with self.catalog.db() as db:
            db.execute('BEGIN IMMEDIATE')
            if self._get(db,key)['revision']!=expected:raise ValueError('OFFICE_CHANGED_DURING_PREVIEW')
            return self._plan(db,{'mode':mode,'format':fmt,'document_id':key,'expected_revision':expected,'document':saved['document'],'origin':saved['origin'],'source_state':source_state,'environment':environment,'sheet_id':sheet_id,'losses':losses,'accepted_facts_created':0})
    def finish(self,key,expected_digest,result):
        with self.catalog.db() as db:
            db.execute('BEGIN IMMEDIATE');row=db.execute('SELECT * FROM office_plans WHERE id=?',(uid(key),)).fetchone()
            if not row:raise ValueError('OFFICE_PLAN_UNAVAILABLE')
            p=json.loads(row['payload'])
            if tables.sha(p)!=expected_digest or p['rules']!=rules():raise ValueError('OFFICE_REVIEW_CHANGED')
            if self._get(db,p['document_id'])['revision']!=p['expected_revision']:raise ValueError('OFFICE_CHANGED_DURING_OPERATION')
            if row['result'] and json.loads(row['result']).get('state')!='QUEUED':
                old=json.loads(row['result'])
                if old!=result:raise ValueError('OFFICE_OPERATION_ALREADY_RECORDED')
                return old
            db.execute('UPDATE office_plans SET result=? WHERE id=?',(tables.canonical(result),key));return result
    def reserve(self,key,expected):
        with self.catalog.db() as db:
            db.execute('BEGIN IMMEDIATE');row=db.execute('SELECT payload,result FROM office_plans WHERE id=?',(uid(key),)).fetchone()
            if not row or tables.sha(json.loads(row['payload']))!=expected:raise ValueError('OFFICE_REVIEW_CHANGED')
            if row['result'] is None:db.execute('UPDATE office_plans SET result=? WHERE id=?',(tables.canonical({'state':'QUEUED'}),key))
