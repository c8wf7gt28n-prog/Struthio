"""Owner-private return writing. Recovery copies never become project records.

The one bounded handoff per workspace/owner uses the existing Kernel database.
Reads do not create this table. Updates compare the exact retained revision;
neither reading nor keeping executes an action embedded in saved text.
"""
from __future__ import annotations
import hashlib,json,time,math
from . import cabinet

MAX_DRAFTS=40
MAX_BYTES=256*1024
REVISION={'type':'integer','minimum':0,'maximum':2147483647}
DRAFT={'type':'object','additionalProperties':False,'properties':{
    'id':cabinet.TEXT,'title':{'type':'string','maxLength':200},'text':{'type':'string','maxLength':60000}},
    'required':['id','title','text']}
FIELDS={
 'ledger.session.read':({},[]),
 'ledger.session.keep':({'expected_revision':REVISION,'note':{'type':'string','maxLength':8000},
    'drafts':{'type':'array','maxItems':MAX_DRAFTS,'items':DRAFT},'context':cabinet.TEXT},
    ['expected_revision','note','drafts'])}
SCOPES={'ledger.session.read':'read','ledger.session.keep':'execute'}


def clean(note,drafts,context=None):
    from .agent_operations import validate
    validate(note,FIELDS['ledger.session.keep'][0]['note'])
    validate(drafts,FIELDS['ledger.session.keep'][0]['drafts'])
    if len(drafts)>MAX_DRAFTS:raise ValueError('A return copy holds at most 40 cabinet drafts; keep additional writing through its own save controls.')
    if context is not None:validate(context,cabinet.TEXT)
    seen=set();rows=[]
    for row in drafts:
        if any(ord(c)<32 for c in row['id']):raise ValueError('Invalid cabinet draft identity')
        if row['id'] in seen:raise ValueError('Duplicate cabinet draft identity')
        seen.add(row['id']);rows.append({key:row[key] for key in ('id','title','text')})
    value=dict(note=note,drafts=sorted(rows,key=lambda row:row['id']),context=context)
    raw=json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False)
    if len(raw.encode('utf-8'))>MAX_BYTES:raise ValueError('Return writing exceeds the 256 KiB budget. Nothing was truncated; keep more writing through its own save controls.')
    return value,raw


def stored(db,owner):
    if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='session_handoffs'").fetchone():return None
    row=db.execute('SELECT revision,length(CAST(payload AS BLOB)),CASE WHEN length(CAST(payload AS BLOB))<=? THEN payload END,digest,updated FROM session_handoffs WHERE owner=?',
                   (MAX_BYTES,owner)).fetchone()
    if row is None:return None
    revision,size,raw,digest,updated=row
    try:
        if (type(revision) is not int or not 1<=revision<=2147483647 or size>MAX_BYTES or not isinstance(raw,str)
                or type(updated) not in (int,float) or not math.isfinite(updated) or updated<0):raise ValueError('Invalid return copy bounds')
        if hashlib.sha256(raw.encode('utf-8')).hexdigest()!=digest:raise ValueError('Changed return copy')
        value=json.loads(raw)
        if set(value)!= {'note','drafts','context'}:raise ValueError('Unexpected return copy fields')
        checked,canonical=clean(**value)
        if canonical!=raw:raise ValueError('Noncanonical return copy')
    except (ValueError,KeyError,TypeError):
        raise ValueError('The saved return copy failed integrity checking; it has not been replaced.') from None
    return dict(schema='ledger.return-thread/1',revision=revision,updated=updated,**checked)


def empty():return dict(schema='ledger.return-thread/1',revision=0,updated=None,note='',drafts=[],context=None)


def read(kernel,principal):
    with kernel.db() as db:return stored(db,principal.identity) or empty()


def keep(kernel,principal,expected_revision,note,drafts,context=None):
    from .agent_operations import validate
    validate(expected_revision,REVISION);value,raw=clean(note,drafts,context)
    with kernel.db() as db:
        db.execute('BEGIN IMMEDIATE')
        before=stored(db,principal.identity) or empty()
        if before['revision']!=expected_revision:
            raise ValueError('The saved return copy changed in another session. Your current writing is intact; inspect the stored copy before replacing it.')
        if before['revision'] and all(before[key]==value[key] for key in value):return {**before,'changed':False}
        if expected_revision>=2147483647:raise ValueError('The return revision limit was reached; existing writing has not been replaced.')
        db.execute('CREATE TABLE IF NOT EXISTS session_handoffs(owner TEXT PRIMARY KEY,revision INTEGER NOT NULL,payload TEXT NOT NULL,digest TEXT NOT NULL,updated REAL NOT NULL)')
        revision=expected_revision+1;updated=time.time();digest=hashlib.sha256(raw.encode('utf-8')).hexdigest()
        db.execute('INSERT INTO session_handoffs VALUES(?,?,?,?,?) ON CONFLICT(owner) DO UPDATE SET revision=excluded.revision,payload=excluded.payload,digest=excluded.digest,updated=excluded.updated',
                   (principal.identity,revision,raw,digest,updated))
    return dict(schema='ledger.return-thread/1',revision=revision,updated=updated,changed=True,**value)


def dispatch(kernel,operation,args,principal):
    return read(kernel,principal) if operation=='ledger.session.read' else keep(kernel,principal,**args)
