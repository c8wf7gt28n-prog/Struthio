"""Caller-private Settings adapters over the original personality profile.

Profile change and shared journal commit in one existing SQLite transaction.
The whole profile token catches direct/legacy changes, including away-and-back.
"""
import copy,hashlib,json,time,uuid,sqlite3
from . import memory_service as memory,memory_cabinet,activity
from .settings_registry import SPECS,MEMORY_KEYS
from sdk.cli.arc1cli import learning_contracts as c,record_store


def visible(changes,actor):
    return [row for row in changes if row['key'] not in MEMORY_KEYS or row.get('actor')==actor]


def profile(db,actor):
    row=db.execute("SELECT length(CAST(payload AS BLOB)),CASE WHEN length(CAST(payload AS BLOB))<=? THEN payload END,sha256 FROM stacy_memory WHERE owner=? AND kind='profile' AND id='current'",
                   (memory_cabinet.MAX_RECORD,actor)).fetchone()
    if row is None:return None
    size,raw,digest=row
    try:
        if not isinstance(raw,str) or size>memory_cabinet.MAX_RECORD or hashlib.sha256(raw.encode()).hexdigest()!=digest:raise ValueError('Invalid profile')
        value=memory_cabinet.validate('profile','current',record_store.strict(raw));c.parameters(value['parameters'])
        return value
    except (ValueError,KeyError,TypeError):raise ValueError('The owner memory profile is unavailable or failed integrity checking. Existing profile data was not replaced.') from None


def token(value,actor):return c.digest(dict(owner=actor,profile=value))


def field(value,key):
    if key=='memory.profile.enabled':return value['enabled']
    if key=='memory.soft_half_life_days':return value['parameters']['soft_half_life_days']
    return value['parameters']['weights'][key.removeprefix('memory.weight.')]


def rows(kernel,actor):
    from . import ledger_control as control
    result={}
    with kernel.db() as db:
        db.execute('BEGIN');changes=visible(control._history(db),actor)
        try:stored=profile(db,actor);error=None
        except (ValueError,sqlite3.Error) as exc:stored=None;error='Owner memory profile unavailable: '+str(exc)
    stamp=token(stored,actor)
    for definition in SPECS:
        key=definition['key']
        if key not in MEMORY_KEYS:continue
        current=field(stored,key) if stored else None
        state=('STORE_UNAVAILABLE' if error else 'PROFILE_NOT_IMPORTED') if stored is None else (
            'PROFILE_POLICY_READ_BACK' if key=='memory.profile.enabled' else 'NEXT_PROFILE_CONTEXT' if stored['enabled'] else 'PROFILE_DISABLED')
        meaning=(error or 'Import a personality reference using the existing Memory controls before changing these values.') if stored is None else (
            'Read from the existing owner profile. This does not establish model compliance or change a running reply.' if key=='memory.profile.enabled' or stored['enabled'] else
            'Stored parameters read back; the personality profile is off. No claim that these values are active in a reply.')
        effective=current if stored and (key=='memory.profile.enabled' or stored['enabled']) else None
        latest=next((r for r in changes if r['key']==key),None)
        result[key]={**definition,'value':current,'stored':current,'revision':control._revision(key,current,changes,stamp),
                     'store_revision':stamp,'editable':stored is not None,'latest_change':latest,'history_limit':100,
                     'effective':effective,'application_state':state,'effective_source':meaning,'desktop_effects':[]}
    return result


def change(kernel,key,new,actor,expected_marker=None,has_expected=False,expected_revision=None,undo_id=None):
    from . import ledger_control as control
    control.validate(key,new)
    if expected_revision is None and undo_id is None:raise ValueError('Read this owner setting and supply expected_revision before applying a memory change.')
    with kernel.db() as db:
        db.execute('BEGIN IMMEDIATE');before=profile(db,actor)
        if before is None:raise ValueError('Import a personality reference in Memory first. No profile was created.')
        old=field(before,key);stamp=token(before,actor);journal=visible(control._history(db),actor)
        if has_expected and old!=expected_marker:raise ValueError('Setting changed since it was read; your draft is preserved')
        if expected_revision is not None and expected_revision!=control._revision(key,old,journal,stamp):
            raise ValueError('SETTING_REVISION_CHANGED: the owner profile changed; your draft is preserved')
        previous=None
        if undo_id:
            previous=next((r for r in journal if r['id']==undo_id),None)
            latest=next((r for r in journal if r['key']==key),None)
            if not previous or previous['actor']!=actor or previous['undone'] or not latest or latest['id']!=undo_id or old!=previous['after'] or stamp!=previous.get('store_revision'):
                raise ValueError('SETTING_UNDO_CONFLICT: the profile changed or this change is not owned by this caller')
        if key=='memory.profile.enabled':memory.commit_profile(db,actor,'memory.profile.enable',{'enabled':new})
        else:
            parameters=copy.deepcopy(before['parameters'])
            if key=='memory.soft_half_life_days':parameters['soft_half_life_days']=new
            else:parameters['weights'][key.removeprefix('memory.weight.')]=new
            memory.commit_profile(db,actor,'memory.profile.configure',{'parameters':parameters})
        after=profile(db,actor);after_stamp=token(after,actor)
        record=dict(id=uuid.uuid4().hex,key=key,before=old,after=new,actor=actor,at=time.time(),undone=False,
                    scope='owner_memory',store_revision=after_stamp,before_store_revision=stamp)
        if undo_id:record['restores']=undo_id
        db.execute('INSERT INTO settings VALUES(?,?)',('ledger.change.'+record['id'],json.dumps(record)))
        if previous:
            previous['undone']=True;db.execute('UPDATE settings SET value=? WHERE key=?',(json.dumps(previous),'ledger.change.'+undo_id))
        activity.append(db,activity.make_event(actor,'ledger.settings.set','APPLIED',key,correlation_id=record['id']));control._trim_history(db)
    return {**record,'revision':control._revision(key,new,[record],after_stamp)}
