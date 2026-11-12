"""Working notebook blocks over existing concern notes, with inert references."""
from __future__ import annotations
import hashlib,json,os,re,stat,time,uuid
from pathlib import Path
from .concern_catalog import Catalog,MAX_OBJECTS

SCHEMA='arc.notebook/1'
IMPORT_PROFILE='appflowy-editor-json-v1'
KINDS=('text','note','source','requirement','table','query','result','unsupported')
MAX_BLOCKS=64;MAX_BYTES=96*1024;MAX_TEXT=16*1024;MAX_IMPORT=2*1024*1024
def encoded(v):
    try:return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
    except RecursionError:raise ValueError('NOTEBOOK_JSON_DEPTH') from None
def digest(v):return hashlib.sha256(v if isinstance(v,bytes) else encoded(v).encode()).hexdigest()
def rules():return digest([Path(__file__).read_bytes().hex(),Path(__file__).with_name('concern_catalog.py').read_bytes().hex()])
def ident(v):
    if not isinstance(v,str) or not re.fullmatch(r'owner:[a-f0-9]{32}',v):raise ValueError('NOTEBOOK_ID')
    return v
def short(v,limit=240,empty=False):
    if not isinstance(v,str) or len(v.encode())>limit or '\0' in v or any(ord(c)<32 and c not in '\n\t' for c in v) or not empty and not v.strip():raise ValueError('NOTEBOOK_TEXT_LIMIT')
    return v
def strict(raw):
    def pairs(values):
        out={}
        for k,v in values:
            if k in out:raise ValueError('NOTEBOOK_DUPLICATE_MEMBER')
            out[k]=v
        return out
    def bad(v):raise ValueError('NOTEBOOK_NONFINITE_NUMBER')
    try:return json.loads(raw,object_pairs_hook=pairs,parse_constant=bad)
    except RecursionError:raise ValueError('NOTEBOOK_JSON_DEPTH') from None
def read_input(path):
    path=Path(path).absolute()
    if path.suffix.lower()!='.json' or any(p.is_symlink() for p in (path,*path.parents)):raise ValueError('APPFLOWY_IMPORT_FILE_PROFILE')
    fd=os.open(path,os.O_RDONLY|getattr(os,'O_NOFOLLOW',0)|getattr(os,'O_NONBLOCK',0))
    try:
        info=os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_size>MAX_IMPORT:raise ValueError('APPFLOWY_IMPORT_FILE_LIMIT')
        with os.fdopen(fd,'rb',closefd=False) as stream:raw=stream.read(MAX_IMPORT+1)
        if len(raw)!=info.st_size or len(raw)>MAX_IMPORT:raise ValueError('APPFLOWY_IMPORT_SOURCE_CHANGED')
        return raw
    finally:os.close(fd)
def target(kind,t):
    if not isinstance(t,dict):raise ValueError('NOTEBOOK_TARGET')
    if kind in ('text','unsupported'):
        if t:raise ValueError('NOTEBOOK_TEXT_HAS_NO_AUTHORITY_TARGET')
        return t
    typ=t.get('type')
    allowed={
      'note':{'catalog':({'type','object_id'},{'type','object_id'})},
      'source':{'file':({'type','path'},{'type','path'}),'intake':({'type','item'},{'type','item'}),'marginalia':({'type','name','path'},{'type','name'})},
      'requirement':{'catalog':({'type','object_id'},{'type','object_id'}),'register':({'type','record_id'},{'type','record_id'})},
      'table':{'csv':({'type','path'},{'type','path'}),'office':({'type','object_id','sheet'},{'type','object_id','sheet'})},
      'query':{'catalog.search':({'type','query','limit'},{'type','query'}),'jobs.list':({'type','limit'},{'type'})},
      'result':{'job':({'type','id'},{'type','id'}),'query_read':({'type','id'},{'type','id'})}}
    fields,required=allowed.get(kind,{}).get(typ,(set(),{'UNKNOWN_TARGET'}))
    if not required.issubset(t) or set(t)-fields:raise ValueError('NOTEBOOK_TARGET_PROFILE')
    for k,v in t.items():
        if k=='limit':
            if type(v) is not int or not 1<=v<=20:raise ValueError('NOTEBOOK_QUERY_LIMIT')
        else:short(v,4096 if k=='path' else 300)
    if 'object_id' in t:ident(t['object_id'])
    if 'sheet' in t and not re.fullmatch('[a-f0-9]{32}',t['sheet']):raise ValueError('NOTEBOOK_OFFICE_SHEET_ID')
    if 'item' in t and not re.fullmatch('[a-f0-9]{32}',t['item']):raise ValueError('NOTEBOOK_ITEM_ID')
    if 'id' in t and not re.fullmatch('[a-f0-9]{32}',t['id']):raise ValueError('NOTEBOOK_RESULT_ID')
    return t
def document(value):
    if not isinstance(value,dict) or set(value)!={'schema','title','blocks'} or value['schema']!=SCHEMA:raise ValueError('NOTEBOOK_SCHEMA')
    short(value['title'])
    if not isinstance(value['blocks'],list) or len(value['blocks'])>MAX_BLOCKS:raise ValueError('NOTEBOOK_BLOCK_LIMIT')
    seen=set()
    for b in value['blocks']:
        if not isinstance(b,dict) or set(b)!={'id','kind','title','body','target','binding','origin'}:raise ValueError('NOTEBOOK_BLOCK_SCHEMA')
        ident(b['id'])
        if b['id'] in seen or b['kind'] not in KINDS:raise ValueError('NOTEBOOK_BLOCK_IDENTITY')
        seen.add(b['id']);short(b['title']);short(b['body'],MAX_TEXT,True);target(b['kind'],b['target'])
        if b['kind'] in ('text','unsupported'):
            if b['binding'] is not None:raise ValueError('NOTEBOOK_PROSE_IS_NOT_A_RECORD_BINDING')
        elif not isinstance(b['binding'],str) or not re.fullmatch('[a-f0-9]{64}',b['binding']):raise ValueError('NOTEBOOK_REFERENCE_REVIEW_REQUIRED')
        if not isinstance(b['origin'],dict) or len(encoded(b['origin']).encode())>8192:raise ValueError('NOTEBOOK_ORIGIN_LIMIT')
    if len(encoded(value).encode())>MAX_BYTES:raise ValueError('NOTEBOOK_SIZE_LIMIT')
    return value
def block(kind='text',title='Idea',body='',target_value=None,binding=None,origin=None):
    return {'id':'owner:'+uuid.uuid4().hex,'kind':kind,'title':title,'body':body,'target':target_value or {},'binding':binding,'origin':origin or {}}

def appflowy(raw,name):
    if len(raw)>MAX_IMPORT:raise ValueError('NOTEBOOK_IMPORT_SIZE_LIMIT')
    value=strict(raw)
    if not isinstance(value,dict) or set(value)!={'document'} or not isinstance(value['document'],dict) or value['document'].get('type')!='page':raise ValueError('APPFLOWY_DOCUMENT_PROFILE_REQUIRED')
    blocks=[];losses=[];counts={};seen=set();source_sha=digest(raw)
    supported={'paragraph','heading','bulleted_list','numbered_list','todo_list','quote','code','divider'}
    def loss(path,typ,reason):
        if len(losses)>=2048:raise ValueError('APPFLOWY_LOSS_REPORT_LIMIT')
        losses.append({'path':path,'type':typ,'reason':reason})
    def walk(n,path,depth):
        if depth>16 or not isinstance(n,dict):raise ValueError('APPFLOWY_NODE_DEPTH_OR_SCHEMA')
        typ=n.get('type');attrs=n.get('data',n.get('attributes',{}))
        if 'data' in n and 'attributes' in n:raise ValueError('APPFLOWY_AMBIGUOUS_ATTRIBUTE_PROFILE')
        if not isinstance(typ,str) or not isinstance(attrs,dict):raise ValueError('APPFLOWY_NODE_SCHEMA')
        children=n.get('children',[])
        if not isinstance(children,list):raise ValueError('APPFLOWY_CHILDREN_SCHEMA')
        if path=='document' and (attrs or set(n)-{'type','attributes','data','children'}):loss(path,typ,'PAGE_METADATA_RETAINED_IN_ORIGINAL_NOT_RENDERED')
        if path!='document':
            if len(blocks)>=MAX_BLOCKS:raise ValueError('APPFLOWY_BLOCK_LIMIT')
            counts[typ]=counts.get(typ,0)+1;plain=[]
            delta=attrs.get('delta',n.get('delta',[]))
            if not isinstance(delta,list):loss(path,typ,'DELTA_NOT_A_SUPPORTED_LIST');delta=[]
            if len(delta)>512:raise ValueError('APPFLOWY_DELTA_OPERATION_LIMIT')
            for i,op in enumerate(delta):
                if not isinstance(op,dict):raise ValueError('APPFLOWY_DELTA_SCHEMA')
                if isinstance(op.get('insert'),str):plain.append(op['insert'])
                elif 'insert' in op:plain.append('[Unsupported embedded object]');loss(path+'/delta/'+str(i),typ,'EMBEDDED_OBJECT_RETAINED_IN_ORIGINAL')
                else:loss(path+'/delta/'+str(i),typ,'NONINSERT_DELTA_OPERATION')
                if op.get('attributes'):loss(path+'/delta/'+str(i),typ,'INLINE_ATTRIBUTES_RETAINED_NOT_RENDERED')
                if set(op)-{'insert','attributes'}:loss(path+'/delta/'+str(i),typ,'EXTRA_DELTA_FIELDS_RETAINED_IN_ORIGINAL')
            if typ not in supported:loss(path,typ,'UNSUPPORTED_BLOCK_RETAINED_AS_LITERAL_PLACEHOLDER')
            if children:loss(path,typ,'NESTING_RETAINED_AS_ORIGIN_PATH_FLAT_WORKING_VIEW')
            extra=set(attrs)-{'delta','level','checked','number','language'}
            if extra:loss(path,typ,'ATTRIBUTES_NOT_INTERPRETED:'+','.join(sorted(extra)))
            if set(n)-{'type','attributes','data','children','id','delta'}:loss(path,typ,'EXTRA_NODE_FIELDS_RETAINED_IN_ORIGINAL')
            origin_id=n.get('id')
            if origin_id is not None:
                if not isinstance(origin_id,str) or len(origin_id)>200 or origin_id in seen:raise ValueError('APPFLOWY_DUPLICATE_OR_INVALID_NODE_ID')
                seen.add(origin_id)
            origin={'profile':IMPORT_PROFILE,'source_sha256':source_sha,'path':path,'type':typ,'node_id':origin_id,'attributes':{k:v for k,v in attrs.items() if k!='delta'}}
            b=block('text' if typ in supported else 'unsupported',typ.replace('_',' ').capitalize(),''.join(plain),origin=origin)
            blocks.append(b)
        for i,child in enumerate(children):walk(child,path+'/children/'+str(i),depth+1)
    walk(value['document'],'document',0)
    doc=document({'schema':SCHEMA,'title':Path(name).stem[:160] or 'Imported AppFlowy document','blocks':blocks})
    return {'document':doc,'losses':losses,'node_types':counts,'source_sha256':source_sha,'profile':IMPORT_PROFILE,'conversion':'ONE_WAY_LITERAL_WORKING_BLOCKS','accepted_facts_created':0}

class Notebook:
    def __init__(self,catalog):
        self.catalog=catalog
        with catalog.db() as db:
            db.executescript('''
             CREATE TABLE IF NOT EXISTS notebooks(id TEXT PRIMARY KEY,version INTEGER,origin TEXT,original BLOB);
             CREATE TABLE IF NOT EXISTS notebook_blocks(notebook TEXT,id TEXT PRIMARY KEY,position INTEGER,kind TEXT,spec TEXT,active INTEGER);
             CREATE TABLE IF NOT EXISTS notebook_drafts(notebook TEXT,writer TEXT,base TEXT,payload TEXT,at REAL,PRIMARY KEY(notebook,writer));
             CREATE TABLE IF NOT EXISTS notebook_history(notebook TEXT,version INTEGER,payload TEXT,PRIMARY KEY(notebook,version));
             CREATE TABLE IF NOT EXISTS notebook_reads(id TEXT PRIMARY KEY,notebook TEXT,block TEXT,payload TEXT);
             CREATE TABLE IF NOT EXISTS notebook_imports(id TEXT PRIMARY KEY,payload TEXT,result TEXT,at REAL);
            ''')
    def exists(self,ident_value):
        with self.catalog.db() as db:return db.execute('SELECT 1 FROM notebooks WHERE id=?',(ident_value,)).fetchone() is not None
    def listing(self):
        with self.catalog.db() as db:return [dict(r) for r in db.execute('SELECT n.id,n.version,o.title,o.state FROM notebooks n JOIN objects o ON o.id=n.id ORDER BY o.title')]
    def _get(self,db,ident_value):
        ident(ident_value);row=db.execute('SELECT * FROM notebooks WHERE id=?',(ident_value,)).fetchone()
        if not row:raise ValueError('NOTEBOOK_UNAVAILABLE')
        owner=self.catalog._object(db,ident_value);blocks=[];state=[]
        for r in db.execute('SELECT * FROM notebook_blocks WHERE notebook=? ORDER BY position,id',(ident_value,)):
            o=self.catalog._object(db,r['id']);note=db.execute('SELECT body,version FROM notes WHERE object_id=?',(r['id'],)).fetchone()
            if not note:raise ValueError('NOTEBOOK_BLOCK_NOTE_MISSING')
            spec=strict(r['spec']);state.append([dict(r),o['version'],o['title'],note['version'],digest(note['body'].encode())])
            if r['active']:blocks.append({'id':r['id'],'kind':r['kind'],'title':o['title'],'body':note['body'],**spec})
        doc=document({'schema':SCHEMA,'title':owner['title'],'blocks':blocks})
        return {'schema':SCHEMA,'id':ident_value,'version':row['version'],'revision':digest([owner,row['version'],state]),'document':doc,'origin':strict(row['origin']),'authority':'WORKING_NOTEBOOK','accepted_facts_created':0}
    def get(self,ident_value):
        with self.catalog.db() as db:
            db.execute('BEGIN');return self._get(db,ident_value)
    def _write(self,db,ident_value,doc):
        old={r['id']:dict(r) for r in db.execute('SELECT * FROM notebook_blocks WHERE notebook=?',(ident_value,))}
        new=[b for b in doc['blocks'] if b['id'] not in old]
        if len(old)+len(new)>256:raise ValueError('NOTEBOOK_RETAINED_BLOCK_LIMIT')
        if db.execute('SELECT count(*) FROM objects').fetchone()[0]+len(new)>MAX_OBJECTS:raise ValueError('NOTEBOOK_CATALOG_LIMIT')
        for b in new:
            if db.execute('SELECT 1 FROM objects WHERE id=?',(b['id'],)).fetchone():raise ValueError('NOTEBOOK_BLOCK_BELONGS_TO_ANOTHER_RECORD')
        active={b['id'] for b in doc['blocks']}
        for key in old:
            if key not in active:db.execute("UPDATE objects SET state=?,version=version+1 WHERE id=? AND state!='archived'",('archived',key))
        db.execute('UPDATE notebook_blocks SET active=0 WHERE notebook=?',(ident_value,))
        for pos,b in enumerate(doc['blocks']):
            if b['id'] not in old:
                db.execute('INSERT INTO objects VALUES(?,?,?,?,?,1)',(b['id'],'note',b['title'],'Notebook working block; references confer no source acceptance.','active'))
                db.execute('INSERT INTO notes VALUES(?,?,1)',(b['id'],b['body']));db.execute('INSERT INTO relations VALUES(?,?,?)',(b['id'],'part_of',ident_value))
            else:
                o=self.catalog._object(db,b['id'])
                if o['title']!=b['title'] or o['state']!='active':db.execute('UPDATE objects SET title=?,state=?,version=version+1 WHERE id=?',(b['title'],'active',b['id']))
                current=db.execute('SELECT body FROM notes WHERE object_id=?',(b['id'],)).fetchone()[0]
                if current!=b['body']:db.execute('UPDATE notes SET body=?,version=version+1 WHERE object_id=?',(b['body'],b['id']))
            spec={k:b[k] for k in ('target','binding','origin')}
            db.execute('INSERT OR REPLACE INTO notebook_blocks VALUES(?,?,?,?,?,1)',(ident_value,b['id'],pos,b['kind'],encoded(spec)));self.catalog._index(db,b['id'])
        o=self.catalog._object(db,ident_value)
        if o['title']!=doc['title']:db.execute('UPDATE objects SET title=?,version=version+1 WHERE id=?',(doc['title'],ident_value))
        self.catalog._index(db,ident_value)
    def _create(self,db,doc,parent,origin=None,original=None):
        parent_row=self.catalog._object(db,parent)
        if parent_row['state']=='archived':raise ValueError('NOTEBOOK_DESTINATION_ARCHIVED')
        if db.execute('SELECT count(*) FROM notebooks').fetchone()[0]>=32:raise ValueError('NOTEBOOK_COUNT_LIMIT')
        ident_value='owner:'+uuid.uuid4().hex
        db.execute('INSERT INTO objects VALUES(?,?,?,?,?,1)',(ident_value,'collection',doc['title'],'Engineering notebook; working prose and checked references.','active'))
        db.execute('INSERT INTO relations VALUES(?,?,?)',(ident_value,'part_of',parent))
        db.execute('INSERT INTO notebooks VALUES(?,1,?,?)',(ident_value,encoded(origin or {}),original))
        self._write(db,ident_value,doc);self.catalog._event(db,'notebook.create',ident_value)
        return self._get(db,ident_value)
    def create(self,title,parent='inbox'):
        doc=document({'schema':SCHEMA,'title':title,'blocks':[]})
        with self.catalog.db() as db:
            db.execute('BEGIN IMMEDIATE');return self._create(db,doc,parent)
    def save(self,ident_value,expected,doc):
        document(doc)
        with self.catalog.db() as db:
            db.execute('BEGIN IMMEDIATE');old=self._get(db,ident_value)
            if old['revision']!=expected:raise ValueError('NOTEBOOK_CHANGED_KEEP_DRAFT_AND_REVIEW')
            if doc==old['document']:return old
            if db.execute('SELECT count(*) FROM notebook_history WHERE notebook=?',(ident_value,)).fetchone()[0]>=4096:raise ValueError('NOTEBOOK_HISTORY_LIMIT')
            db.execute('INSERT INTO notebook_history VALUES(?,?,?)',(ident_value,old['version'],encoded(old['document'])))
            self._write(db,ident_value,doc);db.execute('UPDATE notebooks SET version=version+1 WHERE id=?',(ident_value,))
            self.catalog._event(db,'notebook.save',ident_value)
            return self._get(db,ident_value)
    def draft(self,ident_value,writer,base,doc):
        document(doc)
        if not re.fullmatch('[a-f0-9]{32}',writer) or not re.fullmatch('[a-f0-9]{64}',base):raise ValueError('NOTEBOOK_DRAFT_IDENTITY')
        with self.catalog.db() as db:
            self._get(db,ident_value)
            if db.execute('SELECT count(*) FROM notebook_drafts WHERE notebook=?',(ident_value,)).fetchone()[0]>=16 and not db.execute('SELECT 1 FROM notebook_drafts WHERE notebook=? AND writer=?',(ident_value,writer)).fetchone():raise ValueError('NOTEBOOK_DRAFT_LIMIT')
            db.execute('INSERT OR REPLACE INTO notebook_drafts VALUES(?,?,?,?,?)',(ident_value,writer,base,encoded(doc),time.time()))
        return {'state':'DRAFT_ONLY','saved_notebook_changed':False}
    def drafts(self,ident_value):
        with self.catalog.db() as db:
            self._get(db,ident_value);return [{'writer':r['writer'],'base_revision':r['base'],'document':strict(r['payload']),'at':r['at']} for r in db.execute('SELECT * FROM notebook_drafts WHERE notebook=? ORDER BY at DESC',(ident_value,))]
    def discard(self,ident_value,writer):
        with self.catalog.db() as db:self._get(db,ident_value);db.execute('DELETE FROM notebook_drafts WHERE notebook=? AND writer=?',(ident_value,writer))
        return {'state':'DRAFT_DISCARDED','saved_notebook_changed':False}
    def import_preview(self,path,parent='inbox'):
        path=Path(path).absolute()
        raw=read_input(path);value=appflowy(raw,path.name)
        with self.catalog.db() as db:
            db.execute('BEGIN IMMEDIATE');parent_row=self.catalog._object(db,parent)
            if parent_row['state']=='archived':raise ValueError('NOTEBOOK_DESTINATION_ARCHIVED')
            plan={**value,'id':uuid.uuid4().hex,'path':str(path),'parent':parent,'parent_revision':digest(parent_row),'rules':rules()}
            db.execute('DELETE FROM notebook_imports WHERE result IS NULL AND at<?',(time.time()-3600,))
            for r in db.execute('SELECT id,payload FROM notebook_imports WHERE result IS NULL').fetchall():
                prior=strict(r['payload'])
                if prior['path']==plan['path'] and prior['parent']==parent:db.execute('DELETE FROM notebook_imports WHERE id=?',(r['id'],))
            if db.execute('SELECT count(*) FROM notebook_imports').fetchone()[0]>=1024 or db.execute('SELECT count(*) FROM notebook_imports WHERE result IS NULL').fetchone()[0]>=8:raise ValueError('NOTEBOOK_IMPORT_PLAN_LIMIT')
            db.execute('INSERT INTO notebook_imports VALUES(?,?,NULL,?)',(plan['id'],encoded(plan),time.time()))
        return {**plan,'digest':digest(plan)}
    def import_commit(self,ident_value,expected):
        with self.catalog.db() as db:
            db.execute('BEGIN IMMEDIATE');row=db.execute('SELECT * FROM notebook_imports WHERE id=?',(ident_value,)).fetchone()
            if not row:raise ValueError('NOTEBOOK_IMPORT_PLAN_UNAVAILABLE')
            p=strict(row['payload'])
            if digest(p)!=expected or p['rules']!=rules():raise ValueError('NOTEBOOK_IMPORT_REVIEW_CHANGED')
            if row['result']:return {**strict(row['result']),'replayed':True}
            if time.time()-row['at']>3600:raise ValueError('NOTEBOOK_IMPORT_PLAN_EXPIRED')
            if digest(self.catalog._object(db,p['parent']))!=p['parent_revision']:raise ValueError('NOTEBOOK_IMPORT_DESTINATION_CHANGED')
            path=Path(p['path'])
            if any(x.is_symlink() for x in (path,*path.parents)):raise ValueError('NOTEBOOK_IMPORT_SOURCE_CHANGED')
            raw=read_input(path)
            if len(raw)>MAX_IMPORT or digest(raw)!=p['source_sha256']:raise ValueError('NOTEBOOK_IMPORT_SOURCE_CHANGED')
            for existing in db.execute('SELECT id,origin FROM notebooks'):
                origin=strict(existing['origin'])
                if origin.get('source_sha256')==p['source_sha256'] and origin.get('parent')==p['parent']:
                    result={'state':'ALREADY_IMPORTED','notebook':existing['id'],'replayed':False,'accepted_facts_created':0};break
            else:
                origin={k:p[k] for k in ('profile','source_sha256','losses','node_types','conversion','parent')};origin['name']=path.name
                saved=self._create(db,p['document'],p['parent'],origin,raw)
                result={'state':'IMPORTED','notebook':saved['id'],'replayed':False,'losses':p['losses'],'accepted_facts_created':0}
            if digest(read_input(path))!=p['source_sha256']:raise ValueError('NOTEBOOK_IMPORT_SOURCE_CHANGED')
            db.execute('UPDATE notebook_imports SET result=? WHERE id=?',(encoded(result),ident_value))
        return result
    def record_read(self,notebook,block_id,expected,payload):
        if len(encoded(payload).encode())>128*1024:raise ValueError('NOTEBOOK_QUERY_RESULT_LIMIT')
        with self.catalog.db() as db:
            db.execute('BEGIN IMMEDIATE');current=self._get(db,notebook)
            if current['revision']!=expected:raise ValueError('NOTEBOOK_QUERY_CHANGED')
            if db.execute('SELECT count(*) FROM notebook_reads WHERE notebook=?',(notebook,)).fetchone()[0]>=1024:raise ValueError('NOTEBOOK_QUERY_HISTORY_LIMIT')
            ident_value=uuid.uuid4().hex
            value={**payload,'id':ident_value,'notebook':notebook,'block':block_id,'at':time.time(),'authority':'RECORDED_READ_ONLY_QUERY','effects':['read']}
            db.execute('INSERT INTO notebook_reads VALUES(?,?,?,?)',(ident_value,notebook,block_id,encoded(value)))
        return value
    def read_record(self,ident_value):
        with self.catalog.db() as db:
            row=db.execute('SELECT payload FROM notebook_reads WHERE id=?',(ident_value,)).fetchone()
            if not row:raise ValueError('NOTEBOOK_QUERY_READ_UNAVAILABLE')
            return strict(row['payload'])
    def original(self,ident_value):
        with self.catalog.db() as db:
            self._get(db,ident_value);row=db.execute('SELECT original,origin FROM notebooks WHERE id=?',(ident_value,)).fetchone()
            raw=row['original']
            return {'origin':strict(row['origin']),'text':raw.decode('utf-8') if raw is not None else None,'sha256':digest(raw) if raw is not None else None,'authority':'INERT_IMPORT_ORIGINAL'}
