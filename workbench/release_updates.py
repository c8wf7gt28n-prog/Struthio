"""Explicit offline releases using a restricted TUF-1 metadata profile.

Ed25519, SHA256, the four top-level roles, sequential dual-signed root rotation,
expiry and persistent version/hash high-water marks. No delegations, mirrors,
online updater, automatic activation, or bundled publisher trust/private key.
This is a limited verifier, not a claim of full TUF client qualification.
"""
import datetime as D
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import shlex
import stat
import time
import uuid
from functools import wraps
from zipfile import ZipFile,ZIP_STORED,ZIP_DEFLATED,BadZipFile,LargeZipFile
from . import project_desk as R,edit_storage as S,change_sets as C,work_trail,workspace_backup,state_backup
from pillkit.pill import strict_json

PLACE={'type':'string','minLength':1,'maxLength':4096}
FIELDS={
 'releases.status':({},[]),'releases.clock':({},[]),
 'releases.trust':({'root':PLACE,'expected_sha256':C.SHA},['root','expected_sha256']),
 'releases.preview':({'bundle':PLACE},['bundle']),
 'releases.install':({'id':R.ID,'expected_digest':C.SHA,'directory':PLACE},['id','expected_digest','directory']),
 'releases.recover':({'id':R.ID,'action':{'type':'string','enum':['FINISH','REVERT_POINTER']}},['id','action']),
}
SCOPES={op:'read' if op=='releases.status' else 'approve' for op in FIELDS}
SQL=('CREATE TABLE release_trust(owner TEXT PRIMARY KEY,payload TEXT NOT NULL)',
 'CREATE TABLE release_previews(id TEXT PRIMARY KEY,owner TEXT NOT NULL,payload TEXT NOT NULL,digest TEXT NOT NULL)',
 'CREATE TABLE release_journal(id TEXT PRIMARY KEY,owner TEXT NOT NULL,state TEXT NOT NULL,payload TEXT NOT NULL)')
CRASH_AT=None


def ensure(db):
 db.execute('CREATE TABLE IF NOT EXISTS release_migrations(version INTEGER PRIMARY KEY,digest TEXT NOT NULL)')
 applied=dict(db.execute('SELECT version,digest FROM release_migrations'))
 if applied and applied!={1:R.digest(SQL)}:raise ValueError('RELEASE_MIGRATION_UNSUPPORTED')
 if not applied:
  for sql in SQL:db.execute(sql)
  db.execute('INSERT INTO release_migrations VALUES(1,?)',(R.digest(SQL),))


def canonical(value):
 # Restrict strings to the subset where JSON encoding equals TUF canonical JSON.
 def valid(v):
  if isinstance(v,str):
   if any(ord(c)<32 or 0xD800<=ord(c)<=0xDFFF for c in v):raise ValueError('Unsupported canonical metadata string')
  elif isinstance(v,dict):
   for k,c in v.items():
    if not isinstance(k,str):raise ValueError('Metadata keys must be strings')
    valid(k);valid(c)
  elif isinstance(v,list):
   for c in v:valid(c)
  elif v is None or type(v) in (bool,int):pass
  else:raise ValueError('Unsupported metadata scalar; floats are not admitted')
 valid(value);return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()


def sha(raw):return hashlib.sha256(raw).hexdigest()
def boot():return Path('/proc/sys/kernel/random/boot_id').read_text().strip()


def zip_errors(function):
 @wraps(function)
 def checked(*a,**kw):
  try:return function(*a,**kw)
  except (BadZipFile,LargeZipFile,EOFError,NotImplementedError,RuntimeError) as exc:raise ValueError('Update archive refused: '+str(exc)) from None
 return checked


def load(k,p):
 with k.db() as db:row=db.execute('SELECT payload FROM release_trust WHERE owner=?',(p.identity,)).fetchone()
 return json.loads(row[0]) if row else {'versions':{},'hashes':{},'installed_counter':0,'root':None,'clock':None}


def save(k,p,value):
 with k.db() as db:db.execute('INSERT OR REPLACE INTO release_trust VALUES(?,?)',(p.identity,R.canonical(value)))


def now_for(value):
 clock=value.get('clock');now=time.time()
 if not clock or clock['boot']!=boot() or not 0<=time.monotonic()-clock['monotonic']<86400:raise ValueError('CONFIRM_OFFLINE_CLOCK_ON_THIS_BOOT')
 if now<clock['utc']-60 or now<value.get('last_utc',0)-60:raise ValueError('CLOCK_MOVED_BACKWARDS')
 return now


def metadata(raw,kind,now):
 if len(raw)>1048576:raise ValueError('Metadata size limit')
 value=strict_json(raw,'release metadata');canonical(value)
 if set(value)!={'signed','signatures'} or not isinstance(value['signatures'],list) or len(value['signatures'])>64:raise ValueError('Metadata envelope refused')
 s=value['signed']
 if s.get('_type')!=kind or not re.fullmatch(r'1\.\d+\.\d+',str(s.get('spec_version',''))) or type(s.get('version'))!=int or s['version']<1:raise ValueError('Unsupported metadata type/version')
 expiry=D.datetime.strptime(s['expires'],'%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=D.timezone.utc).timestamp()
 if expiry<=now:raise ValueError('EXPIRED_'+kind.upper())
 return value


def check_root(value):
 s=value['signed']
 if set(s)!={'_type','spec_version','version','expires','consistent_snapshot','keys','roles'} or s['consistent_snapshot'] is not True:raise ValueError('Only the declared consistent-snapshot root profile is supported')
 if set(s['roles'])!={'root','timestamp','snapshot','targets'} or not 1<=len(s['keys'])<=32:raise ValueError('Root role/key profile refused')
 for ident,key in s['keys'].items():
  if key.get('keytype')!='ed25519' or key.get('scheme')!='ed25519' or set(key)!={'keytype','scheme','keyval'} or set(key['keyval'])!={'public'} or not re.fullmatch('[0-9a-f]{64}',key['keyval']['public']):raise ValueError('Only Ed25519 public keys are supported')
  if sha(canonical(key))!=ident:raise ValueError('Root key id differs from its canonical key')
 for role in s['roles'].values():
  if set(role)!={'keyids','threshold'} or type(role['threshold'])!=int or not 1<=role['threshold']<=len(set(role['keyids'])) or len(role['keyids'])!=len(set(role['keyids'])) or not set(role['keyids'])<=set(s['keys']):raise ValueError('Invalid role threshold')


def signatures(value,root,role):
 from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
 from cryptography.exceptions import InvalidSignature
 trusted=root['signed'];spec=trusted['roles'][role];seen=set();valid=set();publics=set()
 for item in value['signatures']:
  if not isinstance(item,dict) or set(item)!={'keyid','sig'}:raise ValueError('Signature fields refused')
  ident=item['keyid']
  if ident in seen:continue
  seen.add(ident)
  if ident not in spec['keyids']:continue
  public=trusted['keys'][ident]['keyval']['public']
  try:Ed25519PublicKey.from_public_bytes(bytes.fromhex(public)).verify(bytes.fromhex(item['sig']),canonical(value['signed']))
  except (InvalidSignature,ValueError):continue
  valid.add(ident);publics.add(public)
 if len(valid)<spec['threshold'] or len(publics)<spec['threshold']:raise ValueError('SIGNATURE_THRESHOLD_'+role.upper())


@zip_errors
def archive(path,maximum=128*1048576):
 path=Path(path).expanduser().absolute()
 if any(p.is_symlink() for p in (path,*path.parents)) or not path.is_file() or path.stat().st_size>maximum or path.stat().st_nlink!=1:raise ValueError('Use an ordinary bounded update bundle')
 raw=path.read_bytes();z=ZipFile(io.BytesIO(raw));names=set();total=0
 for item in z.infolist():
  S.relative(item.filename)
  mode=item.external_attr>>16;total+=item.file_size
  if item.filename.casefold() in names or item.is_dir() or stat.S_IFMT(mode) not in (0,stat.S_IFREG) or item.flag_bits&1 or item.compress_type not in (ZIP_STORED,ZIP_DEFLATED):raise ValueError('Unsafe/duplicate update archive member')
  names.add(item.filename.casefold())
  if item.file_size>256*1048576 or item.file_size>max(1048576,item.compress_size*200):raise ValueError('Update expansion limit')
 if len(names)>6000 or total>512*1048576:raise ValueError('Update package limit')
 return raw,z


@zip_errors
def verify_bundle(k,path,p,persist=True):
 value=load(k,p);now=now_for(value)
 if value['root'] is None:raise ValueError('TRUST_A_ROOT_FINGERPRINT_FIRST')
 raw,z=archive(path);root=value['root'];check_root(root)
 # An expired old root can authorize the next root; only the final root must be current.
 for _ in range(32):
  name='metadata/'+str(root['signed']['version']+1)+'.root.json'
  if name not in z.namelist():break
  new=metadata(z.read(name),'root',-1);check_root(new)
  if new['signed']['version']!=root['signed']['version']+1:raise ValueError('Root rotation skipped a version')
  signatures(new,root,'root');signatures(new,new,'root');root=new
 if 'metadata/'+str(root['signed']['version']+1)+'.root.json' in z.namelist():raise ValueError('Root rotation chain exceeds 32')
 metadata(canonical(root),'root',now);check_root(root)
 if root!=value['root']:
  # Persist validated root transitions even if later metadata is unavailable.
  value['root']=root
  if persist:save(k,p,value)
 timestamp_raw=z.read('metadata/timestamp.json');timestamp=metadata(timestamp_raw,'timestamp',now);signatures(timestamp,root,'timestamp')
 def advance(role,doc,data):
  version=doc['signed']['version'];old=value['versions'].get(role,0)
  if version<old or version==old and value['hashes'].get(role)!=sha(data):raise ValueError('METADATA_ROLLBACK_OR_EQUIVOCATION_'+role.upper())
  value['versions'][role]=version;value['hashes'][role]=sha(data)
  if persist:save(k,p,value)
 if set(timestamp['signed'])!={'_type','spec_version','version','expires','meta'} or set(timestamp['signed']['meta'])!={'snapshot.json'}:raise ValueError('Timestamp profile refused')
 snapshot_link=timestamp['signed']['meta']['snapshot.json']
 if snapshot_link['version']<value['versions'].get('snapshot',0):raise ValueError('SNAPSHOT_REFERENCE_ROLLBACK')
 advance('timestamp',timestamp,timestamp_raw)
 snapshot_raw=z.read('metadata/'+str(snapshot_link['version'])+'.snapshot.json');snapshot=metadata(snapshot_raw,'snapshot',now)
 def bound(raw,link,version):
  if set(link)!={'version','length','hashes'} or type(link['version'])!=int or type(link['length'])!=int or link['version']!=version or link['length']!=len(raw) or link['hashes']!={'sha256':sha(raw)}:raise ValueError('Metadata version/hash/length binding differs')
 bound(snapshot_raw,snapshot_link,snapshot['signed']['version']);signatures(snapshot,root,'snapshot')
 if set(snapshot['signed'])!={'_type','spec_version','version','expires','meta'} or set(snapshot['signed']['meta'])!={'targets.json'}:raise ValueError('Delegations/extra metadata are outside this profile')
 link=snapshot['signed']['meta']['targets.json']
 if link['version']<value['versions'].get('targets',0):raise ValueError('TARGETS_REFERENCE_ROLLBACK')
 advance('snapshot',snapshot,snapshot_raw)
 targets_raw=z.read('metadata/'+str(link['version'])+'.targets.json');targets=metadata(targets_raw,'targets',now)
 bound(targets_raw,link,targets['signed']['version']);signatures(targets,root,'targets')
 if set(targets['signed'])!={'_type','spec_version','version','expires','targets'} or len(targets['signed']['targets'])!=1:raise ValueError('Only one nondelegated release target is supported')
 advance('targets',targets,targets_raw)
 name,info=next(iter(targets['signed']['targets'].items()));S.relative(name)
 if set(info)!={'length','hashes','custom'} or set(info['hashes'])!={'sha256'}:raise ValueError('Target metadata profile refused')
 data=z.read('targets/'+info['hashes']['sha256']+'.'+name)
 if len(data)!=info['length'] or sha(data)!=info['hashes']['sha256']:raise ValueError('TARGET_HASH_OR_SIZE_MISMATCH')
 custom=info['custom']
 if set(custom)!={'product','version','counter','python_min','python_max','kernel'} or custom['product']!='Ledger & Slate' or custom['kernel']!='arc-ledger.kernel/1':raise ValueError('Release compatibility metadata refused')
 import sys
 if type(custom['counter'])!=int or custom['counter']<=value['installed_counter']:raise ValueError('RELEASE_ROLLBACK_OR_ALREADY_INSTALLED')
 if not tuple(custom['python_min'])<=sys.version_info[:2]<=tuple(custom['python_max']):raise ValueError('Unsupported Python version for this release')
 value['last_utc']=now
 if persist:save(k,p,value)
 return value,{'target':name,'sha256':sha(data),'bytes':len(data),'compatibility':custom,'root_version':root['signed']['version'],
  'metadata_versions':value['versions'],'bundle_sha256':sha(raw)},data


@zip_errors
def program(raw):
 # Validate bytes as data. No script from the downloaded program is executed.
 z=ZipFile(io.BytesIO(raw));members=z.infolist();files={};prefix=None;total=0
 if not 1<=len(members)<=6000:raise ValueError('Program file count limit')
 for item in members:
  S.relative(item.filename);parts=item.filename.split('/');prefix=prefix or parts[0]
  mode=item.external_attr>>16;total+=item.file_size
  if parts[0]!=prefix or len(parts)<2 or item.is_dir() or stat.S_IFMT(mode) not in (0,stat.S_IFREG) or item.flag_bits&1 or item.compress_type not in (ZIP_STORED,ZIP_DEFLATED):raise ValueError('Unsafe program archive')
  name='/'.join(parts[1:]);S.relative(name)
  if name.casefold() in {n.casefold() for n in files} or set(Path(name).parts)&{'.ledger','.venv','.git','__pycache__'}:raise ValueError('Program package contains duplicate/private state')
  if item.file_size>128*1048576 or item.file_size>max(1048576,item.compress_size*200) or total>512*1048576:raise ValueError('Program expansion limit')
  files[name]=(z.read(item),0o755 if item.external_attr>>16&0o111 else 0o644)
 if 'MANIFEST.json' not in files:raise ValueError('Missing program manifest')
 m=strict_json(files['MANIFEST.json'][0],'program manifest')
 if m.get('schema')!='arc.ledger-runtime/1' or m.get('product')!='Ledger & Slate' or m.get('package_profile')!='runtime' or set(files)!=(set(m['files'])|{'MANIFEST.json'}):raise ValueError('Program manifest/payload differs')
 for name,info in m['files'].items():
  data=files[name][0]
  if info!={'bytes':len(data),'sha256':sha(data)}:raise ValueError('Program file differs: '+name)
 return m,files


def journal(k,p,entry):
 with k.db() as db:db.execute('INSERT OR REPLACE INTO release_journal VALUES(?,?,?,?)',(entry['id'],p.identity,entry['state'],R.canonical(entry)))


def pointer(folder,target):
 path=folder/'current'
 if path.exists() and not path.is_symlink():raise ValueError('current must be the owned release pointer, never an ordinary directory')
 temp=folder/('.current-'+uuid.uuid4().hex)
 os.symlink(target,temp);os.replace(temp,path)
 fd=os.open(folder,os.O_RDONLY|os.O_DIRECTORY)
 try:os.fsync(fd)
 finally:os.close(fd)


def launcher(k,folder):
 import sys
 from .session import config_dir
 script='#!/bin/sh\nset -eu\nexport PYTHONPATH='+shlex.quote(str(folder/'current'))+'\nexport ARC_LEDGER_WORKSPACE='+shlex.quote(str(k.root))+'\nexport ARC1_WORKBENCH_CONFIG_HOME='+shlex.quote(str(config_dir()))+'\ncd '+shlex.quote(str(folder/'current'))+'\nexec '+shlex.join([sys.executable,'-m','workbench.launch'])+' "$@"\n'
 from pillkit.tls_link import private
 private(folder/'open-current.sh',script.encode());(folder/'open-current.sh').chmod(0o700)


def install(k,a,p):
 with k.db() as db:row=db.execute('SELECT payload,digest FROM release_previews WHERE id=? AND owner=?',(a['id'],p.identity)).fetchone()
 if not row or row[1]!=a['expected_digest']:raise ValueError('Review the exact signed update preview')
 preview=json.loads(row[0]);trust,checked,data=verify_bundle(k,preview['bundle'],p)
 if checked!=preview['verified']:raise ValueError('Update metadata or payload changed after review')
 m,files=program(data)
 if m['version']!=checked['compatibility']['version']:raise ValueError('Signed and inner program versions differ')
 from .locations import program as current_program
 for name in ('requirements-qt.txt','requirements-pills.txt','requirements-office.txt'):
  current=current_program(k.root)/name
  if current.exists() and (name not in files or files[name][0]!=current.read_bytes()):raise ValueError('DEPENDENCY_CHANGE_REQUIRES_SEPARATE_RUNTIME_INSTALLATION')
 folder=state_backup.safe_path(a['directory']) if hasattr(state_backup,'safe_path') else workspace_backup.safe_base(a['directory'])
 from .locations import program as installed
 if any(workspace_backup.nested(folder,base) for base in (k.root,Path(__file__).resolve().parents[1])):raise ValueError('Keep releases outside the live workspace and program')
 folder.mkdir(parents=True,mode=0o700,exist_ok=True);marker=folder/'LEDGER_RELEASE_STORE.json'
 if not marker.exists():
  if any(folder.iterdir()):raise ValueError('Choose an empty release store')
  from pillkit.tls_link import private
  private(marker,R.canonical({'schema':'arc.release-store/1','owner':p.identity}).encode())
 if strict_json(marker.read_bytes(),'release store')!={'schema':'arc.release-store/1','owner':p.identity}:raise ValueError('Release store belongs to another owner/profile')
 ident=uuid.uuid4().hex;backup=folder/'backups'/ident
 # Both actions require a closed coordinator; the snapshot is verified before activation.
 saved=workspace_backup.create(k.root,backup)
 with state_backup.closed_ledger(k.state):
  trust,current_checked,_=verify_bundle(k,preview['bundle'],p)
  if current_checked!=checked:raise ValueError('Release trust changed before installation; preview again')
  release='releases/'+str(checked['compatibility']['counter'])+'-'+checked['sha256'][:12]
  target=folder/release;target.parent.mkdir(mode=0o700,exist_ok=True)
  with S.directory(target.parent):pass
  stage=folder/('.install-'+ident);stage.mkdir(mode=0o700)
  for name,(raw,mode) in files.items():
   with S.parent(stage,name,True) as (fd,base):
    out=os.open(base,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,mode,dir_fd=fd)
    with os.fdopen(out,'wb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
    os.fsync(fd)
  previous=os.readlink(folder/'current') if (folder/'current').is_symlink() else None
  entry={'id':ident,'state':'PREPARED','folder':str(folder),'stage':stage.name,'release':release,'previous':previous,'backup':str(backup),
   'target_sha256':checked['sha256'],'counter':checked['compatibility']['counter'],'version':m['version'],'owner':p.identity,
   'manifest_sha256':sha(files['MANIFEST.json'][0]),'bundle_object':S.keep_bytes(k,Path(preview['bundle']).read_bytes())}
  journal(k,p,entry)
  if CRASH_AT=='PREPARED':raise RuntimeError('RELEASE_TEST_INTERRUPTION')
  with S.directory(folder) as fd:S.rename_linux(fd,stage.name,release)
  entry['state']='PUBLISHED';journal(k,p,entry)
  if CRASH_AT=='PUBLISHED':raise RuntimeError('RELEASE_TEST_INTERRUPTION')
  launcher(k,folder)
  pointer(folder,release);entry['state']='ACTIVATED';entry['launcher']=str(folder/'open-current.sh');journal(k,p,entry)
  trust['installed_counter']=entry['counter'];save(k,p,trust)
 return {**entry,'started':False,'notice':'Program pointer activated. Data backup retained; launching/migrating the new program is a separate owner action.'}


def recover(k,a,p):
 with k.db() as db:row=db.execute('SELECT payload FROM release_journal WHERE id=? AND owner=?',(a['id'],p.identity)).fetchone()
 if not row:raise ValueError('Release journal unavailable')
 e=json.loads(row[0]);folder=workspace_backup.safe_base(e['folder'])
 with state_backup.closed_ledger(k.state):
  if a['action']=='REVERT_POINTER':
   if not (folder/'current').is_symlink() or os.readlink(folder/'current')!=e['release']:raise ValueError('A later or unknown pointer exists; not reverted')
   if e['previous'] is None:raise ValueError('No earlier installed pointer; retain both program and data backup for inspection')
   pointer(folder,e['previous']);e['state']='POINTER_REVERTED_DATA_NOT_RESTORED'
  else:
   trust=load(k,p)
   already_active=trust['installed_counter']==e['counter'] and (folder/'current').is_symlink() and os.readlink(folder/'current')==e['release']
   if not already_active:
    trust,verified,_=verify_bundle(k,copies_path(k,e['bundle_object']),p)
    if verified['sha256']!=e['target_sha256']:raise ValueError('Frozen installation differs from its signed target')
   target=folder/e['release'];stage=folder/e['stage']
   with S.directory(target.parent):pass
   if not target.exists() and stage.exists():
    with S.directory(folder) as fd:S.rename_linux(fd,stage.name,e['release'])
   if not target.is_dir():raise ValueError('Staged program missing')
   # Recheck every file against the frozen, signed inner manifest before activation.
   manifest_raw,_=S.read_bytes(target,'MANIFEST.json',4*1048576)
   if sha(manifest_raw)!=e['manifest_sha256']:raise ValueError('Retained program manifest changed')
   manifest=strict_json(manifest_raw,'program manifest')
   for name,info in manifest['files'].items():
    raw,actual=S.read_bytes(target,name,128*1048576)
    if {'bytes':len(raw),'sha256':sha(raw)}!=info:raise ValueError('Retained program changed')
   existing=os.readlink(folder/'current') if (folder/'current').is_symlink() else None
   if existing not in (e['previous'],e['release']):raise ValueError('A later release pointer exists')
   launcher(k,folder)
   pointer(folder,e['release']);e['state']='ACTIVATED';trust=load(k,p);trust['installed_counter']=max(trust['installed_counter'],e['counter']);save(k,p,trust)
  journal(k,p,e)
 return {**e,'started':False,'data_rollback':'Restore the verified backup into NEW workspace/profile destinations before starting an older incompatible program.'}


def copies_path(k,digest):
 from .working_copies import store
 return store(k)/digest


def dispatch(k,op,a,p):
 # One owner has one trust/version history. Serialize the whole validation,
 # including partial-progress persistence, so concurrent requests cannot save
 # an older snapshot over a newer high-water mark.
 with S.lock(k,sha(('release-owner:'+p.identity).encode())[:32]):return _dispatch(k,op,a,p)


def _dispatch(k,op,a,p):
 value=load(k,p)
 if op=='releases.status':
  with k.db() as db:entries=[json.loads(r[0]) for r in db.execute('SELECT payload FROM release_journal WHERE owner=? ORDER BY rowid DESC LIMIT 20',(p.identity,))]
  return {'trusted':value['root'] is not None,'root_version':value['root']['signed']['version'] if value['root'] else None,
    'versions':value['versions'],'installed_counter':value['installed_counter'],'clock':value['clock'],'installations':entries,
    'profile':'RESTRICTED_TUF1_ED25519_SHA256_NO_DELEGATIONS','production_publisher_trust':'OWNER_BOOTSTRAP_REQUIRED'}
 if op=='releases.clock':
  now=time.time()
  if now<value.get('last_utc',0)-60:raise ValueError('CLOCK_MOVED_BACKWARDS: correct the clock before updating')
  value['clock']={'utc':now,'monotonic':time.monotonic(),'boot':boot()};save(k,p,value);return value['clock']
 if op=='releases.trust':
  if value['root'] is not None:raise ValueError('Root replacement uses sequential dual-signed rotation in a release bundle')
  now=now_for(value);path=Path(a['root']).expanduser().absolute()
  if any(v.is_symlink() for v in (path,*path.parents)) or not path.is_file() or path.stat().st_size>1048576:raise ValueError('Use an ordinary root metadata file up to 1 MiB')
  raw=path.read_bytes()
  if sha(raw)!=a['expected_sha256']:raise ValueError('Bootstrap root fingerprint differs')
  root=metadata(raw,'root',now);check_root(root);signatures(root,root,'root');value['root']=root;value['last_utc']=now;save(k,p,value)
  return {'trusted_root':root['signed']['version'],'sha256':sha(raw),'keys_installed':len(root['signed']['keys'])}
 if op=='releases.preview':
  value,checked,data=verify_bundle(k,a['bundle'],p);m,_=program(data)
  if m['version']!=checked['compatibility']['version']:raise ValueError('Release target and manifest version differ')
  preview={'id':uuid.uuid4().hex,'bundle':str(Path(a['bundle']).expanduser().absolute()),'verified':checked,'created':time.time(),
    'meaning':'Authentic to the explicitly trusted publisher; no downloaded program has been executed.'}
  digest=R.digest(preview)
  with k.db() as db:db.execute('INSERT INTO release_previews VALUES(?,?,?,?)',(preview['id'],p.identity,R.canonical(preview),digest))
  return {**preview,'content_digest':digest,'next':'Close Graphite, then use release_cli install for a backed-up side-by-side installation.'}
 if op=='releases.install':return install(k,a,p)
 if op=='releases.recover':return recover(k,a,p)
 raise ValueError('Unknown release operation')
