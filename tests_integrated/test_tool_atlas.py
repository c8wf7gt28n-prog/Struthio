"""Atlas integration boundaries; no model generations or native probe jobs."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from workbench import tool_atlas as atlas, capability_catalog, stac_bridge
from workbench.engineering_kernel import Kernel, CAPABILITIES, TOOLS, Principal, operator
from workbench.engineering_cli import schemas


class AtlasTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.root = Path(self.temp.name)
        self.env = patch.dict(os.environ, {'ARC1_WORKBENCH_CONFIG_HOME': str(self.root/'profile'),
                                          'ARC_LEDGER_CONCERN': str(self.root/'Concern')})
        self.env.start(); (self.root/'workspace').mkdir(); self.kernel = Kernel(self.root/'workspace'); self.owner = operator('owner')

    def tearDown(self):
        self.env.stop(); self.temp.cleanup()

    def call(self, op, args=None, principal=None):
        value = self.kernel.dispatch(op, args or {}, principal or self.owner)
        self.assertTrue(value['ok'], value); return value['result']

    def test_full_registry_has_stable_ids_no_duplicates_and_exact_schemas(self):
        rows = atlas.entries(self.kernel, self.owner)
        self.assertEqual(len(rows), len(CAPABILITIES) + len(TOOLS))
        self.assertEqual(len({(r['kind'], r['name']) for r in rows}), len(rows))
        for row in rows:
            self.assertEqual(row['name'], row['legacy_id'])
            if row['kind'] == 'OPERATION': self.assertEqual(row['contract']['arguments'], schemas()[row['name']])
        self.assertTrue(all(r['qualification'] == 'UNTESTED' for r in rows))

    def test_search_vocabulary_and_paging_do_not_change_execution_eligibility(self):
        for query, expected in [('KiCad', 'cad.drc'), ('Python', 'lab.python'), ('ngspice', 'spice.qualify')]:
            value = self.call('atlas.lookup', {'query': query, 'kind': 'JOB_TOOL'})
            self.assertIn(expected, [r['name'] for r in value['entries']])
        first = self.call('atlas.lookup', {'limit': 2})
        second = self.call('atlas.lookup', {'limit': 2, 'offset': 2})
        self.assertTrue(first['has_more']); self.assertNotEqual(first['entries'], second['entries'])
        self.assertEqual(first['native_invocations'], 0)

    def test_snapshot_is_private_and_rechecks_adapter_source(self):
        value = self.call('atlas.passport.save', {'name': 'atlas.lookup'})
        args = {'id': value['id']}
        self.assertEqual(self.call('atlas.passport.get', args)['freshness'], 'BINDING_UNCHANGED')
        self.assertFalse(self.kernel.dispatch('atlas.passport.get', args, operator('other'))['ok'])
        self.assertEqual(self.call('atlas.passports.list', principal=operator('other'))['passports'], [])
        source = capability_catalog.source
        def changed(root, name):
            row = source(root, name)
            return {**row, 'sha256': '0'*64} if name == 'workbench/tool_atlas.py' else row
        with patch.object(capability_catalog, 'source', side_effect=changed):
            current = self.call('atlas.passport.get', args)
        self.assertEqual(current['freshness'], 'STALE'); self.assertEqual(current['qualification'], 'UNTESTED')
        self.assertEqual(current['snapshot'], value)

    def test_native_binary_change_invalidates_snapshot_without_running_it(self):
        native = self.root/'unfamiliar-kicad'; native.write_bytes(b'synthetic binary identity')
        with patch.object(atlas.shutil, 'which', return_value=str(native)), patch('subprocess.Popen') as spawned:
            saved = self.call('atlas.passport.save', {'name': 'cad.drc', 'kind': 'JOB_TOOL'})
            native.write_bytes(b'changed synthetic binary identity')
            result = self.call('atlas.passport.get', {'id': saved['id']})
            self.assertEqual(result['freshness'], 'STALE'); spawned.assert_not_called()

    def test_session_change_is_stale_and_does_not_promote_qualification(self):
        saved = self.call('atlas.passport.save', {'name': 'atlas.lookup'})
        changed = {**atlas.host(), 'session_digest': 'new-session'}
        with patch.object(atlas, 'host', return_value=changed):
            result = self.call('atlas.passport.get', {'id': saved['id']})
        self.assertEqual(result['freshness'], 'STALE'); self.assertEqual(result['qualification'], 'UNTESTED')
        with patch.object(atlas, 'host', return_value={**changed, 'session_digest': None}):
            unbound = self.call('atlas.passport.save', {'name': 'atlas.lookup'})
            self.assertEqual(self.call('atlas.passport.get', {'id': unbound['id']})['freshness'], 'HOST_BINDING_UNAVAILABLE')

    def test_scope_and_tutor_mode_block_snapshot_writes(self):
        args = {'name': 'atlas.lookup'}
        for p in (Principal('reader'), Principal('tutor', self.owner.scopes, mode='Tutor')):
            self.assertFalse(self.kernel.dispatch('atlas.passport.save', args, p)['ok'])
            self.call('atlas.operation_schema', args, p)
        self.assertEqual(self.call('atlas.passports.list')['passports'], [])

    def test_invocation_checks_real_contract_and_never_submits_job(self):
        reader = Principal('reader')
        result = self.call('atlas.invocation', {'operation': 'jobs.cancel', 'arguments': {'id': 'a'*32}}, reader)
        self.assertFalse(result['scope_eligible']); self.assertFalse(result['runtime_authorization'])
        self.assertEqual(result['state'], 'SCHEMA_CHECKED_NOT_DISPATCHED')
        for arguments in ({}, {'id': 4}, {'id': 'a'*32, 'shell': 'anything'}):
            self.assertFalse(self.kernel.dispatch('atlas.invocation', {'operation': 'jobs.cancel', 'arguments': arguments}, self.owner)['ok'])
        with self.kernel.db() as db: self.assertEqual(db.execute('SELECT count(*) FROM jobs').fetchone()[0], 0)

    def test_stac_forwards_caller_and_rejects_extra_stages_or_shell_syntax(self):
        program = 'atlas | operation atlas.lookup'
        ir = stac_bridge.compile_program(program)
        self.assertEqual(ir['ir']['operation'], 'atlas.operation_schema')
        actual = self.call('stac.run', {'program': program}, Principal('reader'))
        expected = self.call('atlas.operation_schema', {'name': 'atlas.lookup'}, Principal('reader'))
        self.assertEqual(actual['result'], expected)
        self.assertEqual(self.call('stac.run', {'program': 'atlas | find "KiCad"'})['result']['matches'],
                         self.call('atlas.lookup', {'query': 'KiCad'})['matches'])
        for program in ('atlas | operation atlas.lookup | run', 'atlas; echo bad', 'atlas | shell "rm something"'):
            self.assertFalse(self.kernel.dispatch('stac.run', {'program': program}, self.owner)['ok'])


if __name__ == '__main__': unittest.main()
