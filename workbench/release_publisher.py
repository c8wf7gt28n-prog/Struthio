"""Offline authoring utility. Creates owner-held keys; never ships private keys."""
import argparse
import datetime as D
import json
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
from pillkit.pill import write_private
from .release_updates import canonical,sha,program


def key_meta(private):
 return {'keytype':'ed25519','scheme':'ed25519','keyval':{'public':private.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw).hex()}}


def signed(body,keys):
 return {'signed':body,'signatures':[{'keyid':sha(canonical(key_meta(key))),'sig':key.sign(canonical(body)).hex()} for key in keys]}


def expiry(days):return (D.datetime.now(D.timezone.utc)+D.timedelta(days=days)).strftime('%Y-%m-%dT%H:%M:%SZ')


def initialize(folder):
 folder=Path(folder);folder.mkdir(mode=0o700,parents=True,exist_ok=False);keys={};roles={};private={}
 for role in ('root','timestamp','snapshot','targets'):
  private[role]=[]
  for index in range(3 if role=='root' else 1):
   key=Ed25519PrivateKey.generate();meta=key_meta(key);ident=sha(canonical(meta));keys[ident]=meta
   name=role+'-'+str(index)+'.key';write_private(folder/name,key.private_bytes(serialization.Encoding.Raw,serialization.PrivateFormat.Raw,serialization.NoEncryption()));private[role].append(name)
  roles[role]={'keyids':[sha(canonical(key_meta(Ed25519PrivateKey.from_private_bytes((folder/n).read_bytes())))) for n in private[role]],'threshold':2 if role=='root' else 1}
 root=signed({'_type':'root','spec_version':'1.0.31','version':1,'expires':expiry(365),'consistent_snapshot':True,'keys':keys,'roles':roles},load_keys(folder,private['root']))
 write_private(folder/'root.json',canonical(root));write_private(folder/'publisher.json',canonical({'private':private,'last_counter':0}))
 return {'root':str(folder/'root.json'),'sha256':sha(canonical(root)),'root_threshold':'2 of 3','notice':'Authoring keys are together for setup; production custodians should separate offline root keys.'}


def load_keys(folder,names):
 result=[]
 for name in names:
  path=Path(folder)/name
  if path.is_symlink() or path.stat().st_mode&0o077:raise ValueError('Publisher key permissions/path refused')
  result.append(Ed25519PrivateKey.from_private_bytes(path.read_bytes()))
 return result


def build(folder,program_path,counter,out):
 folder=Path(folder);state=json.loads((folder/'publisher.json').read_text())
 if counter<=state['last_counter']:raise ValueError('Publisher counter must increase')
 raw=Path(program_path).read_bytes();manifest,_=program(raw);root=json.loads((folder/'root.json').read_text());name='ledger-program.zip'
 custom={'product':'Ledger & Slate','version':manifest['version'],'counter':counter,'python_min':[3,11],'python_max':[3,13],'kernel':'arc-ledger.kernel/1'}
 targets=signed({'_type':'targets','spec_version':'1.0.31','version':counter,'expires':expiry(180),'targets':{
  name:{'length':len(raw),'hashes':{'sha256':sha(raw)},'custom':custom}}},load_keys(folder,state['private']['targets']))
 targets_raw=canonical(targets)
 def link(data):return {'version':counter,'length':len(data),'hashes':{'sha256':sha(data)}}
 snapshot=signed({'_type':'snapshot','spec_version':'1.0.31','version':counter,'expires':expiry(90),'meta':{'targets.json':link(targets_raw)}},load_keys(folder,state['private']['snapshot']))
 snapshot_raw=canonical(snapshot)
 timestamp=signed({'_type':'timestamp','spec_version':'1.0.31','version':counter,'expires':expiry(30),'meta':{'snapshot.json':link(snapshot_raw)}},load_keys(folder,state['private']['timestamp']))
 with open(out,'xb') as stream:
  with ZipFile(stream,'w',ZIP_DEFLATED) as z:
   z.writestr('metadata/root.json',canonical(root));z.writestr('metadata/timestamp.json',canonical(timestamp))
   z.writestr('metadata/'+str(counter)+'.snapshot.json',snapshot_raw);z.writestr('metadata/'+str(counter)+'.targets.json',targets_raw)
   for path in sorted(folder.glob('*.root.json')):z.writestr('metadata/'+path.name,path.read_bytes())
   z.writestr('targets/'+sha(raw)+'.'+name,raw)
 from pillkit.tls_link import private
 state['last_counter']=counter;private(folder/'publisher.json',canonical(state))
 return {'bundle':str(out),'counter':counter,'version':manifest['version'],'private_keys_included':False}


def rotate(folder):
 import tempfile,shutil
 folder=Path(folder);state=json.loads((folder/'publisher.json').read_text());old=json.loads((folder/'root.json').read_text());version=old['signed']['version']+1
 with tempfile.TemporaryDirectory(prefix='root-rotation-') as temp:
  newdir=Path(temp)/'keys';initialize(newdir);new=json.loads((newdir/'root.json').read_text());newstate=json.loads((newdir/'publisher.json').read_text())
  new['signed']['version']=version;root=signed(new['signed'],load_keys(folder,state['private']['root'])+load_keys(newdir,newstate['private']['root']))
  private={}
  for role,names in newstate['private'].items():
   private[role]=[]
   for name in names:
    destination='v'+str(version)+'-'+name;write_private(folder/destination,(newdir/name).read_bytes());private[role].append(destination)
  write_private(folder/(str(version)+'.root.json'),canonical(root))
  from pillkit.tls_link import private as replace
  replace(folder/'root.json',canonical(root));replace(folder/'publisher.json',canonical({'private':private,'last_counter':state['last_counter']}))
 return {'root_version':version,'old_and_new_threshold_signatures':True,'public_root_sha256':sha(canonical(root))}


def main():
 p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
 a=sub.add_parser('init');a.add_argument('directory',type=Path)
 a=sub.add_parser('rotate-root');a.add_argument('directory',type=Path)
 a=sub.add_parser('build');a.add_argument('--keys',type=Path,required=True);a.add_argument('--program',type=Path,required=True);a.add_argument('--counter',type=int,required=True);a.add_argument('--out',type=Path,required=True)
 a=p.parse_args();result=initialize(a.directory) if a.command=='init' else rotate(a.directory) if a.command=='rotate-root' else build(a.keys,a.program,a.counter,a.out);print(json.dumps(result,indent=2))


if __name__=='__main__':main()
