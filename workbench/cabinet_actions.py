"""Bounded selection actions shared by Slate and Qt. This module executes nothing.

Ranking is a declared record-kind rule, not a model fit or an execution grant.
Availability covers this presentation step; provider/runtime checks still apply.
"""
from __future__ import annotations
import sqlite3
from . import cabinet, explore, capability_catalog

FIELDS={'ledger.cabinet.actions':({'id':cabinet.TEXT},['id'])}
SCOPES={op:'read' for op in FIELDS}


def permitted(principal,scope):
    return scope in principal.scopes and not (principal.mode=='Tutor' and scope!='read')


def snapshot(kernel,ident,principal):
    from .engineering_kernel import CAPABILITIES
    from .engineering_cli import schemas
    from . import agent_operations
    try:value=cabinet.get(kernel,ident,principal)
    except (ValueError,OSError,sqlite3.Error):
        return dict(schema='ledger.cabinet-actions/1',context=None,actions=[],signature=None,
                    notice='Selected record unavailable. Refresh the cabinet before choosing an action.')
    node=value['node'];record=value['record'] or {};actions=[];definitions=schemas()
    context={key:node.get(key) for key in ('id','canonical_id','label','role','provider','revision','canonical_home')}
    context['reference_revision']=record.get('project_revision')
    # Some providers version their note separately from their tree object.
    # Digest only the saved record already read, never a source/master file.
    context['saved_record_digest']=cabinet.digest(record)

    def add(key,label,kind,reason,**extra):
        row=dict(id=key,label=label,kind=kind,reason=reason,state='READY',enabled=True,
                 unavailable_reason=None,basis='SELECTED_RECORD_KIND',checks_remaining=[],**extra)
        actions.append(row);return row

    def block(row,reason):row.update(state='UNAVAILABLE',enabled=False,unavailable_reason=reason)

    def command(key,label,op,args,reason):
        row=add(key,label,'READ',reason,operation=op,arguments=args,required_scope=CAPABILITIES.get(op))
        if CAPABILITIES.get(op)!='read':block(row,'This action has no current read-only command.')
        elif not permitted(principal,'read'):block(row,'Read scope is required.')
        else:
            try:agent_operations.validate(args,definitions[op])
            except (ValueError,KeyError,TypeError):block(row,'The saved inputs do not match the current command contract.')
        row['checks_remaining']=['The command rechecks current record access and its own provider requirements.']
        return row

    command('record','Read saved details','ledger.cabinet.get',{'id':ident},
            'Inspect this placement and its current saved record.')
    # Same forms and scopes as CabinetRecordTab. Preparing focuses the existing
    # draft; only its separate Keep/Create button can submit new writing.
    form=('project' if ident in ('cabinet:projects','catalog:projects') else
          'idea' if node['role']=='project' or ident in ('cabinet:unassigned','cabinet:concern') else None)
    if form:
        op='projects.create' if form=='project' else 'ideas.capture'
        row=add('write','Name a new project' if form=='project' else 'Write an idea here','PREPARE',
                'Focus the existing writing space. Keep or Create submits it separately.',
                form=form,operation=op,required_scope=CAPABILITIES.get(op),state_note='Writing is still needed.')
        row['state']='NEEDS_INPUT';row['required_arguments']=definitions.get(op,{}).get('required',[])
        if op not in CAPABILITIES:block(row,'The writing command is unavailable.')
        elif not permitted(principal,CAPABILITIES[op]):block(row,'Writing requires the '+CAPABILITIES[op]+' scope in an allowed mode.')
        row['checks_remaining']=['Writing and all creation checks are required when Keep or Create is chosen.']
    for index,spec in enumerate(value['actions']):
        command('check:'+str(index),spec['label'],spec['operation'],spec['arguments'],
                'Explicitly read through this record’s existing provider; current access and binding checks still apply.')

    views={row[0]:row for row in explore.VIEWS}
    for suggestion in explore.suggestions(context):
        key=suggestion['id'];view=views.get(key)
        row=add('workspace:'+key,'Open '+(view[1] if view else key),'WORKSPACE',suggestion['reason'],
                instrument='instrument:'+key,required_scope='read')
        if view is None:block(row,'This workspace has no current presentation route.');continue
        source=capability_catalog.source(kernel.root,'workbench/'+view[5])
        if source['state']!='PRESENT':block(row,'The workspace source is missing or unsafe.')
        elif not any(op.startswith(view[7]) for op in CAPABILITIES):block(row,'The workspace has no registered commands.')
        elif not permitted(principal,'read'):block(row,'Read scope is required to inspect this workspace.')
        row['checks_remaining']=['Opening the workspace does not bind or copy the selected record.',
                                 'Its own inputs, permissions and runtime checks apply when work is submitted.']
    add('explore','Explore all capabilities','EXPLORE','Browse the existing workshop with this selection.',required_scope='read')
    for rank,row in enumerate(actions):row['rank']=rank
    result=dict(schema='ledger.cabinet-actions/1',context=context,actions=actions,
                notice='Ordered by saved record kind: inspect, prepare writing, provider checks, then related workspaces. Availability is for this step only; it grants no execution authority.')
    result['signature']=cabinet.digest(result)
    return result


def dispatch(kernel,operation,args,principal):return snapshot(kernel,args['id'],principal)
