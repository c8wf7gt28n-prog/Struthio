from common import *
from workbench import reference_service as rs, intake_service as intake, pdf_service
k = Kernel(RUN / 'ws'); hold_processes()
ns_id = call(k, 'intake.namespaces')['namespaces'][0]['id']
with k.db() as db:
    ns = intake.namespace(db, ns_id, P.identity, False)
    for item, in db.execute('SELECT item FROM ref_sources WHERE ns=?', (ns_id,)).fetchall():
        original = intake.load(db, 'items', item)
        try:
            raw, decision = intake.eligible(db, ns, original, include_historical=True); ok = 'original eligible, %d bytes, decision %s' % (len(raw) if hasattr(raw, '__len__') else -1, decision['id'][:8])
        except Exception as e: ok = 'NOT eligible: %r' % e
        row = rs.source(db, ns, item)
        print(original['name'], '|', ok, '| sha matches:', row['source_sha256'] == original['sha256'], '| decision matches:', row['decision'] == decision['id'],
              '| extractor fingerprint matches this program:', row['extractor_hash'] == rs.fingerprint())
print('fingerprint of the index rows:', row['extractor_hash'][:16], '| this program + tools now:', rs.fingerprint()[:16])
import shutil as sh; print('pdftotext on this machine:', sh.which('pdftotext'))
