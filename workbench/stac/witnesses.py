"""staC 0.5 — trusted, source-bound engineering claim/witness semantics.

This module does NOT assert that a citation is a proof or authorize actions.
A candidate describes a question about an original manufacturer's requirement.
Only verify_witness() calls Ledger's *registered, read-only* source readers
again and compares the fresh, exact fitment/grade/page/quantity to the claimed
one. The resulting SUPPORTED state is limited to the source requirement; it
never qualifies implementation behavior or a physical target.

The caller must provide a trusted Ledger Kernel read broker. Never expose
this function as an arbitrary model-callable authority or accept an LLM-supplied
``validated=True`` flag. Hashes are local identity digests, NOT signatures.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Callable

from .. import record_io
from .evidence import EvidenceSupport
from .quantities import Quantity, DimensionError
from .source_facts import resolve_fact

CLAIM_SCHEMA = 'arc.stac.claim/0.5'
WITNESS_SCHEMA = 'arc.stac.witness.candidate/0.5'
JUDGMENT_SCHEMA = 'arc.stac.witness.judgment/0.5'
PROFILE = 'arc-record-io-json/1'  # Do not claim compatibility with RFC 8785.


class WitnessError(ValueError):
    """Malformed, untyped or unauthorized witness operation."""


def _fact(value: dict) -> dict:
    if not isinstance(value, dict) or not isinstance(value.get('payload'), dict):
        raise WitnessError('TYPED_FACT_REQUIRED')
    kind = value.get('type')
    if kind == 'FactInquiry':
        fact = value['payload']
    elif kind in ('ClaimCandidate', 'WitnessCandidate'):
        fact = value['payload'].get('fact_inquiry')
    else:
        raise WitnessError('CLAIM_REQUIRES_FACT_INQUIRY')
    if not isinstance(fact, dict) or fact.get('type') != 'FactInquiry':
        raise WitnessError('TYPED_FACT_REQUIRED')
    return fact


def _quantity(row: dict) -> dict | None:
    if not isinstance(row, dict):
        return None
    maximum = row.get('max')
    unit = row.get('unit')
    if maximum is None:
        return None
    if type(maximum) not in (int, str) or not isinstance(unit, str):
        return None
    try:
        n = Decimal(str(maximum))
        q = Quantity(n, {'µs': 'us', 'μs': 'us'}.get(unit, unit))
        if not n.is_finite() or q.dimension != 'time' or not n >= 0:
            return None
        canonical_si = format(q.as_base().normalize(), 'f')
        return {'relation': '<=', 'value_si': canonical_si,
                'base_unit': 's', 'dimension': 'time',
                'source_value': format(n.normalize(), 'f'), 'source_unit': q.unit}
    except (InvalidOperation, DimensionError, ValueError, ArithmeticError, OverflowError):
        return None


def _claim_record(fact: dict) -> dict:
    """Build a *provisional* vendor-requirement proposition; no support granted."""
    row = fact.get('reviewed_fact') if fact.get('state') == 'REVIEWED_FACT' else None
    source = fact.get('original_page') if fact.get('original_verified') is True else None
    if not isinstance(row, dict) or not isinstance(source, dict):
        row = None
        source = None
    quantity = _quantity(row) if row is not None else None
    source_identity = None
    if row is not None and quantity is not None:
        source_identity = {
            'vendor_record_set_sha256': fact.get('vendor_record_set_sha256'),
            'fact_id': row.get('fact_id'),
            'document_id': source.get('document_id'),
            'original_sha256': source.get('source_sha256'),
            'page_index': source.get('page_index'),
            'page_text_sha256': source.get('original_text_sha256'),
        }
    return {
        'schema': CLAIM_SCHEMA,
        'kind': 'VENDOR_UPPER_BOUND_REQUIREMENT',
        'subject': {'project': 'ARC-1', 'board_revision': fact.get('board_revision'),
                    'component': fact.get('component'), 'mpn': fact.get('native_mpn'),
                    'source_generation': fact.get('native_source_revision')},
        'property': fact.get('property'),
        'conditions': row.get('conditions') if row else None,
        'variant': {'grade': row.get('grade'), 'package': row.get('package')} if row else None,
        'bound': quantity,
        'source_locator': source_identity,
    }


def claim_from_fact(value: dict) -> dict:
    """Produce a non-authoritative, immutable-by-convention claim candidate."""
    f = _fact(value)
    claim = _claim_record(f)
    digest = record_io.digest(claim)
    return {'type': 'ClaimCandidate', 'schema': CLAIM_SCHEMA,
            'claim': claim, 'claim_digest': digest, 'digest_profile': PROFILE,
            'state': 'PENDING_WITNESS' if claim['source_locator'] else 'UNRESOLVED',
            'fact_inquiry': f,
            'evidence_state': EvidenceSupport().state.value,
            'source_verified_by_witness_checker': False,
            'physical_qualification_granted': False,
            'note': 'A claim candidate and its original citation are not themselves verification.'}


def witness_from_claim(value: dict) -> dict:
    """Record a source locator, not a signed or reviewed witness."""
    if value.get('type') != 'ClaimCandidate' or not isinstance(value.get('payload'), dict):
        raise WitnessError('WITNESS_REQUIRES_CLAIM_CANDIDATE')
    candidate = value['payload']
    if candidate.get('schema') != CLAIM_SCHEMA or candidate.get('digest_profile') != PROFILE:
        raise WitnessError('INVALID_CLAIM_CANDIDATE')
    if not isinstance(candidate.get('claim'), dict) or record_io.digest(candidate['claim']) != candidate.get('claim_digest'):
        raise WitnessError('CLAIM_IDENTITY_MISMATCH')
    source = candidate['claim'].get('source_locator')
    locator = {'source_kind': 'REVIEWED_VENDOR_ORIGINAL', **source} if isinstance(source, dict) else None
    return {'type': 'WitnessCandidate', 'schema': WITNESS_SCHEMA,
            'claim': candidate['claim'], 'claim_digest': candidate['claim_digest'],
            'locator': locator, 'state': 'PENDING_VERIFICATION' if locator else 'SOURCE_UNAVAILABLE',
            'fact_inquiry': _fact(value), 'digest_profile': PROFILE,
            'evidence_state': 'UNKNOWN', 'source_verified': False,
            'physical_qualification_granted': False,
            'note': 'Locator is supplied as untrusted data until checked against live Ledger sources.'}


def _judgment(candidate: dict, state: str, reason: str, *, fresh: dict | None = None) -> dict:
    if state not in ('VERIFIED_SOURCE_REQUIREMENT', 'SOURCE_UNAVAILABLE', 'REJECTED'):
        raise WitnessError('INVALID_JUDGMENT_STATE')
    valid = state == 'VERIFIED_SOURCE_REQUIREMENT'
    source = fresh.get('original_page') if valid and isinstance(fresh, dict) else None
    claim = candidate['claim']
    return {
        'type': 'WitnessJudgment', 'schema': JUDGMENT_SCHEMA,
        'claim_digest': candidate['claim_digest'],
        'claim': claim,
        'state': state,
        'reason': reason,
        'support': {'positive': bool(valid), 'negative': False},
        'evidence_state': EvidenceSupport(positive=bool(valid)).state.value,
        'scope': 'MANUFACTURER_REQUIREMENT_ONLY',
        'reviewed_source_witness': ({'original': source,
                                     'fact_id': fresh['reviewed_fact']['fact_id'],
                                     'vendor_record_set_sha256': fresh['vendor_record_set_sha256'],
                                     'selected_design_ref': fresh['design_ref'],
                                     'native_source_generation': fresh['native_source_revision']}
                                    if valid else None),
        'fact_inquiry': fresh if valid else _fact({'type': 'WitnessCandidate', 'payload': candidate}),
        'outstanding_obligations': ([] if valid else ['APPLICABLE_VENDOR_ORIGINAL']) + [
            'CURRENT_IMPLEMENTATION_TIMING', 'REGISTERED_TEST_ORACLE',
            'APPLICABLE_TEST_RESULT', 'PHYSICAL_TARGET_QUALIFICATION'],
        'tests_executed': [], 'model_invoked': False,
        'simulation_pass_proven': False, 'physical_qualification_granted': False,
        'digest_profile': PROFILE,
    }


def verify_witness(value: dict, kernel_read: Callable[[str, dict], dict]) -> dict:
    """Check candidate against FRESH native fitment, reviewed fact and original page.

    This function intentionally discards all candidate ``original_verified``
    assertions and independently reads the original through Ledger's vendor.page
    original=True contract (via resolve_fact). A fake citation/claim cannot
    become a verified witness merely by filling fields in JSON.
    """
    if value.get('type') != 'WitnessCandidate' or not isinstance(value.get('payload'), dict):
        raise WitnessError('VERIFY_REQUIRES_WITNESS_CANDIDATE')
    candidate = value['payload']
    if candidate.get('schema') != WITNESS_SCHEMA or candidate.get('digest_profile') != PROFILE:
        raise WitnessError('INVALID_WITNESS_CANDIDATE')
    claim = candidate.get('claim')
    if not isinstance(claim, dict) or claim.get('schema') != CLAIM_SCHEMA:
        raise WitnessError('INVALID_TYPED_CLAIM')
    if record_io.digest(claim) != candidate.get('claim_digest'):
        return _judgment(candidate, 'REJECTED', 'CLAIM_DIGEST_MISMATCH')
    original_locator = claim.get('source_locator')
    expected = ({'source_kind': 'REVIEWED_VENDOR_ORIGINAL', **original_locator}
                if isinstance(original_locator, dict) else None)
    if candidate.get('locator') != expected:
        return _judgment(candidate, 'REJECTED', 'WITNESS_LOCATOR_MISMATCH')
    subj = claim.get('subject')
    if not isinstance(subj, dict) or (subj.get('project'), subj.get('board_revision')) != ('ARC-1', 'R10'):
        return _judgment(candidate, 'REJECTED', 'UNSUPPORTED_CLAIM_CONTEXT')
    ref = subj.get('component')
    prop = claim.get('property')
    if not isinstance(ref, str) or not ref or not isinstance(prop, str) or not prop:
        return _judgment(candidate, 'REJECTED', 'INVALID_CLAIM_TARGET')
    try:
        # Fresh read; cannot rely on a dictionary or citation supplied by the model.
        part = kernel_read('links.inspect', {'component': ref})
        if (not isinstance(part, dict) or part.get('state') != 'CURRENT' or
            part.get('revision') != subj.get('source_generation') or
            part.get('board_revision') != 'R10' or
            (part.get('component') or {}).get('value') != subj.get('mpn')):
            return _judgment(candidate, 'SOURCE_UNAVAILABLE', 'NATIVE_REVISION_OR_FITMENT_CHANGED')
        fresh = resolve_fact(part, prop, kernel_read)
        if fresh.get('state') != 'REVIEWED_FACT' or not fresh.get('original_verified'):
            return _judgment(candidate, 'SOURCE_UNAVAILABLE', str(fresh.get('reason', 'SOURCE_NOT_QUALIFIED')))
        # Bind the whole typed proposition. Numeric, grade, conditions, PDF and
        # page source identity must all still agree—not merely a matching URL.
        if _claim_record(fresh) != claim:
            return _judgment(candidate, 'REJECTED', 'SOURCE_CLAIM_CHANGED_OR_FORGED')
        again = kernel_read('links.inspect', {'component': ref, 'expected_revision': subj['source_generation']})
        if not isinstance(again, dict) or again.get('state') != 'CURRENT' or again.get('revision') != subj['source_generation']:
            return _judgment(candidate, 'SOURCE_UNAVAILABLE', 'NATIVE_SOURCE_CHANGED_DURING_CHECK')
    except (ValueError, KeyError, TypeError, AttributeError) as exc:
        return _judgment(candidate, 'SOURCE_UNAVAILABLE', 'SOURCE_CHECK_BLOCKED_' + type(exc).__name__)
    return _judgment(candidate, 'VERIFIED_SOURCE_REQUIREMENT', 'FRESH_REVIEWED_ORIGINAL_AND_FITMENT_MATCH', fresh=fresh)
