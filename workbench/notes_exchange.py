"""Owner-private Kernel routes into the existing concern catalog."""
from sdk.cli.arc1cli import notes_exchange as core
from sdk.cli.arc1cli.concern_catalog import Catalog
from .session import config_dir

ID={'type':'string','pattern':'^[a-f0-9]{32}$'}
COLLECTION={'type':'string','pattern':'^owner:[a-f0-9]{32}$'}
SHA={'type':'string','pattern':'^[a-f0-9]{64}$'}
BOUND={'plan':ID,'expected_digest':SHA}
FIELDS={
 'notes.exchange.profiles':({},[]),
 'notes.exchange.collections':({},[]),
 'notes.exchange.preview':({'path':{'type':'string','minLength':1,'maxLength':4096},'profile':{'type':'string','enum':list(core.PROFILES)},'collection':COLLECTION,'parent':{'type':'string','minLength':1,'maxLength':100}},['path','profile']),
 'notes.exchange.plan_note':({**BOUND,'key':ID},[*BOUND,'key']),
 'notes.exchange.commit':(BOUND,list(BOUND)),
 'notes.exchange.get':({'collection':COLLECTION},['collection']),
 'notes.exchange.note':({'collection':COLLECTION,'key':ID},['collection','key']),
 'notes.exchange.conflict':({'collection':COLLECTION,'key':ID},['collection','key']),
 'notes.exchange.resolve':({'collection':COLLECTION,'key':ID,'incoming_sha256':SHA,'expected_note_version':{'type':'integer','minimum':0},'choice':{'type':'string','enum':['keep-local','use-incoming']}},['collection','key','incoming_sha256','expected_note_version','choice']),
 'notes.exchange.export':({'collection':COLLECTION,'path':{'type':'string','minLength':1,'maxLength':4096}},['collection','path'])}
SCOPES={op:'approve' if op.rsplit('.',1)[1] in ('preview','commit','resolve','export') else 'read' for op in FIELDS}
def path():return config_dir()/'concern/catalog.sqlite3'
def dispatch(kernel,op,args,p):
    if op=='notes.exchange.profiles':return {'schema':core.VERSION,'profiles':core.PROFILES,'default':'markdown-v1','authority':'WORKING_NOTES_ONLY','remote_available':False}
    if p.identity!='desktop-owner' or 'read' not in p.scopes:raise ValueError('NOTES_OWNER_PROFILE_REQUIRED')
    exchange=core.Exchange(Catalog(path()))
    suffix=op.rsplit('.',1)[1]
    if suffix=='collections':return {'collections':exchange.collections()}
    if suffix=='preview':return exchange.preview(args['path'],args['profile'],args.get('collection'),args.get('parent','inbox'))
    if suffix=='plan_note':return exchange.plan_note(args['plan'],args['expected_digest'],args['key'])
    if suffix=='commit':return exchange.commit(args['plan'],args['expected_digest'])
    if suffix=='get':
        value=exchange.get(args['collection'])
        return {**value,'notes':[{k:v for k,v in n.items() if k not in ('body','metadata')} for n in value['notes']]}
    if suffix=='note':
        value=exchange.get(args['collection']);n=next((n for n in value['notes'] if n['key']==args['key']),None)
        if n is None:raise ValueError('NOTES_ITEM_UNAVAILABLE')
        return {'note':n,'backlinks':[l for l in value['links'] if l.get('target_key')==args['key']],'content_is_inert':True}
    if suffix=='conflict':return exchange.conflict(args['collection'],args['key'])
    if suffix=='resolve':return exchange.resolve(args['collection'],args['key'],args['incoming_sha256'],args['expected_note_version'],args['choice'])
    if suffix=='export':return exchange.export(args['collection'],args['path'])
    raise ValueError('NOTES_OPERATION_UNAVAILABLE')
