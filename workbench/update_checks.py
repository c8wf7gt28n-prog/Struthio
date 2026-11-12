"""Disposable signed-release verification and real-process installation recovery.

Publisher keys and the deliberately inert miniature program exist only in a
private temporary fixture. No downloaded code is executed.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from zipfile import ZipFile,ZIP_DEFLATED


def program_fixture(base,version='5.0.0a6'):
 from .release_updates import canonical,sha
 program=Path(__file__).resolve().parents[1]
 files={name:(program/name).read_bytes() for name in ('requirements-qt.txt','requirements-pills.txt','requirements-office.txt')}
 files['workbench/launch.py']=b"raise RuntimeError('The installation fixture must never be executed')\n"
 files['workbench/version.py']=('VERSION = '+repr(version)+'\n').encode()
 manifest={'schema':'arc.ledger-runtime/1','product':'Ledger & Slate','version':version,'package_profile':'runtime','delivery_stage':6,
  'files':{name:{'bytes':len(raw),'sha256':sha(raw)} for name,raw in files.items()}}
 path=base/('program-'+version+'.zip')
 with ZipFile(path,'x',ZIP_DEFLATED) as z:
  for name,raw in files.items():z.writestr('Ledger/'+name,raw)
  z.writestr('Ledger/MANIFEST.json',canonical(manifest))
 return path


def setup(base):
 from .baseline import environment
 from .locations import office
 from .engineering_kernel import Kernel,operator
 from .edit_checks import invoke
 from . import release_publisher as P
 root=base/'Office';os.environ.update(environment(os.environ,root,base/'profile'));office(root);k=Kernel(root);p=operator('stage-six-publisher-check')
 initialized=P.initialize(base/'publisher');invoke(k,'releases.clock',{},p)
 invoke(k,'releases.trust',{'root':initialized['root'],'expected_sha256':initialized['sha256']},p)
 return k,p,program_fixture(base)


def child(mode,root,profile,expected):
 from .baseline import environment
 from .engineering_kernel import Kernel,operator
 from .edit_checks import invoke
 from . import release_updates as U,workspace_backup
 os.environ.update(environment(os.environ,root,profile));k=Kernel(root);p=operator('stage-six-publisher-check')
 if mode=='crash':
  U.CRASH_AT='PUBLISHED'
  try:invoke(k,'releases.install',{'id':expected['id'],'expected_digest':expected['digest'],'directory':expected['store']},p)
  except RuntimeError:os._exit(79)
  raise ValueError('Installation fault checkpoint not reached')
 status=invoke(k,'releases.status',{},p);entry=status['installations'][0]
 if entry['state']!='PUBLISHED':raise ValueError('Installation journal did not survive process exit')
 result=invoke(k,'releases.recover',{'id':entry['id'],'action':'FINISH'},p)
 if result['state']!='ACTIVATED' or result['started']:raise ValueError('Recovery did not activate without executing')
 folder=Path(result['folder'])
 if not (folder/'open-current.sh').is_file() or os.readlink(folder/'current')!=result['release']:raise ValueError('Recovered launcher or pointer missing')
 verified=workspace_backup.verify(Path(result['backup']))
 return {'state':'PASSED','journal_recovered':True,'signed_program_rechecked':True,'launcher_present':True,'new_code_executed':False,
  'backup_state':verified['state'],'backup':result['backup'],'counter':result['counter']}


def self_test():
 from .baseline import environment
 from .edit_checks import invoke
 from . import release_publisher as P,workspace_backup
 with tempfile.TemporaryDirectory(prefix='ledger-update-check-') as tmp:
  base=Path(tmp);k,p,program=setup(base);bundle=base/'release.zip';P.build(base/'publisher',program,1,bundle)
  (k.root/'Files').mkdir(exist_ok=True);(k.root/'Files'/'kept.txt').write_text('Owner data, not program payload.\n')
  preview=invoke(k,'releases.preview',{'bundle':str(bundle)},p)
  expected={'id':preview['id'],'digest':preview['content_digest'],'store':str(base/'releases')}
  def run(mode,code):
   proc=subprocess.run([sys.executable,'-m','workbench.update_checks','--child',mode,str(k.root),str(base/'profile'),json.dumps(expected)],env=environment(os.environ,k.root,base/'profile'),capture_output=True,text=True,timeout=60)
   if proc.returncode!=code:raise ValueError('Update recovery child failed: '+(proc.stderr or proc.stdout)[-1500:])
   return {'exit_code':code} if code else json.loads(proc.stdout)
  crash=run('crash',79);recovery=run('recover',0)
  restored=workspace_backup.restore(Path(recovery.pop('backup')),base/'Restored')
  if (Path(restored['workspace'])/'Files'/'kept.txt').read_text()!='Owner data, not program payload.\n':raise ValueError('Pre-update data backup did not restore')
  if k.dispatch('releases.preview',{'bundle':str(bundle)},p)['ok']:raise ValueError('An installed counter was offered again')
  return {'state':'PASSED','scope':'Restricted TUF1 profile and real process exit after program publication before pointer activation',
   'crash':crash,'recovery':recovery,'complete_backup_restored':True,'installed_counter_replay_refused':True,
   'program_fixture':'INERT_MINIATURE_PACKAGE_NOT_EXECUTED','production_publisher_custody':'PENDING','power_loss_qualification':'NOT_PERFORMED'}


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--child',nargs=4);a=p.parse_args()
 try:
  result=child(a.child[0],Path(a.child[1]),Path(a.child[2]),json.loads(a.child[3])) if a.child else self_test()
  print(json.dumps(result,indent=2));return 0
 except (ValueError,OSError,ImportError,subprocess.SubprocessError) as exc:print(json.dumps({'state':'FAILED','error':str(exc)},indent=2));return 1


if __name__=='__main__':raise SystemExit(main())
