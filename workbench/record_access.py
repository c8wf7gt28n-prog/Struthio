"""Checked reads over existing records. Job payloads and history are unchanged."""
from sdk.cli.arc1cli.record_visibility import private_job,job_readable

ERROR='Record unavailable to this caller'
PRIVATE_OUTPUTS=frozenset({'brain','intake','references','knowledge','study','investigations'})

def readable(kernel,table,row,principal):
    if table=='jobs':return job_readable(row,principal.identity)
    if table!='evidence':return True  # Existing engineering candidates are project records.
    job=None
    if row.get('job'):
        try:job=kernel.record('jobs',row['job'])
        # Malformed shared engineering evidence remains inspectable so staC
        # can reject its correlation. Private orphans always fail closed.
        except (ValueError,TypeError):return not private_job(row)
        # An evidence row cannot disguise the linked private job as public.
        if private_job(job) and job.get('evidence') not in (None,row.get('id')):return False
        if not job_readable(job,principal.identity):return False
    if private_job(row) and (not job or not private_job(job)):
        return False # Orphaned or contradictory private evidence is not shared.
    return True

def read(kernel,table,ident,principal):
    from .engineering_kernel import KernelError
    try:row=kernel.record(table,ident)
    except (ValueError,TypeError):raise KernelError(ERROR) from None
    if not readable(kernel,table,row,principal):raise KernelError(ERROR)
    return row

def listing(kernel,table,principal,limit=100):
    import json
    result=[]
    # Filter before the visible result limit; hidden records must not starve
    # an owner's accessible history. Iterator use avoids materializing all rows.
    with kernel.db() as db:
        for raw, in db.execute('SELECT payload FROM '+table+' ORDER BY rowid DESC'):
            row=json.loads(raw)
            if readable(kernel,table,row,principal):result.append(row)
            if len(result)>=limit:break
    return result

def file_read(kernel,name,principal):
    from .engineering_kernel import KernelError
    # Normalize and reject traversal/symlinks through the existing path guard.
    path=kernel.safe(name)
    parts=path.relative_to(kernel.root).parts
    if len(parts)>=2 and parts[0]=='build' and parts[1] in PRIVATE_OUTPUTS:
        if len(parts)<5 or parts[2]!='runs':raise KernelError(ERROR)
        row=read(kernel,'jobs',parts[3],principal)
        if not private_job(row) or row.get('owner')!=principal.identity:raise KernelError(ERROR)
    return path
