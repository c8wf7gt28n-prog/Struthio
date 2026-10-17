"""Installer tests (workbench/setup_arc1.py, workbench/launch.py, INSTALL_ARC1.cmd).

Runs real installs into temporary folders (HOME redirected) with the Linux
platform layer. The Windows layer (shortcuts, Apps & Features, uninstaller
.cmd, winget) is checked through fakes: it has NOT been run on Windows here.

    python3 tests/test_r10_installer.py
"""
import io
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from workbench import launch, setup_arc1 as setup  # noqa: E402


class FakePlatform:
    def __init__(self):
        self.calls = []

    def create_shortcuts(self, spec, desktop):
        self.calls.append(('shortcuts', spec, desktop))
        return ['/fake/Start Menu/ARC-1 Workbench.lnk'] + (['/fake/Desktop/ARC-1 Workbench.lnk'] if desktop else [])

    def remove_shortcuts(self, paths):
        self.calls.append(('remove', list(paths)))

    def register(self, target, size_kb):
        self.calls.append(('register', str(target), size_kb))

    def unregister(self):
        self.calls.append(('unregister',))

    def uninstaller(self, target, base_python):
        return setup.PosixPlatform().uninstaller(target, base_python)

    def can_install_compiler(self):
        return False


class InstallerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.home = Path(cls.tmp.name) / 'home'
        cls.home.mkdir()
        cls.env = mock.patch.dict(os.environ, {'HOME': str(cls.home), 'XDG_DATA_HOME': str(cls.home / 'share'),
                                               'USERPROFILE': str(cls.home)})
        cls.env.start()
        # A clean source tree, as a user would have after extracting the ZIP.
        cls.source = Path(cls.tmp.name) / 'extracted' / 'arc1'
        shutil.copytree(ROOT, cls.source, ignore=shutil.ignore_patterns('.git', '__pycache__', 'build', 'reports'))
        cls.target = Path(cls.tmp.name) / 'Programs' / 'ARC-1 Workbench'

    @classmethod
    def tearDownClass(cls):
        cls.env.stop()
        cls.tmp.cleanup()

    def do_install(self, **kw):
        out = io.StringIO()
        plat = FakePlatform()
        report = setup.install(self.source, self.target, assume_yes=True, skip_qt=True, launch=False,
                               ui=setup.Console(True, out), plat=plat, **kw)
        return report, plat, out.getvalue()

    def test_1_fresh_install(self):
        report, plat, out = self.do_install()
        app = self.target / 'app'
        self.assertTrue(setup.looks_like_arc1(app))
        info = setup.read_install(self.target)
        self.assertEqual(info['version'], setup.VERSION)
        self.assertEqual(info['manifest'], setup.manifest_of(app))
        self.assertFalse(any('__pycache__' in k or '/build/' in k for k in info['manifest']))
        self.assertTrue(setup.venv_python(self.target).exists())
        kind, spec, desktop = plat.calls[1]
        self.assertEqual((kind, spec['args'], desktop), ('shortcuts', '-m workbench.launch', True))
        self.assertEqual(spec['workdir'], str(app))
        self.assertIn(('register', str(self.target), report and plat.calls[2][2]), plat.calls)
        self.assertTrue((self.target / 'Uninstall ARC-1 Workbench.sh').is_file())
        self.assertIn('[6/6] Self-check', out)
        self.assertEqual(report['doctor_exit'], 0, out)
        self.assertIsNone(report['backup'])

    def test_2_upgrade_without_changes_makes_no_backup(self):
        report, plat, out = self.do_install()
        self.assertIsNone(report['backup'])
        self.assertIn('reusing', out)             # the private Python is kept across upgrades
        self.assertIn(('remove', ['/fake/Start Menu/ARC-1 Workbench.lnk', '/fake/Desktop/ARC-1 Workbench.lnk']),
                      plat.calls)

    def test_3_upgrade_keeps_your_work(self):
        app = self.target / 'app'
        edited = app / 'firmware' / 'f133' / 'src' / 'lcd_status.c'
        edited.write_text(edited.read_text() + '\n/* my change */\n')
        mine = app / 'examples' / 'my_notes.txt'
        mine.write_text('notes')
        report, _, out = self.do_install()
        backup = Path(report['backup'])
        self.assertTrue(backup.is_relative_to(self.home))
        self.assertIn('my change', (backup / 'firmware/f133/src/lcd_status.c').read_text())
        self.assertEqual((backup / 'examples/my_notes.txt').read_text(), 'notes')
        self.assertNotIn('my change', edited.read_text())   # the new version is installed
        self.assertIn('firmware/f133/src/lcd_status.c', out)
        self.assertIn('2 file(s) you changed are backed up', out)

    def test_4_failed_copy_leaves_installation_untouched(self):
        before = setup.manifest_of(self.target / 'app')
        with mock.patch.object(setup, 'copy_app', side_effect=OSError('disk full')):
            with self.assertRaises(OSError):
                self.do_install()
        self.assertEqual(setup.manifest_of(self.target / 'app'), before)
        report, _, _ = self.do_install()             # a retry cleans up and succeeds
        self.assertFalse((self.target / 'app.incoming').exists())

    def test_5_refusals(self):
        with self.assertRaises(setup.SetupError):
            setup.install(self.source, self.source / 'inside', assume_yes=True, skip_qt=True, launch=False,
                          ui=setup.Console(True, io.StringIO()), plat=FakePlatform())
        with self.assertRaises(setup.SetupError):
            setup.install(self.home, self.target, assume_yes=True, skip_qt=True, launch=False,
                          ui=setup.Console(True, io.StringIO()), plat=FakePlatform())
        with mock.patch('builtins.input', return_value='n'):
            with self.assertRaises(setup.SetupError):
                setup.install(self.source, self.target, skip_qt=True, launch=False,
                              ui=setup.Console(False, io.StringIO()), plat=FakePlatform())

    def test_6_uninstall_backs_up_then_removes(self):
        app = self.target / 'app'
        (app / 'examples' / 'keep_me.c').write_text('int x;')
        plat = FakePlatform()
        with mock.patch('builtins.input', return_value='n'):   # default answer is "no"
            with self.assertRaises(setup.SetupError):
                setup.uninstall(self.target, ui=setup.Console(False, io.StringIO()), plat=plat)
        self.assertTrue(app.exists())
        out = io.StringIO()
        self.assertTrue(setup.uninstall(self.target, assume_yes=False, ui=setup.Console(True, out), plat=plat))
        self.assertFalse(self.target.exists())
        self.assertIn(('unregister',), plat.calls)
        backups = sorted(setup.backup_root().glob('*before uninstall*'))
        self.assertTrue(backups and (backups[-1] / 'examples' / 'keep_me.c').is_file())
        with self.assertRaises(setup.SetupError):
            setup.uninstall(self.target, assume_yes=True, ui=setup.Console(True, io.StringIO()), plat=plat)


class WindowsLayerTests(unittest.TestCase):
    """The Windows-only code, exercised with fakes (not a Windows run)."""

    def test_shortcuts_pass_paths_as_environment_not_script_text(self):
        seen = {}

        def runner(argv, timeout, env=None, cwd=None):
            seen['argv'], seen['env'] = argv, env
            return 0, 'C:\\Users\\a\\Start Menu\\ARC-1 Workbench.lnk\r\n'
        plat = setup.WindowsPlatform(runner)
        evil = 'C:\\x\'; Remove-Item -Recurse C:\\ ;\'\\pythonw.exe'
        links = plat.create_shortcuts({'target': evil, 'args': '-m workbench.launch', 'workdir': 'C:\\app',
                                       'icon': 'C:\\app\\workbench\\arc1.ico', 'icon_png': ''}, True)
        self.assertEqual(links, ['C:\\Users\\a\\Start Menu\\ARC-1 Workbench.lnk'])
        self.assertEqual(seen['argv'][0], 'powershell.exe')
        self.assertNotIn(evil, ' '.join(seen['argv']))
        self.assertEqual((seen['env']['ARC1_TARGET'], seen['env']['ARC1_DESKTOP']), (evil, '1'))

    def test_shortcut_failure_is_reported(self):
        plat = setup.WindowsPlatform(lambda *a, **k: (1, 'COM error'))
        with self.assertRaises(setup.SetupError):
            plat.create_shortcuts({'target': 't', 'args': '', 'workdir': 'w', 'icon': 'i'}, False)

    def test_apps_and_features_entry(self):
        v = setup.WindowsPlatform().uninstall_values(Path('C:/Users/a/AppData/Local/Programs/ARC-1 Workbench'), 1234)
        self.assertEqual((v['DisplayName'], v['DisplayVersion'], v['NoModify'], v['EstimatedSize']),
                         ('ARC-1 Workbench', setup.VERSION, 1, 1234))
        self.assertTrue(v['UninstallString'].startswith('cmd.exe /c ""'))
        self.assertTrue(v['DisplayIcon'].endswith('arc1.ico'))

    def test_uninstaller_runs_a_temp_copy(self):
        name, text = setup.WindowsPlatform().uninstaller(Path('C:/T'), 'C:\\Python312\\python.exe')
        self.assertEqual(name, 'Uninstall ARC-1 Workbench.cmd')
        self.assertIn('\r\n', text)
        self.assertIn('copy /y "%~dp0app\\workbench\\setup_arc1.py" "%TEMP%', text)
        self.assertIn('cd /d "%TEMP%"', text)          # the install folder must not be the working directory
        self.assertIn('uninstall --target', text)

    def test_compiler_found_off_path(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / 'clang.exe').write_text('')
            with mock.patch.object(setup, 'WIN_COMPILER_DIRS', [d]), \
                    mock.patch.object(setup.shutil, 'which', return_value=None):
                cc, extra = setup.find_compiler(windows=True)
                self.assertEqual((cc, extra), (os.path.join(d, 'clang.exe'), d))
                self.assertEqual(setup.find_compiler(windows=False), (None, None))


class BootstrapAndLauncherTests(unittest.TestCase):
    def test_install_cmd_is_crlf_and_hands_over_to_setup(self):
        raw = (ROOT / 'INSTALL_ARC1.cmd').read_bytes()
        self.assertNotIn(b'\n', raw.replace(b'\r\n', b''), 'INSTALL_ARC1.cmd must use CRLF line endings')
        text = raw.decode('ascii')
        for needle in (':find_python', 'call :find_python', 'goto have_python', 'Python.Python.3.12 --scope user',
                       '-I "%~dp0workbench\\setup_arc1.py" install --source "%~dp0."',
                       'This file was started from inside the ZIP'):
            self.assertIn(needle, text)

    def test_launcher_adds_only_existing_compiler_folders(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.dict(os.environ, {'PATH': '/usr/bin'}):
            extra = launch.extend_path({'extra_path': [d, '/does/not/exist', 5]})
            self.assertEqual(extra, [d])
            self.assertTrue(os.environ['PATH'].startswith(d + os.pathsep))

    def test_launcher_falls_back_to_tk_without_qt(self):
        with mock.patch.dict(sys.modules, {'PySide6': None}):
            self.assertEqual(launch.choose_frontend(), 'tk')


if __name__ == '__main__':
    unittest.main(verbosity=2)
