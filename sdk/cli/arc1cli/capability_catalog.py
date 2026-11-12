"""Portable, conservative capability assessment; no IO or execution authority."""
from __future__ import annotations

SCHEMA = 'arc.capability-assessment/1'
DIMENSIONS = ('declared', 'installed', 'available', 'permitted', 'qualified')


def assess(*, declared, source_present, required_inputs, project_attached,
           scope_eligible, native_state='NOT_REQUIRED', requires_arguments=False,
           mode='Engineer'):
    """Describe observed prerequisites, never predict success or grant authority.

    Qualification intentionally has no caller-controlled success flag. A future
    evidence adapter must validate its own source/tool/profile-bound receipt.
    """
    if type(declared) is not bool or source_present not in (True, False, None):
        raise ValueError('CAPABILITY_DECLARATION_INVALID')
    if type(project_attached) is not bool or type(scope_eligible) is not bool:
        raise ValueError('CAPABILITY_CONTEXT_INVALID')
    if native_state not in ('NOT_REQUIRED','DETECTED','MISSING','INCOMPATIBLE','INVALID','UNASSESSED'):
        raise ValueError('CAPABILITY_NATIVE_STATE_INVALID')
    missing = sorted(set(required_inputs))
    if any(not isinstance(x, str) or len(x)>500 for x in missing):
        raise ValueError('CAPABILITY_INPUTS_INVALID')
    installed = 'SOURCE_PRESENT' if source_present is True else 'SOURCE_MISSING' if source_present is False else 'UNRESOLVED'
    permission = 'SCOPE_ELIGIBLE' if scope_eligible else 'OUTSIDE_SCOPE'
    reasons=[]
    if not declared: reasons.append('NOT_DECLARED')
    if source_present is not True: reasons.append(installed)
    if not project_attached: reasons.append('PROJECT_NOT_ATTACHED')
    if missing: reasons.append('MISSING_INPUTS')
    if not scope_eligible: reasons.append('OUTSIDE_SCOPE')
    if native_state in ('MISSING','INCOMPATIBLE','INVALID'): reasons.append('NATIVE_'+native_state)
    available = 'BLOCKED' if reasons else 'CONDITIONAL' if requires_arguments or native_state in ('DETECTED','UNASSESSED') else 'PASSIVE_PREREQUISITES_PRESENT'
    if requires_arguments: reasons.append('ARGUMENTS_AND_RUNTIME_CHECKS_REQUIRED')
    if native_state=='DETECTED': reasons.append('NATIVE_VERSION_COMPATIBILITY_UNMEASURED')
    if native_state=='UNASSESSED': reasons.append('NATIVE_PREREQUISITES_UNASSESSED')
    return {'schema':SCHEMA,
            'declared':{'state':'REGISTERED' if declared else 'NOT_DECLARED'},
            'installed':{'state':installed,'native':native_state,'basis':'PASSIVE_FILE_CHECKS_ONLY'},
            'available':{'state':available,'reasons':reasons,'missing_inputs':missing},
            'permitted':{'state':permission,'mode':mode,'basis':'OPERATION_SCOPE_ONLY',
                         'notice':'Argument, owner, source, tool and effect checks still run at dispatch.'},
            'qualified':{'state':'UNASSESSED','basis':'NO_QUALIFICATION_RECEIPT_ADAPTER',
                         'notice':'Presence, permission and a successful read are not qualification.'}}


def summary(assessment):
    """A short UI description; full five-dimensional record remains available."""
    available=assessment['available']
    if available['state']=='BLOCKED': return 'Blocked · '+', '.join(available['reasons'][:2]).lower().replace('_',' ')
    if available['state']=='CONDITIONAL': return 'Conditional · checks required'
    return 'Prerequisites present · unassessed'
