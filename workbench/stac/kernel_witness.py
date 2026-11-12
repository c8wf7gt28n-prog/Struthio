"""staC 0.6 — read-only witnesses of *registered Ledger Kernel job evidence*.

Only the Kernel's registered jobs.get, evidence.read, project.inspect read
operations are used. A completed process, zero exit status, or even an explicit
host simulation PASS does NOT establish a product-level engineering claim,
accepted test oracle, physical measurement, or permission to run a tool.

The result verifies *internal consistency of the recorded Kernel artifacts*;
it is not a cryptographic attestation of the raw test artifact bytes.
"""
from __future__ import annotations

import re
from typing import Callable
from .. import record_io
from ..engineering_kernel import TOOLS

JOB_SCHEMA = 'arc.stac.kernel.job/0.6'
WITNESS_SCHEMA = 'arc.stac.kernel.test-witness/0.6'
JOB_ID = re.compile(r'^[0-9a-f]{32}$')
CLASSES = frozenset({'HOST_SIM', 'RTL_SIM', 'STATIC_CHECK'})
TERMINAL = frozenset({'Completed','Failed','Cancelled','Interrupted'})
PROFILE = 'arc-record-io-json/1'

class TestWitnessError(ValueError):
    """Malformed Kernel record, unauthorized request, or inconsistent evidence."""


def _id(value: str, name: str) -> str:
    if not isinstance(value, str) or not JOB_ID.fullmatch(value):
        raise TestWitnessError('INVALID_' + name.upper() + '_ID')
    return value


def _read(read: Callable[[str, dict], dict], op: str, id: str) -> dict:
    value = read(op, {'id': id})
    if not isinstance(value, dict):
        raise TestWitnessError('KERNEL_RECORD_NOT_OBJECT')
    return value


def inspect_job(id: str, read: Callable[[str, dict], dict]) -> dict:
    """Capture a job's precise Kernel record digest as an UNVERIFIED candidate."""
    id = _id(id, 'job')
    try:
        job = _read(read, 'jobs.get', id)
    except Exception as exc:
        # The read broker returns an error on missing records. Never invent jobs.
        raise TestWitnessError('KERNEL_JOB_NOT_AVAILABLE') from exc
    if job.get('id') != id:
        raise TestWitnessError('KERNEL_JOB_ID_MISMATCH')
    return {'type': 'KernelJobInspection', 'schema': JOB_SCHEMA,
            'id': id, 'record_digest': record_io.digest(job),
            'digest_profile': PROFILE,
            'job_state': job.get('state'), 'tool': job.get('tool'),
            'revision': job.get('revision'), 'evidence_id': job.get('evidence'),
            'state': 'PENDING_RECORD_CORROBORATION',
            'evidence_state': 'UNKNOWN', 'physical_qualification_granted': False,
            'note': 'A job record is not an approved passing test or physical qualification.'}


def _judgment(candidate: dict, state: str, reason: str, *, job: dict | None = None,
              evidence: dict | None = None, applicability: str = 'NOT_ASSESSED',
              source_now: str | None = None) -> dict:
    """Only emit allowlisted, non-sensitive fields, never stdout/stderr or argv."""
    consistent = state in ('RECORDED_HOST_PASS', 'RECORDED_CHECK_FAILURE', 'RECORDED_TOOL_SUCCESS_ONLY')
    j, e = job or {}, evidence or {}
    return {'type': 'KernelTestWitness', 'schema': WITNESS_SCHEMA,
            'job_id': candidate['id'], 'evidence_id': candidate.get('evidence_id'),
            'job_record_digest': record_io.digest(j) if consistent else None,
            'evidence_record_digest': record_io.digest(e) if consistent else None,
            'digest_profile': PROFILE, 'state': state, 'reason': reason,
            'job_state': j.get('state'), 'tool': j.get('tool'),
            'source_revision': j.get('revision'),
            'observed_project_revision': source_now,
            'source_applicability': applicability,
            'execution_class': e.get('class') if consistent else None,
            'recorded_tool_outcome': (e.get('outcome') if e.get('outcome') in
                (None, 'PASS', 'FAIL', 'FAILED', 'BLOCKED', 'UNASSESSED',
                 'SOURCE-CHECKED', 'OK', 'NOT_ASSESSED', 'NOT_INSTRUMENTED') else
                 'UNRECOGNIZED') if consistent else None,
            'exit_status': e.get('exit_status') if consistent else None,
            'target_status': (e.get('target_status') if e.get('target_status') in
                (None, 'PASS', 'FAIL', 'FAILED', 'BLOCKED', 'HOLD', 'NOT_ASSESSED')
                else 'UNRECOGNIZED') if consistent else None,
            'evidence_state': ('SUPPORTED' if state == 'RECORDED_HOST_PASS' else
                               'REFUTED' if state == 'RECORDED_CHECK_FAILURE' else 'UNKNOWN'),
            'support_scope': 'REGISTERED_KERNEL_TEST_OUTCOME_ONLY',
            'evidence_record_correlated': consistent,
            'raw_artifacts_rehashed': False,
            'original_test_oracle_approved': False,
            'proves_current_component_requirement': False,
            'physical_hardware_test_proven': False,
            'physical_qualification_granted': False,
            'model_invoked': False,
            'outstanding_obligations': ['APPROVED_TEST_ORACLE_LINK',
                                        'COMPONENT_REQUIREMENT_BINDING',
                                        'RAW_ARTIFACT_VERIFICATION',
                                        'PHYSICAL_TARGET_QUALIFICATION']}


def verify_test(value: dict, read: Callable[[str, dict], dict]) -> dict:
    """Verify job/evidence bidirectional links, outcome, and source currency.

    The live Engineering Kernel is re-read; a model-supplied job/evidence object
    cannot produce a passing witness. Runs NO job and accepts NO caller-provided
    authorization bits. A second read detects mutable records during the check.
    """
    if value.get('type') != 'KernelJobInspection' or not isinstance(value.get('payload'), dict):
        raise TestWitnessError('VERIFY_TEST_REQUIRES_JOB_INSPECTION')
    candidate = value['payload']
    if candidate.get('schema') != JOB_SCHEMA or candidate.get('digest_profile') != PROFILE:
        raise TestWitnessError('INVALID_JOB_INSPECTION')
    id = _id(candidate.get('id'), 'job')
    if candidate.get('type') != 'KernelJobInspection':
        raise TestWitnessError('INVALID_INSPECTION_TYPE')
    job = _read(read, 'jobs.get', id)
    if job.get('id') != id or record_io.digest(job) != candidate.get('record_digest'):
        return _judgment(candidate, 'REJECTED', 'JOB_CHANGED_OR_FORGED')
    if job.get('state') not in TERMINAL:
        return _judgment(candidate, 'RECORD_INCOMPLETE', 'JOB_NOT_TERMINAL')
    evidence_id = job.get('evidence')
    if evidence_id is None:
        return _judgment(candidate, 'RECORD_INCOMPLETE', 'NO_LINKED_KERNEL_EVIDENCE')
    try:
        _id(evidence_id, 'evidence')
    except TestWitnessError:
        return _judgment(candidate, 'REJECTED', 'INVALID_LINKED_EVIDENCE_ID')
    if candidate.get('evidence_id') != evidence_id:
        return _judgment(candidate, 'REJECTED', 'EVIDENCE_LINK_CHANGED')
    evidence = _read(read, 'evidence.read', evidence_id)
    if (evidence.get('id') != evidence_id or evidence.get('job') != id or
        job.get('tool') not in TOOLS or evidence.get('tool') != job.get('tool') or
        not isinstance(job.get('revision'), str) or
        not re.fullmatch(r'[0-9a-f]{64}', job['revision']) or
        evidence.get('revision') != job['revision'] or
        evidence.get('candidate') != job.get('candidate') or
        evidence.get('state') != job.get('state')):
        return _judgment(candidate, 'REJECTED', 'EVIDENCE_JOB_IDENTITY_OR_REVISION_MISMATCH')
    environment = evidence.get('environment')
    if (not isinstance(environment, dict) or environment.get('physical_hardware') is not False or
        evidence.get('class') not in CLASSES):
        return _judgment(candidate, 'REJECTED', 'UNSUPPORTED_OR_PHYSICAL_EVIDENCE_CLASS')
    source_now = None
    try:
        current = read('project.inspect', {})
        source_now = current.get('revision') if isinstance(current, dict) else None
    except Exception:
        pass
    if job.get('candidate'):
        applicability = 'CANDIDATE_ONLY'
    elif isinstance(source_now, str) and source_now == job['revision']:
        applicability = 'MATCHES_CURRENT_PROJECT_REVISION'
    elif isinstance(source_now, str):
        applicability = 'HISTORICAL_SOURCE_REVISION'
    else:
        applicability = 'CURRENT_SOURCE_UNAVAILABLE'
    # No explicit tool outcome means zero exit code is only process success.
    exit_ok = type(evidence.get('exit_status')) is int and evidence['exit_status'] == 0
    explicit_pass = evidence.get('outcome') == 'PASS'
    if job.get('state') != 'Completed' or not exit_ok or evidence.get('outcome') in ('FAIL', 'FAILED', 'BLOCKED'):
        state, reason = 'RECORDED_CHECK_FAILURE', 'RECORDED_NONPASSING_KERNEL_RESULT'
    elif explicit_pass:
        state, reason = 'RECORDED_HOST_PASS', 'EXPLICIT_KERNEL_PASS_ONLY'
    else:
        state, reason = 'RECORDED_TOOL_SUCCESS_ONLY', 'EXIT_ZERO_IS_NOT_A_TEST_ORACLE'
    # Barrier against edits to mutable Kernel job/evidence records mid-operation.
    last_job = _read(read, 'jobs.get', id)
    last_ev = _read(read, 'evidence.read', evidence_id)
    if record_io.digest(last_job) != record_io.digest(job) or record_io.digest(last_ev) != record_io.digest(evidence):
        return _judgment(candidate, 'REJECTED', 'KERNEL_RECORD_DRIFT_DURING_VERIFICATION')
    if isinstance(source_now, str):
        # Freshness is a separate axis from the recorded host-test outcome.
        # Do not claim a CURRENT project binding across a changing source read.
        try:
            last_source = read('project.inspect', {})
            if not isinstance(last_source, dict) or last_source.get('revision') != source_now:
                return _judgment(candidate, 'REJECTED', 'CURRENT_SOURCE_DRIFT_DURING_VERIFICATION')
        except Exception:
            return _judgment(candidate, 'REJECTED', 'CURRENT_SOURCE_RECHECK_UNAVAILABLE')
    return _judgment(candidate, state, reason, job=job, evidence=evidence,
                     applicability=applicability, source_now=source_now)
