"""Bounded filing of existing private memory and guarded owner corrections.

Browsing never checks source files or makes stored procedures usable evidence.
The original Memory service still owns feedback, checkpoints and source checks.
"""
from __future__ import annotations
import hashlib,math,re,sqlite3
from . import memory_service as memory
from sdk.cli.arc1cli import learning_contracts as c,record_store as records

MAX_BYTES=4*1024*1024
MAX_RECORD=128*1024
KINDS=('profile','feedback','task','lesson')
FIELDS={'memory.cabinet':({'limit':{'type':'integer','minimum':1,'maximum':1000}},[]),
 'memory.direction.revise':({'id':memory.ID,'replacement':memory.ID,'expected_history':memory.SHA,
    'instruction':{'type':'string','minLength':1,'maxLength':300},
    'reason':{'type':'string','minLength':1,'maxLength':200}},
    ['id','replacement','expected_history','instruction','reason'])}
SCOPES={'memory.cabinet':'read','memory.direction.revise':'approve'}


def validate(kind,ident,value):
    if not isinstance(value,dict):raise ValueError('MEMORY_SHAPE')
    if kind!='profile':
        c.ident(ident)
        if value.get('id')!=ident:raise ValueError('MEMORY_IDENTITY')
    if kind=='feedback':
        if type(value.get('forgotten',False)) is not bool or type(value.get('undone',False)) is not bool:raise ValueError('MEMORY_FLAGS')
        if not value.get('forgotten'):
            if not re.fullmatch('[a-z][a-z0-9_]{0,47}',value.get('preference','')) or value.get('context') not in c.CONTEXTS:raise ValueError('MEMORY_SCOPE')
            c.text(value.get('instruction'),300,False);c.text(value.get('source_reference'),300,False)
            if value.get('kind') not in c.WEIGHTS or type(value.get('soft')) is not bool:raise ValueError('MEMORY_KIND')
            if type(value.get('feedback')) not in (int,float) or not math.isfinite(value['feedback']) or not 0<=value['feedback']<=1:raise ValueError('MEMORY_FEEDBACK')
        for old in c.strings(value.get('supersedes',[]),1000,32):c.ident(old)
        if type(value.get('sequence')) is not int or value['sequence']<1:raise ValueError('MEMORY_SEQUENCE')
    elif kind in ('task','lesson'):
        c.text(value.get('title'),120,False)
        if kind=='task' and value.get('latest'):c.ident(value['latest'])
        if kind=='lesson':
            c.text(value.get('body'),1500,False)
            if value.get('review') not in ('PROPOSED_UNREVIEWED','OWNER_REVIEWED_PROCEDURE','REJECTED') or not isinstance(value.get('references'),list):raise ValueError('MEMORY_PROCEDURE')
    elif kind=='profile':
        if ident!='current' or type(value.get('enabled')) is not bool or type(value.get('revision')) is not int:raise ValueError('MEMORY_PROFILE')
        memory.original_seed(value)
    return value


def load(db,actor):
    values={kind:{} for kind in KINDS};complete={kind:True for kind in KINDS};used=0
    if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='stacy_memory'").fetchone():return values,complete
    rows=db.execute("SELECT kind,id,length(CAST(payload AS BLOB)),CASE WHEN length(CAST(payload AS BLOB))<=? THEN payload END,sha256 FROM stacy_memory WHERE owner=? AND kind IN ('profile','feedback','task','lesson') ORDER BY rowid DESC LIMIT 4001",(MAX_RECORD,actor))
    for index,(kind,ident,size,raw,digest) in enumerate(rows):
        if index>=4000 or size is not None and used+size>MAX_BYTES:
            complete={kind:False for kind in KINDS};break
        try:
            if not isinstance(raw,str) or type(size) is not int or size>MAX_RECORD:raise ValueError('MEMORY_RECORD_BOUND')
            used+=size
            if hashlib.sha256(raw.encode()).hexdigest()!=digest:raise ValueError('MEMORY_RECORD_DIGEST')
            values[kind][ident]=validate(kind,ident,records.strict(raw))
        except (ValueError,KeyError,TypeError):complete[kind]=False
    return values,complete


def family(events,selected):
    ids={event['id'] for event in events if (event.get('preference'),event.get('context'))==(selected['preference'],selected['context'])}
    by_id={event['id']:event for event in events}
    while True:
        old=set(ids)
        for ident in old:ids.update(i for i in by_id.get(ident,{}).get('supersedes',[]) if i in by_id)
        if ids==old:break
    return sorted((by_id[i] for i in ids),key=lambda row:row['id'])


def state(event,active,complete):
    if event.get('forgotten'):return 'FORGOTTEN'
    if event.get('undone'):return 'UNDONE'
    if not complete:return 'HISTORY_INCOMPLETE'
    return 'ACTIVE' if event['id'] in active else 'SUPERSEDED'


def projection(values,complete,limit):
    events=list(values['feedback'].values());active={row['id'] for row in c.active(events)}
    profile=values['profile'].get('current');rows=[]
    for kind in KINDS:
        for ident,value in values[kind].items():
            status=state(value,active,complete['feedback']) if kind=='feedback' else value.get('review','STORED')
            label=('Forgotten direction' if value.get('forgotten') else value.get('instruction','Saved direction')) if kind=='feedback' else value.get('title','Personality reference')
            rows.append(dict(kind=kind,id=ident,label=label,state=status,context=value.get('context'),created=value.get('created'),
                             origin='OWNER_APPROVED_FEEDBACK' if kind=='feedback' else 'OWNER_TASK_RECORD' if kind=='task' else 'STORED_PROCEDURE_BINDINGS_NOT_RECHECKED' if kind=='lesson' else 'OWNER_SELECTED_PRESENTATION_REFERENCE'))
    rows.sort(key=lambda row:(KINDS.index(row['kind']),row['label'].casefold(),row['id']))
    return dict(schema='ledger.memory-cabinet/1',records=rows[:limit],partial=not all(complete.values()) or len(rows)>limit,
        history_complete=complete['feedback'],profile_enabled=bool(profile and profile['enabled']),
        profile_state='UNAVAILABLE' if not complete['profile'] else 'ENABLED' if profile and profile['enabled'] else 'OFF_OR_NOT_IMPORTED',
        notices=[] if all(complete.values()) else ['Some memory records exceed the bounded view or failed integrity checks. Existing Memory controls remain available.'],
        notice='Stored owner memory only. No source freshness, model compliance, execution permission or engineering proof is inferred.')


def snapshot(kernel,principal,limit=300):
    with kernel.db() as db:
        db.execute('BEGIN');values,complete=load(db,principal.identity)
    return projection(values,complete,limit)


def detail(kernel,principal,kind,ident):
    if kind not in KINDS:raise ValueError('Memory record unavailable to this caller')
    with kernel.db() as db:
        db.execute('BEGIN');values,complete=load(db,principal.identity)
    value=values[kind].get(ident)
    if value is None:
        if kind=='profile' and ident=='current' and complete['profile']:
            return dict(kind='memory_profile',state='NOT_IMPORTED',display_text='No personality reference has been imported. Existing Memory controls handle import and enablement.'),[]
        raise ValueError('Memory record unavailable in this caller’s bounded view')
    actions=[];record={k:v for k,v in value.items() if k not in ('body','original_b64')}
    record.update(kind='memory_'+kind,authority='OWNER_MEMORY_NOT_ENGINEERING_PROOF_OR_PERMISSION')
    if kind=='feedback':
        events=list(values['feedback'].values());active={row['id'] for row in c.active(events)}
        record['state']=state(value,active,complete['feedback']);history=[] if value.get('forgotten') else family(events,value)
        record['history']=history;record['history_digest']=c.digest(history) if complete['feedback'] and history else None
        record['editable']=record['state']=='ACTIVE' and record['history_digest'] is not None and 'approve' in principal.scopes and principal.mode!='Tutor'
        profile=values['profile'].get('current');record['profile_use']=('Profile state unavailable' if not complete['profile'] else
            'Profile enabled · actual context selection still applies' if profile and profile['enabled'] else 'Profile off or not imported · directions remain stored')
        lines=['Saved direction',value.get('instruction','This memory entry no longer retains its text. Separate recovery copies are unaffected.'),'',
               'Context: '+value.get('context','Not retained').replace('_',' '),'Status: '+record['state'].replace('_',' ').title(),
               'Origin: '+value.get('source_reference','Forgotten'),'Use: '+record['profile_use'],
               '', 'A preference guides collaboration. It does not grant permission or override original evidence.']
        for old in sorted(history,key=lambda row:row['sequence'],reverse=True)[:8]:
            if old['id']!=ident:lines+=['','History entry · '+state(old,active,complete['feedback']).lower(),old.get('instruction','Forgotten text is not retained.')]
        if len(history)>9:lines+=['','More history is retained in this record’s bounded Detail.']
        record['display_text']='\n'.join(lines)
    elif kind=='lesson':
        record.update(state=value['review'],binding_state='NOT_RECHECKED',body=None,
                      display_text='Stored procedure · '+value['review'].replace('_',' ').lower()+'\n\nProcedure text is withheld here. Choose Check procedure sources to use the existing source-checked reader. Review status does not establish current source availability.')
        actions.append(dict(label='Check procedure sources',operation='memory.lessons',arguments={'query':value['title']}))
    elif kind=='task':
        record['display_text']='Saved task\n'+value['title']+'\n\nTask checkpoints keep owner notes and checked readback receipts. Sources are rechecked through the original resume controls.'
        actions.append(dict(label='Read task history',operation='memory.task',arguments={'id':ident}))
    else:
        record['expression']=memory.original_seed(value)
        record['display_text']='Owner-selected personality reference\n'+record['expression']['character']+'\n\nState: '+('Enabled' if value['enabled'] else 'Off')+'\nThe imported original is retained. Directions are separate owner feedback; no model weights are trained.'
        actions.append(dict(label='Read personality reference',operation='memory.profile',arguments={}))
    return record,actions


def revise(kernel,args,principal):
    c.ident(args['id']);c.ident(args['replacement']);c.text(args['instruction'],300,False);c.text(args['reason'],200,False)
    with kernel.db() as db:
        db.execute('BEGIN IMMEDIATE');values,complete=load(db,principal.identity)
        old=values['feedback'].get(args['id'])
        if old is None or old.get('forgotten'):raise ValueError('Direction unavailable to this caller')
        event_args=dict(id=args['replacement'],preference=old['preference'],context=old['context'],feedback=old['feedback'],
                        instruction=args['instruction'],source_reference=args['reason'],kind='owner_correction',soft=False,supersedes=[old['id']])
        # A matching request ID may be retried without applying the correction twice.
        if values['feedback'].get(args['replacement']):
            created=memory.commit_feedback(db,principal.identity,event_args)
            return dict(record=created,previous=old['id'],duplicate=True)
        events=list(values['feedback'].values())
        if not complete['feedback'] or c.digest(family(events,old))!=args['expected_history']:
            raise ValueError('Direction history changed or is incomplete. Your writing is intact; refresh the saved history before correcting it.')
        if old['id'] not in {row['id'] for row in c.active(events)}:raise ValueError('Only an active direction can be corrected here. History is retained for inspection.')
        created=memory.commit_feedback(db,principal.identity,event_args)
    return dict(record=created,previous=old['id'],duplicate=False,authority='OWNER_CORRECTION_NOT_ENGINEERING_PROOF_OR_EXECUTION_PERMISSION')


def dispatch(kernel,operation,args,principal):
    return snapshot(kernel,principal,args.get('limit',300)) if operation=='memory.cabinet' else revise(kernel,args,principal)
