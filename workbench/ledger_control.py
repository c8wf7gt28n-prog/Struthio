"""Provider/Qt independent command discovery, settings and desktop intents.

Values are adapters over the existing stores, not a second configuration tree.
Desktop intents only navigate/open; engineering execution remains in the Kernel.
"""
from __future__ import annotations
import json
import os
import time
import uuid
import hashlib
from pathlib import Path
from . import activity, reading_profile, operation_priority
from .session import Session
from .settings_registry import SPECS, BY_KEY, spec, SESSION_KEYS, SESSION_BATCH_KEYS, OWNER_KEYS, MEMORY_KEYS, MODEL_KEYS, VIEW_MODES, VIEW_MODES_KEY, WRITING_MARKER_KEY
from . import cabinet, explore, operations, cabinet_actions, return_thread, memory_cabinet, memory_settings, model_settings

S = {'type': 'string', 'maxLength': 500}
DESTINATIONS = ('discovery','algorithms','atlas','organizer','packages','object_glass','trail', 'settings', 'commands', 'activity', 'home', 'engineering', 'brain_link',
                'native_game', 'orange_book', 'ledger', 'arcos', 'native_pcb', 'developer_tools', 'cad', 'kibot', 'spice', 'yosys', 'implementation', 'hdl', 'stacy_knowledge', 'stacy_awareness','brain','intake','references','memory','office','slate','files',
                'documents',  # WORKSHOP-01: the Documents room (recorded extension of the ledger.navigate destination enum)
                'investigations')  # AGENT-01: the Investigations & assignments room (recorded extension)
FIELDS = {
    **cabinet.FIELDS,
    **return_thread.FIELDS,
    **memory_cabinet.FIELDS,
    **cabinet_actions.FIELDS,
    **explore.FIELDS,
    **operations.FIELDS,
    'ledger.commands': ({'query': S}, []),
    'ledger.settings': ({'category': S}, []),
    'ledger.settings.set': ({'key': S, 'value': {}, 'expected': {}, 'expected_revision': S}, ['key', 'value']),
    'ledger.settings.undo': ({'id': S}, ['id']),
    'ledger.settings.effective': ({'key': S}, []),
    'ledger.settings.history': ({'key': S}, []),
    'ledger.settings.restore': ({'key': S, 'expected_revision': S}, ['key', 'expected_revision']),
    'ledger.settings.apply': ({'changes':{'type':'array','minItems':1,'maxItems':25,'items':{
        'type':'object','additionalProperties':False,'properties':{'key':{'type':'string','enum':sorted(SESSION_BATCH_KEYS)},
            'value':{},'expected_revision':S},'required':['key','value','expected_revision']}}}, ['changes']),
    'ledger.activity': ({'after': S, 'query': S, 'limit': {'type': 'integer', 'minimum': 1, 'maximum': 200}}, []),
    'ledger.context': ({}, []),
    'ledger.navigate': ({'destination': {'type': 'string', 'enum': list(DESTINATIONS)}, 'desktop_id':S}, ['destination']),
    'ledger.open': ({'path': S,'desktop_id':S}, ['path']),
    'ledger.desktop_request': ({'id': S}, ['id']),
}
SCOPES = {op: ('execute' if op in ('ledger.settings.set', 'ledger.settings.undo', 'ledger.settings.restore', 'ledger.settings.apply', 'ledger.navigate', 'ledger.open')
               else 'read') for op in FIELDS}
SCOPES.update(return_thread.SCOPES)
SCOPES.update(memory_cabinet.SCOPES)


_BOUND = {}


def bind(kernel, session):
    _BOUND[str(kernel.root)] = session
    # This path comes only from the local desktop, never from a command argument.
    with kernel.db() as db:
        db.execute('INSERT OR REPLACE INTO settings VALUES(?,?)', ('ledger.session_path', str(session.path.resolve())))


def session(kernel):
    bound = _BOUND.get(str(kernel.root))
    if bound is not None:
        return bound
    with kernel.db() as db:
        row = db.execute('SELECT value FROM settings WHERE key=?', ('ledger.session_path',)).fetchone()
    return Session(Path(row[0]) if row else None, kernel.root)


def stored(db, key, default):
    row = db.execute('SELECT value FROM settings WHERE key=?', (key,)).fetchone()
    return json.loads(row[0]) if row else default


def value(kernel, key, current_session=None):
    if key not in BY_KEY:
        raise ValueError('Unknown setting')
    if key in MEMORY_KEYS:raise ValueError('Read owner memory values through ledger.settings with the caller scope')
    if key=='catalog.view':
        from .catalog_settings import read
        return read(kernel)[0]
    s = current_session or session(kernel)
    if key.startswith('favorites.'):
        from sdk.cli.arc1cli.command_bar import FAVORITE_KEYS, session_favorites
        return session_favorites(s.state)[FAVORITE_KEYS[key]]
    if key=='appearance.cursive':return s.state.get('cursive',BY_KEY[key]['default'])
    if key.startswith('layout.'):return s.layout[key.split('.',1)[1]]
    if key.startswith('gemini.'):
        from .clip import preferences
        return preferences()[key.split('.',1)[1]]
    if key.startswith('reading.'):
        return reading_profile.clean(s.state.get('reading_profile', {}))[key.split('.', 1)[1]]
    if key == 'stacy.reactions':
        return s.layout.get('stacy_reactions', True)
    if key.startswith('workspace.'):
        return s.state['view_preferences'][key.split('.', 1)[1]]
    if key == 'operations.priority':
        return operation_priority.policy(kernel.root)
    if key==VIEW_MODES_KEY:return dict(s.state.get('category_views',{}))
    if key==WRITING_MARKER_KEY:
        # Absent in an older profile (or before its loader) means the default, never an error row.
        return s.state.get('writing_marker',BY_KEY[key]['default']) is not False
    with kernel.db() as db:
        current=stored(db, 'ledger.'+key, BY_KEY[key]['default'])
    try:validate(key,current)  # a tampered or foreign-version row is reported, never read back as a choice
    except (ValueError,TypeError) as exc:raise ValueError('Stored value is not valid for this setting: '+str(exc)) from exc
    return current


def category_view_patch(saved,view_key,mode):
    """The one-entry change a hardware pane sends through Set; None when nothing would change."""
    saved=dict(saved or {})
    if saved.get(view_key,VIEW_MODES[0])==mode:return None
    saved.pop(view_key,None)
    if mode!=VIEW_MODES[0]:saved[view_key]=mode
    return saved


def _profile_hash(kernel):
    return hashlib.sha256(str(session(kernel).path.resolve()).encode()).hexdigest()


def _history(db):
    return [json.loads(r[0]) for r in db.execute(
        "SELECT value FROM settings WHERE key LIKE 'ledger.change.%' ORDER BY rowid DESC")]


def _store_revision(key, kernel=None):
    if key.startswith('gemini.'):
        from .clip import preferences
        return preferences()['revision']
    if key=='catalog.view':
        from .catalog_settings import read
        return read(kernel)[1]
    return None


def _observation(kernel,key,current_session=None):
    if key=='catalog.view':
        from .catalog_settings import read
        return read(kernel)
    return value(kernel,key,current_session),_store_revision(key,kernel)


def _revision(key, current, changes, store_revision=None):
    latest=next((r['id'] for r in changes if r['key']==key),None)
    data=[key,current,latest]
    if store_revision is not None:data.append(store_revision)
    return hashlib.sha256(json.dumps(data,sort_keys=True,allow_nan=False).encode()).hexdigest()


def publish_settings_runtime(kernel, desktop_id, values):
    """Desktop consumer receipts, not a second preference store or AI claim."""
    from .operation_stop import process_identity
    safe={key:row for key,row in values.items() if key in BY_KEY}
    document=dict(desktop_id=desktop_id,profile=_profile_hash(kernel),pid=os.getpid(),
                  start=process_identity(os.getpid()),at=time.time(),values=safe)
    leases=kernel.root/'.ledger/desktops'
    with kernel.db() as db:
        db.execute('INSERT OR REPLACE INTO settings VALUES(?,?)',
                   ('ledger.settings_runtime.'+desktop_id,json.dumps(document)))
        # Receipts of desktops whose lease is gone are unreadable by _runtime(); drop them so the table does not grow per launch.
        gone=[(key,) for key, in db.execute("SELECT key FROM settings WHERE key LIKE 'ledger.settings_runtime.%'")
              if not (leases/(key[len('ledger.settings_runtime.'):]+'.json')).is_file()]
        db.executemany('DELETE FROM settings WHERE key=?',gone)


def _runtime(kernel, db):
    from .operation_stop import process_identity, UNKNOWN
    result=[]
    for raw, in db.execute("SELECT value FROM settings WHERE key LIKE 'ledger.settings_runtime.%'"):
        row=json.loads(raw)
        lease=kernel.root/'.ledger/desktops'/(row['desktop_id']+'.json')
        if (lease.is_file() and row['profile']==_profile_hash(kernel) and row['start'] not in (None,UNKNOWN)
                and process_identity(row['pid'])==row['start']):
            result.append(row)
    return sorted(result,key=lambda r:r['at'],reverse=True)


def _effective(row, current, runtime):
    key=row['key']
    # Visual keys are the ones a desktop consumer reads back: every Session-backed store and the catalogue view.
    visual=row['store'].startswith('Session ') or key=='catalog.view'
    if not visual:
        return dict(effective=current,application_state='NEXT_USE_POLICY' if row['application']=='next_use' else 'POLICY_READ_BACK',
                    effective_source='Existing consumer policy store; not a claim about running requests or process priority',desktop_effects=[])
    observations=[dict(desktop_id=r['desktop_id'],at=r['at'],**r['values'][key]) for r in runtime if key in r['values']]
    if not observations:
        return dict(effective=None,application_state='NO_LIVE_DESKTOP_READBACK',
                    effective_source='Saved value only; no connected desktop consumer receipt',desktop_effects=[])
    if key==VIEW_MODES_KEY:
        # Only open panes have an effect; a partial map is not a fallback, and a closed pane is not pending.
        live=[r for r in observations if r.get('state')!='NO_OPEN_PANE' and isinstance(r.get('effective'),dict)]
        if not live:
            return dict(effective=None,application_state='NO_OPEN_PANE',
                        effective_source='No hardware category pane is open on a connected desktop; the saved map applies when one opens',desktop_effects=observations)
        saved=current if isinstance(current,dict) else {}
        applied=all(r.get('requested')==saved and all(mode==saved.get(pane,VIEW_MODES[0]) for pane,mode in r['effective'].items()) for r in live)
        return dict(effective=live[0]['effective'],application_state='APPLIED' if applied else 'PENDING_DESKTOP',
                    effective_source='Live desktop readback of open hardware panes only; each desktop is listed separately',desktop_effects=observations)
    if key==WRITING_MARKER_KEY:
        # The marker controller reports what focused passages show; Reduce motion makes a shown X static, it does not pend it.
        applied=all(r.get('requested')==current and r.get('effective')==current for r in observations)
        motions=sorted({str(r.get('motion','unreported')) for r in observations})
        return dict(effective=observations[0]['effective'],application_state='APPLIED' if applied else 'PENDING_DESKTOP',
                    effective_source='Live desktop readback of the writing-marker controller: '+', '.join(motions)+
                        ' on '+str(observations[0].get('passages',0))+' opted-in passage(s); each desktop is listed separately',desktop_effects=observations)
    waiting=[r for r in observations if r.get('state')=='WAITING_FOR_PANEL']
    if waiting:
        return dict(effective=None,application_state='WAITING_FOR_PANEL',effective_source='Output height will be measured when its panel is shown',desktop_effects=observations)
    applied=all(r['requested']==current for r in observations)
    state=('APPLIED_WITH_FALLBACK' if any(r['effective']!=current for r in observations) else 'APPLIED') if applied else (
        'PENDING_NEXT_LAUNCH' if row['application']=='next_launch' else 'PENDING_DESKTOP')
    return dict(effective=observations[0]['effective'],application_state=state,
                effective_source='Live desktop consumer readback; each desktop is listed separately',desktop_effects=observations)


def settings(kernel, category='', principal=None):
    if principal is None:
        from .engineering_kernel import operator
        principal=operator()
    if category.casefold()=='stacy':category='Slate' # historical CLI category remains accepted
    connected=session(kernel)
    s=Session(connected.path,kernel.root) if connected.path.is_file() else connected
    with kernel.db() as db:
        changes=memory_settings.visible(_history(db),principal.identity);runtime=_runtime(kernel,db)
    private=memory_settings.rows(kernel,principal.identity)
    model_rows=model_settings.rows(kernel,principal.identity,changes)
    rows=[]
    for definition in SPECS:
        if category and definition['category'].casefold()!=category.casefold():continue
        key=definition['key']
        if key in MEMORY_KEYS:
            rows.append(private[key]);continue
        if key in MODEL_KEYS:
            rows.append(model_rows[key]);continue
        latest=next((r for r in changes if r['key']==key),None)
        try:
            current,stamp=_observation(kernel,key,s)
            rows.append({**definition,'value':current,'stored':current,'revision':_revision(key,current,changes,stamp),
                'store_revision':stamp,'editable':True,'latest_change':latest,'history_limit':100,**_effective(definition,current,runtime)})
        except (OSError,ValueError,TypeError,KeyError) as exc:
            # One unreadable store is one unavailable row; the other settings, the Settings page and ledger.context keep working.
            # Program-owned stores (Kernel table, priority file) may be repaired with Default; foreign profile bytes are never replaced.
            repairable=_repairable(key) and isinstance(exc,(ValueError,TypeError))  # an unreadable file (OSError) is not repaired by Default
            rows.append({**definition,'value':None,'stored':None,'effective':None,'editable':False,'repairable':repairable,
                'revision':_revision(key,None,changes),'store_revision':None,'latest_change':latest,'history_limit':100,
                'application_state':'STORE_UNAVAILABLE','desktop_effects':[],
                'effective_source':activity.redact(exc)+(' · Default replaces the invalid stored value' if repairable else '')})
    from .settings_registry import nodes
    return dict(schema='arc.ledger-settings/1',settings=rows,nodes=nodes(),
        coverage=str(len(SPECS))+' genuine settings; remaining coverage is recorded in docs/SETTINGS_INVENTORY_07.md',
        credentials='Use existing credential controls; raw secrets are never registry values',
        scope_notice='Only each key’s actual backing scope is supported. No invented global/project/session overrides.')


def effective(kernel, key='', principal=None):
    if key and key not in BY_KEY:raise ValueError('Unknown setting')
    rows=settings(kernel,principal=principal)['settings']
    return dict(schema='arc.ledger-settings-effective/1',settings=[r for r in rows if not key or r['key']==key])


def history(kernel, key='', principal=None):
    if principal is None:
        from .engineering_kernel import operator
        principal=operator()
    if key and key not in BY_KEY:raise ValueError('Unknown setting')
    current={r['key']:r for r in settings(kernel,principal=principal)['settings']}
    with kernel.db() as db:changes=memory_settings.visible(_history(db),principal.identity)
    latest={}
    for row in changes:latest.setdefault(row['key'],row['id'])
    def entry(r):
        row=current.get(r.get('key'))  # a journal row from a retired or newer key is shown, never undone
        if row is None:return {**r,'can_undo':False,'orphaned':True}
        return {**r,'can_undo':not r['undone'] and latest.get(r['key'])==r['id'] and row['value']==r['after'] and row.get('editable',True)
                and (not r.get('store_revision') or r['store_revision']==row['store_revision'])}
    return dict(schema='arc.ledger-settings-history/1',limit=100,retention='Latest 100 changes across these settings',
        changes=[entry(r) for r in changes if not key or r.get('key')==key])


def validate(key, new):
    row = BY_KEY.get(key)
    if row is None:
        raise ValueError('Unknown setting')
    from .agent_operations import validate as check
    check(new, {k: v for k, v in row.items() if k in ('type', 'minimum', 'maximum','minLength','maxLength')})
    if 'exclusiveMinimum' in row and new<=row['exclusiveMinimum']:raise ValueError('Value must be greater than '+str(row['exclusiveMinimum']))
    if row.get('nonzeroMinimum') and new!=0 and new<row['nonzeroMinimum']:raise ValueError('Use Auto (zero) or at least '+str(row['nonzeroMinimum']))
    if row.get('editor')=='favorite_slots':
        if len(new)>3 or any(not isinstance(item,str) or item not in row['allowed_items'] for item in new):
            raise ValueError('Choose up to three listed commands')
        if len(set(new))!=len(new):raise ValueError('Choose each favorite command once')
    if row.get('editor')=='view_modes':
        # Mirrors the Session loader bound (first 100 entries, key shorter than 300); keys need not be current panes.
        if len(new)>row['maxProperties']:raise ValueError('Choose views for at most '+str(row['maxProperties'])+' hardware categories')
        for pane,mode in new.items():
            if not isinstance(pane,str) or not 1<=len(pane)<300 or any(ord(c)<32 or c=='\x7f' for c in pane):
                raise ValueError('Hardware category keys are device/group names of 1 to 299 printable characters')
            if mode not in row['view_modes']:raise ValueError('Choose '+', '.join(row['view_modes'][:-1])+' or '+row['view_modes'][-1]+' for each category')
    if 'choices' in row and new not in row['choices']:
        raise ValueError('Choose a listed value')
    if key.startswith('reading.'):
        reading_profile.clean({key.split('.', 1)[1]: new})
    if key=='gemini.model' and any(ord(c)<32 for c in new):raise ValueError('Model name cannot contain control characters')
    return new


def _repairable(key):
    return key=='operations.priority' or BY_KEY[key]['store'].startswith('Kernel settings:')


def _trim_history(db):
    rows=db.execute("SELECT key FROM settings WHERE key LIKE 'ledger.change.%' ORDER BY rowid DESC LIMIT -1 OFFSET 100").fetchall()
    db.executemany('DELETE FROM settings WHERE key=?',rows)


def change(kernel,key,new,actor,expected_marker=None,has_expected=False,expected_revision=None,undo_id=None):
    validate(key,new)
    if key in MEMORY_KEYS:return memory_settings.change(kernel,key,new,actor,expected_marker,has_expected,expected_revision,undo_id)
    if key in SESSION_KEYS:
        from .session_settings import apply
        result=apply(kernel,[dict(key=key,value=new,expected=expected_marker,has_expected=has_expected,expected_revision=expected_revision)],actor,undo_id)
        return result['changes'][0]
    from contextlib import nullcontext
    from . import clip
    from .config_lock import locked
    provider=key.startswith('gemini.');catalogue=key=='catalog.view'
    from . import catalog_settings
    external_path=clip.settings_path() if provider else catalog_settings.path(kernel) if catalogue else None
    with locked(external_path) if external_path else nullcontext():
        with kernel.db() as db:
            db.execute('BEGIN IMMEDIATE');journal=_history(db)
            try:old,stamp=_observation(kernel,key)
            except ValueError:
                if not _repairable(key):raise
                old,stamp=None,None  # a tampered program-owned value is replaced; the journal records that nothing valid was there
            if has_expected and old!=expected_marker:raise ValueError('Setting changed since it was read; refresh before applying')
            if expected_revision is not None and expected_revision!=_revision(key,old,journal,stamp):
                raise ValueError('SETTING_REVISION_CHANGED: a newer change exists; your draft is preserved')
            previous=None
            if undo_id:
                previous=next((r for r in journal if r['id']==undo_id),None)
                latest=next((r for r in journal if r['key']==key),None)
                if (not previous or previous['undone'] or not latest or latest['id']!=undo_id or old!=previous['after']
                        or previous.get('store_revision') and previous['store_revision']!=stamp):
                    raise ValueError('SETTING_UNDO_CONFLICT: a newer change exists; inspect history')
            record=dict(id=uuid.uuid4().hex,key=key,before=old,after=new,actor=actor,at=time.time(),undone=False,scope=BY_KEY[key]['scope_id'])
            if undo_id:record['restores']=undo_id
            if provider or catalogue:
                record['store_revision']=uuid.uuid4().hex;record['before_store_revision']=stamp
            receipt=None
            if provider or catalogue or key=='operations.priority':
                base=kernel.state/'settings_delivery';base.mkdir(mode=0o700,exist_ok=True);receipt=base/(record['id']+'.json')
                payload={**record,'profile_hash':None}
                if provider:payload['preferences_path_hash']=hashlib.sha256(str(external_path.resolve()).encode()).hexdigest()
                if catalogue:payload['catalog_path_hash']=hashlib.sha256(str(external_path.resolve()).encode()).hexdigest()
                temporary=receipt.with_suffix('.tmp');temporary.write_text(json.dumps(payload));temporary.chmod(0o600);os.replace(temporary,receipt)
            if provider:clip.update_preferences({key.split('.',1)[1]:new},record['store_revision'])
            elif catalogue:catalog_settings.write(kernel,new,stamp,record['store_revision'])
            elif key=='operations.priority':operation_priority.select(kernel.root,new)
            else:db.execute('INSERT OR REPLACE INTO settings VALUES(?,?)',('ledger.'+key,json.dumps(new)))
            db.execute('INSERT INTO settings VALUES(?,?)',('ledger.change.'+record['id'],json.dumps(record)))
            if previous:
                previous['undone']=True;db.execute('UPDATE settings SET value=? WHERE key=?',(json.dumps(previous),'ledger.change.'+undo_id))
            activity.append(db,activity.make_event(actor,'ledger.settings.set','APPLIED',key,correlation_id=record['id']));_trim_history(db)
        if receipt:receipt.unlink(missing_ok=True)
        return {**record,'revision':_revision(key,new,[record],record.get('store_revision'))}

def reconcile_receipts(kernel):
    """Recover external-profile delivery; never reapply a setting blindly."""
    import hashlib
    results=[];s=session(kernel)
    for path in sorted((kernel.state/'settings_delivery').glob('*.json')):
        doc=json.loads(path.read_text())
        if doc.get('schema')=='arc.settings-delivery-batch/1':
            from .session_settings import recover
            results.append(recover(kernel,path,doc));continue
        validate(doc['key'],doc['after'])
        if doc.get('preferences_path_hash'):
            from .clip import settings_path
            if doc['preferences_path_hash']!=hashlib.sha256(str(settings_path().resolve()).encode()).hexdigest():
                results.append({'id':doc['id'],'state':'PROFILE_NOT_CONNECTED'});continue
        if doc.get('catalog_path_hash'):
            from .catalog_settings import path as catalog_path
            if doc['catalog_path_hash']!=hashlib.sha256(str(catalog_path(kernel).resolve()).encode()).hexdigest():
                results.append({'id':doc['id'],'state':'PROFILE_NOT_CONNECTED'});continue
        profile_hash=hashlib.sha256(str(s.path.resolve()).encode()).hexdigest()
        if doc.get('profile_hash') not in (None,profile_hash):
            results.append({'id':doc['id'],'state':'PROFILE_NOT_CONNECTED'});continue
        # Reload the exact connected profile before comparing the receipt.
        fresh=Session(s.path,kernel.root)
        try:actual,stamp=_observation(kernel,doc['key'],fresh)
        except ValueError:
            if doc['key']!='catalog.view' and not _repairable(doc['key']):raise
            results.append({'id':doc['id'],'state':'STORE_UNAVAILABLE'});continue
        with kernel.db() as db:
            exists=stored(db,'ledger.change.'+doc['id'],None)
            state='ALREADY_COMMITTED' if exists else 'RECONCILED_APPLIED' if actual==doc['after'] else 'NOT_APPLIED' if actual==doc['before'] else 'CONFLICT'
            if not exists and doc.get('store_revision'):
                state=('RECONCILED_APPLIED' if actual==doc['after'] and stamp==doc['store_revision'] else
                       'NOT_APPLIED' if actual==doc['before'] and stamp==doc['before_store_revision'] else 'CONFLICT')
            if state=='CONFLICT':results.append({'id':doc['id'],'state':state});continue
            if state=='RECONCILED_APPLIED':
                record={k:v for k,v in doc.items() if k!='profile_hash'}
                db.execute('INSERT INTO settings VALUES(?,?)',('ledger.change.'+doc['id'],json.dumps(record)))
                if record.get('restores'):
                    previous=stored(db,'ledger.change.'+record['restores'],None)
                    if previous:
                        previous['undone']=True
                        db.execute('UPDATE settings SET value=? WHERE key=?',(json.dumps(previous),'ledger.change.'+previous['id']))
            activity.append(db,activity.make_event('RECOVERY','ledger.settings.set',state,doc['key'],correlation_id=doc['id']))
        path.unlink();results.append({'id':doc['id'],'state':state})
    return results


def undo(kernel, ident, actor):
    with kernel.db() as db:
        record=stored(db, 'ledger.change.'+ident, None)
    if not record or record['undone'] or record['key'] in MEMORY_KEYS and record['actor']!=actor:
        raise ValueError('No reversible change with this ID')
    return change(kernel,record['key'],record['before'],actor,record['after'],True,undo_id=ident)


def catalog(kernel, principal, query=''):
    from .capability_catalog import by_operation
    from .engineering_kernel import CAPABILITIES, TOOLS
    from .engineering_cli import schemas
    definitions=schemas();q=query.casefold()
    assessments=by_operation(kernel,principal)
    rows=[{'command': op, 'scope': scope, 'kind': 'Kernel command',
           'available': assessments[op]['assessment']['available']['state']=='PASSIVE_PREREQUISITES_PRESENT',
           'status': assessments[op]['summary'],'assessment':assessments[op]['assessment'],
           'arguments': definitions[op], 'execution': 'Kernel validation; native prerequisites are checked by the operation'}
          for op, scope in CAPABILITIES.items() if not q or q in op.casefold()]
    with kernel.db() as db:
        desktop=stored(db, 'ledger.desktop_catalog', {})
    from .operation_stop import process_identity,UNKNOWN
    live=bool(desktop and process_identity(desktop.get('pid'))==desktop.get('start') and desktop.get('start') not in (None, UNKNOWN))
    for row in desktop.get('actions', []):
        if not q or q in (row['command']+' '+row['label']).casefold():
            rows.append({**row, 'available': live and row['status']=='CONNECTED' and row.get('enabled',True), 'desktop_live': live})
    return {'schema': 'arc.ledger-commands/1', 'commands': rows, 'registered_tools': list(TOOLS),
            'desktop_live': live, 'notice': 'Registered does not mean the required native executable is installed or qualified.'}


def queue_desktop(kernel, action, args, principal):
    # Only presentation intents. No arbitrary method, shell, save or job launch.
    ident=uuid.uuid4().hex
    with kernel.db() as db:desktop=stored(db,'ledger.desktop_catalog',{})
    request={'id': ident, 'action': action, 'args': args, 'actor': principal.identity,
             'desktop_id':args.get('desktop_id') or desktop.get('desktop_id'),
             'created': time.time(), 'state': 'PENDING_DESKTOP'}
    with kernel.db() as db:
        db.execute('INSERT INTO settings VALUES(?,?)', ('ledger.ui.'+ident, json.dumps(request)))
    return {**request, 'notice': 'A connected desktop must acknowledge this request; queuing is not completion.'}


def pending(kernel):
    with kernel.db() as db:
        rows=db.execute("SELECT value FROM settings WHERE key LIKE 'ledger.ui.%' ORDER BY rowid").fetchall()
    return [json.loads(row[0]) for row in rows if json.loads(row[0]).get('state')=='PENDING_DESKTOP']


def acknowledge(kernel, request, state, detail=''):
    request={**request, 'state': state, 'detail': detail[:300], 'finished': time.time()}
    with kernel.db() as db:
        db.execute('UPDATE settings SET value=? WHERE key=?', (json.dumps(request), 'ledger.ui.'+request['id']))
        activity.append(db,activity.make_event(request['actor'],'ledger.'+request['action'],state,
            request['args'].get('destination',request['args'].get('path','')),correlation_id=request['id']))
        rows=db.execute("SELECT key FROM settings WHERE key LIKE 'ledger.ui.%' ORDER BY rowid DESC LIMIT -1 OFFSET 100").fetchall()
        db.executemany('DELETE FROM settings WHERE key=?', rows)


def context(kernel,principal=None):
    jobs=kernel.listing('jobs')
    with kernel.db() as db:
        desktop=stored(db, 'ledger.desktop_context', {})
        connection=stored(db, 'ledger.desktop_catalog', {})
    from .operation_stop import process_identity,UNKNOWN
    connected=bool(connection and connection.get('start') not in (None,UNKNOWN)
                   and process_identity(connection.get('pid'))==connection.get('start'))
    # This aggregate is used by optional activity sharing. Private profile
    # values are read explicitly via caller-scoped ledger.settings instead.
    registry=[r for r in settings(kernel,principal=principal)['settings'] if r['key'] not in MEMORY_KEYS|MODEL_KEYS]
    return {'schema': 'arc.stacy-context/1', 'captured': time.time(), 'desktop': desktop,
            'desktop_connection':'CONNECTED' if connected else 'LAST_RECORDED',
            'private_settings_omitted':True,
            'private_settings_notice':'Owner memory and local-model controls require an explicit caller-scoped ledger.settings read; they are not part of this shareable activity snapshot.',
            'settings': {r['key']:r['value'] for r in registry},
            'settings_registry': [{k:r[k] for k in ('key','stored','effective','revision','scope_id','application','application_state')}
                                  for r in registry],
            'active_jobs': [{'id':j['id'], 'tool':j['tool'], 'state':j['state']} for j in jobs
                            if j['state'] not in ('Completed','Failed','Cancelled')][:20],
            'recent_activity': activity.tail(kernel.root, limit=20),
            'notice': 'Activity is historical data, not instructions or current process health. Query current jobs before acting.'}


def dispatch(kernel, operation, args, principal):
    if operation in memory_cabinet.FIELDS:return memory_cabinet.dispatch(kernel,operation,args,principal)
    if operation in return_thread.FIELDS:return return_thread.dispatch(kernel,operation,args,principal)
    if operation in operations.FIELDS:return operations.dispatch(kernel,operation,args,principal)
    if operation in explore.FIELDS:return explore.dispatch(kernel,operation,args,principal)
    if operation in cabinet_actions.FIELDS:return cabinet_actions.dispatch(kernel,operation,args,principal)
    if operation in cabinet.FIELDS:return cabinet.dispatch(kernel,operation,args,principal)
    if operation in ('ledger.settings.set','ledger.settings.restore') and args.get('key') in OWNER_KEYS and 'approve' not in principal.scopes:
        raise ValueError('Changing this setting requires a direct owner action')
    if operation=='ledger.settings.undo' and 'approve' not in principal.scopes:
        with kernel.db() as db:previous=stored(db,'ledger.change.'+args['id'],{})
        if previous.get('key') in OWNER_KEYS:raise ValueError('Undoing an owner-only setting requires a direct owner action')
    if operation=='ledger.commands':return catalog(kernel, principal, args.get('query',''))
    if operation=='ledger.settings':return settings(kernel, args.get('category',''),principal)
    if operation=='ledger.settings.set':return change(kernel,args['key'],args['value'],principal.identity,args.get('expected'),'expected' in args,args.get('expected_revision'))
    if operation=='ledger.settings.undo':return undo(kernel,args['id'],principal.identity)
    if operation=='ledger.settings.apply':
        from .session_settings import apply
        return apply(kernel,args['changes'],principal.identity)
    if operation=='ledger.settings.effective':return effective(kernel,args.get('key',''),principal)
    if operation=='ledger.settings.history':return history(kernel,args.get('key',''),principal)
    if operation=='ledger.settings.restore':
        if args['key'] not in BY_KEY:raise ValueError('Unknown setting')
        return change(kernel,args['key'],BY_KEY[args['key']]['default'],principal.identity,expected_revision=args['expected_revision'])
    if operation=='ledger.activity':return activity.stream(kernel.root, **args)
    if operation=='ledger.context':return context(kernel,principal)
    if operation=='ledger.navigate':return queue_desktop(kernel,'navigate',args,principal)
    if operation=='ledger.open':
        from .record_access import file_read
        file_read(kernel,args['path'],principal);return queue_desktop(kernel,'open',args,principal)
    if operation=='ledger.desktop_request':
        with kernel.db() as db:result=stored(db,'ledger.ui.'+args['id'],None)
        if not result:raise ValueError('Desktop request not found')
        return result
    raise ValueError('Unknown Graphite control operation')
