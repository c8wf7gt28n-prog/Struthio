"""Exchange, releases and deployment: paired exchange over the pill link, release publication and offline update recovery,
with their security and recovery boundaries."""
import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
from zipfile import ZipFile,ZIP_DEFLATED
from workbench.edit_checks import invoke
from workbench.deployment_checks import setup,listener
from workbench import release_updates as U,release_publisher as Publisher,update_checks,exchange,pills,files_service as F
from pillkit import pill as P,tls_link as T
from pillkit.state import database


def rewrite(source,dest,change):
 with ZipFile(source) as z:files={n:z.read(n) for n in z.namelist()}
 change(files)
 with ZipFile(dest,'x',ZIP_DEFLATED) as z:
  for n,raw in files.items():z.writestr(n,raw)
 return dest



HOLDS=[]


def setUpModule():
    # Nothing here may start a worker, submit a job or send a provider request (Graphite's test rule). The one exception is a
    # kernel whose own launch the protocol double has replaced (protocol_fixture.ProtocolWorker): it may queue a job row, which
    # the test then runs in this process against the loopback double; no worker can start from it.
    from workbench import clip
    from workbench.engineering_kernel import Kernel as HeldKernel
    real_submit=HeldKernel.submit
    def submit(kernel,*args,**kwargs):
        if 'launch' not in vars(kernel):raise AssertionError('No job submission')
        return real_submit(kernel,*args,**kwargs)
    for held in (patch.object(HeldKernel,'launch',side_effect=AssertionError('No worker launch')),patch.object(HeldKernel,'submit',submit),
            patch.object(clip,'_request',side_effect=AssertionError('No provider request'))):
        held.start();HOLDS.append(held)


def tearDownModule():
    while HOLDS:HOLDS.pop().stop()

class PairedExchange(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.base=Path(self.temp.name)
  self.a,self.p,self.home,self.source,self.copy,self.b,self.q,self.ar,self.br=setup(self.base)

 def request(self):
  preview=invoke(self.a,'exchange.preview',{'copy':self.copy['id'],'peer':self.br.key,'title':'Clock','purpose':'A reviewed black-hand revision'},self.p)
  return invoke(self.a,'exchange.request',{'id':preview['id'],'expected_digest':preview['content_digest']},self.p)

 def incoming(self):
  request=self.request();path=self.a.root/'Files'/request['path'];inspected=invoke(self.b,'exchange.inspect',{'path':str(path)},self.q)
  accepted=invoke(self.b,'exchange.accept',{'path':str(path),'expected_sha256':inspected['sha256']},self.q)
  return request,accepted

 def result(self):
  request,received=self.incoming();text=invoke(self.b,'changes.file',{'copy':received['copy'],'path':'note.txt'},self.q)
  prop=invoke(self.b,'changes.propose',{'copy':received['copy'],'operations':[{'op':'WRITE','path':'note.txt','base_sha256':text['sha256'],'text':'Clock needs black hands.\n'}]},self.q)
  invoke(self.b,'changes.apply',{'id':prop['id'],'expected_digest':prop['content_digest']},self.q)
  result=invoke(self.b,'exchange.return',{'copy':received['copy'],'findings':'Proposed black hands.'},self.q)
  path=self.b.root/'Files'/result['path'];return result,{'path':str(path),'expected_sha256':P.sha256(path.read_bytes())}

 def test_export_is_frozen_and_pill1_exclusions_are_visible(self):
  preview=invoke(self.a,'exchange.preview',{'copy':self.copy['id'],'peer':self.br.key,'title':'Clock','purpose':'Inspect'},self.p)
  self.assertIn('.editorconfig',[r['path'] for r in preview['excluded']])
  (self.a.root/'Files'/self.copy['work']/'note.txt').write_text('Outside edit\n')
  self.assertFalse(self.a.dispatch('exchange.request',{'id':preview['id'],'expected_digest':preview['content_digest']},self.p)['ok'])
  self.assertEqual((self.source/'note.txt').read_text(),'Clock needs blue hands.\n')

 def test_wrong_recipient_and_modified_pill_bytes_are_refused(self):
  request=self.request();raw=(self.a.root/'Files'/request['path']).read_bytes();other=P.Keyring(self.base/'other')
  other.pair(self.ar.card())
  with self.assertRaises(ValueError):P.open_pill(raw,other,replay=False)
  path=self.a.root/'Files'/request['path']
  self.assertFalse(self.b.dispatch('exchange.accept',{'path':str(path),'expected_sha256':'0'*64},self.q)['ok'])
  with self.assertRaises(ValueError):P.open_pill(raw[:-24]+b'x'*24,self.br,replay=False)

 def test_replay_history_migrates_without_the_old_retention_limit(self):
  folder=self.base/'migrated';ring=P.Keyring(folder);sender='a'*32
  P.write_state(folder/'seen.json',{sender:{'ids':['b'*32],'sequences':[7]}})
  # Migration preserves the original independent exclusion sets.
  with self.assertRaises(ValueError):ring.seen(sender,'b'*32,99)
  with self.assertRaises(ValueError):ring.seen(sender,'c'*32,7)
  ring.remember(sender,'d'*32,8)
  with database(folder) as db:db.executemany('INSERT INTO seen VALUES(?,?,?)',[(sender,format(i+100,'032x'),i+100) for i in range(20001)])
  with self.assertRaises(ValueError):P.Keyring(folder).seen(sender,'d'*32,8)
  from concurrent.futures import ThreadPoolExecutor
  with ThreadPoolExecutor(max_workers=4) as pool:values=list(pool.map(lambda _:P.Keyring(folder).next_sequence(),range(24)))
  self.assertEqual(len(set(values)),24)

 def test_tls_pin_mismatch_and_revocation_refuse_real_connections(self):
  other=P.Keyring(self.base/'other');card=T.card(other);T.pair(self.ar,card,card['certificate_sha256'])
  with self.assertRaises(ValueError):T.pair(self.ar,T.card(self.br),'0'*64)
  with listener(self.br,self.base/'quarantine') as endpoint:
   with self.assertRaises(ValueError):T.request(self.ar,endpoint,other.key,'GET','/v1/offers')
   self.br.unpair(self.ar.key)
   with self.assertRaises((ValueError,OSError)):T.request(self.ar,endpoint,self.br.key,'GET','/v1/offers')

 def test_interrupted_tls_transfer_resumes_after_server_and_keyring_restart(self):
  data=os.urandom(T.CHUNK*2+3000);listing={'sample.bin':{'sha256':P.sha256(data),'bytes':len(data)}}
  contract=P.contract(self.ar,self.br.key,'request',{'id':'e'*32,'title':'Bounded transfer','purpose':'Transfer only'},'Sample',listing,['inspect'],['findings'])
  raw=P.build(self.ar,contract,{'sample.bin':data});path=self.base/'sample.pill';P.write_private(path,raw);into=self.base/'quarantine';calls=[]
  def cancel():calls.append(1);return len(calls)>1
  with listener(self.br,into) as endpoint:
   with self.assertRaisesRegex(ValueError,'TRANSFER_STOPPED'):T.send(self.ar,endpoint,path,self.br.key,cancel)
  partial=self.br.folder/'tls-partial'/(self.ar.key+'-'+contract['id']+'.part')
  self.assertEqual(partial.stat().st_size,T.CHUNK)
  with partial.open('ab') as f:f.write(b'unacknowledged tail')
  self.br=P.Keyring(self.br.folder)
  with listener(self.br,into) as endpoint:result=T.send(self.ar,endpoint,path,self.br.key)
  self.assertEqual(result['state'],'QUARANTINED');saved=into/(self.ar.key+'-'+contract['id']+'.pill')
  self.assertEqual(saved.read_bytes(),raw);self.br.seen(self.ar.key,contract['id'],contract['sequence'])
  self.assertEqual(invoke(self.b,'exchange.list',{},self.q)['received'],[])

 def test_conflicting_working_bytes_refuse_returned_edit_staging(self):
  result,args=self.result();work=self.a.root/'Files'/self.copy['work']/'note.txt';work.write_text('An owner revision\n')
  response=self.a.dispatch('exchange.stage_result',args,self.p)
  self.assertFalse(response['ok']);self.assertIn('RESULT_CONFLICT',response['error']['message']);self.assertEqual(work.read_text(),'An owner revision\n')

 def test_revoked_sender_cannot_apply_a_previously_staged_result(self):
  result,args=self.result();entry=invoke(self.a,'exchange.stage_result',args,self.p)
  invoke(self.a,'exchange.revoke',{'peer':self.br.key},self.p)
  self.assertFalse(self.a.dispatch('changes.apply',{'id':entry['proposal'],'expected_digest':entry['proposal_digest']},self.p)['ok'])
  self.assertEqual((self.a.root/'Files'/self.copy['work']/'note.txt').read_text(),'Clock needs blue hands.\n')

 def test_received_copy_has_no_local_master_publication_route(self):
  request,entry=self.incoming()
  self.assertFalse(self.b.dispatch('changes.original.preview',{'copy':entry['copy']},self.q)['ok'])
  self.assertEqual(entry['state'],'ACCEPTED');self.assertEqual(entry['for_slate'],False)

 def test_larger_admitted_pills_can_return_findings_without_a_small_text_limit(self):
  path=self.a.root/'Files'/self.copy['work']/'sample.bin';data=os.urandom(9*1048576);path.write_bytes(data)
  request,accepted=self.incoming()
  self.assertGreater((self.a.root/'Files'/request['path']).stat().st_size,8*1048576)
  result=invoke(self.b,'exchange.return',{'copy':accepted['copy'],'findings':'Read the admitted binary as data only.'},self.q)
  path=self.b.root/'Files'/result['path'];entry=invoke(self.a,'exchange.stage_result',{'path':str(path),'expected_sha256':P.sha256(path.read_bytes())},self.p)
  self.assertEqual(entry['state'],'FINDINGS_ONLY');self.assertNotIn('proposal',entry)


class OfflineUpdates(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.base=Path(self.temp.name)
  self.k,self.p,self.program=update_checks.setup(self.base);self.keys=self.base/'publisher';self.bundle=self.base/'release.zip';Publisher.build(self.keys,self.program,1,self.bundle)

 def preview(self,path=None):return self.k.dispatch('releases.preview',{'bundle':str(path or self.bundle)},self.p)

 def test_boot_clock_fingerprint_and_root_threshold_are_required(self):
  from workbench.engineering_kernel import operator
  p=operator('new-publisher-owner');root=self.keys/'root.json';raw=root.read_bytes()
  self.assertFalse(self.k.dispatch('releases.trust',{'root':str(root),'expected_sha256':U.sha(raw)},p)['ok'])
  invoke(self.k,'releases.clock',{},p)
  self.assertFalse(self.k.dispatch('releases.trust',{'root':str(root),'expected_sha256':'0'*64},p)['ok'])
  value=json.loads(raw);value['signatures']=value['signatures'][:1];bad=self.base/'one-signer.json';bad.write_bytes(U.canonical(value))
  self.assertFalse(self.k.dispatch('releases.trust',{'root':str(bad),'expected_sha256':U.sha(bad.read_bytes())},p)['ok'])
  with patch.object(U,'boot',return_value='different-boot'):self.assertFalse(self.preview()['ok'])

 def test_expired_metadata_bad_signature_and_changed_target_are_refused(self):
  self.assertTrue(self.preview()['ok'])
  with patch.object(U.time,'time',return_value=time.time()+31*86400):
   response=self.preview();self.assertFalse(response['ok']);self.assertIn('EXPIRED_TIMESTAMP',response['error']['message'])
  def bad_signature(files):
   v=json.loads(files['metadata/timestamp.json']);v['signatures'][0]['sig']='0'*128;files['metadata/timestamp.json']=U.canonical(v)
  changed=rewrite(self.bundle,self.base/'bad-signature.zip',bad_signature);self.assertFalse(self.preview(changed)['ok'])
  def corrupt(files):
   name=next(n for n in files if n.startswith('targets/'));files[name]=files[name]+b'changed'
  changed=rewrite(self.bundle,self.base/'bad-target.zip',corrupt);self.assertFalse(self.preview(changed)['ok'])
  broken=self.base/'broken.zip';broken.write_bytes(b'not a zip');self.assertFalse(self.preview(broken)['ok'])

 def test_metadata_rollback_equivocation_and_partial_high_water(self):
  newer=self.base/'release-2.zip';Publisher.build(self.keys,self.program,2,newer)
  def missing(files):files.pop('metadata/2.snapshot.json')
  partial=rewrite(newer,self.base/'partial.zip',missing);self.assertFalse(self.preview(partial)['ok'])
  self.assertEqual(U.load(self.k,self.p)['versions']['timestamp'],2)
  self.assertFalse(self.preview()['ok']);self.assertTrue(self.preview(newer)['ok'])
  state=json.loads((self.keys/'publisher.json').read_text())
  def equivocate(files):
   v=json.loads(files['metadata/timestamp.json'])['signed'];v['expires']=Publisher.expiry(31)
   files['metadata/timestamp.json']=U.canonical(Publisher.signed(v,Publisher.load_keys(self.keys,state['private']['timestamp'])))
  altered=rewrite(newer,self.base/'equivocation.zip',equivocate);self.assertFalse(self.preview(altered)['ok'])

 def test_dual_signed_root_rotation_retains_metadata_high_water(self):
  self.assertTrue(self.preview()['ok']);Publisher.rotate(self.keys);newer=self.base/'rotated.zip';Publisher.build(self.keys,self.program,2,newer)
  state=json.loads((self.keys/'publisher.json').read_text())
  def old_version(files):
   v=json.loads(files['metadata/timestamp.json'])['signed'];v['version']=1
   files['metadata/timestamp.json']=U.canonical(Publisher.signed(v,Publisher.load_keys(self.keys,state['private']['timestamp'])))
  altered=rewrite(newer,self.base/'rotated-old-version.zip',old_version);self.assertFalse(self.preview(altered)['ok'])
  saved=U.load(self.k,self.p);self.assertEqual(saved['root']['signed']['version'],2);self.assertEqual(saved['versions']['timestamp'],1)
  self.assertTrue(self.preview(newer)['ok']);self.assertFalse(self.preview()['ok'])

 def test_overlapping_update_reviews_cannot_regress_trust_history(self):
  import threading
  from concurrent.futures import ThreadPoolExecutor
  newer=self.base/'release-2.zip';Publisher.build(self.keys,self.program,2,newer)
  entered=threading.Event();proceed=threading.Event();original=U.metadata
  def hold(raw,kind,now):
   value=original(raw,kind,now)
   if kind=='timestamp' and value['signed']['version']==2:
    entered.set()
    if not proceed.wait(5):raise ValueError('Concurrent check did not release')
   return value
  with patch.object(U,'metadata',side_effect=hold),ThreadPoolExecutor(max_workers=1) as pool:
   future=pool.submit(self.preview,newer)
   try:
    self.assertTrue(entered.wait(5));self.assertFalse(self.preview()['ok'])
   finally:proceed.set()
   self.assertTrue(future.result(timeout=10)['ok'])
  self.assertEqual(U.load(self.k,self.p)['versions']['timestamp'],2);self.assertFalse(self.preview()['ok'])

 def test_prepared_installation_recovery_rechecks_retained_program(self):
  preview=invoke(self.k,'releases.preview',{'bundle':str(self.bundle)},self.p);store=self.base/'releases'
  with patch.object(U,'CRASH_AT','PREPARED'):
   with self.assertRaisesRegex(RuntimeError,'RELEASE_TEST_INTERRUPTION'):invoke(self.k,'releases.install',{'id':preview['id'],'expected_digest':preview['content_digest'],'directory':str(store)},self.p)
  entry=invoke(self.k,'releases.status',{},self.p)['installations'][0];target=store/entry['stage']/'MANIFEST.json';raw=target.read_bytes();target.write_bytes(raw+b' ')
  self.assertFalse(self.k.dispatch('releases.recover',{'id':entry['id'],'action':'FINISH'},self.p)['ok']);self.assertFalse((store/'current').exists())
  # Recovery publishes the stage but must not activate the changed manifest.
  target=store/entry['release']/'MANIFEST.json';target.write_bytes(raw)
  result=invoke(self.k,'releases.recover',{'id':entry['id'],'action':'FINISH'},self.p);self.assertEqual(result['state'],'ACTIVATED');self.assertFalse(result['started'])
  self.assertFalse(self.preview()['ok'])


class DeploymentProfile(unittest.TestCase):
 def test_configuration_is_inert_and_phone_progress_has_no_authority(self):
  from workbench.continuing_checks import fixture
  from workbench.engineering_kernel import Principal
  with tempfile.TemporaryDirectory() as tmp:
   base=Path(tmp);k,p,home,source,copy,order=fixture(base,'custom-owner')
   value=invoke(k,'deployment.prepare',{'mode':'APPLIANCE','directory':str(base/'configuration')},p)
   self.assertFalse(value['system_changes']);script=(base/'configuration/open-ledger.sh').read_text();self.assertIn('cage --',script)
   self.assertIn('PYTHONPATH=',(base/'configuration/ledger-host.service').read_text())
   remote=Principal('paired-view');self.assertFalse(k.dispatch('deployment.progress',{},remote)['ok'])
   invoke(k,'deployment.share_progress',{'enabled':True},p)
   with k.db() as db:db.execute('INSERT INTO sessions VALUES(?,?)',('test-only-session',json.dumps({'identity':remote.identity,'profile':'view','expires':time.time()+60})))
   result=invoke(k,'deployment.progress',{},remote);self.assertEqual(result['tasks'][0]['title'],'Clock continuation')
   self.assertEqual(set(result['tasks'][0]),{'id','title','state','reason','attempts','reserved_tokens'})
   self.assertFalse(k.dispatch('deployment.prepare',{'mode':'SINGLE','directory':str(base/'unauthorized')},remote)['ok'])
   invoke(k,'deployment.share_progress',{'enabled':False},p);self.assertFalse(k.dispatch('deployment.progress',{},remote)['ok'])


if __name__=='__main__':unittest.main()
