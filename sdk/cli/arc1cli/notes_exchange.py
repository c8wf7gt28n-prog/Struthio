"""Bounded inert text exchanges over the existing concern catalog.

The catalog note is the working copy. Stored upstream bytes are reconciliation
bases, never accepted sources or executable configuration. Same-profile export
preserves text; it does not promise semantic conversion between applications.
"""
from __future__ import annotations
import base64,hashlib,json,os,posixpath,re,stat,time,uuid,zipfile
from pathlib import Path
from urllib.parse import unquote,urlsplit
from .concern_catalog import Catalog,MAX_OBJECTS,MAX_NOTE

VERSION='arc.notes-exchange/1'
PROFILES={'markdown-v1':'Markdown + restricted front matter',
 'org-v1':'Org text and static links',
 'obsidian-v1':'Obsidian Markdown vault subset',
 'logseq-og-v1':'Logseq file-graph Markdown/Org subset',
 'joplin-md-v1':'Joplin Markdown + front matter'}
MAX_FILES=512;MAX_NOTES=128;MAX_TOTAL=32*1024*1024;MAX_ASSET=8*1024*1024
TEXT_LIMIT=128*1024
IGNORED={'.git','.obsidian','.logseq','logseq','node_modules','.ledger','.trash'}
ASSETS={'.png','.jpg','.jpeg','.gif','.webp','.pdf','.txt','.csv','.bin'}
def encoded(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)
def digest(v):return hashlib.sha256(v if isinstance(v,bytes) else encoded(v).encode()).hexdigest()
def rule_hash():return digest([digest(Path(__file__).read_bytes()),digest(Path(__file__).with_name('concern_catalog.py').read_bytes())])
def clean_path(value):
    if not isinstance(value,str) or not value or len(value)>400 or '\\' in value or '\0' in value or ':' in value or value.startswith('/'):raise ValueError('NOTES_PATH_PROFILE')
    if any(p in ('','.','..') or p.startswith('.') for p in value.split('/')):raise ValueError('NOTES_PATH_PROFILE')
    return value
def scalar(v):
    v=v.strip()
    if v.startswith('"'):
        try:return json.loads(v)
        except ValueError:return v
    if v.startswith("'") and v.endswith("'"):return v[1:-1].replace("''","'")
    if v.startswith('['):
        try:return json.loads(v)
        except ValueError:return [x.strip().strip('"').strip("'") for x in v[1:-1].split(',') if x.strip()] if v.endswith(']') else v
    return v
def prose(body):
    """Suppress fenced/source/example text before indexing links or IDs."""
    result=[];mode=None
    for line in body.splitlines():
        head=line.lstrip();upper=head.upper()
        if mode:
            if isinstance(mode,tuple):
                if head.startswith(mode[0]*mode[1]):mode=None
            elif upper.startswith(mode):mode=None
            result.append('');continue
        if upper.startswith(('#+BEGIN_SRC','#+BEGIN_EXAMPLE')):
            mode='#+END_SRC' if upper.startswith('#+BEGIN_SRC') else '#+END_EXAMPLE';result.append('');continue
        char=head[:1]
        if char in (chr(96),'~') and head.startswith(char*3):
            mode=(char,len(head)-len(head.lstrip(char)));result.append('');continue
        result.append(line)
    return '\n'.join(result)
def parse(name,raw,profile):
    body=raw.decode('utf-8-sig').replace('\r\n','\n').replace('\r','\n')
    if len(raw)>TEXT_LIMIT or '\0' in body or any(ord(c)<32 and c not in '\n\t' for c in body):raise ValueError('NOTES_TEXT_PROFILE_OR_LIMIT')
    meta={};warnings=[];rows=body.splitlines();org=name.lower().endswith('.org')
    if rows and rows[0]=='---' and not org:
        try:end=rows.index('---',1)
        except ValueError:end=0;warnings.append('UNCLOSED_FRONT_MATTER_RETAINED')
        key=None
        for line in rows[1:end]:
            m=re.fullmatch(r'([A-Za-z_][\w ?-]*):\s*(.*)',line)
            if m:
                key=m[1];value=scalar(m[2])
                if key in meta:warnings.append('DUPLICATE_METADATA_KEY_RETAINED')
                meta[key]=[] if value=='' else value
            elif key and re.fullmatch(r'\s+-\s+.+',line) and isinstance(meta[key],list):meta[key].append(scalar(line.strip()[2:]))
            elif line.strip():warnings.append('COMPLEX_YAML_RETAINED_UNINTERPRETED')
        if any('!!' in x or re.search(r'(^|\s)[&*][\w-]+',x) for x in rows[1:end]):warnings.append('YAML_TAGS_ALIASES_INERT')
    if org:
        for key,value in re.findall(r'^#\+([A-Za-z_]+):\s*(.*)$',body,re.M):meta[key.lower()]=value
        ids=re.findall(r'^\s*:ID:\s*(.+)$',prose(body),re.M)
        if ids:meta['ids']=ids
        if re.search(r'^#\+(?:BEGIN_SRC|CALL|INCLUDE|BIND):?',body,re.M|re.I):warnings.append('ORG_CODE_INCLUDE_AND_CALLS_INERT')
    if profile=='logseq-og-v1':
        for key,value in re.findall(r'^([A-Za-z_][\w-]*)::\s*(.*)$',body,re.M):meta[key]=value
        meta['block_ids']=re.findall(r'^\s+id::\s*(\S+)\s*$',prose(body),re.M)
        if re.search(r'\{\{(?:query|renderer|eval|embed)|#\+BEGIN_QUERY',body,re.I):warnings.append('LOGSEQ_QUERIES_EMBEDS_INERT')
    if re.search(r'<[A-Za-z!/]|javascript:|data:|obsidian:|joplin:',body,re.I):warnings.append('ACTIVE_MARKUP_OR_URI_RETAINED_AS_TEXT')
    if '!'+ '[[' in body or re.search(r'!\[[^\]]*\]',body):warnings.append('EMBEDS_ARE_REFERENCES_ONLY')
    if '\r' in raw.decode('utf-8-sig') or raw.startswith(b'\xef\xbb\xbf'):warnings.append('WORKING_TEXT_NORMALIZED_ORIGINAL_BYTES_RETAINED')
    title=meta.get('title') or next((m.group(1) for line in rows if (m:=re.match(r'^#{1,6}\s+(.+)',line))),None) or Path(name).stem
    if not isinstance(title,str):title=Path(name).stem;warnings.append('NONSCALAR_TITLE_RETAINED')
    title=title.strip()[:240] or Path(name).stem
    return {'path':name,'body':body,'title':title,'metadata':meta,'warnings':sorted(set(warnings)),'sha256':digest(raw),'body_sha256':digest(body.encode())}
def links(note,profile):
    """Conservative static references; code blocks are deliberately not links."""
    text=re.sub(chr(96)+r'[^'+chr(96)+r'\n]*'+chr(96),'',prose(note['body']));result=[]
    if note['path'].lower().endswith('.org'):
        result += [{'target':t,'kind':'org'} for t in re.findall(r'\[\[([^\]\n]+)\](?:\[[^\]\n]*\])?\]',text)]
    else:
        result += [{'target':t.split('|',1)[0],'kind':'wiki'} for t in re.findall(r'\[\[([^\]\n]+)\]\]',text)]
        result += [{'target':t.strip('<>'),'kind':'markdown'} for t in re.findall(r'!?\[[^\]\n]*\]\(([^)\n]+)\)',text)]
    if profile=='logseq-og-v1':result += [{'target':'id:'+t,'kind':'block'} for t in re.findall(r'\(\(([a-fA-F0-9-]{36})\)\)',text)]
    if len(result)>512:raise ValueError('NOTES_LINK_COUNT_LIMIT')
    return result
def resolve(notes,assets,profile):
    paths={n['path']:n for n in notes};ids={};aliases={}
    for n in notes:
        for alias in n.get('aliases',[]):aliases.setdefault(alias,[]).append(n['key'])
        identifiers=n['metadata'].get('ids',[]) if n['path'].lower().endswith('.org') else []
        if profile=='logseq-og-v1':identifiers=identifiers+n['metadata'].get('block_ids',[])
        for ident in identifiers:ids.setdefault(ident,[]).append(n['key'])
    result=[]
    for n in notes:
        for link in links(n,profile):
            if len(result)>=2048:raise ValueError('NOTES_GRAPH_LINK_COUNT_LIMIT')
            target=unquote(link['target']);anchor=''
            if target.startswith('id:'):
                candidates=ids.get(target[3:],[]);kind='note'
            else:
                if target.startswith('file:'):target=target[5:]
                if '::' in target:target,anchor=target.split('::',1)
                if urlsplit(target).scheme or target.startswith(('/','\\')):result.append({**link,'source':n['key'],'state':'EXTERNAL_INERT'});continue
                if '#' in target:target,anchor=target.split('#',1)
                if not target:target=n['path']
                try:clean_path(posixpath.normpath(posixpath.join(posixpath.dirname(n['path']),target)))
                except ValueError:result.append({**link,'source':n['key'],'state':'OUTSIDE_PROFILE'});continue
                relative=posixpath.normpath(posixpath.join(posixpath.dirname(n['path']),target))
                exact=[relative] if link['kind']!='wiki' else [target,relative]
                expanded=[v+s for v in exact for s in ('','.md','.org')]
                found=list(dict.fromkeys(v for v in expanded if v in paths))
                if not found and link['kind']=='wiki':found=[p for p in paths if Path(p).stem==target]
                candidates=[paths[p]['key'] for p in found];kind='note';basis='CURRENT_PATH'
                if not candidates:
                    candidates=list(dict.fromkeys(key for path in expanded for key in aliases.get(path,[])));basis='PRIOR_PATH_ALIAS'
                    if not candidates and link['kind']=='wiki':candidates=list(dict.fromkeys(key for path,keys in aliases.items() if Path(path).stem==target for key in keys))
                if not candidates and relative in assets:candidates=[relative];kind='attachment';basis='CURRENT_PATH'
            state='RESOLVED' if len(candidates)==1 else 'AMBIGUOUS' if candidates else 'MISSING'
            result.append({**link,'source':n['key'],'state':state,'target_key':candidates[0] if len(candidates)==1 else None,'target_kind':kind,'resolution_basis':'ID' if target.startswith('id:') else basis,'anchor':anchor,'anchor_state':'UNVERIFIED' if anchor else 'NONE'})
    return result
def scan(root,profile):
    if profile not in PROFILES:raise ValueError('NOTES_PROFILE_UNSUPPORTED')
    root=Path(root).absolute()
    if not root.is_dir() or any(p.is_symlink() for p in (root,*root.parents)):raise ValueError('NOTES_SOURCE_DIRECTORY_REQUIRED')
    files={};ignored=[];total=0;count=0;directories=0
    for folder,dirs,names in os.walk(root,followlinks=False):
        dirs.sort();names.sort();directories+=len(dirs)
        if directories>MAX_FILES:raise ValueError('NOTES_DIRECTORY_COUNT_LIMIT')
        for d in list(dirs):
            p=Path(folder)/d;relative=p.relative_to(root).as_posix()
            if p.is_symlink():raise ValueError('NOTES_SYMLINK_REFUSED')
            if d.startswith('.') or d in IGNORED:dirs.remove(d);ignored.append(relative+'/')
        for name in names:
            p=Path(folder)/name;relative=p.relative_to(root).as_posix();count+=1
            if count>MAX_FILES:raise ValueError('NOTES_FILE_COUNT_LIMIT')
            if p.is_symlink():raise ValueError('NOTES_SYMLINK_REFUSED')
            if name.startswith('.'):ignored.append(relative);continue
            clean_path(relative)
            fd=os.open(p,os.O_RDONLY|getattr(os,'O_NOFOLLOW',0)|getattr(os,'O_NONBLOCK',0))
            try:
                info=os.fstat(fd)
                if not stat.S_ISREG(info.st_mode) or info.st_size>MAX_ASSET:raise ValueError('NOTES_FILE_TYPE_OR_SIZE_LIMIT')
                with os.fdopen(fd,'rb',closefd=False) as stream:raw=stream.read(MAX_ASSET+1)
                if len(raw)!=info.st_size:raise ValueError('NOTES_SOURCE_CHANGED_DURING_READ')
            finally:os.close(fd)
            total+=len(raw)
            if total>MAX_TOTAL:raise ValueError('NOTES_TOTAL_SIZE_LIMIT')
            files[relative]=raw
    notes=[];assets={};sidecar={};alias_hints={}
    if 'ledger-notes.json' in files:
        # Duplicate members must not redefine exported identities.
        def pairs(rows):
            d={}
            for k,v in rows:
                if k in d:raise ValueError('NOTES_DUPLICATE_MANIFEST_MEMBER')
                d[k]=v
            return d
        value=json.loads(files['ledger-notes.json'],object_pairs_hook=pairs)
        if value.get('schema')!=VERSION or value.get('profile')!=profile:raise ValueError('NOTES_MANIFEST_PROFILE')
        for row in value.get('notes',[]):
            path=clean_path(row['path']);key=row['key']
            if path in sidecar or not isinstance(key,str) or not re.fullmatch('[a-f0-9]{32}',key) or key in sidecar.values():raise ValueError('NOTES_MANIFEST_IDENTITY')
            sidecar[path]=key
            aliases=row.get('aliases',[])
            if not isinstance(aliases,list) or len(aliases)>32:raise ValueError('NOTES_ALIAS_LIMIT')
            alias_hints[path]=[clean_path(a) for a in aliases]
    for name,raw in files.items():
        if name=='ledger-notes.json':continue
        suffix=Path(name).suffix.lower()
        is_note=suffix=='.org' if profile=='org-v1' else suffix in ('.md','.org') if profile=='logseq-og-v1' else suffix=='.md'
        if is_note:
            n=parse(name,raw,profile);n['raw']=raw;n['hint']=sidecar.get(name);n['aliases']=alias_hints.get(name,[]);notes.append(n)
        elif suffix in ASSETS:assets[name]=raw
        else:ignored.append(name)
    if len(notes)>MAX_NOTES:raise ValueError('NOTES_NOTE_COUNT_LIMIT')
    fingerprint=digest({k:digest(v) for k,v in sorted(files.items())})
    return {'root':str(root),'profile':profile,'notes':notes,'assets':assets,'ignored':ignored,'fingerprint':fingerprint}

class Exchange:
    def __init__(self,catalog):
        self.catalog=catalog
        with catalog.db() as db:
            db.executescript('''
             CREATE TABLE IF NOT EXISTS note_exchange_collections(id TEXT PRIMARY KEY,profile TEXT,root TEXT,parent TEXT,generation INTEGER);
             CREATE TABLE IF NOT EXISTS note_exchange_items(collection_id TEXT,key TEXT,object_id TEXT,path TEXT,raw BLOB,metadata TEXT,deleted INTEGER,PRIMARY KEY(collection_id,key));
             CREATE TABLE IF NOT EXISTS note_exchange_assets(collection_id TEXT,path TEXT,raw BLOB,present INTEGER,PRIMARY KEY(collection_id,path));
             CREATE TABLE IF NOT EXISTS note_exchange_aliases(collection_id TEXT,key TEXT,path TEXT,PRIMARY KEY(collection_id,key,path));
             CREATE TABLE IF NOT EXISTS note_exchange_plans(id TEXT PRIMARY KEY,payload TEXT,result TEXT,at REAL);
             CREATE TABLE IF NOT EXISTS note_exchange_conflicts(collection_id TEXT,key TEXT,incoming BLOB,path TEXT,metadata TEXT,PRIMARY KEY(collection_id,key));
            ''')
    def collections(self):
        with self.catalog.db() as db:return [dict(r) for r in db.execute('SELECT c.*,o.title FROM note_exchange_collections c JOIN objects o ON o.id=c.id ORDER BY o.title')]
    def _items(self,db,collection):
        return [dict(r) for r in db.execute('SELECT * FROM note_exchange_items WHERE collection_id=? ORDER BY key',(collection,))]
    def _token(self,db,collection,parent):
        objects=[]
        for r in self._items(db,collection):
            o=self.catalog._object(db,r['object_id'])
            n=db.execute('SELECT body,version FROM notes WHERE object_id=?',(r['object_id'],)).fetchone()
            drafts=[dict(x) for x in db.execute('SELECT * FROM drafts WHERE object_id=? ORDER BY writer',(r['object_id'],))]
            pending=db.execute('SELECT incoming,path,metadata FROM note_exchange_conflicts WHERE collection_id=? AND key=?',(collection,r['key'])).fetchone()
            objects.append([r['key'],r['path'],digest(r['raw']),r['deleted'],o,dict(n) if n else None,drafts,[digest(pending[0]),pending[1],pending[2]] if pending else None])
        return digest([self.catalog._object(db,parent),objects])
    def preview(self,root,profile,collection=None,parent='inbox'):
        incoming=scan(root,profile);created=False
        with self.catalog.db() as db:
            db.execute('BEGIN IMMEDIATE')
            if collection is None:
                row=db.execute('SELECT id FROM note_exchange_collections WHERE root=? AND profile=?',(incoming['root'],profile)).fetchone()
                collection=row[0] if row else 'owner:'+uuid.uuid4().hex
            source=db.execute('SELECT * FROM note_exchange_collections WHERE id=?',(collection,)).fetchone()
            if source:
                source=dict(source)
                if source['profile']!=profile:raise ValueError('NOTES_COLLECTION_PROFILE_MISMATCH')
                parent=source['parent']
            else:
                if not collection.startswith('owner:'):raise ValueError('NOTES_COLLECTION_UNAVAILABLE')
                if len(self.collections())>=32:raise ValueError('NOTES_COLLECTION_LIMIT')
                source={'generation':0};created=True
            if created and not incoming['notes']:raise ValueError('NOTES_EMPTY_NEW_COLLECTION')
            if self.catalog._object(db,parent)['state']=='archived':raise ValueError('NOTES_DESTINATION_ARCHIVED')
            old=self._items(db,collection);bykey={r['key']:r for r in old};used=set();entries=[]
            for n in incoming['notes']:
                prior=bykey.get(n['hint']) if n['hint'] else None
                if prior is None:prior=next((r for r in old if r['path']==n['path'] and r['key'] not in used),None)
                if prior is None:
                    matches=[r for r in old if r['key'] not in used and r['path'] not in {x['path'] for x in incoming['notes']} and digest(r['raw'])==n['sha256']]
                    if len(matches)==1:prior=matches[0]
                key=prior['key'] if prior else digest([collection,n['hint'] or n['path']])[:32]
                if key in used:raise ValueError('NOTES_AMBIGUOUS_IDENTITY')
                used.add(key);n['key']=key
                history=[r[0] for r in db.execute('SELECT path FROM note_exchange_aliases WHERE collection_id=? AND key=?',(collection,key))]
                n['aliases']=sorted(set(n['aliases']+history+([prior['path']] if prior and prior['path']!=n['path'] else [])))
                if len(n['aliases'])>32:raise ValueError('NOTES_ALIAS_LIMIT')
                if not prior:action='NEW';object_id='owner:'+uuid.uuid5(uuid.NAMESPACE_URL,collection+':'+key).hex
                else:
                    object_id=prior['object_id'];o=self.catalog._object(db,object_id)
                    saved=db.execute('SELECT body,version FROM notes WHERE object_id=?',(object_id,)).fetchone()
                    base=parse(prior['path'],prior['raw'],profile);draft=db.execute('SELECT 1 FROM drafts WHERE object_id=?',(object_id,)).fetchone()
                    changed=n['sha256']!=digest(prior['raw'])
                    local=saved['body']!=base['body'] or o['title']!=base['title']
                    conflict=changed and (draft or local and (saved['body']!=n['body'] or o['title']!=n['title']))
                    pending=db.execute('SELECT incoming FROM note_exchange_conflicts WHERE collection_id=? AND key=?',(collection,key)).fetchone()
                    if pending and digest(pending[0])!=n['sha256']:raise ValueError('NOTES_RESOLVE_EXISTING_CONFLICT_FIRST')
                    action='CONFLICT_HELD' if pending else 'CONFLICT' if conflict else 'UPDATE' if changed else 'RENAME' if prior['path']!=n['path'] else 'RESTORE_REFERENCE' if prior['deleted'] else 'UNCHANGED'
                    if action=='UNCHANGED' and set(n['aliases'])!=set(history):action='ALIASES'
                entries.append({'key':key,'object_id':object_id,'path':n['path'],'old_path':prior['path'] if prior else None,'title':n['title'],'sha256':n['sha256'],'action':action,'warnings':n['warnings']})
            for r in old:
                if r['key'] not in used and not r['deleted']:entries.append({'key':r['key'],'object_id':r['object_id'],'path':r['path'],'title':self.catalog._object(db,r['object_id'])['title'],'action':'UPSTREAM_DELETED','warnings':['SAVED_NOTE_PRESERVED']})
            plan={'schema':VERSION,'id':uuid.uuid4().hex,'collection':collection,'parent':parent,'profile':profile,'root':incoming['root'],'new_collection':created,
                'generation':source['generation'],'source_fingerprint':incoming['fingerprint'],'catalog_token':self._token(db,collection,parent),'entries':entries,
                'ignored':incoming['ignored'],'assets':{p:{'sha256':digest(v),'bytes':len(v)} for p,v in incoming['assets'].items()},'graph':resolve(incoming['notes'],incoming['assets'],profile),
                'authority':'WORKING_NOTES_ONLY','execution':'NONE','conversion':'SAME_PROFILE_TEXT_ONLY','rule_hash':rule_hash()}
            db.execute('DELETE FROM note_exchange_plans WHERE result IS NULL AND at<?',(time.time()-3600,))
            for old_plan in db.execute('SELECT id,payload FROM note_exchange_plans WHERE result IS NULL').fetchall():
                prior=json.loads(old_plan['payload'])
                if all(prior[k]==plan[k] for k in ('root','profile','parent')):db.execute('DELETE FROM note_exchange_plans WHERE id=?',(old_plan['id'],))
            if db.execute('SELECT count(*) FROM note_exchange_plans').fetchone()[0]>=2048 or db.execute('SELECT count(*) FROM note_exchange_plans WHERE result IS NULL').fetchone()[0]>=8:raise ValueError('NOTES_PREVIEW_LIMIT')
            db.execute('INSERT INTO note_exchange_plans VALUES(?,?,NULL,?)',(plan['id'],encoded(plan),time.time()))
        return {**plan,'digest':digest(plan)}
    def _plan(self,db,ident,expected):
        row=db.execute('SELECT payload,result,at FROM note_exchange_plans WHERE id=?',(ident,)).fetchone()
        if not row:raise ValueError('NOTES_PLAN_UNAVAILABLE')
        p=json.loads(row['payload'])
        if digest(p)!=expected or p.get('rule_hash')!=rule_hash():raise ValueError('NOTES_PLAN_CHANGED')
        return p,json.loads(row['result']) if row['result'] else None,row['at']
    def plan_note(self,ident,expected,key):
        with self.catalog.db() as db:p,done,at=self._plan(db,ident,expected)
        incoming=scan(p['root'],p['profile'])
        if incoming['fingerprint']!=p['source_fingerprint']:raise ValueError('NOTES_SOURCE_CHANGED_REVIEW_AGAIN')
        entry=next((e for e in p['entries'] if e['key']==key),None)
        if not entry:raise ValueError('NOTES_PLAN_ITEM_UNAVAILABLE')
        n=next((n for n in incoming['notes'] if n['path']==entry['path']),None)
        return {'entry':entry,'incoming_body':n['body'] if n else None,'metadata':n['metadata'] if n else {},'content_is_inert':True}
    def commit(self,ident,expected):
        with self.catalog.db() as db:
            p,done,at=self._plan(db,ident,expected)
            if done:return {**done,'replayed':True}
        if time.time()-at>3600:raise ValueError('NOTES_PLAN_EXPIRED')
        incoming=scan(p['root'],p['profile'])
        if incoming['fingerprint']!=p['source_fingerprint']:raise ValueError('NOTES_SOURCE_CHANGED_REVIEW_AGAIN')
        lookup={n['path']:n for n in incoming['notes']}
        with self.catalog.db() as db:
            db.execute('BEGIN IMMEDIATE');p,done,at=self._plan(db,ident,expected)
            if done:return {**done,'replayed':True}
            if self._token(db,p['collection'],p['parent'])!=p['catalog_token']:raise ValueError('NOTES_LOCAL_CHANGED_REVIEW_AGAIN')
            source=db.execute('SELECT generation FROM note_exchange_collections WHERE id=?',(p['collection'],)).fetchone()
            if (source[0] if source else 0)!=p['generation']:raise ValueError('NOTES_COLLECTION_CHANGED')
            additions=sum(e['action']=='NEW' for e in p['entries'])+int(p['new_collection'])
            if db.execute('SELECT count(*) FROM objects').fetchone()[0]+additions>MAX_OBJECTS:raise ValueError('NOTES_CATALOG_LIMIT')
            if p['new_collection']:
                db.execute('INSERT INTO objects VALUES(?,?,?,?,?,1)',(p['collection'],'collection',Path(p['root']).name[:240] or 'Imported notes','Optional '+PROFILES[p['profile']]+' exchange; working notes, no source acceptance.','active'))
                db.execute('INSERT INTO relations VALUES(?,?,?)',(p['collection'],'part_of',p['parent']))
                db.execute('INSERT INTO note_exchange_collections VALUES(?,?,?,?,0)',(p['collection'],p['profile'],p['root'],p['parent']))
                self.catalog._index(db,p['collection'])
            counts={}
            for e in p['entries']:
                action=e['action'];counts[action]=counts.get(action,0)+1
                if action in ('UNCHANGED','CONFLICT_HELD'):continue
                if action=='UPSTREAM_DELETED':
                    db.execute('UPDATE note_exchange_items SET deleted=1 WHERE collection_id=? AND key=?',(p['collection'],e['key']));continue
                n=lookup[e['path']];old=db.execute('SELECT * FROM note_exchange_items WHERE collection_id=? AND key=?',(p['collection'],e['key'])).fetchone()
                if action=='CONFLICT':
                    db.execute('INSERT OR IGNORE INTO note_exchange_conflicts VALUES(?,?,?,?,?)',(p['collection'],e['key'],n['raw'],n['path'],encoded(n['metadata'])));continue
                if action=='NEW':
                    db.execute('INSERT INTO objects VALUES(?,?,?,?,?,1)',(e['object_id'],'note',n['title'],'Imported working note; source acceptance is separate.','active'))
                    db.execute('INSERT INTO relations VALUES(?,?,?)',(e['object_id'],'part_of',p['collection']))
                    db.execute('INSERT INTO notes VALUES(?,?,1)',(e['object_id'],n['body']))
                else:
                    base=parse(old['path'],old['raw'],p['profile']);o=self.catalog._object(db,e['object_id'])
                    current=db.execute('SELECT body FROM notes WHERE object_id=?',(e['object_id'],)).fetchone()[0]
                    if current==base['body'] and current!=n['body']:db.execute('UPDATE notes SET body=?,version=version+1 WHERE object_id=?',(n['body'],e['object_id']))
                    if o['title']==base['title'] and o['title']!=n['title']:db.execute('UPDATE objects SET title=?,version=version+1 WHERE id=?',(n['title'],e['object_id']))
                db.execute('INSERT OR REPLACE INTO note_exchange_items VALUES(?,?,?,?,?,?,0)',(p['collection'],e['key'],e['object_id'],n['path'],n['raw'],encoded(n['metadata'])))
                history=([old['path']] if old and old['path']!=n['path'] else [])+n['aliases']
                for alias in history:db.execute('INSERT OR IGNORE INTO note_exchange_aliases VALUES(?,?,?)',(p['collection'],e['key'],alias))
                self.catalog._index(db,e['object_id'])
            old_assets={r['path']:digest(r['raw']) for r in db.execute('SELECT path,raw FROM note_exchange_assets WHERE collection_id=? AND present=1',(p['collection'],))}
            new_assets={k:digest(v) for k,v in incoming['assets'].items()}
            # Retain removed attachment bytes for surviving local notes.
            db.execute('UPDATE note_exchange_assets SET present=0 WHERE collection_id=?',(p['collection'],))
            for name,raw in incoming['assets'].items():db.execute('INSERT OR REPLACE INTO note_exchange_assets VALUES(?,?,?,1)',(p['collection'],name,raw))
            changed=any(e['action'] not in ('UNCHANGED','CONFLICT_HELD') for e in p['entries']) or old_assets!=new_assets
            if changed:
                db.execute('UPDATE note_exchange_collections SET root=?,generation=generation+1 WHERE id=?',(p['root'],p['collection']))
                self.catalog._event(db,'notes_exchange',p['collection'],encoded(counts))
            result={'schema':VERSION,'state':'COMMITTED','collection':p['collection'],'counts':counts,'replayed':False,'originals_modified':False,'accepted_facts_created':0}
            if scan(p['root'],p['profile'])['fingerprint']!=p['source_fingerprint']:raise ValueError('NOTES_SOURCE_CHANGED_DURING_COMMIT')
            db.execute('UPDATE note_exchange_plans SET result=? WHERE id=?',(encoded(result),ident))
        return result
    def get(self,collection):
        with self.catalog.db() as db:
            db.execute('BEGIN')
            source=db.execute('SELECT * FROM note_exchange_collections WHERE id=?',(collection,)).fetchone()
            if not source:raise ValueError('NOTES_COLLECTION_UNAVAILABLE')
            notes=[]
            for item in self._items(db,collection):
                o=self.catalog._object(db,item['object_id']);saved=db.execute('SELECT body,version FROM notes WHERE object_id=?',(item['object_id'],)).fetchone();parsed=parse(item['path'],saved['body'].encode(),source['profile'])
                aliases=[r[0] for r in db.execute('SELECT path FROM note_exchange_aliases WHERE collection_id=? AND key=?',(collection,item['key']))]
                notes.append({**parsed,'title':o['title'],'key':item['key'],'object_id':item['object_id'],'aliases':aliases,'version':saved['version'],'upstream_deleted':bool(item['deleted']),'pending_conflict':db.execute('SELECT 1 FROM note_exchange_conflicts WHERE collection_id=? AND key=?',(collection,item['key'])).fetchone() is not None})
            assets={r['path']:{'sha256':digest(r['raw']),'bytes':len(r['raw']),'upstream_missing':not bool(r['present'])} for r in db.execute('SELECT path,raw,present FROM note_exchange_assets WHERE collection_id=?',(collection,))}
        return {'schema':VERSION,'collection':collection,'profile':source['profile'],'generation':source['generation'],'notes':notes,'assets':assets,'links':resolve(notes,assets,source['profile']),'authority':'WORKING_NOTES_ONLY'}
    def conflict(self,collection,key):
        with self.catalog.db() as db:
            row=db.execute('SELECT * FROM note_exchange_conflicts WHERE collection_id=? AND key=?',(collection,key)).fetchone()
            if not row:raise ValueError('NOTES_CONFLICT_UNAVAILABLE')
            return {'key':key,'path':row['path'],'body':parse(row['path'],row['incoming'],next(c['profile'] for c in self.collections() if c['id']==collection))['body'],'sha256':digest(row['incoming'])}
    def resolve(self,collection,key,expected,version,choice):
        if choice not in ('keep-local','use-incoming'):raise ValueError('NOTES_CONFLICT_CHOICE')
        with self.catalog.db() as db:
            db.execute('BEGIN IMMEDIATE')
            pending=db.execute('SELECT * FROM note_exchange_conflicts WHERE collection_id=? AND key=?',(collection,key)).fetchone()
            item=db.execute('SELECT * FROM note_exchange_items WHERE collection_id=? AND key=?',(collection,key)).fetchone()
            if not pending or not item or digest(pending['incoming'])!=expected:raise ValueError('NOTES_CONFLICT_CHANGED')
            saved=db.execute('SELECT version FROM notes WHERE object_id=?',(item['object_id'],)).fetchone()
            if not saved or saved[0]!=version:raise ValueError('NOTES_LOCAL_CHANGED_REVIEW_AGAIN')
            if choice=='use-incoming':
                if db.execute('SELECT 1 FROM drafts WHERE object_id=?',(item['object_id'],)).fetchone():raise ValueError('NOTES_RECOVERY_DRAFT_PRESENT')
                profile=db.execute('SELECT profile FROM note_exchange_collections WHERE id=?',(collection,)).fetchone()[0]
                n=parse(pending['path'],pending['incoming'],profile)
                db.execute('UPDATE notes SET body=?,version=version+1 WHERE object_id=?',(n['body'],item['object_id']))
                db.execute('UPDATE objects SET title=?,version=version+1 WHERE id=?',(n['title'],item['object_id']))
                self.catalog._index(db,item['object_id'])
            if item['path']!=pending['path']:db.execute('INSERT OR IGNORE INTO note_exchange_aliases VALUES(?,?,?)',(collection,key,item['path']))
            db.execute('UPDATE note_exchange_items SET raw=?,path=?,metadata=? WHERE collection_id=? AND key=?',(pending['incoming'],pending['path'],pending['metadata'],collection,key))
            db.execute('DELETE FROM note_exchange_conflicts WHERE collection_id=? AND key=?',(collection,key))
            db.execute('UPDATE note_exchange_collections SET generation=generation+1 WHERE id=?',(collection,))
            self.catalog._event(db,'notes_conflict_'+choice,item['object_id'])
        return {'state':'RESOLVED','choice':choice,'object_id':item['object_id'],'accepted_facts_created':0}
    def export(self,collection,destination):
        value=self.get(collection);data={};warnings=[]
        with self.catalog.db() as db:
            for item in self._items(db,collection):
                note=next(n for n in value['notes'] if n['key']==item['key'])
                base=parse(item['path'],item['raw'],value['profile'])
                data[clean_path(item['path'])]=item['raw'] if note['body']==base['body'] else note['body'].encode()
                if note['body']!=base['body']:warnings.append({'path':item['path'],'gap':'EDITED_WORKING_TEXT_EXPORTED_AS_UTF8_LF'})
                if note['pending_conflict']:warnings.append({'path':item['path'],'gap':'UNRESOLVED_INCOMING_EXCLUDED_CURRENT_NOTE_EXPORTED'})
                if note['upstream_deleted']:warnings.append({'path':item['path'],'gap':'UPSTREAM_DELETION_DID_NOT_DELETE_SAVED_NOTE'})
            for row in db.execute('SELECT path,raw FROM note_exchange_assets WHERE collection_id=?',(collection,)):data[clean_path(row['path'])]=row['raw']
        if any(l.get('resolution_basis')=='PRIOR_PATH_ALIAS' and l['state']=='RESOLVED' for l in value['links']):warnings.append({'gap':'LEDGER_PATH_ALIASES_REQUIRE_SIDECAR_OTHER_APPS_MAY_NOT_RESOLVE'})
        if any(n['title']!=parse(n['path'],n['body'].encode(),value['profile'])['title'] for n in value['notes']):warnings.append({'gap':'CATALOG_TITLE_RETAINED_IN_SIDECAR_BODY_NOT_REWRITTEN'})
        if any(a['upstream_missing'] for a in value['assets'].values()):warnings.append({'gap':'REMOVED_ATTACHMENTS_RETAINED_FOR_SAVED_NOTES'})
        manifest={'schema':VERSION,'profile':value['profile'],'notes':[{'path':n['path'],'key':n['key'],'title':n['title'],'aliases':n['aliases'],'upstream_deleted':n['upstream_deleted']} for n in value['notes']],
            'files':{p:{'sha256':digest(v),'bytes':len(v)} for p,v in sorted(data.items())},'warnings':warnings,'authority':'WORKING_NOTES_ONLY','excluded':['recovery drafts','unresolved incoming versions','application plugins/configuration','credentials'],'conversion':'SAME_PROFILE_TEXT_ONLY'}
        data['ledger-notes.json']=(encoded(manifest)+'\n').encode()
        if digest(self.get(collection))!=digest(value):raise ValueError('NOTES_EXPORT_CHANGED_REVIEW_AGAIN')
        destination=Path(destination).absolute()
        if destination.suffix.lower()!='.zip' or not destination.parent.is_dir() or any(p.is_symlink() for p in (destination,*destination.parents)):raise ValueError('NOTES_EXPORT_DESTINATION')
        with destination.open('xb') as stream:
            with zipfile.ZipFile(stream,'w',compression=zipfile.ZIP_DEFLATED) as z:
                for name,raw in sorted(data.items()):
                    info=zipfile.ZipInfo(name);info.create_system=3;info.external_attr=0o100644<<16;info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,raw)
        return {'schema':VERSION,'state':'EXPORTED','path':str(destination),'sha256':digest(destination.read_bytes()),'files':len(data),'warnings':warnings,'originals_modified':False}
