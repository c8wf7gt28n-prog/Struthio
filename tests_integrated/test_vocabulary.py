"""AGENT-01 (owner decision D28): Ingress and Egress are the names for the folders files come in through and leave from.

Mechanical checks of the names and the once-only moves; no Qt, no jobs, no model."""
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from workbench import locations, files_service, receiving, navigator_catalog, cabinet  # noqa: E402


class IngressTests(unittest.TestCase):
    def test_names(self):
        self.assertEqual(locations.INGRESS, 'Ingress');self.assertEqual(locations.OLDER_INGRESS, ('Arrived', 'Inbox'))
        self.assertEqual(receiving.INBOX, 'Ingress');self.assertIs(locations.arrived, locations.ingress)
        self.assertEqual(locations.ARRIVED, 'Ingress')  # the 4.2 constant now names the same folder

    def test_fresh_workspace_gets_ingress(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = locations.ingress(temp, create=True)
            self.assertEqual(folder, Path(temp) / 'Ingress');self.assertTrue(folder.is_dir())
            self.assertEqual(sorted(p.name for p in Path(temp).iterdir()), ['Ingress'])

    def test_arrived_moves_once_without_overwriting(self):
        with tempfile.TemporaryDirectory() as temp:
            old = Path(temp) / 'Arrived';old.mkdir();(old / 'a.txt').write_text('a');(old / 'b.txt').write_text('b')
            folder = locations.ingress(temp, create=True)
            self.assertEqual(folder.name, 'Ingress');self.assertFalse(old.exists())
            self.assertEqual(sorted(p.name for p in folder.iterdir()), ['a.txt', 'b.txt'])
            # a second call changes nothing
            self.assertEqual(locations.ingress(temp), folder);self.assertEqual(sorted(p.name for p in folder.iterdir()), ['a.txt', 'b.txt'])

    def test_both_older_folders_merge_and_names_already_present_stay(self):
        with tempfile.TemporaryDirectory() as temp:
            inbox = Path(temp) / 'Inbox';inbox.mkdir();(inbox / 'old.txt').write_text('inbox')
            arrived = Path(temp) / 'Arrived';arrived.mkdir();(arrived / 'old.txt').write_text('arrived');(arrived / 'new.txt').write_text('n')
            folder = locations.ingress(temp, create=True)
            self.assertEqual((folder / 'old.txt').read_text(), 'arrived');self.assertEqual((folder / 'new.txt').read_text(), 'n')
            self.assertTrue(inbox.is_dir());self.assertEqual((inbox / 'old.txt').read_text(), 'inbox')  # kept, not overwritten, until it is empty
            self.assertFalse(arrived.exists())


class FakeKernel:
    def __init__(self, root):self.root = Path(root)


class EgressTests(unittest.TestCase):
    def test_names(self):
        self.assertEqual(files_service.EXPORTS, 'Egress');self.assertEqual(files_service.OLD_EXPORTS, 'Exports')
        self.assertEqual(cabinet.TRANSFERS[1]['destination'], 'files:Egress')

    def test_root_creates_egress_and_moves_exports_once(self):
        with tempfile.TemporaryDirectory() as temp:
            kernel = FakeKernel(Path(temp) / 'workspace');(kernel.root / 'Files' / 'Exports' / 'Pills').mkdir(parents=True)
            (kernel.root / 'Files' / 'Exports' / 'Pills' / 'x.pill').write_bytes(b'x')
            root = files_service.root(kernel)
            self.assertEqual(root, kernel.root / 'Files')
            self.assertFalse((root / 'Exports').exists());self.assertTrue((root / 'Egress' / 'Pills' / 'x.pill').is_file())
            self.assertEqual(sorted(p.name for p in root.iterdir()), ['.trash', '.versions', 'Egress', 'Slate'])

    def test_reserved_words_name_egress(self):
        with tempfile.TemporaryDirectory() as temp:
            kernel = FakeKernel(temp);files_service.root(kernel)
            from workbench.engineering_kernel import operator
            with self.assertRaises(ValueError) as caught:
                files_service.dispatch(kernel, 'files.rename', {'path': 'Egress', 'name': 'Out'}, operator())
            self.assertIn('Egress', str(caught.exception))


class WordsTests(unittest.TestCase):
    def test_library_rows(self):
        sections = dict(navigator_catalog.paper_sections(()))
        self.assertEqual(sections['ARRIVE'][0][:2], ('Ingress', 'office'));self.assertEqual(sections['ARRIVE'][0][3], 'inbox')  # counter key kept: a shortcut contract
        self.assertEqual(sections['FILES'][-1][:2], ('Egress', 'files:Egress'));self.assertEqual(sections['FILES'][-1][3], 'exports')
        self.assertEqual(navigator_catalog.SECTION_ROLES['ARRIVE'], 'ARRIVAL_VIEW')

    def test_no_old_words_in_owner_facing_rows(self):
        from workbench import rooms, shell2
        import inspect
        for module in (rooms, shell2):
            text = inspect.getsource(module)
            for word in ("'Arrived'", "'Exports'"):self.assertFalse(word in text, '%s still says %s' % (module.__name__, word))  # no source dump on failure


if __name__ == '__main__':
    unittest.main()
