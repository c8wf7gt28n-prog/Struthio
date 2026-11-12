"""Gemini function-call transport using the existing local credential adapter."""
from __future__ import annotations
import json
from sdk.cli.arc1cli.workshop_contract import ACTION_FIELDS,MAX_CONTEXT
from . import clip

SYSTEM='''You are Graphite, inside the Graphite workspace. Investigate the approved engineering goal using only the declared tools. Read relevant source and actual diagnostics before proposing a justified change. Existing tests and hardware facts remain authoritative. A successful host test is not physical hardware proof. You may revise isolated scoped implementation files, never tests, permission code or accepted source. Explain changes and stop if the evidence is insufficient. Finish only with passing required checks; independent source acceptance remains outside your authority. Do not include private reasoning. Provide observable findings and actions.'''

def available():
    s=clip.Settings.load()
    return {'configured':bool(s.ready() and s.model),'model':s.model or None,
            'provider':'gemini','pricing':'owner-selected unpaid configuration; availability does not prove billing status',
            'automatic_paid_fallback':False}

def turn(context,history,timeout=60):
    s=clip.Settings.load()
    if not s.ready() or not s.model:raise clip.ClipError('Configure a Gemini key and explicit model in Graphite settings on this computer.','key')
    functions=[{'name':name,'description':'Graphite bounded action '+name,
                'parameters':{'type':'object','properties':props,'required':required}}
               for name,(props,required) in ACTION_FIELDS.items()]
    contents=[{'role':'user','parts':[{'text':json.dumps(context,separators=(',',':'))}]}]+history
    if len(json.dumps(contents).encode())>MAX_CONTEXT:raise ValueError('Provider context budget reached; prepare a new bounded task')
    payload={'systemInstruction':{'parts':[{'text':SYSTEM}]},'contents':contents,
             'tools':[{'functionDeclarations':functions}],
             'toolConfig':{'functionCallingConfig':{'mode':'AUTO'}},
             'generationConfig':{'maxOutputTokens':6000,'temperature':0.2}}
    data=clip._request('%s/models/%s:generateContent'%(clip.API,s.model),s.api_key(),payload,timeout=timeout)
    if len(json.dumps(data).encode())>200000:raise ValueError('Gemini output budget exceeded')
    candidates=data.get('candidates') or []
    if not candidates:raise clip.ClipError('Gemini returned no candidate; inspect the provider settings.','blocked')
    candidate=candidates[0]
    if candidate.get('finishReason')=='MAX_TOKENS':raise ValueError('Gemini response was truncated; no partial action executed')
    # Keep opaque tool-call signatures as required by the provider. Do not save
    # private thought text. No key or authorization header enters task state.
    parts=[p for p in candidate.get('content',{}).get('parts',[]) if not p.get('thought')]
    calls=[p['functionCall'] for p in parts if 'functionCall' in p]
    text='\n'.join(p.get('text','') for p in parts if 'text' in p)[:4000]
    if len(calls)>4:raise ValueError('At most four actions per provider turn')
    for c in calls:
        if c.get('name') not in ACTION_FIELDS or not isinstance(c.get('args',{}),dict):raise ValueError('Gemini requested an unsupported tool')
    return {'model':s.model,'parts':parts,'calls':calls,'text':text,'usage':data.get('usageMetadata',{})}
