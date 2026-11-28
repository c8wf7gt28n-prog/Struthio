"""1.1 W1, a Windows hand's keys and DOS words (PLAN_1.1.md, W1).

Acceptance first: 60 DOS lines each give the expected Debian command; the file clipboard cuts three files and pastes them
with one Undo; the Fluxbox keys file is written and graphite-do speaks to a running window's door. Then what never runs
(rm, format, chkdsk), deleting for good (your press only), Properties, the clock, the Terminal's own use of DOS words.

Only Fluxbox on a real session can show the keys reaching graphite-do from another app; here graphite-do is called
directly against the door, as the key would call it.

Run alone:  python3 -B -m unittest -v tests_integrated.test_windows_hand
"""
import json, os, subprocess, sys, tempfile, time, unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

ROOT = Path(__file__).resolve().parents[1]
PLACES = {'C': '/', 'D': '/media/me/STICK', 'E': '/media/me/PHOTOS'}
HAS_TREE = lambda name: '/usr/bin/' + name
NO_TREE = lambda name: None
SIXTY = [  # (DOS, the Debian command shown)
    ('dir', 'ls -l'), ('DIR', 'ls -l'), ('dir /w', 'ls'), ('dir /b', 'ls -1'), ('dir /s', 'ls -lR'), ('dir /a', 'ls -la'),
    ('dir /s /a', 'ls -laR'), ('dir/s', 'ls -lR'), ('dir /s /b', 'find .'), ('dir /s /b *.txt', "find . -name '*.txt'"),
    ('dir /od', 'ls -ltr'), ('dir /o-d', 'ls -lt'), ('dir /os', 'ls -lSr'), ('dir *.pdf', 'ls -l *.pdf'), ('dir C:\\', 'ls -l /'),
    ('dir D:\\Letters', 'ls -l /media/me/STICK/Letters'), ('dir "My Files"', "ls -l 'My Files'"), ('dir /ad', 'ls -ld */'),
    ('cd..', 'cd ..'), ('cd\\', 'cd /'), ('cd \\Users', 'cd /Users'), ('cd D:\\Photos', 'cd /media/me/STICK/Photos'),
    ('D:', 'cd /media/me/STICK'), ('e:', 'cd /media/me/PHOTOS'), ('C:', 'cd /'), ('cls', 'clear'),
    ('copy a.txt b.txt', 'cp -n a.txt b.txt'), ('copy /y a.txt b.txt', 'cp a.txt b.txt'), ('copy notes.txt D:\\', 'cp -n notes.txt /media/me/STICK'),
    ('xcopy docs backup /s /e', 'cp -rn docs/. backup'), ('xcopy docs backup /s /e /y', 'cp -r docs/. backup'),
    ('move a.txt Old', 'mv -n a.txt Old'), ('move /y a.txt Old', 'mv a.txt Old'), ('del a.txt', 'gio trash a.txt'),
    ('del /q *.tmp', 'gio trash *.tmp'), ('erase old.log', 'gio trash old.log'), ('ren a.txt b.txt', 'mv -n a.txt b.txt'),
    ('ren *.txt *.bak', 'for f in *.txt; do mv -n -- "$f" "${f%.txt}.bak"; done'), ('md Letters\\2026', 'mkdir -p Letters/2026'),
    ('rd Old', 'rmdir Old'), ('rd /s /q Old', 'gio trash Old'), ('type notes.txt', 'cat notes.txt'), ('more < notes.txt', 'more < notes.txt'),
    ('tree /a', 'tree -d --charset=ascii'), ('tree /f', 'tree'), ('attrib +r a.txt', 'chmod a-w a.txt'), ('attrib -r a.txt', 'chmod u+w a.txt'),
    ('ver', 'cat /etc/debian_version && uname -sr'), ('date', "date '+%A %d %B %Y'"), ('time /t', 'date +%H:%M'),
    ('set', 'env | sort'), ('set HO', "env | grep -i '^HO'"), ('path', 'echo $PATH'), ('echo %HOME%', 'echo "${HOME}"'),
    ('find "invoice" notes.txt', "grep -F invoice notes.txt"), ('find /i /n "tax" a.txt', "grep -Fin tax a.txt"),
    ('dir | find "pdf"', 'ls -l | grep -F pdf'), ('ipconfig', 'ip -brief address'), ('ipconfig /all', 'ip address'),
    ('ping debian.org', 'ping -c 4 debian.org'), ('ping -n 2 debian.org', 'ping -c 2 debian.org'), ('ping -t debian.org', 'ping debian.org'),
    ('tasklist', 'ps -e -o pid,rss,comm --sort=comm'), ('taskkill /pid 4242', 'kill 4242'), ('taskkill /f /im firefox.exe', 'pkill -9 -x firefox'),
    ('dir /?', 'ls --help'), ('echo hello > nul', 'echo hello > /dev/null'),
]


class DosWords(unittest.TestCase):
    def test_sixty_dos_lines_give_the_expected_debian_command(self):
        from workbench import dos_words as dw
        self.assertGreaterEqual(len(SIXTY), 60)
        wrong = []
        for dos, debian in SIXTY:
            said = dw.translate(dos, cwd='/home/me', places=PLACES, which=HAS_TREE)
            got = said.command if said is not None else None
            if got != debian:wrong.append((dos, debian, got))
        self.assertEqual(wrong, [])
        said = dw.translate('dir /s', cwd='/home/me', places=PLACES)
        self.assertEqual(said.shown(), 'dir /s \u2192 ls -lR')      # the line above the output, as the plan shows it

    def test_a_debian_line_goes_to_the_shell_as_typed(self):
        from workbench import dos_words as dw
        for line in ('ls -la', 'find . -name "*.txt"', 'echo hi', 'cd docs', 'ping -c 3 debian.org', 'time ls', 'type ls',
                     'set -e', 'mkdir new', 'tree', 'grep -r tax .', 'cat a.txt | sort', 'more notes.txt', 'date -u'):
            self.assertIsNone(dw.translate(line, cwd='/home/me', places=PLACES, which=HAS_TREE), line)
        self.assertEqual(dw.translate('tree', cwd='/home/me', places=PLACES, which=NO_TREE), None)
        self.assertEqual(dw.translate('tree /f', cwd='/home/me', places=PLACES, which=NO_TREE).command, 'find .')

    def test_nothing_in_dos_words_runs_rm_and_format_and_chkdsk_are_only_explained(self):
        from workbench import dos_words as dw
        for dos, _ in SIXTY + [('del /s /q *.bak', ''), ('rd /s Old', ''), ('rmdir /s /q Old', '')]:
            said = dw.translate(dos, cwd='/home/me', places=PLACES, which=HAS_TREE)
            self.assertNotRegex(said.run + ' ', r'(^|[;&| ])rm ', dos)
        for dos in ('del a.txt', 'rd /s /q Old', 'del /s /q *.bak'):
            said = dw.translate(dos, cwd='/home/me', places=PLACES);self.assertEqual((said.kind, said.run), ('trash', ''), dos)
        self.assertTrue(dw.translate('del *.*', cwd='/home/me', places=PLACES).ask)
        self.assertFalse(dw.translate('del /q *.*', cwd='/home/me', places=PLACES).ask)
        for dos in ('format D:', 'chkdsk C:', 'chkdsk', 'fdisk', 'diskpart', 'date 01-12-2026', 'ipconfig /release', 'attrib +h a.txt'):
            said = dw.translate(dos, cwd='/home/me', places=PLACES)
            self.assertEqual((said.kind, said.run), ('explain', ''), dos);self.assertTrue(said.words, dos)
        self.assertIn('never run', dw.translate('format D:', places=PLACES).words)
        said = dw.translate('F:', cwd='/home/me', places=PLACES)
        self.assertEqual(said.kind, 'explain');self.assertIn('no drive F:', said.words)

    def test_drive_letters_are_the_mounted_drives_in_order(self):
        from workbench import dos_words as dw
        mounts = ('/dev/sda2 / ext4 rw 0 0\n/dev/sdb1 /media/me/STICK vfat rw 0 0\nproc /proc proc rw 0 0\n'
                  '/dev/sdc1 /media/me/MY\\040PHOTOS exfat rw 0 0\n/dev/sdd1 /mnt/backup ext4 rw 0 0\n')
        self.assertEqual(dw.drives(mounts), {'C': '/', 'D': '/media/me/STICK', 'E': '/media/me/MY PHOTOS', 'F': '/mnt/backup'})
        here = dw.drives(mounts)
        self.assertEqual(dw.translate('cd\\', cwd='/media/me/STICK/Letters', places=here).target, '/media/me/STICK')
        self.assertEqual(dw.translate('dir E:\\', cwd='/home/me', places=here).command, "ls -l '/media/me/MY PHOTOS'")

    def test_the_terminal_shows_the_debian_command_then_runs_it_or_only_shows_it(self):
        from workbench import dos_words as dw
        with tempfile.TemporaryDirectory() as temp:
            ran, said = [], []
            console = SimpleNamespace(working_dir=lambda: Path(temp), sign_text=lambda: '~ $', say=lambda html, echo=None: said.append((html, echo)),
                                      run_shell=lambda line, extra_env=None: ran.append((line, extra_env)), link=lambda label, fn: label, host=None)
            with patch.object(dw, 'drives', return_value=PLACES):
                self.assertTrue(dw.in_terminal(console, 'dir /s', mode='on'))
                self.assertEqual(ran, [('ls -lR', None)]);self.assertIn('dir /s \u2192 ls -lR', said[0][0])
                self.assertTrue(dw.in_terminal(console, 'set NAME=Me', mode='on'))
                self.assertTrue(dw.in_terminal(console, 'type a.txt', mode='on'))
                self.assertEqual(ran[-1], ('cat a.txt', {'NAME': 'Me'}))
                ran.clear();said.clear()
                self.assertTrue(dw.in_terminal(console, 'dir /s', mode='show'))
                self.assertEqual(ran, []);self.assertIn('nothing was run', said[-1][0])
                self.assertFalse(dw.in_terminal(console, 'dir /s', mode='off'))
                self.assertFalse(dw.in_terminal(console, 'ls -la', mode='on'))


class FileClipboard(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory();base = Path(self.temp.name)
        self.home = base / 'home';self.home.mkdir();(base / 'ws').mkdir()
        self.env = patch.dict(os.environ, {'HOME': str(self.home), 'XDG_DATA_HOME': str(self.home / '.local/share'), 'XDG_CONFIG_HOME': str(self.home / '.config')})
        self.env.start()
        from workbench.engineering_kernel import Kernel, operator
        self.kernel = Kernel(base / 'ws');self.owner = operator()

    def tearDown(self):
        self.env.stop();self.temp.cleanup()

    def test_three_files_cut_and_pasted_with_one_undo(self):
        from workbench import windows_hand as wh
        downloads = self.home / 'Downloads';invoices = self.home / 'Invoices';downloads.mkdir();invoices.mkdir()
        names = ['invoice-1.pdf', 'invoice-2.pdf', 'invoice-3.pdf']
        for n in names:(downloads / n).write_text(n)
        clip = wh.FileClipboard()
        self.assertEqual(clip.hold([downloads / n for n in names], 'move'), '3 files cut: paste them in a folder.')
        answer = clip.paste(self.kernel, invoices, self.owner)
        self.assertTrue(answer.get('ok'), answer);result = answer['result']
        self.assertEqual(result['done'], 3);self.assertEqual(sorted(p.name for p in invoices.iterdir()), names)
        self.assertEqual(list(downloads.iterdir()), []);self.assertEqual(clip.paths, [], 'a cut is pasted once')
        back = self.kernel.dispatch('files.batch_undo', {'batch': result['batch']}, self.owner)      # ONE Undo for the paste
        self.assertTrue(back.get('ok'), back);self.assertEqual(back['result']['back'], 3)
        self.assertEqual(sorted(p.name for p in downloads.iterdir()), names);self.assertEqual(list(invoices.iterdir()), [])

    def test_a_copy_pastes_again_and_never_writes_over(self):
        from workbench import windows_hand as wh
        (self.home / 'a.txt').write_text('one');target = self.home / 'Copies';target.mkdir()
        clip = wh.FileClipboard();clip.hold([self.home / 'a.txt'], 'copy')
        for _ in range(2):self.assertTrue(clip.paste(self.kernel, target, self.owner).get('ok'))
        self.assertEqual(len(list(target.iterdir())), 2, 'the second paste took a free name');self.assertEqual((self.home / 'a.txt').read_text(), 'one')
        self.assertEqual(wh.FileClipboard().words(), 'Nothing is held to paste.')

    def test_delete_for_good_is_your_press_only_and_only_in_your_home(self):
        from workbench.engineering_kernel import Principal
        from workbench import home_reach as hr
        doomed = self.home / 'old.txt';doomed.write_text('x')
        with patch.object(hr, 'in_her_work', return_value=True):
            refused = self.kernel.dispatch('files.delete_for_good', {'path': str(doomed)}, self.owner)
        self.assertFalse(refused.get('ok'));self.assertIn('your press only', str(refused['error']));self.assertTrue(doomed.exists())
        outside = self.kernel.dispatch('files.delete_for_good', {'path': '/etc/hostname'}, self.owner)
        self.assertFalse(outside.get('ok'))
        home_itself = self.kernel.dispatch('files.delete_for_good', {'path': str(self.home)}, self.owner)
        self.assertFalse(home_itself.get('ok'));self.assertTrue(self.home.exists())
        done = self.kernel.dispatch('files.delete_for_good', {'path': str(doomed)}, self.owner)
        self.assertTrue(done.get('ok'), done);self.assertFalse(doomed.exists());self.assertIn('cannot be put back', done['result']['words'])

    def test_properties_say_what_the_file_is_in_words(self):
        from workbench import windows_hand as wh
        f = self.home / 'letter.txt';f.write_text('hello');os.chmod(f, 0o640)
        rows = dict(wh.properties(f, query=lambda kind: 'invented-editor.desktop' if kind == 'text/plain' else ''))
        self.assertEqual(rows['Name'], 'letter.txt');self.assertIn('TXT file', rows['Kind']);self.assertEqual(rows['Size'], '5 bytes')
        self.assertEqual(rows['Where'], '~');self.assertTrue(rows['Who may'].startswith('You may read and change it; others in the group'))
        self.assertIn('everyone else may neither read nor change it', rows['Who may'])
        self.assertEqual(rows['Opens with'], 'invented-editor')
        self.assertEqual([r[0] for r in wh.properties(self.home)][:3], ['Name', 'Kind', 'Size'])

    def test_the_two_settings_are_kept_and_show_keys_is_on_at_first(self):
        from workbench import windows_hand as wh
        self.assertEqual(wh.read(), {'show_keys': True, 'dos_words': 'on'})
        wh.write(show_keys=False, dos_words='show');self.assertEqual(wh.read(), {'show_keys': False, 'dos_words': 'show'})
        wh.write(dos_words='nonsense');self.assertEqual(wh.dos_words(), 'show')


class KeysFromAnyApp(unittest.TestCase):
    def test_the_fluxbox_keys_file_names_each_key_and_graphite_do(self):
        tool = ROOT / 'tools' / 'graphite-do'
        with tempfile.TemporaryDirectory() as temp:
            out = subprocess.run([sys.executable, '-B', str(tool), '--write-keys', temp + '/fluxbox'], capture_output=True, text=True, timeout=30)
            self.assertEqual(out.returncode, 0, out.stderr);init = Path(out.stdout.strip())
            self.assertEqual(init, Path(temp) / 'fluxbox' / 'init')
            self.assertIn('session.keyFile:\t%s/fluxbox/keys' % temp, init.read_text())
            keys = (Path(temp) / 'fluxbox' / 'keys').read_text()
        for line in ('Super_L :Exec "%s" start' % tool, 'Mod4 e :Exec "%s" files' % tool,  # 1.1 B2: the Windows key opens Start 'Mod4 d :Exec "%s" show' % tool, 'Mod4 l :Exec "%s" lock' % tool,
                     'Control Mod1 Delete :Exec "%s" tasks' % tool, 'Print :Exec "%s" screenshot' % tool, 'Mod1 F4 :Close'):
            self.assertIn(line + '\n', keys)
        self.assertRegex(keys, r'\nMod1 Tab :NextWindow')
        self.assertTrue(os.access(tool, os.X_OK))
        script = (ROOT / 'LS_XSESSION.sh').read_text()
        self.assertIn('--write-keys "$ledger_session_dir/fluxbox"', script);self.assertIn('${ledger_fluxbox_rc:+-rc "$ledger_fluxbox_rc"}', script)

    def test_graphite_do_speaks_to_the_running_windows_door(self):
        from PySide6.QtWidgets import QApplication, QMainWindow
        from workbench import windows_keys_qt as wk
        app = QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as temp:
            host = QMainWindow();sock = Path(temp) / 'do.sock'
            door = wk.Door(host, sock);self.assertTrue(door.listening, door.why);self.assertEqual(oct(sock.stat().st_mode & 0o777), '0o600')
            env = dict(os.environ, GRAPHITE_DO_SOCKET=str(sock), HOME=temp)
            answers = {}
            with patch.object(wk, 'screenshot', lambda h: str(Path(temp) / 'Pictures/Screenshots/Screenshot.png')):
                for verb in ('ping', 'show', 'screenshot', 'nonsense'):
                    child = subprocess.Popen([sys.executable, '-B', str(ROOT / 'tools' / 'graphite-do'), verb], env=env, stdout=subprocess.PIPE, text=True)
                    deadline = time.monotonic() + 20
                    while child.poll() is None and time.monotonic() < deadline:app.processEvents();time.sleep(0.01)
                    answers[verb] = (child.returncode, child.stdout.read().strip());child.stdout.close()
            self.assertEqual(answers['ping'], (0, 'Graphite is here.'))
            self.assertEqual(answers['show'], (0, 'Graphite is in front.'))
            self.assertEqual(answers['screenshot'][0], 0);self.assertIn('Screenshots', answers['screenshot'][1])
            self.assertEqual(answers['nonsense'][0], 1);self.assertIn('graphite-do knows', answers['nonsense'][1])
            self.assertEqual(door.heard, ['ping', 'show', 'screenshot'], 'an unknown word never reaches the window')
            door.close();self.assertFalse(sock.exists());host.deleteLater()
        out = subprocess.run([sys.executable, '-B', str(ROOT / 'tools' / 'graphite-do'), 'ping'], env=dict(os.environ, GRAPHITE_DO_SOCKET='/nonexistent/x.sock'),
                             capture_output=True, text=True, timeout=30)
        self.assertEqual(out.returncode, 1);self.assertIn('Graphite is not running here', out.stdout)

    def test_printscreen_saves_a_picture_into_screenshots_and_says_so(self):
        from PySide6.QtWidgets import QApplication, QMainWindow
        from workbench import windows_keys_qt as wk
        app = QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as temp:
            host = QMainWindow();host.resize(320, 200);host.show();app.processEvents()
            made = wk.screenshot(host, Path(temp) / 'Pictures' / 'Screenshots', now=0)
            if not made:self.skipTest('this display gives no picture of the screen')
            self.assertTrue(Path(made).is_file());self.assertTrue(Path(made).name.startswith('Screenshot '))
            self.assertIn('Saved a picture of the screen', host.statusBar().currentMessage())
            host.close();host.deleteLater()

    def test_the_clock_says_the_time_and_the_date_and_a_press_shows_the_month(self):
        from PySide6.QtWidgets import QApplication, QWidget
        from workbench import dock_clock_qt as dc
        app = QApplication.instance() or QApplication([])
        stamp = time.mktime((2026, 11, 28, 14, 5, 0, 0, 0, -1))
        self.assertEqual(dc.words(stamp), ('14:05', 'Sat 28 Nov', 'Saturday 28 November 2026'))
        bar = QWidget();bar.resize(1366, 28);clock = dc.attach(bar)
        self.assertRegex(clock.text(), r'^\d\d:\d\d \u00b7 \w{3} \d{1,2} \w{3}$')
        width = dc.place(clock, bar, 28);self.assertEqual(clock.geometry().right() + 1, 1366);self.assertGreater(width, 40)
        month = clock.show_month();app.processEvents()
        self.assertTrue(month.isVisible());self.assertTrue(month.today.text().startswith('Today is '))
        month.close();bar.deleteLater()


if __name__ == '__main__':
    unittest.main()
