"""Disposable real-TLS request/result, restart and complete-restore walkthrough.

Both workspaces run on this host. This does not qualify a physical two-machine
network, production publisher custody, a display, native workers or a model.
"""
import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
from unittest.mock import patch


@contextmanager
def listener(ring,into):
 from pillkit.tls_link import Server
 server=Server(('127.0.0.1',0),ring,into);thread=threading.Thread(target=server.serve_forever,kwargs={'poll_interval':.05},daemon=True);thread.start()
 try:yield '127.0.0.1:'+str(server.server_address[1])
 finally:server.shutdown();server.server_close();thread.join(timeout=10)


def setup(base):
 from .edit_checks import fixture
 from .engineering_kernel import Kernel,operator
 from .baseline import environment
 from .locations import office
 from . import pills
 from pillkit import tls_link as T
 a,p,home,source,copy=fixture(base/'A','stage-six-owner')
 root=base/'B'/'Office';os.environ.update(environment(os.environ,root,base/'B'/'profile'));office(root);b=Kernel(root);q=operator('stage-six-appliance')
 ar=pills.ring(a);br=pills.ring(b);ac=T.card(ar);bc=T.card(br)
 T.pair(ar,bc,bc['certificate_sha256']);T.pair(br,ac,ac['certificate_sha256'])
 return a,p,home,source,copy,b,q,ar,br


def exchange(base):
 from .edit_checks import invoke
 from . import files_service as F
 from pillkit import tls_link as T
 a,p,home,source,copy,b,q,ar,br=setup(base)
 preview=invoke(a,'exchange.preview',{'copy':copy['id'],'peer':br.key,'title':'Clock hand revision','purpose':'Propose black hands; keep the master blue until owner publication.'},p)
 if '.editorconfig' not in [r['path'] for r in preview['excluded']]:raise ValueError('Pill/1 exclusions were not displayed')
 request=invoke(a,'exchange.request',{'id':preview['id'],'expected_digest':preview['content_digest']},p)
 into=F.root(a)/'Received'/'Pills'
 with listener(ar,into) as endpoint:
  fetched=invoke(b,'exchange.fetch',{'address':endpoint,'peer':ar.key},q)
  incoming=fetched['saved'][0];inspected=invoke(b,'exchange.inspect',{'path':incoming},q)
  if invoke(b,'exchange.list',{},q)['received']:raise ValueError('Transport accepted work automatically')
  accepted=invoke(b,'exchange.accept',{'path':incoming,'expected_sha256':inspected['sha256'],'for_slate':True},q)
  repeated=invoke(b,'exchange.accept',{'path':incoming,'expected_sha256':inspected['sha256'],'for_slate':True},q)
  if repeated['copy']!=accepted['copy']:raise ValueError('Acceptance was duplicated')
  text=invoke(b,'changes.file',{'copy':accepted['copy'],'path':'note.txt'},q)
  proposal=invoke(b,'changes.propose',{'copy':accepted['copy'],'operations':[{'op':'WRITE','path':'note.txt','base_sha256':text['sha256'],'text':'Clock needs black hands.\n'}]},q)
  invoke(b,'changes.apply',{'id':proposal['id'],'expected_digest':proposal['content_digest']},q)
  result=invoke(b,'exchange.return',{'copy':accepted['copy'],'findings':'A black-hand working revision, for owner review.'},q)
  invoke(b,'exchange.send',{'path':result['path'],'address':endpoint,'peer':ar.key},q)
 incoming=str(into/(br.key+'-'+result['id']+'.pill'));inspected=invoke(a,'exchange.inspect',{'path':incoming},p)
 staged=invoke(a,'exchange.stage_result',{'path':incoming,'expected_sha256':inspected['sha256']},p)
 before=(source/'note.txt').read_text();work=a.root/'Files'/copy['work']
 if (work/'note.txt').read_text()!=before:raise ValueError('Staging applied returned bytes')
 invoke(a,'changes.review',{'id':staged['proposal']},p)
 invoke(a,'changes.apply',{'id':staged['proposal'],'expected_digest':staged['proposal_digest']},p)
 if (source/'note.txt').read_text()!=before:raise ValueError('Working application changed the master')
 with patch('pathlib.Path.home',return_value=home):
  publication=invoke(a,'changes.original.preview',{'copy':copy['id']},p)
  commit=invoke(a,'changes.publish',{'id':publication['id'],'expected_digest':publication['content_digest']},p)
  if (source/'note.txt').read_text()!='Clock needs black hands.\n':raise ValueError('Explicit master publication failed')
  invoke(a,'changes.undo',{'id':commit['id']},p)
 if (source/'note.txt').read_text()!=before:raise ValueError('Master undo failed')
 expected={'request':request['id'],'result':result['id'],'proposal':staged['proposal'],'digest':staged['proposal_digest'],
  'work':copy['work'],'sender':br.key,'sequence':result['contract']['sequence']}
 return a,p,expected


def reopen(root,profile,expected):
 from .baseline import environment
 from .engineering_kernel import Kernel,operator
 from .edit_checks import invoke
 from . import pills
 os.environ.update(environment(os.environ,root,profile));k=Kernel(root);p=operator('stage-six-owner')
 records=invoke(k,'exchange.list',{},p)
 if not any(r['id']==expected['result'] for r in records['received']) or not any(r['id']==expected['request'] for r in records['outgoing']):raise ValueError('Exchange provenance was lost')
 proposal=invoke(k,'changes.review',{'id':expected['proposal']},p)
 if proposal['proposal']['content_digest']!=expected['digest']:raise ValueError('Frozen returned proposal changed')
 if (root/'Files'/expected['work']/'note.txt').read_text()!='Clock needs black hands.\n':raise ValueError('Working result was lost')
 try:pills.ring(k).seen(expected['sender'],expected['result'],expected['sequence'])
 except ValueError:pass
 else:raise ValueError('Replay exclusions were lost')
 return {'state':'PASSED','exchange_provenance':True,'frozen_proposal':True,'working_bytes':True,'replay_history':True,'effects_replayed':0}


def self_test():
 from .baseline import environment
 from . import workspace_backup
 with tempfile.TemporaryDirectory(prefix='ledger-stage-six-') as tmp:
  base=Path(tmp);k,p,expected=exchange(base)
  def restart(root,profile):
   child=subprocess.run([sys.executable,'-m','workbench.deployment_checks','--reopen',str(root),str(profile),json.dumps(expected)],env=environment(os.environ,root,profile),capture_output=True,text=True,timeout=60)
   if child.returncode:raise ValueError('Exchange restart failed: '+(child.stderr or child.stdout)[-1500:])
   return json.loads(child.stdout)
  first=restart(k.root,base/'A'/'profile');os.environ.update(environment(os.environ,k.root,base/'A'/'profile'))
  saved=workspace_backup.create(k.root,base/'backup');restored=workspace_backup.restore(base/'backup',base/'Restored')
  second=restart(Path(restored['workspace']),Path(restored['profile']))
  return {'state':'PASSED','scope':'Two independent workspaces, real mutual TLS 1.3 on this host; explicit working review and master publication/undo',
   'quarantine_is_not_acceptance':True,'working_copy_is_not_master':True,'master_publication_and_undo':True,
   'restart':first,'backup':{n:saved[n] for n in ('state','files','databases')},'restored_restart':second,
   'physical_two_machine_qualification':'PENDING','qt':'SEPARATE_CHECK','model_calls':0,'external_network_calls':0}


def ui_test():
 from .baseline import environment
 with tempfile.TemporaryDirectory(prefix='ledger-stage-six-ui-') as tmp:
  base=Path(tmp);root=base/'Office';os.environ.update(environment(os.environ,root,base/'profile'));os.environ['QT_QPA_PLATFORM']='offscreen'
  from .locations import office
  from .qt_app import make_app,WorkbenchWindow
  from .deployment_qt import show
  office(root);app=make_app(['ledger-stage-six-check']);host=WorkbenchWindow(root=root,restore=False)
  try:
   host.show();tab=show(host);app.processEvents()
   if tab.pages.count()!=3 or show(host) is not tab:raise ValueError('Deployment panel routes did not open exactly once')
   return {'state':'PASSED','scope':'Real Qt deployment panel opens without a listener, model or grant','physical_display':'PENDING'}
  finally:host.close();app.processEvents()


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--ui',action='store_true');p.add_argument('--reopen',nargs=3);a=p.parse_args()
 try:
  result=reopen(Path(a.reopen[0]),Path(a.reopen[1]),json.loads(a.reopen[2])) if a.reopen else ui_test() if a.ui else self_test()
  print(json.dumps(result,indent=2));return 0
 except (ValueError,OSError,ImportError,subprocess.SubprocessError) as exc:print(json.dumps({'state':'FAILED','error':str(exc)},indent=2));return 1


if __name__=='__main__':raise SystemExit(main())
