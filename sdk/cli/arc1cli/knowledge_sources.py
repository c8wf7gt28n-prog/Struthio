"""Pinned source snapshots and ROM qualification. No Qt, providers or approval."""
from __future__ import annotations
from contextlib import closing
import hashlib,json,os,re,shutil,sqlite3,tempfile,time,zipfile
from pathlib import Path
from . import record_store as records

VERSION='arc.knowledge-sources/1'
MAX_DB=160*1024*1024
MAX_ARCHIVE=256*1024*1024
MAX_EXPANDED=640*1024*1024

def digest(value):return hashlib.sha256(records.canonical(value)).hexdigest()
def fingerprint():return digest({'reader':records.sha(Path(__file__)),'sqlite':sqlite3.sqlite_version,'profile':VERSION})
def regular(path):
    path=Path(path).absolute()
    if any(p.is_symlink() for p in (path,*path.parents)) or not path.is_file():raise ValueError('KNOWLEDGE_REGULAR_FILE_REQUIRED')
    return path
def interrupted(check):
    if check:check()
def quote_id(name):return '"'+name.replace('"','""')+'"'

class PinnedConnection(sqlite3.Connection):
    def close(self):
        try:super().close()
        finally:
            folder=getattr(self,'snapshot_folder',None)
            if folder:folder.cleanup();self.snapshot_folder=None

def pinned_index(path,expected,check=None):
    """Copy exact sealed bytes before SQLite opens them. Never assert immutable."""
    path=regular(path)
    if not re.fullmatch('[0-9a-f]{64}',expected):raise ValueError('KNOWLEDGE_INDEX_HASH_REQUIRED')
    if path.stat().st_size>MAX_DB:raise ValueError('KNOWLEDGE_INDEX_SIZE_LIMIT')
    if any(Path(str(path)+suffix).exists() for suffix in ('-wal','-shm','-journal')):raise ValueError('SEALED_INDEX_HAS_LIVE_SQLITE_SIDECAR')
    folder=tempfile.TemporaryDirectory(prefix='ledger-pinned-index-');target=Path(folder.name)/'source.sqlite'
    con=None;start=time.monotonic();h=hashlib.sha256();size=0
    try:
        with path.open('rb') as src,target.open('xb') as out:
            while True:
                interrupted(check);raw=src.read(1024*1024)
                if not raw:break
                size+=len(raw)
                if size>MAX_DB or time.monotonic()-start>30:raise ValueError('KNOWLEDGE_INDEX_COPY_LIMIT')
                h.update(raw);out.write(raw)
        if h.hexdigest()!=expected:raise ValueError('KNOWLEDGE_INDEX_CHANGED')
        if any(Path(str(path)+suffix).exists() for suffix in ('-wal','-shm','-journal')):raise ValueError('SEALED_INDEX_BECAME_LIVE')
        con=sqlite3.connect(target.as_uri()+'?mode=ro',uri=True,factory=PinnedConnection,timeout=2)
        con.snapshot_folder=folder
        con.execute('PRAGMA query_only=ON');con.execute('PRAGMA trusted_schema=OFF')
        deadline=time.monotonic()+30
        def progress():
            interrupted(check)
            return int(time.monotonic()>deadline)
        con.set_progress_handler(progress,2000)
        return con
    except BaseException:
        if con:con.close()
        else:folder.cleanup()
        raise

def qualify_index(path,expected,check=None):
    """Backup a frozen connection, then run database and all FTS checks on backup."""
    with closing(pinned_index(path,expected,check)) as source,tempfile.TemporaryDirectory(prefix='ledger-index-check-') as tmp:
        target=sqlite3.connect(Path(tmp)/'qualification.sqlite',timeout=2)
        try:
            deadline=time.monotonic()+60
            def progress(*_):
                interrupted(check)
                if time.monotonic()>deadline:raise ValueError('KNOWLEDGE_BACKUP_TIME_LIMIT')
            source.backup(target,pages=256,progress=progress,sleep=.01)
            target.execute('PRAGMA trusted_schema=OFF')
            target.set_progress_handler(lambda:int(time.monotonic()>deadline),2000)
            status=target.execute('PRAGMA integrity_check').fetchall()
            if status!=[('ok',)]:raise ValueError('KNOWLEDGE_SQLITE_INTEGRITY')
            tables=target.execute("SELECT name,sql FROM sqlite_schema WHERE type='table' AND sql IS NOT NULL").fetchall()
            checked=[]
            for name,sql in tables:
                if not re.search(r'\bUSING\s+fts5\s*\(',sql,re.I):continue
                interrupted(check);q=quote_id(name)
                # rank 1 also compares an external-content table with its index.
                target.execute('INSERT INTO '+q+'('+q+',rank) VALUES(?,1)',('integrity-check',))
                checked.append({'table':name,'integrity':'PASS','external_content_compared':True})
            target.commit()
            counts={}
            for name in ('pages','documents'):
                if any(n==name for n,_ in tables):counts[name]=target.execute('SELECT count(*) FROM '+quote_id(name)).fetchone()[0]
            return {'sha256':expected,'bytes':Path(path).stat().st_size,'database_integrity':'PASS','fts_checks':checked,'counts':counts,'method':'PINNED_BYTES_ONLINE_BACKUP_DISPOSABLE_CHECK','sqlite':sqlite3.sqlite_version}
        finally:target.close()

def header(folder,expected=None):
    folder=Path(folder).absolute();mp=records.inside(folder,'VOLUME.json')
    if expected and records.sha(mp)!=expected:raise ValueError('KNOWLEDGE_VOLUME_CHANGED')
    manifest=records.load(mp);cp=records.inside(folder,'CATALOG.json')
    if records.sha(cp)!=manifest['catalog_sha256']:raise ValueError('KNOWLEDGE_CATALOG_CHANGED')
    catalog=records.check_catalog(records.load(cp))
    if catalog['volume_id']!=manifest['volume_id']:raise ValueError('KNOWLEDGE_VOLUME_ID_MISMATCH')
    return manifest,catalog

def verify_rom(folder,check=None):
    interrupted(check);before=records.sha(records.inside(folder,'VOLUME.json'))
    logical=records.verify_volume(folder,before);manifest,catalog=header(folder,before)
    expected={'VOLUME.json','CATALOG.json',*manifest['sidecars'],*(r['object'] for r in catalog['records'].values())}
    actual={p.relative_to(folder).as_posix() for p in Path(folder).rglob('*') if p.is_file()}
    if actual!=expected:raise ValueError('KNOWLEDGE_VOLUME_UNLISTED_OR_MISSING_FILES')
    indexes={}
    for name,row in manifest['sidecars'].items():
        if name.lower().endswith(('.sqlite','.db')):
            interrupted(check);indexes[name]=qualify_index(records.inside(folder,name),row['sha256'],check)
    if 'SEARCH.sqlite' not in indexes:raise ValueError('KNOWLEDGE_SEARCH_INDEX_REQUIRED')
    extraction={}
    if 'EXTRACTION.json' in manifest['sidecars']:
        ep=records.inside(folder,'EXTRACTION.json')
        if records.sha(ep)!=manifest['sidecars']['EXTRACTION.json']['sha256']:raise ValueError('KNOWLEDGE_EXTRACTION_CHANGED')
        extraction=records.load(ep)
    header(folder,before);interrupted(check)
    return {'schema':VERSION,**logical,'reader':fingerprint(),'indexes':indexes,
      'vendor_documents':sum(n.lower().endswith('.pdf') and r['kind']=='vendor-original' for n,r in catalog['records'].items()),
      'extraction':{'profile':'SEALED_ARCHIVE_PROFILE','pdftotext_version':extraction.get('pdftotext_version'),
        'documents':len(extraction.get('documents',[])),'ocr_performed':False,
        'source_languages':'PRESERVED_METADATA_OR_UNKNOWN','new_engineering_values_approved':False},
      'current_project_acceptance':False,'engineering_claim_review':'NOT_GRANTED'}

def original(folder,report,name):
    manifest,catalog=header(folder,report['manifest_sha256'])
    row=catalog['records'].get(records.safe_name(name))
    if not row:raise ValueError('KNOWLEDGE_RECORD_UNKNOWN')
    path=records.inside(folder,row['object'])
    if not path.is_file() or path.stat().st_size!=row['bytes'] or records.sha(path)!=row['sha256']:raise ValueError('KNOWLEDGE_ORIGINAL_UNAVAILABLE_OR_CHANGED')
    return path,row

def source_rows(folder,report,offset=0,limit=100):
    _,catalog=header(folder,report['manifest_sha256'])
    rows=[{'record_id':n,'source_sha256':r['sha256'],'bytes':r['bytes'],'title':r['title'],
           'revision':r.get('metadata',{}).get('revision','UNKNOWN'),'variant':r.get('metadata',{}).get('variant','UNKNOWN'),
           'language':r.get('metadata',{}).get('language','UNKNOWN'),'rights':r.get('metadata',{}).get('rights','UNREVIEWED'),
           'kind':r['kind'],'current_design_authority':False} for n,r in sorted(catalog['records'].items())
          if n.lower().endswith('.pdf') and r['kind']=='vendor-original']
    return {'sources':rows[offset:offset+limit],'total':len(rows),'reader':report['reader']}

def search(folder,report,query,limit=30):
    if not isinstance(query,str) or not 1<=len(query)<=200 or type(limit)!=int or not 1<=limit<=40:raise ValueError('KNOWLEDGE_QUERY_LIMIT')
    manifest,catalog=header(folder,report['manifest_sha256']);vendor=[n for n,r in catalog['records'].items() if n.endswith('.pdf') and r['kind']=='vendor-original']
    if not vendor:return {'hits':[],'gaps':['NO_VENDOR_PDFS_IN_ARCHIVE']}
    terms=re.findall(r'\w+',query,re.UNICODE)[:20]
    if not terms:return {'hits':[],'gaps':['NO_SEARCH_TERMS']}
    names=','.join('?' for _ in vendor);params=[]
    with closing(pinned_index(records.inside(folder,'SEARCH.sqlite'),manifest['sidecars']['SEARCH.sqlite']['sha256'])) as con:
        if re.search('[\u3400-\u9fff]',query):
            sql='SELECT record_path,page_index,page_label,substr(body,1,500) FROM pages WHERE instr(body,?)>0 AND record_path IN ('+names+') LIMIT ?';params=[query,*vendor,limit]
        else:
            match=' AND '.join('"'+x.replace('"','""')+'"' for x in terms)
            sql="SELECT record_path,page_index,page_label,snippet(pages,3,'[',']',' ... ',25) FROM pages WHERE pages MATCH ? AND record_path IN ("+names+') ORDER BY bm25(pages),record_path,page_index LIMIT ?';params=[match,*vendor,limit]
        rows=con.execute(sql,params).fetchall()
    hits=[]
    for name,page,label,excerpt in rows:
        try:_,row=original(folder,report,name);state='ARCHIVE_ORIGINAL_VERIFIED'
        except (ValueError,OSError):row=catalog['records'][name];state='ORIGINAL_UNAVAILABLE'
        hits.append({'record_id':name,'page_index':int(page),'page_label':label,'source_sha256':row['sha256'],
          'excerpt':excerpt if state=='ARCHIVE_ORIGINAL_VERIFIED' else None,'state':state,
          'text_basis':'SEALED_SEARCH_DERIVATIVE','current_design_authority':False})
    header(folder,report['manifest_sha256'])
    return {'hits':hits,'gaps':[],'ranking':'LEXICAL_OR_LITERAL_HAN_SUBSTRING','model_calls':0,'reader':report['reader']}

def scan_baseline(path,expected,check=None):
    path=regular(path)
    if path.stat().st_size>MAX_ARCHIVE or records.sha(path)!=expected:raise ValueError('KNOWLEDGE_BASELINE_ARCHIVE_CHANGED_OR_LIMIT')
    with zipfile.ZipFile(path) as z:
        info=z.infolist();names=[x.filename for x in info]
        if len(names)>5000 or len(names)!=len(set(names)) or sum(x.file_size for x in info)>MAX_EXPANDED:raise ValueError('KNOWLEDGE_BASELINE_ZIP_LIMIT')
        prefix='Ledger_User_Data_Archive/';manifest_name=prefix+'ARCHIVE_MANIFEST.json'
        if manifest_name not in names:raise ValueError('KNOWLEDGE_BASELINE_REQUIRES_SEALED_USER_ARCHIVE')
        manifest=records.strict(z.read(manifest_name))
        if manifest.get('schema')!='arc.sealed-user-archive/1':raise ValueError('KNOWLEDGE_BASELINE_SCHEMA')
        for name,row in manifest['files'].items():
            interrupted(check);records.safe_name(name)
            entry=z.getinfo(prefix+name)
            if entry.is_dir() or (entry.external_attr>>16)&0o170000==0o120000 or entry.flag_bits&1:raise ValueError('KNOWLEDGE_BASELINE_UNSAFE_MEMBER')
            raw=z.read(entry)
            if len(raw)!=row['bytes'] or hashlib.sha256(raw).hexdigest()!=row['sha256']:raise ValueError('KNOWLEDGE_BASELINE_MEMBER_CHANGED')
        selected=[]
        for name,row in sorted(manifest['files'].items()):
            if name.startswith('Original_Ledger/') and (name.endswith(('.kicad_pcb','.kicad_sch','.kicad_pro')) or name.endswith('docs/HARDWARE_STATUS.md') or '/firmware/' in name and name.endswith(('.c','.h','.v','.sv'))):
                rel=name.removeprefix('Original_Ledger/')
                selected.append({'path':rel,'sha256':row['sha256'],'bytes':row['bytes']})
        native=[r for r in selected if r['path'].endswith('.kicad_pcb')]
        if len(native)!=1:raise ValueError('KNOWLEDGE_BASELINE_NATIVE_SELECTION_REQUIRED')
        if records.sha(path)!=expected:raise ValueError('KNOWLEDGE_BASELINE_CHANGED_DURING_SCAN')
        return {'schema':'arc.knowledge-baseline/1','archive_sha256':expected,'archive_manifest_sha256':hashlib.sha256(z.read(manifest_name)).hexdigest(),
          'working_version':'V1','selection_state':'REFERENCE_SNAPSHOT_REQUIRES_OWNER_SELECTION',
          'original_files':manifest['original_ledger_files'],'verified_manifest_entries':len(manifest['files']),
          'selected_sources':selected,'native_boards':native,'editable_development_history_imported':False,
          'project_source_promoted':False,'physical_qualification':False,'reader':fingerprint()}
