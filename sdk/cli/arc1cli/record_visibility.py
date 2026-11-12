"""Record sharing policy 1. No caller-supplied visibility flag grants access."""
PRIVATE_FAMILIES=('brain.','intake.','references.','knowledge.','study.','memory.','research.','network.')  # network.: a capture's filter, command and counts are this computer's traffic (HATCH DESK D5)

def private_job(job):
    return isinstance(job.get('tool'),str) and job['tool'].startswith(PRIVATE_FAMILIES)

def job_readable(job,identity):
    return not private_job(job) or (isinstance(job.get('owner'),str) and job['owner']==identity)

# This is the reviewed PWA operation set, not every present/future local read.
# Expanding it requires a transport and object-authorization review.
REMOTE_OPERATIONS=frozenset({
 'capabilities','project.inspect','project.authority','files.read','files.search',
 'jobs.list','jobs.get','jobs.submit','jobs.cancel','jobs.pause','jobs.resume',
 'evidence.list','evidence.read','evidence.compare','candidates.list','candidates.diff',
 'candidates.authorize_execution','candidates.reject','candidates.accept',
 'clip.authorize','clip.submit','clip.prepare','clip.overview','clip.inspect','clip.context',
 'clip.propose','clip.test','clip.finish','agent.handoff','tasks.plan','tasks.templates',
 'hardware.coverage.inspect','hardware.proof.inspect','hardware.proof.result','hardware.proof.trace',
 'repairs.inspect','repairs.authorize'})
