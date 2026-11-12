"""Portable presentation of independent job facts; no approval or execution."""

def describe(job,evidence=None,*,current=None,review='NOT_SUBMITTED'):
    e=evidence or {};code=e.get('exit_status')
    outcome=e.get('outcome') or ('PROCESS_SUCCEEDED' if code==0 else 'PROCESS_FAILED' if code is not None else 'PENDING')
    physical=e.get('environment',{}).get('physical_hardware')
    return {'lifecycle':job['state'],'outcome':outcome,'evidence_class':e.get('class','UNASSESSED'),
        'physical_target':'BLOCKED' if physical is False else 'RECORDED_PHYSICAL' if physical is True else 'UNASSESSED',
        'currentness':'NO_EVIDENCE' if not evidence else 'CURRENT_INPUTS' if current is True else 'STALE' if current is False else 'UNAVAILABLE',
        'review':review}
