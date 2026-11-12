"""Atomic settings changes in the existing Session file and Kernel journal."""
import json
import os
import time
import uuid
from . import activity, reading_profile
from .session import Session
from .settings_registry import SESSION_KEYS, VIEW_MODES_KEY, WRITING_MARKER_KEY
from .config_lock import locked
WRITING_MARKER_FIELD='writing_marker'


def write_value(session,key,value):
    if key.startswith('reading.'):
        profile=reading_profile.clean(session.state.get('reading_profile',{}))
        profile[key.split('.',1)[1]]=value;session.state['reading_profile']=reading_profile.clean(profile)
    elif key.startswith('favorites.'):
        from sdk.cli.arc1cli.command_bar import FAVORITE_KEYS, session_favorites
        groups=session_favorites(session.state);groups[FAVORITE_KEYS[key]]=list(value)
        session.state['toolbar_favorites']=groups;session.state['toolbar_favorites_version']=2
    elif key=='appearance.cursive':session.state['cursive']=value
    elif key.startswith('layout.'):session.set_layout(**{key.split('.',1)[1]:value})
    elif key=='stacy.reactions':session.set_layout(stacy_reactions=value)
    elif key.startswith('workspace.'):session.state['view_preferences'][key.split('.',1)[1]]=value
    elif key==VIEW_MODES_KEY:session.state['category_views']={str(k):v for k,v in value.items()}
    elif key==WRITING_MARKER_KEY:session.state[WRITING_MARKER_FIELD]=bool(value)
    else:raise ValueError('Setting is not backed by the connected session')


def refresh_session(session,kernel):
    fresh=Session(session.path,kernel.root)
    if not session.path.is_file():return
    session.state['reading_profile']=reading_profile.clean(fresh.state.get('reading_profile',{}))
    session.state['view_preferences']=fresh.state['view_preferences']
    session.state['cursive']=fresh.state['cursive']
    for key in ('toolbar_favorites','toolbar_favorites_version'):session.state[key]=fresh.state[key]
    # The whole map is shared state now; a bound desktop must not resurrect its stale copy over another writer's save.
    session.state['category_views']=dict(fresh.state.get('category_views',{}))
    # The marker field is read through the Session loader; a profile without it (older, or a loader not yet shipped) means the default.
    session.state[WRITING_MARKER_FIELD]=fresh.state.get(WRITING_MARKER_FIELD,True) is not False
    for name in ('stacy_reactions','navigator_width','output_height','output_visible','output_tab'):
        session.state['layout'][name]=fresh.layout[name]


def apply(kernel,changes,actor,undo_id=None):
    from . import ledger_control as control
    if not isinstance(changes,list) or not 1<=len(changes)<=len(SESSION_KEYS):raise ValueError('Choose one or more connected session settings')
    keys=[r['key'] for r in changes]
    if len(set(keys))!=len(keys) or not set(keys)<=SESSION_KEYS:raise ValueError('A session batch must contain distinct session setting keys')
    for row in changes:control.validate(row['key'],row['value'])
    session=control.session(kernel);batch=uuid.uuid4().hex;records=[];receipt=None
    with locked(session.path),kernel.db() as db:
        db.execute('BEGIN IMMEDIATE');refresh_session(session,kernel);journal=control._history(db)
        previous=None
        for row in changes:
            key=row['key'];old=control.value(kernel,key,session)
            if row.get('has_expected') and old!=row.get('expected'):
                raise ValueError('Setting changed since it was read; refresh before applying')
            if row.get('expected_revision') is not None and row['expected_revision']!=control._revision(key,old,journal):
                raise ValueError('SETTING_REVISION_CHANGED: '+key+' has a newer change; your draft is preserved')
            if undo_id:
                previous=next((r for r in journal if r['id']==undo_id),None)
                latest=next((r for r in journal if r['key']==key),None)
                if not previous or previous['undone'] or not latest or latest['id']!=undo_id or old!=previous['after']:
                    raise ValueError('SETTING_UNDO_CONFLICT: a newer change exists; inspect history')
            record=dict(id=uuid.uuid4().hex,key=key,before=old,after=row['value'],actor=actor,at=time.time(),
                        undone=False,scope=control.BY_KEY[key]['scope_id'])
            if len(changes)>1:record['batch']=batch
            if undo_id:record['restores']=undo_id
            records.append(record)
        # All validation and all revision checks precede the single profile write.
        base=kernel.state/'settings_delivery';base.mkdir(mode=0o700,exist_ok=True)
        receipt=base/((records[0]['id'] if len(records)==1 else batch)+'.json')
        payload=({**records[0],'profile_hash':control._profile_hash(kernel)} if len(records)==1 else
                 dict(schema='arc.settings-delivery-batch/1',id=batch,changes=records,profile_hash=control._profile_hash(kernel)))
        temporary=receipt.with_suffix('.tmp');temporary.write_text(json.dumps(payload));temporary.chmod(0o600);os.replace(temporary,receipt)
        for row in changes:write_value(session,row['key'],row['value'])
        session.save()
        for record in records:
            db.execute('INSERT INTO settings VALUES(?,?)',('ledger.change.'+record['id'],json.dumps(record)))
            activity.append(db,activity.make_event(actor,'ledger.settings.set','APPLIED',record['key'],correlation_id=record['id']))
        if previous:
            previous['undone']=True;db.execute('UPDATE settings SET value=? WHERE key=?',(json.dumps(previous),'ledger.change.'+undo_id))
        control._trim_history(db)
    receipt.unlink(missing_ok=True)
    return dict(schema='arc.ledger-settings-apply/1',batch=batch,changes=[
        {**r,'revision':control._revision(r['key'],r['after'],[r])} for r in records])


def recover(kernel,path,document):
    from . import ledger_control as control
    session=control.session(kernel);records=document.get('changes',[])
    if not records or len(records)>len(SESSION_KEYS) or any(r.get('key') not in SESSION_KEYS for r in records):
        raise ValueError('Invalid settings delivery batch')
    for row in records:control.validate(row['key'],row['after'])
    with locked(session.path),kernel.db() as db:
        db.execute('BEGIN IMMEDIATE')
        if document.get('profile_hash')!=control._profile_hash(kernel):return dict(id=document['id'],state='PROFILE_NOT_CONNECTED')
        fresh=Session(session.path,kernel.root)
        existing=[control.stored(db,'ledger.change.'+r['id'],None) for r in records]
        actual=[control.value(kernel,r['key'],fresh) for r in records]
        state=('ALREADY_COMMITTED' if all(existing) else 'CONFLICT' if any(existing) else
               'RECONCILED_APPLIED' if actual==[r['after'] for r in records] else
               'NOT_APPLIED' if actual==[r['before'] for r in records] else 'CONFLICT')
        if state=='CONFLICT':return dict(id=document['id'],state=state)
        if state=='RECONCILED_APPLIED':
            for row in records:db.execute('INSERT INTO settings VALUES(?,?)',('ledger.change.'+row['id'],json.dumps(row)))
            control._trim_history(db)
        activity.append(db,activity.make_event('RECOVERY','ledger.settings.apply',state,correlation_id=document['id']))
    path.unlink();return dict(id=document['id'],state=state)
