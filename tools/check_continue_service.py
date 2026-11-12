"""A real run of the resident Ledger service carrying an assignment while no desktop is open (HATCH AGENT-02 WI-A). No Qt.

The mechanical steps: a disposable profile and workspace; the Ledger service is started exactly as the desktop starts it
(workbench.host_client.ensure: python -m workbench.host_service --root <workspace>, detached in its own session); through
the client (the same authenticated socket the desktop uses) a page with three quantities is created and "add up the numbers
on this page" is assigned and released (agent.release), with no desktop stepping it; the service's own 5 s tick
(Coordinator.tick_agenda -> agent_loop.pump) steps it until it is DONE (at most 40 s): the total paragraph is on the page,
service_steps counts every step and the investigation sheet's steps carry driver service. A second, longer assignment is
released and, once the service has stepped it, the service is shut down (rpc shutdown): its own Master Stop on the way out
pauses the assignment with "The Ledger service stopped", and the process is confirmed ended (exit code 0).

The only process this check starts is the service itself; the service starts no job, worker or model here (the jobs table
is counted afterwards). Nothing here is owner-host, live-model or physical acceptance. The report goes to
build/ui_checks/continue_service/continue-service.json (ARC_LEDGER_CONTINUE_CAPTURE_DIR redirects it). Run it by hand:
it starts a real process, so it is not part of the release check's UI gate.
"""
import json,os,shutil,signal,sys,tempfile,time
from pathlib import Path
PROGRAM=Path(__file__).resolve().parents[1]
OUT=Path(os.environ.get('ARC_LEDGER_CONTINUE_CAPTURE_DIR',str(PROGRAM/'build/ui_checks/continue_service')));OUT.mkdir(parents=True,exist_ok=True)
RUN=Path(tempfile.mkdtemp(prefix='ledger-agent02-continue-service-'))
os.environ.update(ARC1_WORKBENCH_CONFIG_HOME=str(RUN/'profile'),ARC_LEDGER_CONCERN=str(RUN/'Concern'),PYTHONDONTWRITEBYTECODE='1')  # the service inherits it: no caches in the program tree
for name in ('ARC_LEDGER_EMBEDDED','ARC_LEDGER_XSESSION','ARC_LEDGER_WORKSPACE','INVOCATION_ID','ARC_LEDGER_SUPERVISION'):os.environ.pop(name,None)
sys.path.insert(0,str(PROGRAM));sys.dont_write_bytecode=True
from workbench import host_client,locations,agent_loop
from workbench.engineering_kernel import Kernel,operator
from workbench.operation_stop import process_identity

WAIT_SECONDS=40
REQUEST='add up the numbers on this page'
DOC_TEXT='Pellets 12.5 kg, grit 3 kg and oyster shell 0.5 kg this week.'
checks=[];owner=operator()
def check(text):checks.append(text);print(text,flush=True)
root=locations.office(RUN/'workspace')
client=None;process=None;report={}
def call(op,args=None):
 value=client.dispatch(op,args or {},owner);assert value['ok'],value;return value['result']
def status(ident):return call('agent.status',{'id':ident})['assignments'][0]
def alive(pid,start):return start is not None and process_identity(pid)==start
try:
 # 01 · start the service as the desktop does; one new process, ready
 began=time.monotonic();client=host_client.ensure(root)
 info=client.rpc('status');pid=info['pid'];start=info['process_start']
 owned=[p for p in host_client._OWNED.values() if p.pid==pid];assert len(owned)==1 and owned[0].poll() is None,host_client._OWNED
 process=owned[0];assert os.getsid(pid)==pid and os.getsid(pid)!=os.getsid(0)   # its own session, as host_client.ensure starts it
 assert info['qt_loaded'] is False and info['work']['held'] is False and info['jobs_total']==0,info
 check('01 host_client.ensure started the Ledger service (pid %d, its own session, transport %s, %s) in %.1f s; no Qt loaded, work not held, no jobs'%(pid,info['transport'],info['supervision'],time.monotonic()-began))
 # 02 · through the client: the page, the assignment, the release (no desktop steps it)
 setting=next(r for r in call('ledger.settings')['settings'] if r['key']==agent_loop.SETTING);assert setting['stored'] is True,setting
 doc=call('documents.create',{'title':'Feed this week','text':DOC_TEXT})['id']
 first=call('agent.assign',{'request':REQUEST,'context':{'document':doc}})['assignment'];ident=first['id']
 assert (first['profile'],first['state'],first['driver'])==('numbers_on_page','READY',None),first
 released=call('agent.release',{'id':ident});row=released['assignment']
 assert (row['state'],row['driver'],row['lease_live'],row['steps_used'])==('RUNNING',None,False,0) and 'Graphite service continues' in released['next'],released
 check('02 Through the client: setting %s is on; page %s created; “%s” assigned (numbers_on_page, READY) and released: RUNNING, no driver, no lease — “%s”'%(agent_loop.SETTING,doc[:8],REQUEST,released['next']))
 # 03 · the service's own tick steps it to DONE
 released_at=time.monotonic();seen=[]
 while time.monotonic()-released_at<WAIT_SECONDS:
  row=status(ident)
  if not seen or seen[-1]!=(row['steps_used'],row['state']):seen.append((row['steps_used'],row['state']))
  if row['state']!='RUNNING':break
  time.sleep(.5)
 elapsed=time.monotonic()-released_at
 assert row['state']=='DONE',(row,seen,elapsed)
 assert (row['driver'],row['service_steps'],row['steps_used'],row['model_used'])==('service',5,5,False),row
 page=call('documents.get',{'id':doc})['document'];total=page['blocks'][-1]['text']
 assert total.startswith('Total of the 3 quantities on this page: 16 kg'),page['blocks']
 sheet=call('investigation.sheet',{'id':row['investigation']})
 drivers=[json.loads(s['inputs']).get('driver') for s in sheet['attempted']];assert drivers==['service']*5,drivers
 assert {s['authority'] for s in sheet['attempted']}=={'execute,read'},sheet['attempted']
 check('03 The service’s own 5 s tick stepped it to DONE in %.1f s with no desktop (steps seen %s): service_steps 5 of 5; the page reads “%s…” (revision %d); every attempted step on the sheet carries driver service, authority read+execute'%(elapsed,' → '.join('%d %s'%s for s in seen),total[:46],page['revision']))
 # 04 · a longer assignment, released; the service shuts down while it runs: its Master Stop pauses it on the way out
 steps=[{'operation':'documents.get','arguments':{'id':doc},'purpose':'Read the page again (%d)'%n} for n in range(1,31)]
 second=call('agent.assign',{'request':'read the page thirty times','profile':'operation_sequence','context':{'steps':steps}})['assignment']['id']
 call('agent.release',{'id':second});waited=time.monotonic()
 while time.monotonic()-waited<20 and status(second)['service_steps']<1:time.sleep(.5)
 before=status(second);assert before['state']=='RUNNING' and before['service_steps']>=1,before
 stopping=client.rpc('shutdown');assert stopping=={'state':'STOPPING','jobs_stopped':False},stopping
 code=process.wait(timeout=30);ended=not alive(pid,start)
 assert code==0 and ended,(code,ended)
 try:client.rpc('status',timeout=1);answered=True
 except host_client.HostUnavailable:answered=False
 assert not answered
 check('04 A second assignment (30 reads) was released and stepped by the service (%d step%s); rpc shutdown answered %s; the process ended with exit code %d and no longer answers'%(before['service_steps'],'' if before['service_steps']==1 else 's',stopping['state'],code))
 # 05 · read the record the service left (the service is gone, so an in-process Kernel opens the same file)
 k=Kernel(root)
 after=agent_loop.status(k,second,owner)[0];done=agent_loop.status(k,ident,owner)[0]
 assert (after['state'],after['paused_reason'])==('PAUSED','The Graphite service stopped') and after['steps_used']==after['service_steps']>=1,after
 assert done['state']=='DONE'
 with k.db() as db:jobs_total=db.execute('SELECT count(*) FROM jobs').fetchone()[0]
 assert jobs_total==0
 check('05 After the shutdown the record says: the long assignment PAUSED “The Graphite service stopped” after %d service step%s (Today offers resume); the first stays DONE; the jobs table is empty'%(after['service_steps'],'' if after['service_steps']==1 else 's'))
 report=dict(schema='ledger.agent02-continue-service/1',release='Graphite 0.1',state='PASSED',mode='REAL_RESIDENT_PROCESS',checks=checks,
  service={'pid':pid,'transport':info['transport'],'supervision':info['supervision'],'own_session':True,'exit_code':code,'started_by':'workbench.host_client.ensure'},
  setting={'key':agent_loop.SETTING,'stored':True},lease_seconds=agent_loop.LEASE_SECONDS,wait_bound_seconds=WAIT_SECONDS,
  first={'id':ident,'state':done['state'],'steps_used':done['steps_used'],'service_steps':done['service_steps'],'seconds_to_done':round(elapsed,1),'steps_seen':seen,'total_paragraph':total,'sheet_drivers':drivers},
  second={'id':second,'state':after['state'],'paused_reason':after['paused_reason'],'service_steps':after['service_steps']},
  processes_started=1,real_job_submissions=jobs_total,worker_processes_started=0,model_generations=0,provider_requests=0,native_invocations=0,
  acceptance_claimed=False,note='The resident service carried the assignment with no desktop open, in a disposable profile; owner-host supervision (systemd user unit) and the live model remain open.')
finally:
 if process is not None and process.poll() is None:
  try:client.rpc('shutdown',timeout=2)
  except Exception:pass
  try:process.wait(timeout=20)
  except Exception:
   os.killpg(process.pid,signal.SIGTERM);process.wait(timeout=10)
 shutil.rmtree(RUN,ignore_errors=True)
if not report:raise SystemExit('check_continue_service did not finish')
(OUT/'continue-service.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
print(json.dumps(dict(state=report['state'],checks=len(checks),seconds_to_done=report['first']['seconds_to_done'])))
