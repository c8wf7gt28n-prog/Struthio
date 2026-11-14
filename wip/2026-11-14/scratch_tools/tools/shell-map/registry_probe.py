"""Read-only: compare the live registry with docs/GRAPHITE_0.1_REGISTRY.json, then simulate ONE added read-only operation
and ONE added setting (in memory only) and print which record sections would differ. Writes nothing in the tree."""
import copy, hashlib, json, os, sys, tempfile
from pathlib import Path
PROGRAM = Path(sys.argv[1]).resolve()
RUN = Path(tempfile.mkdtemp(prefix='graphite-regprobe-')); (RUN / 'home').mkdir()
os.environ.update(HOME=str(RUN / 'home'), ARC1_WORKBENCH_CONFIG_HOME=str(RUN / 'profile'), ARC_LEDGER_CONCERN=str(RUN / 'home' / 'Concern'))
os.chdir(RUN); sys.dont_write_bytecode = True
sys.path.insert(0, str(PROGRAM)); sys.path.insert(0, str(PROGRAM / 'tools'))
import record_registry as rr
from check_hatch import record_sections
record = rr.read(PROGRAM)
inventory, tools, handlers, specs = rr.live_sources()
live = rr.snapshot((inventory, tools, handlers, specs))
def brief(sections):
    return {k: (v['state'], v['differences']) for k, v in sections.items()}
print('LIVE vs RECORD:', json.dumps(brief(record_sections(live, record))))
print('live counts:', live['counts'], '| record counts:', record['counts'])
# one added read-only operation, served by a module with FIELDS + dispatch (the handler_map route)
inv2 = copy.deepcopy(inventory)
row = {'operation': 'ledger.field', 'scope': 'read', 'arguments': {'type': 'object', 'properties': {'limit': {'type': 'integer', 'minimum': 1, 'maximum': 500}}, 'required': [], 'additionalProperties': False}}
inv2['operations'] = sorted(inv2['operations'] + [row], key=lambda r: r['operation'])
inv2['schema_digest'] = hashlib.sha256(json.dumps(inv2['operations'], sort_keys=True, separators=(',', ':')).encode()).hexdigest()
h2 = dict(handlers); h2['ledger.field'] = {'path': 'workbench/field.py', 'symbol': 'dispatch', 'basis': 'DECLARED_FIELDS_ROUTE'}
one_op = rr.snapshot((inv2, tools, h2, specs))
print('ONE READ OP ADDED:', json.dumps(brief(record_sections(one_op, record))))
changed = sorted(k for k in one_op if one_op[k] != record.get(k))
print('  top-level record keys that would change:', changed, '| counts ->', one_op['counts'])
# one added setting
from workbench.settings_registry import spec
s2 = list(specs) + [spec('appearance.field_probe', 'Field probe', 'Appearance', True, 'boolean', 'probe', application='immediate', store='Session field_probe')]
one_setting = rr.snapshot((inventory, tools, handlers, s2))
print('ONE SETTING ADDED:', json.dumps(brief(record_sections(one_setting, record))))
print('  top-level record keys that would change:', sorted(k for k in one_setting if one_setting[k] != record.get(k)), '| counts ->', one_setting['counts'])
# how an existing small read op looks in the live schema and the record
from workbench.engineering_cli import schemas
print('schemas()["ledger.browse"]:', json.dumps(schemas()['ledger.browse']))
print('record op row ledger.browse:', json.dumps(record['operations']['ledger.browse']), '| adapter:', record['adapters']['operations']['ledger.browse'])
print('record adapters.settings[reading.reduce_motion]:', record['adapters']['settings']['reading.reduce_motion'])
