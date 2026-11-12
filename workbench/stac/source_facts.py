"""Verified, grade-aware manufacturer fact selection through Ledger Kernel.

Never parse a search hit into an approved number. Only exact native MPN +
reviewed selected_for binding + verified vendor.value + original vendor.page
may yield REVIEWED_FACT. The historical ROM's presence is a separate question.
"""
from __future__ import annotations
from hashlib import sha256
import re

_SHA256 = re.compile(r'^[0-9a-f]{64}$')


def _sha(value):
    return isinstance(value, str) and bool(_SHA256.fullmatch(value.lower()))


def _same_part(left, right):
    """Strict MPN equality; no fuzzy part-family or package substitutions."""
    return isinstance(left,str) and isinstance(right,str) and left.strip().upper() == right.strip().upper()


def _same_parameter(row, name):
    """Exact, case-insensitive symbol/parameter matching, no semantic guessing."""
    if not isinstance(name,str):return False
    return any(isinstance(row.get(key),str) and row[key].casefold()==name.casefold()
               for key in ('symbol','parameter'))


def _unknown(base, reason, *, candidates=(), state='UNKNOWN', details=()):
    return {**base, 'state':state, 'reason':reason,
            'reviewed_fact':None, 'original_page':None,
            'candidates':list(candidates), 'diagnostics':list(details),
            'source_binding':'UNRESOLVED'}


def resolve_fact(part: dict, property_name: str, kernel_read) -> dict:
    """Return either a verified source-selected fact or an explicit unknown.

    kernel_read(name, args) must be the existing staC read-only Kernel broker.
    This function grants no authority to edit design, claim physical proof or
    promote generated text to REVIEWED_FACT.
    """
    component=part.get('component',{})
    board=part.get('board_revision')
    ref=component.get('reference')
    native_mpn=component.get('value')
    base={'type':'FactInquiry', 'component':ref, 'board_revision':board,
          'native_mpn':native_mpn, 'property':property_name,
          'native_source_revision':part.get('revision'), 'native_state':part.get('state'),
          'native_source_manifest':part.get('source_manifest',{}),
          'physical_measurements':False, 'routed_connectivity_verified':False,
          'original_verified':False, 'vendor_status':'UNKNOWN',
          'vendor_record_set_sha256':None, 'model_invoked':False}
    if base['native_state']!='CURRENT':
        return _unknown(base,'NATIVE_SOURCE_REVIEW_REQUIRED')
    status=kernel_read('vendor.status', {})
    if not isinstance(status,dict):return _unknown(base,'INVALID_VENDOR_STATUS')
    base['vendor_status']=status.get('status','UNKNOWN')
    if base['vendor_status']!='AVAILABLE':
        return _unknown(base,'VENDOR_SOURCE_BLOCKED')
    record_digest=status.get('record_set_sha256')
    if not _sha(record_digest):
        return _unknown(base,'UNVERIFIED_VENDOR_RECORD_SET')
    base['vendor_record_set_sha256']=record_digest
    if board!='R10' or not isinstance(ref,str) or not isinstance(native_mpn,str):
        return _unknown(base,'UNSUPPORTED_FITMENT_CONTEXT')
    # Vendor KB's reviewed selection contract uses exact 'R10 U45 MPN'.
    # See tests.test_vendor_kb.U45 and vendor_kb.engineering_value().
    design_ref=f'{board} {ref} {native_mpn}'
    try:
        result=kernel_read('vendor.facts', {})
    except (ValueError, KeyError):
        return _unknown(base,'VENDOR_FACTS_UNAVAILABLE')
    if not isinstance(result,dict) or result.get('record_set_sha256')!=record_digest:
        return _unknown(base,'VENDOR_RECORD_SET_DRIFT')
    facts=result.get('facts',[])
    if not isinstance(facts,list) or len(facts)>10000:
        return _unknown(base,'INVALID_FACT_LIST')
    matching=[]
    for f in facts:
        if (not isinstance(f,dict) or not isinstance(f.get('selected_for'),list)
            or design_ref not in f['selected_for']):
            continue
        if not _same_parameter(f,property_name):continue
        if not _same_part(f.get('part'),native_mpn):continue
        matching.append(f)
    if not matching:
        return _unknown(base,'NO_EXACT_REVIEWED_FITMENT_FACT')
    summaries=[{'fact_id':x.get('fact_id'), 'effective_state':x.get('effective_state',x.get('state'))}
               for x in matching]
    reviewed=[f for f in matching if f.get('state')=='REVIEWED_FACT'
              and f.get('effective_state')=='REVIEWED_FACT'
              and f.get('usable_for_engineering') is True]
    # Multiple candidates are a conflict until explicitly reconciled, even if
    # they currently happen to quote the same value.
    if len(matching)>1:
        return _unknown(base,'MULTIPLE_FITMENT_FACTS',candidates=summaries,state='CONFLICT')
    if len(reviewed)!=1:
        return _unknown(base,'FACT_NOT_CURRENTLY_REVIEWED',candidates=summaries)
    selected=reviewed[0]
    fact_id=selected.get('fact_id')
    if not isinstance(fact_id,str) or not 1<=len(fact_id)<=150:
        return _unknown(base,'INVALID_REVIEWED_FACT_ID')
    try:
        verified=kernel_read('vendor.value', {'fact_id':fact_id,'design_ref':design_ref})
    except (ValueError,KeyError):
        return _unknown(base,'VENDOR_VALUE_REJECTED',candidates=summaries)
    if (not isinstance(verified,dict) or verified.get('record_set_sha256')!=record_digest or
        verified.get('fact_state')!='REVIEWED_FACT'):
        return _unknown(base,'VENDOR_VALUE_UNVERIFIED',candidates=summaries)
    value=verified.get('value')
    if (not isinstance(value,dict) or value.get('fact_id')!=fact_id or
        not _same_part(value.get('part'),native_mpn) or
        value.get('grade')!=selected.get('grade') or
        value.get('parameter')!=selected.get('parameter') or
        value.get('document_id')!=selected.get('document_id') or
        value.get('reviewed_source_sha256')!=selected.get('reviewed_source_sha256') or
        value.get('page_index')!=selected.get('page_index') or
        not _sha(value.get('reviewed_source_sha256'))):
        return _unknown(base,'FACT_VALUE_IDENTITY_MISMATCH',candidates=summaries)
    doc_id=value['document_id'];idx=value['page_index']
    if not isinstance(idx,int) or isinstance(idx,bool) or not 0<=idx<=10000:
        return _unknown(base,'INVALID_PAGE_REFERENCE',candidates=summaries)
    # Verify the original PDF via Ledger's own original-page endpoint. Indexed
    # text or an FTS hit alone is not original source verification.
    try:
        page_response=kernel_read('vendor.page',{'document_id':doc_id,'page_index':idx,'original':True})
    except (ValueError,KeyError):
        return _unknown(base,'ORIGINAL_PAGE_UNAVAILABLE',candidates=summaries)
    if (not isinstance(page_response,dict) or page_response.get('record_set_sha256')!=record_digest
        or page_response.get('fact_state')!='EXTRACTED_TEXT'):
        return _unknown(base,'ORIGINAL_PAGE_RECORD_DRIFT',candidates=summaries)
    page=page_response.get('page');doc=page_response.get('document')
    digest=value['reviewed_source_sha256']
    if (not isinstance(page,dict) or not isinstance(doc,dict)
        or doc.get('document_id')!=doc_id or doc.get('source_state')!='CURRENT'
        or doc.get('source_sha256')!=digest or doc.get('current_sha256')!=digest
        or page.get('document_id')!=doc_id or page.get('source_sha256')!=digest
        or page.get('page_index')!=idx):
        return _unknown(base,'ORIGINAL_SOURCE_HASH_OR_ID_MISMATCH',candidates=summaries)
    page_text=page.get('page_text')
    # A blank page extraction is not enough to check a numerical claim. The
    # original may still be legitimate, but its fact needs direct page review.
    if not isinstance(page_text,str) or not page_text.strip():
        return _unknown(base,'ORIGINAL_PAGE_TEXT_UNREADABLE',candidates=summaries)
    bound={key:value.get(key) for key in ('fact_id','part','package','grade','parameter','symbol','unit',
          'min','typ','max','conditions','document_id','reviewed_source_sha256','page_index','page_label','region')}
    source={'document_id':doc_id, 'source_sha256':digest, 'page_index':idx,
            'page_label':page.get('page_label') or value.get('page_label'),
            'original_text_sha256':sha256(page_text.encode('utf-8')).hexdigest(),
            'document_revision':doc.get('revision'),
            'rights':doc.get('rights','UNREVIEWED'),
            'original_pdf_verified':True}
    return {**base,'state':'REVIEWED_FACT','reason':'EXACT_SOURCE_AND_FITMENT_BOUND',
            'reviewed_fact':bound,'original_page':source,'original_verified':True,
            'source_binding':'REVIEWED_ORIGINAL','candidates':summaries,'diagnostics':[],
            'design_ref':design_ref}
