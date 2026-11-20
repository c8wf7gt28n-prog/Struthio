"""The record paths the Kernel's views and exchanges read and write (workbench/record_io.project_path): a name inside the
project, never a hidden one, never through a link or out of the folder; Graphite's own state only under .ledger and only when
the caller asks for it. 0.8.4: written for a planted bug that let a hidden folder under .ledger through. Run alone:

  python -B -m unittest -v tests_integrated.test_record_paths
"""
import os
import tempfile
import unittest
from pathlib import Path

from workbench import record_io


class RecordPaths(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='graphite-record-paths-')
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        (self.root / 'build').mkdir()
        (self.root / 'build' / 'net.json').write_text('{}')

    def refused(self, name, private=False, must_exist=False):
        with self.assertRaises(ValueError) as caught:
            record_io.project_path(self.root, name, must_exist, private)
        return str(caught.exception).split(':')[0]

    def test_a_project_name_is_read_where_it_is(self):
        self.assertEqual(record_io.project_path(self.root, 'build/net.json'), self.root / 'build' / 'net.json')
        self.assertEqual(self.refused('build/gone.json', must_exist=True), 'MISSING_SOURCE')

    def test_graphites_own_state_is_reached_only_when_asked_and_never_a_hidden_name_in_it(self):
        self.assertEqual(record_io.project_path(self.root, '.ledger/console/run/state.json', False, private=True),
                         self.root / '.ledger' / 'console' / 'run' / 'state.json')
        self.assertEqual(self.refused('.ledger/console/run/state.json'), 'PRIVATE_PATH')
        for name in ('.ledger/.keys/x', '.ledger/console/.run/state.json', '.ledger/console/run/.state.json', '.git/config',
                     'build/.secret', '.env'):
            self.assertEqual(self.refused(name, private=True), 'PRIVATE_PATH', name)

    def test_names_that_leave_the_folder_or_hide_in_it_are_refused(self):
        for name in ('', '/etc/passwd', 'build/../../x', './build/net.json', 'build//net.json', 'build\\net.json', 'C:x', 'a\x00b', None):
            self.assertEqual(self.refused(name), 'INVALID_PATH', name)
        outside = tempfile.TemporaryDirectory(prefix='graphite-outside-')
        self.addCleanup(outside.cleanup)
        os.symlink(outside.name, self.root / 'linked')
        self.assertEqual(self.refused('linked/x.json'), 'PATH_ESCAPE')
        os.symlink(self.root / 'build', self.root / 'inside')
        self.assertEqual(self.refused('inside/net.json'), 'SYMLINK_PATH')


if __name__ == '__main__':
    unittest.main()
