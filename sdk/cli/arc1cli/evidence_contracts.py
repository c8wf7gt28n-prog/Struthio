"""Small source-evidence contracts. Effects, review and support never grant authority."""
from __future__ import annotations
import hashlib,json,re
from decimal import Decimal,InvalidOperation
from fractions import Fraction
from . import record_store as records

VERSION='arc.reference-evidence/1'
UNITS={'s':('duration',1),'ms':('duration',Fraction(1,1000)),'us':('duration',Fraction(1,10**6)),
 'ns':('duration',Fraction(1,10**9)),'ps':('duration',Fraction(1,10**12)),
 'Hz':('frequency',1),'kHz':('frequency',1000),'MHz':('frequency',10**6),'GHz':('frequency',10**9),
 'V':('voltage',1),'mV':('voltage',Fraction(1,1000)),'A':('current',1),'mA':('current',Fraction(1,1000)),
 'B':('storage',1),'KiB':('storage',1024),'MiB':('storage',1024**2)}

def digest(value):return hashlib.sha256(records.canonical(value)).hexdigest()
def quantity(value,unit):
    unit=unit.replace('µ','u').replace('μ','u') if isinstance(unit,str) else unit
    if unit not in UNITS:raise ValueError('EVIDENCE_UNIT_REQUIRED_OR_UNSUPPORTED')
    if not isinstance(value,str) or not re.fullmatch(r'[+-]?\d{1,20}(?:\.\d{1,16})?(?:[eE][+-]?\d{1,2})?',value):raise ValueError('EVIDENCE_DECIMAL_REQUIRED')
    decimal=Decimal(value)
    if not decimal.is_finite() or abs(decimal.adjusted())>24:raise ValueError('EVIDENCE_QUANTITY_LIMIT')
    exact=Fraction(decimal)*UNITS[unit][1]
    return {'value':value,'unit':unit,'dimension':UNITS[unit][0],'numerator':str(exact.numerator),'denominator':str(exact.denominator)}

def support(positive=False,negative=False):
    if type(positive) is not bool or type(negative) is not bool:raise ValueError('EVIDENCE_SUPPORT_BOOLEAN')
    return {(False,False):'UNKNOWN',(True,False):'SUPPORTED',(False,True):'REFUTED',(True,True):'CONFLICT'}[(positive,negative)]

def context_key(fact):
    return digest({k:fact[k] for k in ('subject','property','variant','conditions','role')})

def inquiry(subject,property_name,variant,conditions,facts):
    question={'subject':subject,'property':property_name,'variant':variant,'conditions':conditions}
    intent=digest({'schema':'arc.fact-inquiry/1',**question});matches=[f for f in facts if f['subject']==subject and f['property']==property_name]
    obligations=[]
    if not variant and any(f['variant'] for f in matches):obligations.append('SPECIFY_EXACT_VARIANT')
    applicable=[f for f in matches if f['variant']==variant and f['conditions']==conditions and f.get('applicability')=='CURRENT_REFERENCE' and f['role']!='HYPOTHESIS']
    if not applicable:
        if matches and any(f['conditions']!=conditions for f in matches):obligations.append('MATCH_SOURCE_OPERATING_CONDITIONS')
        obligations.append('OBTAIN_CURRENT_REVIEWED_SOURCE_FACT')
    if obligations:applicable=[]
    positives=any(f['polarity']=='SUPPORT' for f in applicable);negatives=any(f['polarity']=='REFUTE' for f in applicable)
    groups={}
    for fact in applicable:groups.setdefault(context_key(fact),set()).add((fact['quantity']['dimension'],fact['quantity']['numerator'],fact['quantity']['denominator']))
    value_disputes=[key for key,values in groups.items() if len(values)>1]
    if value_disputes:obligations.append('REVIEW_DIFFERENT_VALUES_IN_IDENTICAL_SOURCE_CONTEXT')
    obligations+=['VERIFY_CURRENT_FITTED_PART_AND_IMPLEMENTATION','PHYSICAL_QUALIFICATION_NOT_ESTABLISHED']
    return {'schema':'arc.fact-inquiry/1','intent_id':intent,'question':question,'result_type':'Question<SourceFact>',
      'support':support(positives,negatives),'source_facts':[f['id'] for f in applicable],'value_disputes':value_disputes,
      'obligations':list(dict.fromkeys(obligations)),'effects':['read'],'authority':'SOURCE_RECORDS_ONLY_NOT_HARDWARE_TRUTH'}

def validate_answer(answer,packet):
    if not isinstance(answer,dict) or set(answer)!={'state','text','citations'}:raise ValueError('REFERENCE_ANSWER_SCHEMA')
    if answer['state'] not in ('ANSWER','INSUFFICIENT_EVIDENCE') or not isinstance(answer['text'],str) or len(answer['text'])>8000:raise ValueError('REFERENCE_ANSWER_SHAPE')
    citations=answer['citations'];available={v['id'] for v in packet['passages']}
    if not isinstance(citations,list) or len(citations)>20 or any(not isinstance(v,str) or v not in available for v in citations):raise ValueError('REFERENCE_ANSWER_INVENTED_CITATION')
    if answer['state']=='ANSWER' and not citations:raise ValueError('REFERENCE_ANSWER_NEEDS_CITATION')
    return {'schema':'arc.reference-answer-validation/1','locator_membership':'CHECKED','natural_language_entailment':'NOT_VERIFIED',
      'technical_truth':'NOT_ESTABLISHED','citations':list(dict.fromkeys(citations)),'state':answer['state']}
