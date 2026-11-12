"""staC 0.4: deterministic, read-only static semantic inspector.

This describes a compiler's *typed operation plan*, not a runtime proof. It
validates against the same registered signatures used by the staC interpreter.
No model, files, Ledger tools or other external effects are invoked here.
"""
from __future__ import annotations
from typing import Any

from .. import record_io
from .language import SIGNATURES, intent_hash

SCHEMA = 'arc.stac.static/0.4'
SCHEMA_05 = 'arc.stac.static/0.5'
TYPE_NAMES = {
    'Context': 'Context<ARC-1@R10>',
    'PartInspection': 'Evidence<Part>',
    'ConnectivityTrace': 'Evidence<ConnectivityTrace>',
    'FactInquiry': 'Question<ReviewedRequirement>',
    'QualificationAssessment': 'Assessment<Compliance>',
    'ScenarioAssessment': 'Scenario<Duration>',
    'ProvenanceReport': 'Provenance<SourceRef>',
    'GapReport': 'List<UnresolvedEvidence>',
    'ChallengeReport': 'List<HypothesisTest>',
    'KnowledgePacket': 'EngineeringKnowledgePacket',
    'ROMStatus': 'Evidence<ROMInventory>',
    'VendorStatus': 'Evidence<VendorAvailability>',
    'EngineeringQuestion': 'Question<Qualification>',
    'ObligationReport': 'List<ProofObligation<Qualification>>',
    'ClaimCandidate': 'Claim<VendorRequirement,Proposed>',
    'WitnessCandidate': 'Witness<SourceRef,Unchecked>',
    'WitnessJudgment': 'Judgment<VendorRequirement,SourceChecked>',
    'PredicateAssessment': 'Scenario<Predicate<Duration>,Hypothetical>',
    'KernelJobInspection': 'KernelRecord<Job,Unchecked>',
    'KernelTestWitness': 'Witness<KernelTestOutcome,RecordCorroborated>',
}


class SemanticError(ValueError):
    pass


def inspect(ir: dict[str, Any]) -> dict[str, Any]:
    """Validate compiler IR and return typed AST presentation (does not execute)."""
    # Re-use the interpreter's complete schema/type/effect+argument validation.
    # Import locally to avoid module cycles; no runtime Kernel is constructed.
    from .runtime import _validate_ir
    try:
        nodes = _validate_ir(ir)
    except Exception as exc:
        raise SemanticError('INVALID_TYPED_PROGRAM: ' + str(exc)) from exc
    typed=[]
    for i, node in enumerate(nodes):
        operation=node['op']
        if operation=='context.select':
            command='use';in_type='Context';out_type='Context'
            declared=()
        else:
            matching=[(name,s) for name,s in SIGNATURES.items() if s[3]==operation]
            if len(matching)!=1:
                raise SemanticError('UNREGISTERED_STATIC_OPERATION')
            command,signature=matching[0]
            in_type=node['input_type'];out_type=node['output_type']
            declared=signature[2]
        if in_type not in TYPE_NAMES or out_type not in TYPE_NAMES:
            raise SemanticError('UNREGISTERED_SEMANTIC_TYPE')
        typed.append({'index':i,'command':command,'operation':operation,
                      'input':TYPE_NAMES[in_type], 'output':TYPE_NAMES[out_type],
                      'declared_effects':list(declared),
                      'registered':True,
                      'arguments':node['arguments']})
    if any(effect not in ('read',) for effect in ir['effects']):
        raise SemanticError('EXECUTION_EFFECT_NOT_AUTHORIZED')
    body={'schema':'arc.stac.semantics/0.6' if ir['version']==6 else (SCHEMA_05 if ir['version']==5 else SCHEMA), 'ir_schema':ir['schema'],
          'intent_digest':intent_hash(ir),
          'digest_profile':ir['digest_profile'],
          'symbolic_context':ir['context'],
          'result_type':TYPE_NAMES[ir['result_type']],
          'declared_effects':ir['effects'],
          'run_time_authorization_granted':False,
          'evidence_validated':False,
          'source_binding_state':'SYMBOLIC_UNPINNED',
          'proof_obligations': ['SOURCE_BINDING_REQUIRED','APPLICABLE_EVIDENCE_REQUIRED']
                 if any(n['operation'] in ('stac.question','stac.obligations','stac.assess','stac.claim','stac.witness','stac.verify') for n in typed) else [],
          'typed_ast':typed}
    body['semantic_digest']=record_io.digest(body)
    return body
