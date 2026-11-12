"""Bounded preference accounting and checkpoint contracts; no model or authority."""
from __future__ import annotations
import hashlib,math,re
from .record_store import canonical

CONTEXTS=('creative_exploration','engineering_execution','review','delivery','general')
WEIGHTS={'owner_correction':4.0,'owner_statement':2.0,'owner_confirmed_choice':0.5}
VERSION='arc.stacy-memory/1'
def digest(value):return hashlib.sha256(canonical(value)).hexdigest()
def ident(value,size=32):
    if not isinstance(value,str) or not re.fullmatch('[0-9a-f]{'+str(size)+'}',value):raise ValueError('MEMORY_INVALID_ID')
    return value
def text(value,limit,empty=True):
    if not isinstance(value,str) or len(value)>limit or '\x00' in value or not empty and not value.strip():raise ValueError('MEMORY_TEXT_BOUND')
    return value
def strings(value,count=30,width=500):
    if not isinstance(value,list) or len(value)>count:raise ValueError('MEMORY_LIST_BOUND')
    return [text(v,width) for v in value]
def active(events):
    visible=[e for e in events if not e.get('forgotten') and not e.get('undone')]
    superseded={i for e in visible for i in e.get('supersedes',[])}
    return [e for e in visible if e['id'] not in superseded]
def parameters(value):
    if not isinstance(value,dict) or set(value)!={'weights','soft_half_life_days'}:raise ValueError('MEMORY_PARAMETER_FIELDS')
    weights=value['weights'];days=value['soft_half_life_days']
    if not isinstance(weights,dict) or set(weights)!=set(WEIGHTS):raise ValueError('MEMORY_WEIGHT_FIELDS')
    if any(type(v) not in (int,float) or not math.isfinite(v) or not 0<v<=10 for v in weights.values()):raise ValueError('MEMORY_WEIGHT_BOUND')
    if type(days) not in (int,float) or not math.isfinite(days) or not 1<=days<=730:raise ValueError('MEMORY_HALF_LIFE_BOUND')
    return value
def posterior(events,context,now,params=None):
    if context not in CONTEXTS:raise ValueError('MEMORY_CONTEXT')
    params=parameters(params or {'weights':WEIGHTS,'soft_half_life_days':90});groups={}
    for e in sorted(active(events),key=lambda event:event['sequence']):
        if e['context'] not in ('general',context):continue
        row=groups.setdefault(e['preference'],{'a':1.0,'b':1.0,'events':[],'instruction':'','last_sequence':-1})
        decay=2**(-max(0,now-e['created'])/(86400*params['soft_half_life_days'])) if e['soft'] else 1.0
        weight=params['weights'][e['kind']]*decay;row['a']+=weight*e['feedback'];row['b']+=weight*(1-e['feedback']);row['events'].append(e['id'])
        if e['sequence']>row['last_sequence']:row['instruction']=e['instruction'];row['last_sequence']=e['sequence']
    result=[]
    for preference,row in groups.items():
        a,b=row['a'],row['b'];result.append({'preference':preference,**row,'mean':a/(a+b),'variance':a*b/((a+b)**2*(a+b+1)),
          'meaning':'COLLABORATION_PREFERENCE_NOT_PERSONALITY_MEASUREMENT_OR_OPERATION_SAFETY'})
    return sorted(result,key=lambda v:(-v['last_sequence'],v['preference']))
def note(value):
    allowed={'goal','constraints','findings','contradictions','next_step','summary'}
    if not isinstance(value,dict) or set(value)!=allowed:raise ValueError('CHECKPOINT_NOTE_FIELDS')
    return {'goal':text(value['goal'],1000,False),'constraints':strings(value['constraints'],20,300),
      'findings':strings(value['findings'],20,500),'contradictions':strings(value['contradictions'],20,500),
      'next_step':text(value['next_step'],1000,False),'summary':text(value['summary'],3000)}
def seed(raw):
    from .record_store import strict
    if len(raw)>65536:raise ValueError('PERSONALITY_SEED_BYTE_BOUND')
    value=strict(raw)
    if not isinstance(value,dict) or value.get('schema')!='arc.stacy.owner_personality_seed/1':raise ValueError('PERSONALITY_SEED_SCHEMA')
    expression=value.get('stacy_expression',{})
    if not isinstance(expression,dict):raise ValueError('PERSONALITY_EXPRESSION')
    character=text(expression.get('default_character',''),600,False)
    inherit=strings(expression.get('inherit_from_ryan',[]),10,150);retain=strings(expression.get('retain_independently',[]),10,150)
    return {'name':text(value.get('name','Owner selected seed'),120),'version':text(value.get('version',''),40),
      'character':character,'inherit':inherit,'retain':retain,'status':'OWNER_SELECTED_STARTING_REFERENCE_INTERPRETATIONS_EDITABLE',
      'model_training':'NONE','authority':'PRESENTATION_ONLY'}
