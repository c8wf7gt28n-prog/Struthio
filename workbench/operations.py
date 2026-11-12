"""Right-column read model over the existing Agenda, jobs and cabinet."""
from . import agenda,cabinet,host_observations
import sqlite3,time

FIELDS={'ledger.operations':({'context':cabinet.TEXT,'idle':{'type':'boolean'}},[])}
SCOPES={'ledger.operations':'read'}
# Machine words kept in schedule_checks.reasons (older readers and tests match them); the desktop shows SERVICES_HELD as the
# one service sentence from service_lifecycle.SUMMARIES that the snapshot carries beside it (V-05: one phrasing everywhere).
SERVICES_HELD='Ledger services off'
AI_HELD='New Slate activity off'
PUBLIC_REASONS={AI_HELD:'New Graphite AI activity off'}  # GRAPHITE-01: the public words for a machine word


def tool_words(tool,state=None):
    """A job in words: the capability family that owns the tool (explore.VIEWS, by operation prefix) and its state, lower case;
    the raw tool id stays for the tooltip. 'brain.infer' Interrupted -> 'Local model · interrupted'."""
    from .explore import VIEWS
    name=str(tool or 'Job');family=next((row[1] for row in VIEWS if any(name.startswith(prefix) for prefix in row[7])),None)
    words=family or name
    return words+(' · '+str(state).lower() if state else '')


def snapshot(kernel,principal,context=None,idle=False):
    from . import local_brain,ledger_control,continuing_work,work_trail
    from .service_lifecycle import snapshot as service_status,unavailable
    clock=time.time();view=agenda.view(kernel,principal,clock)
    brain=local_brain.status(kernel);enabled=ledger_control.value(kernel,'stacy.enabled')
    services=ledger_control.value(kernel,'operations.services_enabled');held=work_trail.execution_held(kernel)
    # An unreadable cycle row must not take the Agenda, slate and selection readback down with it.
    try:service_state=service_status(kernel)
    except (ValueError,OSError,sqlite3.Error,KeyError,TypeError) as exc:service_state=unavailable(exc)
    selection=None;notices=[]
    if context:
        try:
            node=cabinet.get(kernel,context,principal)['node']
            selection={key:node.get(key) for key in ('id','label','role','revision','provider','canonical_id','scope')}
        except (ValueError,OSError):notices.append('The selected cabinet record is unavailable; refresh the cabinet.')
    first=None
    agenda_running=any(row.get('kind')!='job' for row in view['now'])
    with agenda.opened(kernel) as db:
        for row in view['next']:
            if row.get('kind')=='job':continue
            current=agenda.owned(db,row['id'],principal.identity);reasons=[]
            if row['state']=='PAUSED':reasons.append('Paused by owner')
            if agenda_running:reasons.append('Another Agenda item is running')
            if current['after']:
                before=db.execute('SELECT title,state FROM agenda_items WHERE id=? AND owner=?',(current['after'],principal.identity)).fetchone()
                if before is None:reasons.append('Dependency unavailable')
                elif before['state']!='DONE':reasons.append('After '+before['title'][:100]+' · '+before['state'].lower())
            if current['due'] and current['due']>clock and not (current['reason'] or '').startswith('Missed '):reasons.append('Scheduled for a later time')
            if (current['idle'] or current['nice']=='background') and not idle:reasons.append('Waits for idle time')
            if held:reasons.append('New work held · use explicit Resume')
            if not services:reasons.append(SERVICES_HELD)
            linked=continuing_work.linked(db,row['id'])
            if not enabled and (linked or not (current['program'] or current['investigation']) or current['copy']):reasons.append(AI_HELD)
            eligible=row['state']=='NEXT' and agenda.ready(db,current,idle,clock) and not reasons
            row['schedule_checks']=dict(state='PASSED' if eligible else 'WAITING',reasons=reasons,services_summary=service_state['summary'],
                notice='Queue checks only; runtime, model, source and grant checks still apply at execution.')
            if eligible and first is None:first=row['id']
    # The panel needs identities and controls, not private programs or snapshots.
    safe=('kind','id','title','state','nice','position','reason','after','cpu_nice','can_adjust_nice','cpu_priority_note','cpu_priority_basis','schedule_checks','resource_request','resource_wait','created')
    queues={key:[{field:row[field] for field in safe if field in row} for row in view.get(key,[])] for key in ('now','next','waiting','later','suggested','done')}
    queues.update(counts=view['counts'],rules=view['rules'])
    return dict(schema='ledger.operations/1',sampled_at=clock,host=host_observations.snapshot(),agenda=queues,services=service_state,
        selection=selection,notices=notices,first_queue_checks_passed=first,idle=idle,
        slate=dict(local_state=brain['state'],new_ai_enabled=enabled,services_enabled=services,work_held=held,
                   model_id=(brain.get('selection') or {}).get('model_id'),basis='EXISTING_LOCAL_BRAIN_AND_ADMISSION_STORES'),
        notice='Observation and existing controls. Queue position, Agenda tier and OS CPU niceness are separate.',
        jobs_submitted=0,model_calls=0,native_invocations=0)


def dispatch(kernel,operation,args,principal):return snapshot(kernel,principal,**args)
