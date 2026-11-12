"""Signed pill/1 exchange attached to profiled copies and frozen Changes review."""
import json
import os
from pathlib import Path
import time
import uuid
from . import project_desk as R,edit_storage as S,change_sets as C,import_profiles as I,working_copies as copies,files_service as F,pills,work_trail

FIELDS={
 'exchange.identity':({},[]),
 'exchange.pair':({'card':{'type':'object'},'expected_fingerprint':C.SHA},['card','expected_fingerprint']),
 'exchange.revoke':({'peer':R.ID},['peer']),
 'exchange.rotate_certificate':({},[]),
 'exchange.preview':({'copy':R.ID,'peer':R.ID,'title':R.TITLE,'purpose':{'type':'string','maxLength':4000}},['copy','peer','title','purpose']),
 'exchange.request':({'id':R.ID,'expected_digest':C.SHA},['id','expected_digest']),
 'exchange.inspect':({'path':pills.PLACE},['path']),
 'exchange.accept':({'path':pills.PLACE,'expected_sha256':C.SHA,'for_slate':{'type':'boolean'}},['path','expected_sha256']),
 'exchange.return':({'copy':R.ID,'findings':{'type':'string','maxLength':200000}},['copy']),
 'exchange.stage_result':({'path':pills.PLACE,'expected_sha256':C.SHA},['path','expected_sha256']),
 'exchange.list':(R.PAGE,[]),
 'exchange.send':({'path':F.REL,'address':{'type':'string','maxLength':300},'peer':R.ID},['path','address','peer']),
 'exchange.fetch':({'address':{'type':'string','maxLength':300},'peer':R.ID},['address','peer']),
}
SCOPES={op:'read' if op in ('exchange.identity','exchange.inspect','exchange.list') else 'approve' for op in FIELDS}
SQL=(
 'CREATE TABLE exchange_messages(id TEXT PRIMARY KEY,owner TEXT NOT NULL,sender TEXT NOT NULL,sequence INTEGER NOT NULL,kind TEXT NOT NULL,state TEXT NOT NULL,payload TEXT NOT NULL,UNIQUE(sender,sequence))',
 'CREATE TABLE exchange_outgoing(id TEXT PRIMARY KEY,owner TEXT NOT NULL,payload TEXT NOT NULL)',
)


def ensure(db):
 db.execute('CREATE TABLE IF NOT EXISTS exchange_migrations(version INTEGER PRIMARY KEY,digest TEXT NOT NULL)')
 known={1:R.digest(SQL)};applied=dict(db.execute('SELECT version,digest FROM exchange_migrations'))
 if applied and applied!=known:raise ValueError('EXCHANGE_MIGRATION_UNSUPPORTED')
 if not applied:
  for sql in SQL:db.execute(sql)
  db.execute('INSERT INTO exchange_migrations VALUES(1,?)',(known[1],))


def keys(k):return pills.ring(k)


def open_in(k,path):
 from pillkit import tls_link
 path=tls_link.ordinary(Path(path).expanduser());raw=path.read_bytes();value=pills.kit().open_pill(raw,keys(k),replay=False)
 return raw,value


def export(k,raw,ident,peer):
 folder=F.root(k)/F.EXPORTS/'Pills';folder.mkdir(parents=True,mode=0o700,exist_ok=True);dest=folder/(ident+'.pill')
 if dest.exists():
  if dest.read_bytes()!=raw:raise ValueError('Export identity collision')
 else:
  from pillkit.tls_link import private
  private(dest,raw)
 # Queue approved exports for an explicitly started listener; this opens no socket.
 from pillkit import tls_link as T
 if peer in pills.kit().read_state(keys(k).folder/'tls-peers.json',{}):T.publish(keys(k),dest)
 return F.rel_of(k,dest)


def preview(k,a,p):
 from pillkit import pill as P
 keys(k).peer(a['peer']);meta,row,root=S.workspace(k,a['copy'],p)
 tree=C.tree(k,root,meta,True,C.load_base(k,row)['files']);selected={};excluded=[]
 for path,info in tree['files'].items():
  try:P.safe_rel(path)
  except ValueError:excluded.append({'path':path,'reason':'PILL_1_CANNOT_CARRY_HIDDEN_OR_NONPORTABLE_NAME'});continue
  if info['bytes']>P.MAX_FILE:raise ValueError('A pill member exceeds 64 MiB')
  selected[path]=info
 if not selected or len(selected)>500 or sum(v['bytes'] for v in selected.values())>192*1048576:raise ValueError('Select 1–500 visible files, up to 192 MiB total for pill export')
 value={'id':uuid.uuid4().hex,'copy':a['copy'],'owner':p.identity,'peer':a['peer'],'title':a['title'],'purpose':a['purpose'],
  'files':selected,'excluded':excluded,'profile':meta['profile'],'created':time.time(),'authority':'PREVIEW_NOT_EXPORTED'}
 value['content_digest']=R.digest(value)
 with k.db() as db:return S.put(db,p.identity,'exchange_preview',value)


def request(k,a,p):
 from pillkit import pill as P
 with k.db() as db:value=S.get(db,p.identity,'exchange_preview',a['id'])
 if value['content_digest']!=a['expected_digest']:raise ValueError('Review the exact pill preview')
 with S.lock(k,value['copy']):
  meta,row,root=S.workspace(k,value['copy'],p)
  for path,info in value['files'].items():
   if S.inspect_file(root,path)!=info:raise ValueError('Export source changed; preview again')
  ring=keys(k);ring.peer(value['peer'])
  ident=uuid.uuid5(uuid.NAMESPACE_URL,'pill-request:'+value['id']).hex
  with k.db() as db:prior=db.execute('SELECT payload FROM exchange_outgoing WHERE id=? AND owner=?',(ident,p.identity)).fetchone()
  if prior:return json.loads(prior[0])
  listing={path:{'sha256':f['sha256'],'bytes':f['bytes']} for path,f in value['files'].items()}
  task={'id':uuid.uuid4().hex,'title':value['title'],'purpose':value['purpose']}
  c=P.contract(ring,value['peer'],'request',task,Path(row['work']).name,listing,['inspect','analyze','propose_revisions','test'],['findings','candidate_files'])
  c['id']=ident
  raw=P.build(ring,c,{path:S.object_bytes(k,f['sha256'],P.MAX_FILE) for path,f in value['files'].items()})
  kept=S.keep_bytes(k,raw);path=export(k,raw,ident,value['peer'])
  result={'id':ident,'copy':row['id'],'path':path,'raw':kept,'contract':c,'excluded':value['excluded'],'direction':'REQUEST','to':value['peer']}
  with k.db() as db:db.execute('INSERT INTO exchange_outgoing VALUES(?,?,?)',(ident,p.identity,R.canonical(result)))
  return result


def reserve(k,raw,pill,p):
 c=pill.contract;sha=S.keep_bytes(k,raw)
 with k.db() as db:
  db.execute('BEGIN IMMEDIATE');row=db.execute('SELECT owner,payload FROM exchange_messages WHERE id=?',(pill.id,)).fetchone()
  if row:
   value=json.loads(row[1])
   if row[0]!=p.identity or value['raw']!=sha:raise ValueError('PILL_REPLAY_OR_ID_COLLISION')
  else:
   keys(k).seen(c['sender']['key'],pill.id,c['sequence'])
   value={'id':pill.id,'owner':p.identity,'sender':c['sender']['key'],'sequence':c['sequence'],'kind':pill.kind,'raw':sha,
    'state':'PREPARED','copy':uuid.uuid5(uuid.NAMESPACE_URL,'pill-copy:'+p.identity+':'+pill.id).hex,'contract':c,'created':time.time()}
   db.execute('INSERT INTO exchange_messages VALUES(?,?,?,?,?,?,?)',(pill.id,p.identity,value['sender'],value['sequence'],pill.kind,'PREPARED',R.canonical(value)))
 try:keys(k).remember(c['sender']['key'],pill.id,c['sequence'])
 except pills.kit().PillError as exc:
  if not str(exc).startswith('PILL_REPLAY:'):raise
  # This exact-byte, same-owner durable intent makes a duplicate acknowledgement recoverable.
  with k.db() as db:check=db.execute('SELECT payload FROM exchange_messages WHERE id=? AND owner=?',(pill.id,p.identity)).fetchone()
  if not check or json.loads(check[0])['raw']!=sha:raise
 return value


def accepted(k,raw,pill,p,for_slate):
 if pill.kind!='request':raise ValueError('Accept a request; use stage_result for a returned result')
 pills.policy(pill);entry=reserve(k,raw,pill,p)
 if entry['state']!='PREPARED':return entry
 ident=entry['copy'];work='Working copies/Pill-'+ident[:12]
 value={'files':{},'directories':[],'entries':[],'profile':'MIXED','limits':dict(I.DEFAULT_LIMITS)}
 for path,data in pill.files.items():
  C.check_path(value,path)
  if I.SENSITIVE.search(data):raise ValueError('Pill contains credential-like material; import refused')
  digest=S.keep_bytes(k,data);value['files'][path]={'sha256':digest,'bytes':len(data),'mode':0o600}
 base=S.keep_bytes(k,json.dumps(I.manifest(value),sort_keys=True).encode())
 with S.lock(k,ident):
  target=F.root(k)/work;target.parent.mkdir(parents=True,mode=0o700,exist_ok=True)
  if not target.exists():
   stage=target.parent/('.pill-'+ident)
   if stage.exists():
    import shutil
    shutil.rmtree(stage)
   I.write_tree(k,stage,value);work_trail.accepting(k)
   with S.directory(target.parent) as fd:S.rename_linux(fd,stage.name,target.name)
  if I.folder_scan(target,'MIXED',value['limits'])['files']!=value['files']:raise ValueError('Retained imported pill copy differs; inspect recovery')
  meta={'schema':'arc.profiled-copy/1','id':ident,'copy':ident,'owner':p.identity,'created':time.time(),'preview':pill.id,
   'profile':'MIXED','limits':value['limits'],'source_kind':'PILL','original_update':'RETURN_RESULT_ONLY_NO_LOCAL_MASTER'}
  entry.update(state='ACCEPTED',work=work,for_slate=for_slate)
  with copies.opened(k) as db:
   db.execute('INSERT OR IGNORE INTO copies(id,owner,source,base,base_size,base_mtime,base_mode,work,for_slate,state,revision,created,updated,kind) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
     (ident,p.identity,'pill:'+pill.id,base,len(value['files']),0,0o700,work,int(for_slate),'WORKING',0,time.time(),time.time(),'folder'))
   S.put(db,p.identity,'workspace',meta)
   db.execute('UPDATE exchange_messages SET state=?,payload=? WHERE id=?',('ACCEPTED',R.canonical(entry),pill.id))
 return entry


def returned(k,a,p):
 from pillkit import pill as P
 meta,row,root=S.workspace(k,a['copy'],p)
 with k.db() as db:matches=[json.loads(r[0]) for r in db.execute("SELECT payload FROM exchange_messages WHERE owner=? AND kind='request' AND state='ACCEPTED'",(p.identity,))]
 entry=next((e for e in matches if e['copy']==row['id']),None)
 if not entry:raise ValueError('This copy did not arrive through reviewed exchange')
 original=P.open_pill(S.object_bytes(k,entry['raw'],P.MAX_PILL),keys(k),replay=False);base=original.contract['source']['files']
 tree=C.tree(k,root,meta,True,C.load_base(k,row)['files']);changes=[];carried={}
 for path in sorted(set(base)|set(tree['files'])):
  P.safe_rel(path);before=base.get(path,{}).get('sha256','');after=tree['files'].get(path,{}).get('sha256','')
  if before==after:continue
  changes.append({'op':'replace' if before and after else 'create' if after else 'delete','path':path,'before':before,'after':after})
  if after:carried[path]=S.object_bytes(k,after,P.MAX_FILE)
 findings=a.get('findings','');ring=keys(k);c=P.contract(ring,entry['sender'],'result',original.contract['task'],original.contract['source']['label'],base,
    in_reply_to=entry['id'],result={'findings':findings,'changes':changes,'evidence':[]})
 if C.tree(k,root,meta,False,C.load_base(k,row)['files'])['files']!=tree['files']:raise ValueError('Result source changed; review and export again')
 raw=P.build(ring,c,carried);path=export(k,raw,c['id'],entry['sender']);kept=S.keep_bytes(k,raw)
 result={'id':c['id'],'copy':row['id'],'path':path,'raw':kept,'contract':c,'direction':'RESULT','to':entry['sender']}
 with k.db() as db:db.execute('INSERT INTO exchange_outgoing VALUES(?,?,?)',(c['id'],p.identity,R.canonical(result)))
 return result


def stage_result(k,raw,pill,p):
 if pill.kind!='result':raise ValueError('This operation stages a result pill only')
 c=pill.contract
 with k.db() as db:row=db.execute('SELECT payload FROM exchange_outgoing WHERE id=? AND owner=?',(c['in_reply_to'],p.identity)).fetchone()
 if not row:raise ValueError('No matching outgoing request owned by this caller')
 sent=json.loads(row[0]);request=sent['contract']
 if sent['to']!=c['sender']['key'] or c['task']!=request['task'] or c['source']!=request['source']:raise ValueError('Result sender/task/source differs from its exact request')
 entry=reserve(k,raw,pill,p)
 if entry['state']!='PREPARED':return entry
 meta,copy,root=S.workspace(k,sent['copy'],p);changes=[]
 for item in c['result']['changes']:
  path=item['path'];C.check_path(meta,path);actual=S.inspect_file(root,path)
  if (actual['sha256'] if actual else '')!=item['before']:raise ValueError('RESULT_CONFLICT: working bytes changed since the request')
  if actual:S.keep_file(k,root,path)
  after=S.keep_bytes(k,pill.files[path]) if item['after'] else None
  changes.append({'path':path,'before':item['before'] or None,'after':after,'before_mode':actual['mode'] if actual else None,
    'after_mode':actual['mode'] if actual and after else 0o644 if after else None,'operation':'PILL_'+item['op'].upper()})
 if changes:
  with S.lock(k,copy['id']):proposal=C.freeze(k,meta,copy,changes,p,'WORKING',c['result']['findings'][:4000],
   provenance={'origin':'PAIRED_PILL_RESULT','pill':pill.id,'sender':entry['sender'],'request':request['id'],'source_revision':c['source']['revision']},
   fixed_id=uuid.uuid5(uuid.NAMESPACE_URL,'pill-proposal:'+p.identity+':'+pill.id).hex)
  entry['proposal']=proposal['id'];entry['proposal_digest']=proposal['content_digest']
 entry.update(state='STAGED_FOR_REVIEW' if changes else 'FINDINGS_ONLY',copy=copy['id'],findings=c['result']['findings'])
 with k.db() as db:db.execute('UPDATE exchange_messages SET state=?,payload=? WHERE id=?',(entry['state'],R.canonical(entry),entry['id']))
 return entry


def dispatch(k,op,a,p):
 from pillkit import tls_link as T
 ring=keys(k)
 if op=='exchange.identity':
  paired=pills.kit().read_state(ring.folder/'tls-peers.json',{})
  return {'card':T.card(ring),'peers':[{'key':key,'name':value['name'],'tls':key in paired} for key,value in ring.peers().items()]}
 if op=='exchange.pair':return T.pair(ring,a['card'],a['expected_fingerprint'])
 if op=='exchange.revoke':ring.unpair(a['peer']);return {'revoked':a['peer'],'replay_history':'RETAINED'}
 if op=='exchange.rotate_certificate':T.certificate(ring,True);return T.card(ring)
 if op=='exchange.list':
  with k.db() as db:
   received=[json.loads(r[0]) for r in db.execute('SELECT payload FROM exchange_messages WHERE owner=? ORDER BY rowid DESC LIMIT ? OFFSET ?',(p.identity,a.get('limit',100),a.get('offset',0)))]
   outgoing=[json.loads(r[0]) for r in db.execute('SELECT payload FROM exchange_outgoing WHERE owner=? ORDER BY rowid DESC LIMIT ? OFFSET ?',(p.identity,a.get('limit',100),a.get('offset',0)))]
  return {'received':received,'outgoing':outgoing}
 if op=='exchange.inspect':
  raw,pill=open_in(k,a['path']);new=True
  try:ring.seen(pill.contract['sender']['key'],pill.id,pill.contract['sequence'])
  except ValueError:new=False
  return {'pill':pill.summary(),'contract':pill.contract,'sha256':pills.kit().sha256(raw),'new':new,'authority':'QUARANTINE_ONLY_NO_WORK_GRANTED'}
 work_trail.accepting(k)
 if op=='exchange.preview':return preview(k,a,p)
 if op=='exchange.request':return request(k,a,p)
 if op=='exchange.return':return returned(k,a,p)
 if op in ('exchange.accept','exchange.stage_result'):
  raw,pill=open_in(k,a['path'])
  if pills.kit().sha256(raw)!=a['expected_sha256']:raise ValueError('Pill changed after inspection')
  return accepted(k,raw,pill,p,a.get('for_slate',False)) if op=='exchange.accept' else stage_result(k,raw,pill,p)
 epoch=work_trail.work_status(k)['epoch']
 def stopped():
  gate=work_trail.work_status(k);return gate['held'] or gate['epoch']!=epoch
 if op=='exchange.send':return T.send(ring,a['address'],F.resolve(k,a['path']),a['peer'],stopped)
 if op=='exchange.fetch':return T.fetch(ring,a['address'],F.root(k)/'Received'/'Pills',a['peer'],stopped)
 raise ValueError('Unknown exchange operation')
