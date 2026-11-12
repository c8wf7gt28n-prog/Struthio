"""Operator-only workbook text proposals through the existing candidate journal.

This adapter never promotes worksheet outcomes, IDs, sources, check IDs or
physical gates. It does not widen the default AI delegation.
"""
import copy
from . import record_io as io

PATHS=('docs/ledger2/REQUIREMENTS.json','docs/ledger2/OPEN_ISSUES.json','project/register/bindings.json')
FIELDS={'register.propose':({'export_id':{'type':'string','minLength':32,'maxLength':32},
                           'path':{'type':'string','maxLength':300}},['export_id','path'])}
SCOPES={'register.propose':'approve'}


def altered(root,changes):
    sources={name:io.load(root,name) for name in PATHS};desired=copy.deepcopy(sources);touched=set()
    for change in changes:
        rid=change['record_id'];field=change['field'];before=change['before'];after=change['after']
        if not isinstance(after,str) or not after.strip() or len(after)>4000:raise ValueError('INVALID_TEXT_PROPOSAL')
        if any(ord(c)<32 and c not in '\n\t' for c in after):raise ValueError('CONTROL_CHARACTER_IN_TEXT')
        match=None
        for row in desired[PATHS[0]]['requirements']:
            if row['id']==rid:
                if field!='statement':raise ValueError('CHECK_CASE_IDENTIFIERS_ARE_PROTECTED')
                match=(PATHS[0],row,'requirement');break
        if match is None:
            for row in desired[PATHS[1]]['issues']:
                if row['id']==rid:
                    target={'statement':'issue','owner':'owner_or_gate'}.get(field)
                    if not target:raise ValueError('PROTECTED_ACTION_FIELD')
                    match=(PATHS[1],row,target);break
        if match is None:
            for row in desired[PATHS[2]]['requirements']:
                if row['record_id']==rid:
                    if field not in ('statement','acceptance_criterion'):raise ValueError('PROTECTED_REQUIREMENT_FIELD')
                    match=(PATHS[2],row,field);break
        if match is None:raise ValueError('PROPOSAL_RECORD_NOT_OWNED')
        name,row,target=match
        key=(name,rid,target)
        if key in touched:raise ValueError('DUPLICATE_FIELD_PROPOSAL')
        touched.add(key)
        if row[target]!=before:raise ValueError('TEXT_BASE_DRIFT')
        row[target]=after
    return {name:desired[name] for name in PATHS if desired[name]!=sources[name]}


def dispatch(kernel,operation,args,principal):
    from .register_exchange import preview
    result=preview(kernel,principal,args)
    if result['status']!='PREVIEW' or not result['changes']:raise ValueError('A_CURRENT_NONEMPTY_TEXT_PREVIEW_IS_REQUIRED')
    desired=altered(kernel.root,result['changes'])
    if not desired:raise ValueError('NO_TEXT_CHANGES')
    # Uses the operator's existing explicit paths; never constructs a wider Principal.
    base_hashes={n:io.sha(io.project_path(kernel.root,n)) for n in desired}
    metadata={'export_id':result['export_id'],'changes':result['changes'],
              'source_hashes':base_hashes,'authority':'OWNED_TEXT_ONLY'}
    candidate=kernel.create_candidate({'goal':'Review workbook text proposal '+result['export_id'][:12],
        'paths':sorted(desired),'required_tools':['register.validate_text']},principal,register_text=metadata)
    ident=candidate['id']
    for name,value in desired.items():
        payload=io.canonical(value).decode('utf-8')+'\n'
        kernel.patch({'id':ident,'path':name,'sha256':base_hashes[name],'content':payload},principal)
    return {'status':'CANDIDATE_CREATED','candidate_id':ident,'state':'Draft','changes':result['changes'],
            'accepted_source_writes':0,'approval_required':True,'required_tool':'register.validate_text',
            'next':'Inspect the diff, authorize execution for this exact candidate revision, run register.validate_text on baseline and candidate, then review and accept or reject.'}


def validate_candidate(kernel,candidate):
    meta=candidate['register_proposal']
    if set(candidate['changes'])!=set(meta['source_hashes']):raise ValueError('REGISTER_CANDIDATE_SCOPE_CHANGED')
    for name,sha in meta['source_hashes'].items():
        if name not in PATHS or io.sha(io.project_path(kernel.root,name))!=sha:raise ValueError('REGISTER_TEXT_SOURCE_DRIFT')
    desired=altered(kernel.root,meta['changes'])
    if set(desired)!=set(candidate['changes']):raise ValueError('REGISTER_CANDIDATE_PATH_MISMATCH')
    for name,value in desired.items():
        actual=io.load(kernel.candidate_root(candidate['id']),name)
        if actual!=value:raise ValueError('REGISTER_CANDIDATE_CHANGED_PROTECTED_FIELDS')


def validate_current(root):
    from .engineering_register import binding_paths
    binding_paths(root)
    campaign=io.load(root,PATHS[0]);issues=io.load(root,PATHS[1])
    for data,key,fields in [(campaign,'requirements',('id','requirement')),(issues,'issues',('id','issue','owner_or_gate'))]:
        ids=[]
        for row in data[key]:
            ids.append(row['id'])
            for field in fields:
                value=row[field]
                if not isinstance(value,str) or not value.strip() or len(value)>4000:raise ValueError('REGISTER_TEXT_SCHEMA')
        if len(ids)!=len(set(ids)):raise ValueError('DUPLICATE_REGISTER_ID')
    return {'schema':'arc.register-text-check/1','status':'PASS','evidence_class':'STATIC_CHECK',
        'requirements':len(campaign['requirements']),'actions':len(issues['issues']),
        'scope':'Text and record structure only; does not approve engineering values or physical gates.'}
