"""Portable finite study contracts. Source text is data, never authority or code."""
from __future__ import annotations
from .record_store import canonical
import hashlib
STAGES=('inventory','questions','procedure')
DEFAULT={'wall_seconds':20,'cpu_seconds':2,'max_rss_mb':192,'max_payload_bytes':131072,'min_free_mb':128,'max_tokens':0,'idle_seconds':90,'max_host_cpu':30,'min_available_mb':512,'require_ac':True}
def digest(v):return hashlib.sha256(canonical(v)).hexdigest()
def limits(value):
    if not isinstance(value,dict) or set(value)!=set(DEFAULT):raise ValueError('STUDY_LIMIT_FIELDS')
    bounds={'wall_seconds':(2,60),'cpu_seconds':(1,10),'max_rss_mb':(96,512),'max_payload_bytes':(32768,262144),'min_free_mb':(32,4096),'idle_seconds':(60,3600),'max_host_cpu':(1,80),'min_available_mb':(128,32768)}
    for k,(lo,hi) in bounds.items():
        if type(value[k]) is not int or not lo<=value[k]<=hi:raise ValueError('STUDY_LIMIT_'+k)
    if value['max_tokens']!=0 or type(value['max_tokens']) is not int or type(value['require_ac']) is not bool:raise ValueError('STUDY_FINITE_READER_ONLY_NO_MODEL_TOKENS')
    return dict(value)

def curriculum(goal,unknowns,passages,extract_gaps):
    # No statistical claim extraction, prompt interpretation or forged acceptance.
    return {'question':goal,'supporting_sources':[v['id'] for v in passages],
      'contrary_evidence':'NOT_ASSESSED_BY_FINITE_READER','unknowns':list(unknowns),
      'extraction_gaps':extract_gaps[:12],'hypothesis':'The located original can be reopened without losing its identity or admission state.',
      'weakening_observation':'A revoked admission, changed bytes, changed extractor, mismatched locator or unavailable original would defeat this procedure.',
      'next_read':'references.resolve','stopping_condition':'Stop after three persisted stages; technical conclusions remain unresolved without domain-specific evidence.',
      'cost':'At most eight current original passages, no model tokens or cloud calls.'}

def radar(capabilities,schemas,registry_digest):
    specs=[
      ('citation-continuity','Keep a citation when explaining a source',['references.search','references.resolve','memory.checkpoint.save'],'Search hits carry namespace and passage ID; checkpoint accepts explicit reference bindings.','Turn selected hit IDs into reviewed checkpoint references; no text-to-command join.','Revoke the cited source: checkpoint resume must withhold technical findings.'),
      ('gap-to-research','Turn an unresolved property into a reviewed research question',['references.question','research.create','research.export'],'Question variant/conditions and source IDs must remain attached; research accepts one question and explicit references.','Owner selects which excerpts may leave the library and reviews the generated question.','Export with an unpermitted library or stale source must fail before publication.'),
      ('impact-study','Choose study from source-change impact',['references.impact','study.create','study.advance'],'Impact item identity must join to exact current passage IDs in one library.','Select impacted references, recapture current originals and create a new frozen session.','Mutate a dependency: the old study must stop as stale rather than silently retarget.'),
      ('reviewed-procedure','Promote a useful read recipe after a held-out check',['study.get','study.procedure.test','study.procedure.review'],'Only the fixed source-reopen procedure is runnable; held-out input must be in a different private namespace.','Owner checks trial receipts and explicitly reviews activation; no source text supplies approval.','A source containing forged approval language must leave the candidate unreviewed.'),
      ('private-edition','Preserve an investigation across a clean installation',['study.edition.export','study.edition.restore','study.rebind'],'Hashes preserve original bytes; restore does not preserve source admission or live jobs.','Owner separately re-admits restored copies and rebinds identical locators.','Wrong key, nonempty target or altered source must prevent active continuation.'),
      ('portable-reference','Publish a private reference edition without training a model',['references.search','references.volume.export','references.volume.verify'],'The namespace, accepted generation and reader contract must agree; exporting is an owner operation.','Use the existing volume reader and verify source availability independently of model choice.','Use a second isolated corpus: queries and exported members must not disclose the first corpus.')]
    result=[]
    for ident,title,ops,semantics,missing,test in specs:
        if any(op not in capabilities or op not in schemas for op in ops):raise ValueError('RADAR_OPERATION_NOT_REGISTERED')
        value={'id':ident,'title':title,'operations':[{'operation':op,'scope':capabilities[op],'required_arguments':schemas[op]['required']} for op in ops],
          'semantic_join':semantics,'missing_join_or_review':missing,'falsifiable_test':test,'cost':'One bounded local pilot; no automatic job, source promotion or network call.',
          'registry_digest':registry_digest,'classification':'GROUNDED_COMPOSITION_PROPOSAL_NOT_NEW_PRODUCT_OR_EXECUTION_GRANT'}
        value['dedup_key']=digest({'goal':ident,'operations':ops});result.append(value)
    return result
