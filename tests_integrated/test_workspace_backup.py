"""Workspace backup and restore (LEDGER.sh backup create), working copies and doctor.probe: restore keeps notes, empty folders,
dotfiles and working copies and skips model weights; existing targets, corrupt or unsafe backups, links and an active
coordinator are refused; publication is atomic; probing initialises nothing."""
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from workbench import doctor, locations, workspace_backup as backup
from workbench.engineering_kernel import Kernel, operator
from sdk.cli.arc1cli.concern_catalog import Catalog



HOLDS=[]


def setUpModule():
    # Nothing here may start a worker, submit a job or send a provider request (Graphite's test rule). The one exception is a
    # kernel whose own launch the protocol double has replaced (protocol_fixture.ProtocolWorker): it may queue a job row, which
    # the test then runs in this process against the loopback double; no worker can start from it.
    from workbench import clip
    from workbench.engineering_kernel import Kernel as HeldKernel
    real_submit=HeldKernel.submit
    def submit(kernel,*args,**kwargs):
        if 'launch' not in vars(kernel):raise AssertionError('No job submission')
        return real_submit(kernel,*args,**kwargs)
    for held in (patch.object(HeldKernel,'launch',side_effect=AssertionError('No worker launch')),patch.object(HeldKernel,'submit',submit),
            patch.object(clip,'_request',side_effect=AssertionError('No provider request'))):
        held.start();HOLDS.append(held)


def tearDownModule():
    while HOLDS:HOLDS.pop().stop()

class StageOne(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='ledger-stage-one-test-')
        self.addCleanup(self.temp.cleanup); self.base = Path(self.temp.name)
        self.root = self.base / 'Office'; self.profile = self.base / 'profile'
        self.environment = patch.dict(os.environ, {'ARC1_WORKBENCH_CONFIG_HOME':str(self.profile), 'ARC_LEDGER_WORKSPACE':str(self.root)})
        self.environment.start(); self.addCleanup(self.environment.stop)

    def fixture(self):
        locations.office(self.root); Kernel(self.root)
        catalog = Catalog(self.profile / 'concern/catalog.sqlite3')
        ident = catalog.create('note', 'My exact idea'); catalog.save_note(ident, 'Keep these words.\n', 0)
        folder = self.root / 'Files'; folder.mkdir()
        (folder / '.editorconfig').write_text('root = true\n')
        (folder / 'Empty').mkdir(); (folder / 'Working copies').mkdir()
        (folder / 'Working copies/note.txt').write_text('Candidate, not the master.\n')
        (folder / 'model.gguf').write_bytes(b'not actual weights')
        return ident

    def test_complete_restore_preserves_note_files_empty_folder_and_model_policy(self):
        ident = self.fixture()
        with tempfile.TemporaryDirectory(prefix='ledger-stage-one-master-', dir=Path.home()) as source_dir:
            source = Path(source_dir) / 'master.txt'; source.write_text('Original.\n')
            kernel = Kernel(self.root)
            started = kernel.dispatch('copies.start', {'source':str(source), 'for_slate':True}, operator())
            self.assertTrue(started['ok'], started)
            copy = started['result']; (self.root / 'Files' / copy['work']).write_text('Proposed.\n')
            frozen = kernel.dispatch('copies.propose', {'id':copy['id']}, operator())
            self.assertTrue(frozen['ok'], frozen)
            saved = backup.create(self.root, self.base / 'backup')
            self.assertEqual(source.read_text(), 'Original.\n')
        self.assertTrue(any('model' in r['reason'] for r in saved['skipped']))
        result = backup.restore(self.base / 'backup', self.base / 'Restored')
        out = Path(result['workspace']); profile = Path(result['profile'])
        self.assertEqual(Catalog(profile / 'concern/catalog.sqlite3').get(ident)['note']['body'], 'Keep these words.\n')
        self.assertEqual((out / 'Files/Working copies/note.txt').read_text(), 'Candidate, not the master.\n')
        self.assertTrue((out / 'Files/Empty').is_dir())
        self.assertEqual((out / 'Files/.editorconfig').read_text(), 'root = true\n')
        self.assertFalse((out / 'Files/model.gguf').exists())
        self.assertTrue((self.root / 'Files/model.gguf').exists())
        copied = Kernel(out).dispatch('copies.get', {'id':copy['id']}, operator())
        self.assertTrue(copied['ok'], copied)
        self.assertEqual(copied['result']['proposal']['id'], frozen['result']['id'])
        self.assertEqual((out / 'Files' / copied['result']['work']).read_text(), 'Proposed.\n')

    def test_existing_restore_target_and_corrupt_backup_leave_originals_alone(self):
        self.fixture(); backup.create(self.root, self.base / 'backup')
        target = self.base / 'Existing'; target.mkdir(); (target / 'mine').write_text('untouched')
        with self.assertRaises(ValueError): backup.restore(self.base / 'backup', target)
        self.assertEqual((target / 'mine').read_text(), 'untouched')
        (self.base / 'backup' / 'workspace' / 'Files' / '.editorconfig').write_text('damaged')
        with self.assertRaises(ValueError): backup.restore(self.base / 'backup', self.base / 'New')
        self.assertFalse((self.base / 'New').exists())

    def test_active_coordinator_is_refused(self):
        self.fixture(); lock = self.root / '.ledger/service/coordinator.lock'; lock.parent.mkdir(exist_ok=True)
        with lock.open('a+') as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaises(backup.state_backup.StateBusy): backup.create(self.root, self.base / 'backup')
        self.assertFalse((self.base / 'backup').exists())

    def test_link_and_nested_backup_are_refused(self):
        self.fixture(); (self.root / 'Files/link').symlink_to(self.root / 'Files/.editorconfig')
        with self.assertRaises(ValueError): backup.create(self.root, self.base / 'backup')
        self.assertFalse((self.base / 'backup').exists())
        with self.assertRaises(ValueError): backup.create(self.root, self.root / 'backup')

    def test_unsafe_manifest_and_linked_parent_are_refused_before_publication(self):
        self.fixture(); backup.create(self.root, self.base / 'backup')
        manifest = self.base / 'backup/BACKUP.json'; record = json.loads(manifest.read_text())
        record['files'][0]['path'] = '../escape'; manifest.write_text(json.dumps(record))
        with self.assertRaises(ValueError): backup.restore(self.base / 'backup', self.base / 'New')
        self.assertFalse((self.base / 'escape').exists())
        link = self.base / 'linked'; link.symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(ValueError): backup.fresh(link / 'New')

    def test_atomic_publication_will_not_replace_a_racing_empty_directory(self):
        stage = self.base / 'stage'; destination = self.base / 'racer'
        stage.mkdir(); (stage / 'content').write_text('ours'); destination.mkdir()
        with self.assertRaises(OSError): backup.publish(stage, destination)
        self.assertTrue((stage / 'content').is_file()); self.assertEqual(list(destination.iterdir()), [])

    def test_doctor_does_not_initialize_workspace_or_profile(self):
        result = doctor.probe(self.root)
        self.assertFalse(self.root.exists()); self.assertFalse(self.profile.exists())
        self.assertEqual(result['kernel_database']['state'], 'NOT_CREATED')
        self.assertEqual(result['network_calls'], 0)


if __name__ == '__main__': unittest.main()
