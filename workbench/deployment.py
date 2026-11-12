"""Reviewable single-computer, workstation and appliance launch configuration."""
import json
import os
from pathlib import Path
import shlex
import time
from . import project_desk as R,worker_boundary,work_trail,continuing_work,locations

FIELDS={'deployment.status':({},[]),
 'deployment.prepare':({'mode':{'type':'string','enum':['SINGLE','WORKSTATION','APPLIANCE']},'directory':{'type':'string','minLength':1,'maxLength':4096}},['mode','directory']),
 'deployment.share_progress':({'enabled':{'type':'boolean'}},['enabled']),
 'deployment.progress':({},[])}
SCOPES={op:'read' if op in ('deployment.status','deployment.progress') else 'approve' for op in FIELDS}


def config(k):
 with k.db() as db:row=db.execute("SELECT value FROM settings WHERE key='deployment.profile'").fetchone()
 return json.loads(row[0]) if row else {'mode':'SINGLE','progress_shared':False,'configured':False}


def set_config(k,value):
 with k.db() as db:db.execute("INSERT OR REPLACE INTO settings VALUES('deployment.profile',?)",(R.canonical(value),))


def prepare(k,a,p):
 from . import session,host_cli,workspace_backup
 folder=workspace_backup.fresh(a['directory']);folder.mkdir(parents=True,mode=0o700)
 program=locations.program(k.root);python=program/'.venv/bin/python'
 if not python.is_file():
  import sys
  python=Path(sys.executable)
 unit=host_cli.user_unit(k.root,python,session.config_dir())
 (folder/'ledger-host.service').write_text(unit)
 # Wayland/Cage is a launch choice, not an asserted display qualification.
 command=[str(python),'-m','workbench.launch']
 if a['mode']=='APPLIANCE':command=['cage','--',*command]
 script='#!/bin/sh\nset -eu\nexport ARC_LEDGER_WORKSPACE='+shlex.quote(str(k.root))+'\nexport ARC1_WORKBENCH_CONFIG_HOME='+shlex.quote(str(session.config_dir()))+'\nexport PYTHONPATH='+shlex.quote(str(program))+'\ncd '+shlex.quote(str(program))+'\nexec '+shlex.join(command)+'\n'
 path=folder/'open-ledger.sh';path.write_text(script);path.chmod(0o700)
 guide='These files are a reviewable configuration. No service was enabled and no OS account/display/network was changed.\n\n'
 guide+='Use your ordinary dedicated appliance account. Install the runtime and optional --workers prerequisites first.\n'
 guide+='For an appliance, install Cage/Wayland prerequisites on the actual host and qualify menus, dialogs and native windows. Fluxbox remains the ordinary workstation route.\n'
 guide+='Copy ledger-host.service into your user service directory, review its paths, then explicitly enable it with systemctl --user. Boot without login/linger is a separate administrator decision.\n'
 guide+='Start open-ledger.sh when you want the desktop. A model and network listener are never started by this configuration.\n'
 guide+='Pill TLS listeners are separate, explicit workstation commands. The appliance can fetch requests and send results without listening.\n'
 (folder/'READ_ME_FIRST.txt').write_text(guide)
 value={**config(k),'mode':a['mode'],'configured':True,'files':str(folder),'created':time.time(),'activated':False,'owner':p.identity}
 set_config(k,value)
 return {**value,'system_changes':False,'worker_qualification_required':True,'display_qualification':'PENDING_ON_REAL_HARDWARE'}


def progress(k,p):
 from .engineering_kernel import operator
 settings=config(k);owner=settings.get('progress_owner')
 if owner is None:
  if 'approve' not in p.scopes:raise ValueError('The owner has not shared continuing-work progress')
  owner=p.identity
 if p.identity!=owner:
  if not settings['progress_shared']:raise ValueError('The owner has not shared continuing-work progress')
  with k.db() as db:sessions=[json.loads(r[0]) for r in db.execute('SELECT payload FROM sessions')]
  if not any(s.get('identity')==p.identity and s.get('profile')=='view' and s.get('expires',0)>time.time() for s in sessions):raise ValueError('Read-only paired phone session required')
 rows=continuing_work.dispatch(k,'work.list',{},operator(owner))['records']
 return {'schema':'arc.shared-progress/1','work_held':work_trail.execution_held(k),'tasks':[{
   'id':r['id'],'title':r['title'],'state':r['state'],'reason':r.get('reason'),'attempts':r['used']['steps'],
   'reserved_tokens':r['used']['tokens']} for r in rows[:30]],
   'authority':'READ_ONLY_SUMMARIES_NO_INPUTS_OUTPUTS_GRANTS_OR_APPROVALS'}


def dispatch(k,op,a,p):
 if op=='deployment.status':return {'profile':config(k),'workers':worker_boundary.status(k),'work':work_trail.work_status(k),
   'physical_qualification':'PENDING','network_listener_default':'OFF','legacy_routes_retained':True}
 if op=='deployment.prepare':return prepare(k,a,p)
 if op=='deployment.share_progress':
  value={**config(k),'progress_shared':a['enabled'],'progress_owner':p.identity};set_config(k,value);return {'shared':a['enabled'],'scope':'PAIRED_VIEW_SESSION_SUMMARIES_ONLY'}
 if op=='deployment.progress':return progress(k,p)
 raise ValueError('Unknown deployment operation')
