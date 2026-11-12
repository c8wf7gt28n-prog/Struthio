"""staC 0.4: first-class engineering questions and explicit proof obligations.

An EngineeringQuestion is a *well-typed, unanswered question*. Even a reviewed
manufacturer specification is not an implementation measurement, and neither
that specification nor a hypothetical number constitutes a physical test.

This module is deterministic and pure. It neither promotes claims to evidence
nor obtains a source; the staC runtime supplies source-qualified FactInquiries.
"""
from __future__ import annotations

from .evidence import EvidenceSupport

QUESTION_SCHEMA = 'arc.stac.question/0.4'
OBLIGATIONS_SCHEMA = 'arc.stac.obligations/0.4'


class ObligationError(ValueError):
    pass


def _fact_from(value: dict) -> dict:
    if not isinstance(value, dict) or not isinstance(value.get('payload'), dict):
        raise ObligationError('INVALID_QUESTION_INPUT')
    if value.get('type') == 'FactInquiry':
        f = value['payload']
    elif value.get('type') in ('QualificationAssessment', 'ScenarioAssessment',
                               'EngineeringQuestion', 'WitnessJudgment'):
        f = value['payload'].get('fact_inquiry')
    else:
        raise ObligationError('QUESTION_REQUIRES_SOURCE_FACT_OR_ASSESSMENT')
    if not isinstance(f, dict) or f.get('type') != 'FactInquiry':
        raise ObligationError('MISSING_TYPED_FACT_INQUIRY')
    return f


def _entry(code: str, state: str, why: str, *, witness: dict | None = None) -> dict:
    if state not in ('SATISFIED', 'OPEN'):
        raise ObligationError('INVALID_OBLIGATION_STATE')
    return {'code': code, 'state': state, 'reason': why,
            'source_witness': witness if state == 'SATISFIED' else None}


def _obligations(fact: dict) -> list[dict]:
    bound = (fact.get('state') == 'REVIEWED_FACT' and
             fact.get('original_verified') is True and
             isinstance(fact.get('reviewed_fact'), dict) and
             isinstance(fact.get('original_page'), dict))
    native = (fact.get('native_state') == 'CURRENT' and
              isinstance(fact.get('native_source_revision'), str) and
              bool(fact['native_source_revision']) and
              fact.get('board_revision') == 'R10')
    source = fact.get('original_page') or {}
    vendor_witness = None
    if bound:
        vendor_witness = {'fact_id': fact['reviewed_fact'].get('fact_id'),
                          'document_id': source.get('document_id'),
                          'original_sha256': source.get('source_sha256'),
                          'page_index': source.get('page_index'),
                          'grade': fact['reviewed_fact'].get('grade'),
                          'part': fact.get('native_mpn')}
    native_witness = ({'source_generation': fact['native_source_revision'],
                       'board_revision': fact['board_revision'],
                       'component': fact.get('component')}
                      if native else None)
    return [
        _entry('NATIVE_REVISION_BOUND', 'SATISFIED' if native else 'OPEN',
               'Native source generation must resolve to the selected historical context.',
               witness=native_witness),
        _entry('APPLICABLE_VENDOR_ORIGINAL', 'SATISFIED' if bound else 'OPEN',
               'Reviewed original fact must match the fitted exact part, grade and conditions.',
               witness=vendor_witness),
        _entry('CURRENT_IMPLEMENTATION_TIMING', 'OPEN',
               'No source-bound controller timing behavior was supplied to this question.'),
        _entry('REVIEWED_TEST_ORACLE', 'OPEN',
               'No independently accepted pass/fail criterion was supplied.'),
        _entry('APPLICABLE_TEST_RESULT', 'OPEN',
               'No applicable registered test result for the selected implementation was supplied.'),
        _entry('PHYSICAL_TARGET_QUALIFICATION', 'OPEN',
               'No physical target measurement or authorized qualification was supplied.')
    ]


def question(value: dict) -> dict:
    """Construct Question<Qualification>; reviewed requirements do not prove compliance."""
    fact = _fact_from(value)
    obligations = _obligations(fact)
    return {'type': 'EngineeringQuestion', 'schema': QUESTION_SCHEMA,
            'question_type': 'Question<Qualification>',
            'subject': {'project': 'ARC-1', 'revision': fact.get('board_revision'),
                        'source_generation': fact.get('native_source_revision'),
                        'component': fact.get('component'), 'mpn': fact.get('native_mpn'),
                        'property': fact.get('property')},
            'proposition': 'Selected implementation satisfies applicable source-bound requirement',
            'fact_inquiry': fact, 'knowledge_state': fact.get('state', 'UNKNOWN'),
            'evidence': {'support_positive': False, 'support_negative': False,
                         'state': EvidenceSupport().state.value,
                         'scope': 'IMPLEMENTATION_COMPLIANCE',
                         'applicability': 'NOT_ASSESSED'},
            'proof_obligations': obligations,
            'state': 'UNRESOLVED',
            'observed_measurements': [], 'tests_executed': [],
            'physical_qualification_granted': False,
            'note': 'A well-typed question does not imply that its proposition is proven.'}


def report(value: dict) -> dict:
    """Return inspectable evidence obligations; never invent a witness or a PASS."""
    fact = _fact_from(value)
    witness_state = (value.get('payload', {}).get('state')
                     if value.get('type') == 'WitnessJudgment' else None)
    # A failed witness recheck overrides any positive flag in the earlier fact
    # inquiry. The previous original may have become stale or forged.
    if witness_state and witness_state != 'VERIFIED_SOURCE_REQUIREMENT':
        fact = {**fact, 'state': 'UNKNOWN', 'original_verified': False,
                'reviewed_fact': None, 'original_page': None}
    observations = _obligations(fact)
    if witness_state:
        observations.append(_entry('TRUSTED_WITNESS_RECHECK',
                                   'SATISFIED' if witness_state == 'VERIFIED_SOURCE_REQUIREMENT' else 'OPEN',
                                   'Current original, fitment and claim must match the trusted source recheck.',
                                   witness=value['payload'].get('reviewed_source_witness')))
    if value.get('type') == 'ScenarioAssessment':
        observations.append(_entry('ASSUMPTION_NOT_OBSERVATION', 'OPEN',
                                   'Hypothetical numeric comparison is not a measured test.'))
    if value.get('type') == 'QualificationAssessment':
        observations.append(_entry('ASSESSMENT_NOT_APPROVAL', 'OPEN',
                                   'A read-only assessment never promotes a physical qualification.'))
    return {'type': 'ObligationReport', 'schema': OBLIGATIONS_SCHEMA,
            'question_type': 'Question<Qualification>',
            'subject': {'board_revision': fact.get('board_revision'),
                        'component': fact.get('component'),
                        'property': fact.get('property')},
            'fact_inquiry': fact,
            'obligations': observations,
            'open': [x['code'] for x in observations if x['state'] == 'OPEN'],
            'satisfied': [x['code'] for x in observations if x['state'] == 'SATISFIED'],
            'claim_evidence_state': 'UNKNOWN',
            'reviewed_fact_is_physical_proof': False,
            'effects': ['read'], 'tests_executed': [],
            'physical_qualification_granted': False}
