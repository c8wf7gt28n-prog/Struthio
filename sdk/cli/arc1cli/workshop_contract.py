"""Provider-neutral bounded actions for a source-bound engineering task."""
from __future__ import annotations
import hashlib
import json

CONTRACT = 'arc-ledger.workshop-action/1'
MAX_ACTION = 120000
MAX_CONTEXT = 60000
ACTION_FIELDS = {
    'read_source': ({'path': {'type': 'string'}, 'line': {'type': 'integer'}, 'count': {'type': 'integer'}}, ['path']),
    'search_source': ({'query': {'type': 'string'}}, ['query']),
    'inspect_component': ({}, []),
    'read_diagnostics': ({}, []),
    'run_checks': ({}, []),
    'propose': ({'explanation': {'type': 'string'}, 'patches': {'type': 'array', 'items': {'type': 'object', 'properties': {
        'path': {'type': 'string'}, 'sha256': {'type': 'string'}, 'content': {'type': 'string'}}, 'required': ['path','sha256','content']}}}, ['explanation','patches']),
    'finish': ({'summary': {'type': 'string'}}, ['summary']),
    'stop': ({'reason': {'type': 'string'}}, ['reason']),
}

def binding(task, revision, scope):
    raw=json.dumps([CONTRACT,task,revision,sorted(scope)],separators=(',',':')).encode()
    return hashlib.sha256(raw).hexdigest()

def validate_action(action, *, expected_binding, files):
    if not isinstance(action,dict) or set(action)!={'binding','name','arguments'}:
        raise ValueError('Action requires binding, name and arguments')
    if len(json.dumps(action).encode())>MAX_ACTION:
        raise ValueError('Action exceeds output budget')
    if action['binding']!=expected_binding:raise ValueError('Stale or mismatched action binding')
    name=action['name'];args=action['arguments']
    if name not in ACTION_FIELDS or not isinstance(args,dict):raise ValueError('Unknown action')
    props,required=ACTION_FIELDS[name]
    if set(args)-set(props) or set(required)-set(args):raise ValueError('Unknown or missing action arguments')
    for key,value in args.items():
        kind=props[key]['type']
        if (kind=='string' and not isinstance(value,str)) or (kind=='integer' and type(value)!=int):
            raise ValueError('Wrong argument type: '+key)
    if name=='propose':
        if not args['explanation'].strip() or len(args['explanation'])>4000:raise ValueError('Explain the observed defect and change')
        patches=args['patches']
        if not isinstance(patches,list) or not 1<=len(patches)<=len(files):raise ValueError('One to five scoped patches required')
        seen=set()
        for patch in patches:
            if not isinstance(patch,dict) or set(patch)!={'path','sha256','content'}:raise ValueError('Invalid patch')
            path=patch['path']
            if not isinstance(path,str) or path not in files or path in seen:raise ValueError('Patch is outside task scope or duplicated')
            if patch['sha256']!=files[path]:raise ValueError('Patch source is stale')
            if not isinstance(patch['content'],str) or '\0' in patch['content'] or len(patch['content'].encode())>60000:
                raise ValueError('Invalid bounded UTF-8 source')
            if hashlib.sha256(patch['content'].encode()).hexdigest()==files[path]:raise ValueError('No source change proposed')
            seen.add(path)
    if name=='read_source' and (not 1<=args.get('line',1)<=1000000 or not 1<=args.get('count',100)<=160):
        raise ValueError('Read at most 160 source lines')
    if name=='search_source' and not 1<=len(args['query'])<=160:raise ValueError('Search query must be bounded')
    if name in ('finish','stop') and not 1<=len(next(iter(args.values())))<=4000:raise ValueError('A bounded explanation is required')
    return name,args
