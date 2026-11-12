"""Change sets and imports: import profiles, archive limits, frozen previews, whole-batch review, copy apply, original publish
and undo, stale and outside edits, crash recovery, XLSX cell edits, owner scopes, model multi-file output and legacy rows."""
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET
import zipfile
from workbench.engineering_kernel import Kernel, Principal, operator
from workbench import cell_edits, change_sets, edit_storage, edit_model, local_brain, slate_context
from workbench.edit_checks import fixture, frozen_changes, invoke


def workbook():
    main = cell_edits.MAIN; rel = cell_edits.REL
    parts = {
        '[Content_Types].xml': b'<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/><Override PartName="/docProps/custom.xml" ContentType="application/vnd.openxmlformats-officedocument.custom-properties+xml"/></Types>',
        '_rels/.rels': b'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Target="xl/workbook.xml" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument"/><Relationship Id="rId2" Target="docProps/custom.xml" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/custom-properties"/></Relationships>',
        'xl/workbook.xml': ('<workbook xmlns="' + main + '" xmlns:r="' + rel + '"><sheets><sheet name="Clock" sheetId="1" r:id="rId1"/></sheets></workbook>').encode(),
        'xl/_rels/workbook.xml.rels': b'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Target="worksheets/sheet1.xml" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet"/><Relationship Id="rId2" Target="styles.xml" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles"/></Relationships>',
        'xl/worksheets/sheet1.xml': ('<worksheet xmlns="' + main + '"><dimension ref="A1:C2"/><sheetData><row r="1"><c r="A1" t="inlineStr"><is><t>Part</t></is></c><c r="B1" s="1"><v>330</v></c><c r="C1"><f>B1*2</f><v>660</v></c></row><row r="2"><c r="A2" t="inlineStr"><is><t>Clock</t></is></c></row></sheetData></worksheet>').encode(),
        'xl/styles.xml': b'<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><fonts count="1"><font><sz val="11"/><name val="Calibri"/></font></fonts><fills count="2"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill></fills><borders count="1"><border/></borders><cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs><cellXfs count="2"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/></cellXfs><cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>',
        'docProps/custom.xml': b'<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/custom-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes"><property fmtid="{D5CDD505-2E9C-101B-9397-08002B2CF9AE}" pid="2" name="Note"><vt:lpwstr>This exact metadata part stays unchanged.</vt:lpwstr></property></Properties>',
    }
    out = io.BytesIO()
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
        for name, value in parts.items(): z.writestr(name, value)
    return out.getvalue(), parts



HOLDS=[]


def setUpModule():
    # Nothing here may start a worker, submit a job or send a provider request (Graphite's test rule). The one exception is a
    # kernel whose own launch the protocol double has replaced (protocol_fixture.ProtocolWorker): it may queue a job row, which
    # the test then runs in this process against the loopback double; no worker can start from it.
    from workbench import clip, stacy_foundation
    from workbench.engineering_kernel import Kernel as HeldKernel
    real_submit=HeldKernel.submit
    def submit(kernel,*args,**kwargs):
        if 'launch' not in vars(kernel):raise AssertionError('No job submission')
        return real_submit(kernel,*args,**kwargs)
    # Whether the packaged Graphite seed is current is the release check's runtime section, not these behaviour tests: a seed
    # whose own files verify but whose declared sources were edited or left out since packaging (STALE, SOURCE_UNAVAILABLE)
    # reads as bound here, with its real seed_id. An absent or broken seed still refuses.
    real_seed=stacy_foundation.seed_status
    def seed_status(root):
        value=real_seed(root)
        return {**value,'state':'VERIFIED_SOURCE_BINDINGS'} if value.get('state') in ('STALE','SOURCE_UNAVAILABLE') else value
    for held in (patch.object(HeldKernel,'launch',side_effect=AssertionError('No worker launch')),patch.object(HeldKernel,'submit',submit),
            patch.object(clip,'_request',side_effect=AssertionError('No provider request')),patch.object(stacy_foundation,'seed_status',seed_status)):
        held.start();HOLDS.append(held)


def tearDownModule():
    while HOLDS:HOLDS.pop().stop()

class Changes(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='ledger-edit-test-'); self.addCleanup(temp.cleanup); self.base = Path(temp.name)
        env = patch.dict(os.environ, dict(os.environ)); env.start(); self.addCleanup(env.stop)
        self.kernel, self.owner, self.home, self.source, self.workspace = fixture(self.base, 'owner')
        home = patch('pathlib.Path.home', return_value=self.home); home.start(); self.addCleanup(home.stop)
        self.work = self.kernel.root / 'Files' / self.workspace['work']

    def call(self, op, args): return invoke(self.kernel, op, args, self.owner)
    def file(self, name): return self.call('changes.file', {'copy': self.workspace['id'], 'path': name})
    def propose(self, operations): return self.call('changes.propose', {'copy': self.workspace['id'], 'operations': operations})
    def apply(self, proposal, original=False): return self.call('changes.publish' if original else 'changes.apply', {'id': proposal['id'], 'expected_digest': proposal['content_digest']})

    def test_profiles_retain_config_and_duplicates_but_list_secrets_links_and_caches(self):
        (self.source / 'duplicate.txt').write_bytes((self.source / 'note.txt').read_bytes())
        (self.source / 'secret.txt').write_bytes(b'-----BEGIN ' + b'PRIVATE KEY-----\nnot-a-real-key\n')
        (self.source / '.git').mkdir(); (self.source / '.git' / 'history').write_text('omitted')
        (self.source / 'cache-link').symlink_to(self.base)
        os.mkfifo(self.source / 'pipe')
        preview = self.call('imports.preview', {'source': str(self.source), 'profile': 'CODE'})
        self.assertIn('.editorconfig', preview['files']); self.assertIn('.gitignore', preview['files'])
        self.assertTrue(any(e.get('duplicate_of') for e in preview['entries']))
        excluded = {e['path']: e['reason'] for e in preview['entries'] if e['state'] != 'INCLUDED'}
        self.assertEqual(excluded['secret.txt'], 'SENSITIVE_CONTENT'); self.assertIn('pipe', excluded); self.assertIn('cache-link/', excluded)
        self.assertNotIn('.env', preview['files']); self.assertIn('.git/', excluded)
        exported = self.call('changes.export', {'copy': self.workspace['id']})
        with zipfile.ZipFile(self.kernel.root / 'Files' / exported['export']) as archive:
            self.assertEqual(archive.read('.editorconfig'), b'root = true\n'); self.assertEqual(archive.read('.gitignore'), b'build/\n')
            metadata = next(name for name in archive.namelist() if name.startswith('.ledger-export-'))
            self.assertNotIn(str(self.source).encode(), archive.read(metadata))
        self.assertFalse(exported['originals_changed'])

    def test_archive_paths_duplicates_links_and_expansion_are_refused(self):
        for index, entries in enumerate([[('../escape.txt', b'bad')], [('A.txt', b'a'), ('a.txt', b'b')], [('large.txt', b'0' * 2097152)]]):
            path = self.home / ('bad' + str(index) + '.zip')
            with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as z:
                for name, data in entries: z.writestr(name, data)
            self.assertFalse(self.kernel.dispatch('imports.preview', {'source': str(path), 'profile': 'MIXED'}, self.owner)['ok'])
        path = self.home / 'link.zip'
        with zipfile.ZipFile(path, 'w') as z:
            info = zipfile.ZipInfo('link'); info.external_attr = (stat.S_IFLNK | 0o777) << 16; z.writestr(info, '../elsewhere')
        self.assertFalse(self.kernel.dispatch('imports.preview', {'source': str(path), 'profile': 'MIXED'}, self.owner)['ok'])
        self.assertFalse((self.home / 'escape.txt').exists())

    def test_preview_is_frozen_and_reviewed_limits_are_enforced(self):
        preview = self.call('imports.preview', {'source': str(self.source), 'profile': 'MIXED'})
        path = self.source / 'note.txt'; before = path.stat(); path.write_text(path.read_text().replace('blue', 'pink')); os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))
        self.assertFalse(self.kernel.dispatch('imports.accept', {'id': preview['id'], 'expected_digest': preview['content_digest']}, self.owner)['ok'])
        self.assertEqual(len(self.call('changes.workspaces', {})['workspaces']), 1)
        self.assertFalse(self.kernel.dispatch('imports.preview', {'source': str(self.source), 'profile': 'MIXED',
            'limits': {'files': 1, 'total_bytes': 1048576, 'file_bytes': 1048576}}, self.owner)['ok'])

    def test_whole_batch_review_copy_publish_and_undo_keep_masters_separate(self):
        proposal = frozen_changes(self.kernel, self.owner, self.workspace)
        review = self.call('changes.review', {'id': proposal['id']}); self.assertEqual(review['state'], 'READY_FOR_OWNER_REVIEW')
        self.assertTrue(any(c.get('adapter_report') for c in proposal['changes']))
        frozen = self.call('changes.content', {'id': proposal['id'], 'path': 'note.txt', 'side': 'AFTER'})
        self.assertEqual(frozen['text'], 'Clock needs black hands.\n')
        applied = self.apply(proposal); self.assertEqual(applied['state'], 'DONE')
        self.assertEqual((self.source / 'note.txt').read_text(), 'Clock needs blue hands.\n')
        original = self.call('changes.original.preview', {'copy': self.workspace['id']}); published = self.apply(original, True)
        self.assertEqual((self.source / 'note.txt').read_text(), 'Clock needs black hands.\n')
        self.assertFalse((self.source / 'old.txt').exists()); self.assertTrue((self.source / 'archive' / 'old.txt').is_file())
        self.call('changes.undo', {'id': published['id']})
        self.assertEqual((self.source / 'note.txt').read_text(), 'Clock needs blue hands.\n'); self.assertTrue((self.source / 'old.txt').is_file())
        self.assertEqual((self.source / '.env').read_text(), 'not copied\n')
        self.assertEqual(self.apply(original, True)['state'], 'UNDONE')

    def test_stale_target_aborts_before_any_batch_file_changes(self):
        proposal = frozen_changes(self.kernel, self.owner, self.workspace)
        table = self.work / 'parts.csv'; previous = table.stat(); table.write_text(table.read_text().replace('12,5', '19,5')); os.utime(table, ns=(previous.st_atime_ns, previous.st_mtime_ns))
        self.assertFalse(self.kernel.dispatch('changes.apply', {'id': proposal['id'], 'expected_digest': proposal['content_digest']}, self.owner)['ok'])
        self.assertEqual((self.work / 'note.txt').read_text(), 'Clock needs blue hands.\n'); self.assertFalse((self.work / 'draft.md').exists())
        self.assertIn('19,5', table.read_text())

    def test_original_sibling_changes_and_later_outside_edits_block_publish_or_undo(self):
        proposal = self.propose([{'op': 'WRITE', 'path': 'note.txt', 'base_sha256': self.file('note.txt')['sha256'], 'text': 'black\n'}]); self.apply(proposal)
        original = self.call('changes.original.preview', {'copy': self.workspace['id']})
        (self.source / 'old.txt').write_text('An outside edit\n')
        self.assertFalse(self.kernel.dispatch('changes.publish', {'id': original['id'], 'expected_digest': original['content_digest']}, self.owner)['ok'])
        self.assertEqual((self.source / 'note.txt').read_text(), 'Clock needs blue hands.\n')
        (self.source / 'old.txt').write_text('Retain this version.\n')
        blocked = self.call('changes.commits', {'copy': self.workspace['id']})['commits'][0]
        self.call('changes.recover', {'id': blocked['id'], 'action': 'ROLLBACK'})
        original = self.call('changes.original.preview', {'copy': self.workspace['id']}); published = self.apply(original, True)
        (self.source / 'note.txt').write_text('Later outside note\n')
        self.assertFalse(self.kernel.dispatch('changes.undo', {'id': published['id']}, self.owner)['ok'])
        self.assertEqual((self.source / 'note.txt').read_text(), 'Later outside note\n')

    def test_intent_only_interruption_rolls_back_and_symlink_parent_is_refused(self):
        proposal = self.propose([{'op': 'CREATE', 'path': 'new.txt', 'text': 'new'}])
        with patch.object(change_sets, 'CRASH_AT', 'INTENT'):
            with self.assertRaises(change_sets.Crash): self.apply(proposal)
        commit = self.call('changes.commits', {'copy': self.workspace['id']})['commits'][0]
        self.call('changes.recover', {'id': commit['id'], 'action': 'ROLLBACK'}); self.assertFalse((self.work / 'new.txt').exists())
        from workbench import work_trail
        work_trail.hold(self.kernel, self.owner)
        held = self.propose([{'op': 'CREATE', 'path': 'held.txt', 'text': 'not yet'}])
        self.assertFalse(self.kernel.dispatch('changes.apply', {'id': held['id'], 'expected_digest': held['content_digest']}, self.owner)['ok'])
        self.assertFalse((self.work / 'held.txt').exists())
        self.call('ledger.work.resume', {})
        blocked = self.call('changes.commits', {'copy': self.workspace['id']})['commits'][0]
        self.call('changes.recover', {'id': blocked['id'], 'action': 'ROLLBACK'})
        proposal = self.propose([{'op': 'CREATE', 'path': 'sub/new.txt', 'text': 'new'}]); outside = self.base / 'Outside'; outside.mkdir()
        def race(stage):
            if stage == 'INTENT': (self.work / 'sub').symlink_to(outside, target_is_directory=True)
        with patch.object(change_sets, 'checkpoint', side_effect=race):
            self.assertFalse(self.kernel.dispatch('changes.apply', {'id': proposal['id'], 'expected_digest': proposal['content_digest']}, self.owner)['ok'])
        self.assertFalse((outside / 'new.txt').exists())

    def test_exchange_retains_unexpected_displaced_bytes_instead_of_erasing_them(self):
        proposal = self.propose([{'op': 'DELETE', 'path': 'note.txt', 'base_sha256': self.file('note.txt')['sha256']}])
        original = edit_storage.rename_linux
        def race(fd, source, target, exchange=False):
            if source == 'note.txt':
                changed = os.open(source, os.O_WRONLY | os.O_TRUNC | os.O_NOFOLLOW, dir_fd=fd)
                os.write(changed, b'Outside race retained\n'); os.fsync(changed); os.close(changed)
            return original(fd, source, target, exchange)
        with patch.object(edit_storage, 'rename_linux', side_effect=race):
            self.assertFalse(self.kernel.dispatch('changes.apply', {'id': proposal['id'], 'expected_digest': proposal['content_digest']}, self.owner)['ok'])
        commit = self.call('changes.commits', {'copy': self.workspace['id']})['commits'][0]; observed = self.call('changes.commit', {'id': commit['id']})
        self.assertEqual(observed['observed'][0]['state'], 'CONFLICT')
        self.assertEqual((self.work / observed['entries'][0]['temp']).read_bytes(), b'Outside race retained\n')
        self.assertEqual((self.source / 'note.txt').read_text(), 'Clock needs blue hands.\n')

    def test_xlsx_preserves_other_parts_styles_and_formulas_without_fabricating_cache(self):
        raw, parts = workbook(); (self.work / 'table.xlsx').write_bytes(raw)
        value = self.file('table.xlsx'); self.assertEqual(value['sheets'], ['Clock'])
        proposal = self.propose([{'op': 'CELLS', 'path': 'table.xlsx', 'base_sha256': value['sha256'], 'sheet': 'Clock',
            'cells': [{'cell': 'B1', 'old': {'kind': 'NUMBER', 'value': '330'}, 'new': {'kind': 'NUMBER', 'value': '470'}}]}])
        self.apply(proposal)
        with zipfile.ZipFile(self.work / 'table.xlsx') as z:
            self.assertEqual(z.read('xl/styles.xml'), parts['xl/styles.xml']); self.assertEqual(z.read('docProps/custom.xml'), parts['docProps/custom.xml'])
            tree = ET.fromstring(z.read('xl/worksheets/sheet1.xml')); cells = {c.get('r'): c for c in tree.iter(cell_edits.Q('c'))}
            self.assertEqual(cells['B1'].get('s'), '1'); self.assertEqual(cells['B1'].findtext(cell_edits.Q('v')), '470')
            self.assertEqual(cells['C1'].findtext(cell_edits.Q('f')), 'B1*2'); self.assertIsNone(cells['C1'].find(cell_edits.Q('v')))
        bad = io.BytesIO()
        with zipfile.ZipFile(bad, 'w') as z:
            for name, data in parts.items(): z.writestr(name, data)
            z.writestr('xl/vbaProject.bin', b'not executed')
        with self.assertRaises(ValueError): cell_edits.describe(bad.getvalue(), '.xlsx')

    def test_owner_scopes_frozen_digests_and_old_copy_routes_cannot_bypass_review(self):
        proposal = self.propose([{'op': 'CREATE', 'path': 'safe.txt', 'text': 'safe'}])
        read = Principal('owner'); worker = Principal('owner', frozenset({'read', 'execute'}))
        for principal in (read, worker):
            self.assertFalse(self.kernel.dispatch('changes.apply', {'id': proposal['id'], 'expected_digest': proposal['content_digest']}, principal)['ok'])
        for op, args in [('changes.workspace', {'id': self.workspace['id']}), ('changes.review', {'id': proposal['id']}),
            ('changes.content', {'id': proposal['id'], 'path': 'safe.txt', 'side': 'AFTER'}), ('copies.get', {'id': self.workspace['id']})]:
            self.assertFalse(self.kernel.dispatch(op, args, operator('other'))['ok'])
        self.assertFalse(self.kernel.dispatch('changes.apply', {'id': proposal['id'], 'expected_digest': '0' * 64}, self.owner)['ok'])
        self.assertFalse(self.kernel.dispatch('changes.publish', {'id': proposal['id'], 'expected_digest': proposal['content_digest']}, self.owner)['ok'])
        self.assertFalse(self.kernel.dispatch('copies.propose', {'id': self.workspace['id']}, self.owner)['ok'])

    def test_model_multi_file_output_is_frozen_only_when_complete_and_never_applied(self):
        path = Path(__file__).resolve().parent / 'protocol_fixture.py'
        spec = importlib.util.spec_from_file_location('protocol_fixture_four', path); module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        note = self.file('note.txt'); old = self.file('old.txt')
        candidate = {'text': 'Two exact draft changes.', 'changes': [
            {'path': 'note.txt', 'base_sha256': note['sha256'], 'edits': [{'start': 12, 'end': 16, 'old': 'blue', 'new': 'black'}]},
            {'path': 'old.txt', 'base_sha256': old['sha256'], 'edits': [{'start': 0, 'end': 6, 'old': 'Retain', 'new': 'Keep'}]}]}
        with module.ProtocolWorker(self.kernel, self.base) as worker:
            worker.override = json.dumps(candidate); worker.finish = 'length'
            job = self.call('changes.ask', {'copy': self.workspace['id'], 'goal': 'Update the two notes.', 'paths': ['note.txt', 'old.txt']})
            with self.assertRaisesRegex(ValueError, 'INCOMPLETE'): edit_model.run_job(self.kernel, job)
            self.assertEqual(self.call('changes.workspace', {'id': self.workspace['id']})['proposals'], [])
            worker.finish = 'stop'; job = self.call('changes.ask', {'copy': self.workspace['id'], 'goal': 'Update the two notes.', 'paths': ['note.txt', 'old.txt']})
            result = edit_model.run_job(self.kernel, job); self.assertFalse(result['applied'])
            self.assertEqual((self.work / 'note.txt').read_text(), 'Clock needs blue hands.\n')
            proposal = self.call('changes.review', {'id': result['proposal_id']})['proposal']; self.assertEqual(proposal['provenance']['origin'], 'SLATE')
            self.assertEqual(len(proposal['changes']), 2)
        # The earlier single-file reasoning route can join the same review flow,
        # but cannot borrow an identical file in another registered copy.
        from workbench import slate_reasoning
        with module.ProtocolWorker(self.kernel, self.base):
            address = 'files:' + self.workspace['work'] + '/note.txt'
            context = self.call('slate.context.create', {'question': 'Replace blue with black.', 'addresses': [address], 'include_seed': False})
            job = self.call('slate.ask', {'context': context['id'], 'task': 'EDIT', 'target_address': address})
            result = slate_reasoning.run_job(self.kernel, job)
            local_brain.record_io.write_json(self.kernel.root / 'build' / 'brain' / 'runs' / job['id'] / 'result.json', result)
            job['state'] = 'Completed'; self.kernel.save('jobs', job)
            converted = self.call('changes.from_slate', {'copy': self.workspace['id'], 'job': job['id']})
            self.assertEqual(converted['provenance']['job'], job['id'])
            self.assertEqual((self.work / 'note.txt').read_text(), 'Clock needs blue hands.\n')
            preview = self.call('imports.preview', {'source': str(self.source), 'profile': 'MIXED'})
            other = self.call('imports.accept', {'id': preview['id'], 'expected_digest': preview['content_digest']})
            self.assertFalse(self.kernel.dispatch('changes.from_slate', {'copy': other['id'], 'job': job['id']}, self.owner)['ok'])

    def test_legacy_rows_and_full_hash_change_detection_survive_and_unknown_versions_are_refused(self):
        from workbench import working_folders, working_copies
        legacy_root = self.base / 'Legacy'; legacy_root.mkdir()
        with patch.object(edit_storage, 'ensure', return_value=None):
            legacy = Kernel(legacy_root); legacy_copy = invoke(legacy, 'copies.start', {'source': str(self.source)}, self.owner)
        Kernel(legacy_root); saved = invoke(Kernel(legacy_root), 'copies.get', {'id': legacy_copy['id']}, self.owner)
        self.assertEqual(saved['id'], legacy_copy['id']); self.assertFalse(saved.get('profiled', False))
        with working_copies.opened(legacy) as db: row = working_copies.the_copy(db, saved['id']); base = working_folders.load(legacy, row['base'])['files']
        path = self.source / 'note.txt'; before = path.stat(); path.write_text(path.read_text().replace('blue', 'pink')); os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))
        self.assertNotEqual(working_folders.now_digests(self.source, base)['note.txt'], base['note.txt']['sha'])
        with legacy.db() as db: db.execute('INSERT INTO edit_migrations VALUES(?,?,?)', (99, 'unsupported', 0))
        with self.assertRaisesRegex(ValueError, 'EDIT_MIGRATION_UNSUPPORTED'): Kernel(legacy_root)


if __name__ == '__main__': unittest.main()
