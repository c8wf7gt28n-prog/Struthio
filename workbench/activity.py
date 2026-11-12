"""Durable ordered local journal. Sequence is commit order, not wall-clock order."""
from __future__ import annotations
import hashlib,json,os,time,re,uuid,sqlite3
from pathlib import Path
from .session import config_dir

_ERRORS={}
OBSERVER_OPERATIONS=frozenset({
 'memory.cabinet','ledger.session.read','ledger.cabinet.actions','ledger.cabinet','ledger.cabinet.get','ledger.explore','ledger.operations','ledger.machine',
 'documents.list','documents.get','documents.interpret','documents.render',
 'agent.status','agent.list','conditions.list','conditions.get','helpers.list','helpers.get','ledger.related','ledger.browse',
 'ledger.organizer','intake.package.get','intake.package.list',
 'ledger.trail.list','ledger.trail.inspect','ledger.trail.job','ledger.resources','ledger.resources.observation','ledger.work.status','ledger.object.inspect','ledger.object.current','ledger.object.action',
 'ledger.windows.status','ledger.windows.list','ledger.windows.snapshot',
 'memory.status','memory.profile','memory.preferences','memory.tasks','memory.task','memory.feedback.list','memory.conversation','memory.lessons','stac.status','stac.history',
 'references.status','references.sources','references.passages','references.render.result',
 'intake.status','intake.namespaces','intake.policy','intake.batches','intake.items','intake.catalog','intake.checkpoints',
 'brain.status','brain.runtime','brain.models','brain.result',
 'slate.progress','slate.result','slate.qualifications','slate.qualification.get','slate.context.get','slate.context.check',
 'ledger.activity','ledger.context','ledger.journal.status','ledger.journal.read',
 'ledger.awareness','ledger.awareness.catch_up','ledger.journal.recover',
 'jobs.list','jobs.get','capabilities','stacy.capabilities','stacy.seed.status',
 'ledger.capabilities.search','ledger.capabilities.describe','ledger.capabilities.catalog','ledger.project.status',
 'ledger.workflow.describe','ledger.object.reference',
 # The Office and Slate rooms refresh these every few seconds; reading is not an event.
 'matrix.status','matrix.list','matrix.patterns','matrix.examples','receiving.status','receiving.deliveries','receiving.cards',
 'receiving.translate','viewer.describe','investigation.list','investigation.sheet','investigation.path','agenda.view','files.list','files.get','files.versions','files.trash_list','files.proposals','files.compare','files.find','copies.list','copies.get','copies.review','files.story','system.supports','pills.identity','pills.open','pills.list','confine.status','language.parse','stac.compile','ledger.address.kinds','intake.read','intake.item','ledger.address.read',
 # HATCH DESK D5: Log's Network stream reads these every second or two while it is open
 'network.observe','network.capture.read'})

def folder(root):
    """Legacy journal location, now used only for migration and failed delivery."""
    return config_dir()/'activity'/hashlib.sha256(str(Path(root).resolve()).encode()).hexdigest()[:20]

def redact(value,limit=300):
    text=str(value)
    text=re.sub(r'AIza[\w-]{20,}|sk-(?:proj-|ant-)?[\w-]{20,}|gh[pousr]_[\w]{20,}','[credential removed]',text)
    text=re.sub(r'(?i)(?:authorization|api[_ -]?key|token|password)\s*[:=]\s*\S+','[private value removed]',text)
    text=re.sub(r'(?:/home/|/Users/|/workspace/)[^\s]+|[A-Za-z]:\\[^\n\r]+','[local path]',text)
    return ''.join(c for c in text if ord(c)>=32 or c=='\t')[:limit]

def make_event(origin,operation,state,detail='',**refs):
    event={'schema':'arc.ledger-event/2','id':f'{time.time_ns()}-{uuid.uuid4().hex}','at':time.time(),
           'origin':redact(origin,80),'operation':redact(operation,120),'state':redact(state,60),'detail':redact(detail)}
    for key in ('job_id','evidence_id','candidate_id','correlation_id','parent_id','source_generation'):
        value=refs.get(key)
        if value is not None and re.fullmatch(r'[A-Za-z0-9_.:/-]{1,180}',str(value)):event[key]=str(value)
    if 'job_id' in event:event.setdefault('correlation_id',event['job_id'])
    return event

def ensure(db):
    # executescript would commit an enclosing job transaction.
    db.execute('CREATE TABLE IF NOT EXISTS activity_journal(seq INTEGER PRIMARY KEY AUTOINCREMENT,event_id TEXT UNIQUE NOT NULL,payload TEXT NOT NULL)')
    db.execute('CREATE TABLE IF NOT EXISTS activity_consumers(name TEXT PRIMARY KEY,cursor INTEGER NOT NULL,event_id TEXT,projection TEXT NOT NULL)')
    db.execute('CREATE TABLE IF NOT EXISTS activity_meta(key TEXT PRIMARY KEY,value TEXT NOT NULL)')

def append(db,event):
    raw=json.dumps({k:v for k,v in event.items() if k!='seq'},sort_keys=True)
    row=db.execute('SELECT seq,payload FROM activity_journal WHERE event_id=?',(event['id'],)).fetchone()
    if row:
        if row[1]!=raw:raise ValueError('Journal event identity collision')
        return {**event,'seq':row[0]}
    seq=db.execute('INSERT INTO activity_journal(event_id,payload) VALUES(?,?)',(event['id'],raw)).lastrowid
    return {**event,'seq':seq}

def connect(root):
    base=Path(root).resolve()/'.ledger';base.mkdir(mode=0o700,exist_ok=True)
    db=sqlite3.connect(base/'engineering.sqlite3',timeout=2)
    db.execute('PRAGMA journal_mode=WAL')
    return db

def initialize(root,db):
    ensure(db)
    if db.execute("SELECT 1 FROM activity_meta WHERE key='legacy_imported'").fetchone():return
    events=[]
    if db.execute("SELECT 1 FROM sqlite_master WHERE name='ledger_activity'").fetchone():
        events += [json.loads(r[0]) for r in db.execute('SELECT payload FROM ledger_activity ORDER BY rowid')]
    for path in sorted(folder(root).glob('*.json')):
        try:
            if path.stat().st_size<4096:events.append(json.loads(path.read_text()))
        except (OSError,ValueError):continue
    for event in sorted(events,key=lambda e:(e.get('at',0),e.get('id',''))):
        if isinstance(event,dict) and event.get('id'):append(db,event)
    db.execute("INSERT INTO activity_meta VALUES('legacy_imported',?)",(str(time.time()),))

def _failed(root,event,exc):
    key=str(Path(root).resolve());_ERRORS[key]=redact(exc)
    try:
        base=folder(root)/'pending';base.mkdir(parents=True,mode=0o700,exist_ok=True)
        path=base/(event['id']+'.json');tmp=path.with_suffix('.tmp')
        tmp.write_text(json.dumps(event));tmp.chmod(0o600);os.replace(tmp,path)
    except OSError:_ERRORS[key]+='; recovery spool unavailable'
    return {**event,'journal_error':_ERRORS[key],'committed':False}

def record(root,origin,operation,state,detail='',**refs):
    event=make_event(origin,operation,state,detail,**refs)
    try:
        db=connect(root)
        try:
            with db:ensure(db);event=append(db,event)
        finally:db.close()
        return {**event,'committed':True}
    except (OSError,sqlite3.Error,ValueError) as exc:return _failed(root,event,exc)

def recover(root):
    recovered=0;errors=[]
    for path in sorted((folder(root)/'pending').glob('*.json')):
        try:
            event=json.loads(path.read_text());db=connect(root)
            try:
                with db:ensure(db);append(db,event)
            finally:db.close()
            path.unlink();recovered+=1
        except (OSError,sqlite3.Error,ValueError) as exc:errors.append(redact(exc))
    if not errors:_ERRORS.pop(str(Path(root).resolve()),None)
    return {'recovered':recovered,'errors':errors,'status':status(root)}

def _read(root):
    path=Path(root).resolve()/'.ledger/engineering.sqlite3'
    return sqlite3.connect(path.as_uri()+'?mode=ro',uri=True,timeout=2)

def status(root):
    result={'schema':'arc.ledger-journal/2','head':0,'first':0,'count':0,'state':'CURRENT',
            'retention':'ALL_RECORDED_EVENTS','order':'SQLITE_COMMIT_SEQUENCE',
            'coverage':'Kernel requests, state transitions, settings, saves, navigation and delivered GUI activity. Native stdout/stderr remain linked evidence; not OS-wide tracing.',
            'observer_events_suppressed':sorted(OBSERVER_OPERATIONS)}
    try:
        db=_read(root)
        try:
            low,high,count=db.execute('SELECT MIN(seq),MAX(seq),COUNT(*) FROM activity_journal').fetchone()
            allocated=db.execute("SELECT seq FROM sqlite_sequence WHERE name='activity_journal'").fetchone()
            head=max(high or 0,allocated[0] if allocated else 0)
            result.update(head=head,first=low or 0,count=count)
            if count!=head:result.update(state='INCOMPLETE',reason='A journal segment is missing; retained events are not complete history.')
        finally:db.close()
    except (OSError,sqlite3.Error) as exc:result.update(state='INCOMPLETE',reason=redact(exc))
    pending=list((folder(root)/'pending').glob('*.json'))
    external=list((Path(root).resolve()/'.ledger/settings_delivery').glob('*.json'))
    error=_ERRORS.get(str(Path(root).resolve()))
    if pending or error:result.update(state='INCOMPLETE',pending_deliveries=len(pending),reason=error or 'Pending event delivery requires recovery')
    if external:result.update(state='INCOMPLETE',pending_settings=len(external),reason='External profile setting delivery requires reconciliation')
    files=list((Path(root).resolve()/'.ledger/file_delivery').glob('*.json'))
    if files:result.update(state='INCOMPLETE',pending_files=len(files),reason='External file save requires reconciliation')
    return result

def stream(root,after='',query='',limit=100):
    limit=max(1,min(int(limit),200));health=status(root);gap=health['state']=='INCOMPLETE'
    events=[];position=0;scanned=0
    try:
        db=_read(root)
        try:
            if after:
                row=db.execute('SELECT seq FROM activity_journal WHERE event_id=?',(str(after),)).fetchone()
                if row:position=row[0]
                elif str(after).isdigit():position=int(after)
                else:gap=True
            if position>health['head']:gap=True
            scanned=position
            rows=db.execute('SELECT seq,payload FROM activity_journal WHERE seq>? ORDER BY seq',(position,))
            for seq,raw in rows:
                if seq!=scanned+1:gap=True
                event={**json.loads(raw),'seq':seq};scanned=seq
                if not query or query.casefold() in ' '.join(str(event.get(k,'')) for k in ('origin','operation','state','detail')).casefold():events.append(event)
                if len(events)>=limit:break
            more=scanned<health['head']
        finally:db.close()
    except (OSError,sqlite3.Error,ValueError) as exc:
        gap=True;scanned=position;more=False;health.update(state='INCOMPLETE',reason=redact(exc))
    return {'events':events,'cursor':str(scanned),'head':health['head'],'gap':gap,'truncated':more,
            'has_more':more,'retention':health['retention'],'coverage':health['coverage'],'journal':health}

def recent(root,limit=100):
    try:
        db=_read(root)
        try:rows=db.execute('SELECT seq,payload FROM activity_journal ORDER BY seq DESC LIMIT ?',(max(1,min(int(limit),5000)),)).fetchall()
        finally:db.close()
        return [{**json.loads(raw),'seq':seq} for seq,raw in reversed(rows)]
    except (OSError,sqlite3.Error,ValueError):return []

def tail(root,query='',limit=200):
    events=recent(root,limit)
    if query:events=[e for e in events if query.casefold() in json.dumps(e).casefold()]
    health=status(root)
    return {'events':events,'cursor':str(health['head']),'gap':health['state']=='INCOMPLETE','journal':health}
