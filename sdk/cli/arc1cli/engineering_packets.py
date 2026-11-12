"""Portable EKP v2 contracts; legacy EKP v1 and staC 0.2 remain unchanged.

Canonical bytes use record_store.canonical (the existing ARC JSON profile,
not RFC 8785). Invocation identity is deliberately outside the context digest.
"""
from __future__ import annotations
import hashlib,re,shlex
from pathlib import Path
from . import evidence_contracts as evidence,record_store as records

VERSION='arc.reference-ekp/2'
MAX_BYTES=131072
MAX_PAGES=4

def digest(value):return hashlib.sha256(records.canonical(value)).hexdigest()
def fingerprint():return hashlib.sha256(Path(__file__).read_bytes()+Path(evidence.__file__).read_bytes()).hexdigest()
def ordered(values):return sorted(values,key=records.canonical)
def passage(name,source_sha256,locator,text,authority):
    if not re.fullmatch('[0-9a-f]{64}',source_sha256) or not isinstance(text,str) or len(text)>16000:raise ValueError('EKP_PASSAGE_BOUND')
    body={'name':name,'source_sha256':source_sha256,'locator':locator,'text':text,'authority':authority}
    return {'id':digest(body),**body,'content_trust':'REFERENCE_DATA_NOT_INSTRUCTIONS'}
def disputes(facts):
    """Compare exact reviewed quantities only within the identical source context."""
    groups={}
    for fact in facts:
        q=fact['quantity'];canonical=evidence.quantity(q['value'],q['unit'])
        if q!=canonical:raise ValueError('EKP_FACT_QUANTITY_DERIVATIVE_CHANGED')
        if fact.get('applicability')!='CURRENT_REFERENCE' or fact['role']=='HYPOTHESIS':continue
        groups.setdefault(evidence.context_key(fact),[]).append(fact)
    out=[]
    for key,items in sorted(groups.items()):
        values={(f['quantity']['dimension'],f['quantity']['numerator'],f['quantity']['denominator']) for f in items}
        polarity={f['polarity'] for f in items}
        if len(values)>1 or polarity=={'SUPPORT','REFUTE'}:
            out.append({'context_key':key,'facts':sorted(f['id'] for f in items),'state':'CONFLICT_REQUIRES_REVIEW','value_disagreement':len(values)>1,'support_disagreement':len(polarity)>1})
    return out
def context(*,question,scope,passages,facts,relationships,requirements,evidence_refs,gaps,budget):
    passages=ordered(passages);ids={x['id'] for x in passages}
    if len(passages)!=len(ids) or len(passages)>32:raise ValueError('EKP_PASSAGE_COUNT')
    if any(f['passage'] not in ids for f in facts):raise ValueError('EKP_FACT_WITHOUT_SOURCE_LOCATION')
    claims=[f for f in facts if f['role']!='HYPOTHESIS'];hypotheses=[f for f in facts if f['role']=='HYPOTHESIS']
    value={'schema':VERSION,'question':question,'scope':scope,'passages':passages,'facts':ordered(claims),'hypotheses':ordered(hypotheses),
      'relationships':relationships,'requirements':ordered(requirements),'evidence_refs':ordered(evidence_refs),'contradictions':disputes(claims),
      'gaps':sorted({v if isinstance(v,str) else records.canonical(v).decode() for v in gaps}),'budget':budget,'effects':['read'],'source_trust':'REFERENCE_DATA_NOT_INSTRUCTIONS','cloud_disclosure':'NOT_GRANTED',
      'identity_verification':'SOURCE_BYTES_AND_REGISTERED_ARTIFACTS','applicability_review':'NOT_GRANTED','engineering_compliance':'NOT_ESTABLISHED','physical_qualification':False}
    if len(records.canonical(value))>budget['max_bytes']:raise ValueError('EKP_CONTEXT_BYTE_BUDGET')
    return value
def envelope(context,ident,job,created,dependencies,reader,max_bytes):
    key=digest(context)
    value={'schema':VERSION,'id':ident,'invocation_id':ident,'job':job,'created':created,'state':'CURRENT','program_id':key,'context_digest':key,
      'context':context,'passages':context['passages'],'facts':context['facts'],'dependencies':dependencies,'reader':reader,'inference_authority':'NONE'}
    # Alias fields retain old answer-adapter compatibility; the limit covers the full export.
    if len(records.canonical(value))>max_bytes:raise ValueError('EKP_EXPORT_BYTE_BUDGET')
    return value
def compile_read(program):
    if not isinstance(program,str) or not 1<=len(program.encode())<=4096 or any(x in program for x in ('\n','\r','\x00')):raise ValueError('EKP_READ_PROGRAM_BOUND')
    lexer=shlex.shlex(program,posix=True,punctuation_chars='|');lexer.whitespace_split=True;lexer.commenters='';tokens=list(lexer)
    if len(tokens)!=4 or tokens[0]!='packet' or not re.fullmatch('[0-9a-f]{32}',tokens[1]) or tokens[2]!='|' or tokens[3] not in ('inspect','sources','gaps','why'):raise ValueError('EKP_READ_SYNTAX')
    body={'schema':'arc.stac.packet-ir/1','operation':'references.packet','arguments':{'id':tokens[1]},'presentation':tokens[3],'effects':['read'],'result_type':'EngineeringKnowledgePacket'}
    return {**body,'program_id':digest(body),'authority':'EXISTING_CALLER_PRINCIPAL_REQUIRED'}
