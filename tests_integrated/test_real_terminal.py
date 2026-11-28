"""Graphite 1.1.2 C0: a real terminal in the drop-down (xterm -into, the owner's shell, DOS words through Graphite's bash rc).

The acceptance first: under Xvfb with xterm, the drop-down shows a real terminal; a program reads a key from it; top runs and
q quits; vim opens, edits and saves a file; dir prints its Debian line and runs; Win+` puts it away and gives the keys back.
Then the rc on its own (in a pseudo-terminal, no X) and the pure pieces. The X part starts its own Xvfb and runs the driver
below in a child process (the xcb platform; the tiers' own process is offscreen); without Xvfb, xterm or Qt's xcb platform
it says which is missing.
"""
import json
import os
import pty
import select
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:sys.path.insert(0, str(ROOT))

from workbench import real_terminal_rc as rc  # noqa: E402

ARROW = '→'


# ---- the X driver (a child process: python test_real_terminal.py --x-driver OUT) -----------------------------------------------
def driver(out):
    import ctypes
    out = Path(out);home = Path.home();files = home / 'Files';files.mkdir(parents=True, exist_ok=True)
    (files / 'notes.txt').write_text('invented notes\n');(files / 'probe.sh').write_text('read -n1 k; echo "got:$k" > got.txt\n')
    (home / '.bashrc').write_text("PS1='owner$ '\n")
    log = out / 'xterm.log';report = {}
    from PySide6.QtCore import QTimer  # noqa: F401
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication, QWidget
    app = QApplication([])
    from workbench import drop_terminal_qt as dt, real_terminal_qt as rt
    plain = rt.argv
    rt.argv = lambda *a, **k: plain(*a, extra=('-l', '-lf', str(log)))
    host = QWidget();host.setWindowTitle('An app');host.resize(900, 700);host.show();host.activateWindow()

    def pump(ms=50, n=4):
        for _ in range(n):app.processEvents();QTest.qWait(ms)

    def until(test, seconds=10.0):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            pump(50, 1)
            if test():return True
        return False
    pump(60, 6)
    term = dt.terminal(host)
    term.cwd = files
    real = term.real;report['real'] = real is not None
    if real is None:
        report['why'] = rt.why_not();(out / 'report.json').write_text(json.dumps(report));return 0
    term.drop()
    report['prompt'] = until(lambda: real.client and real.shell_pid() and rt.at_prompt(real.shell_pid()) and log.exists() and 'owner$' in log.read_text(errors='replace'))
    pump(60, 6)
    x = real.xconn()
    report['client_in_drop'] = real.client in x.children(int(real.winId()))
    report['focus_is_xterm'] = x.focused() == real.client
    report['geometry'] = dict(drop=term.geometry().getRect(), area=[real.width(), real.height()])
    kc2ks = x.x.XKeycodeToKeysym;kc2ks.argtypes = [ctypes.c_void_p, ctypes.c_ubyte, ctypes.c_int];kc2ks.restype = ctypes.c_ulong
    names = {' ': 'space', ';': 'semicolon', ':': 'colon', '"': 'quotedbl', '>': 'greater', '$': 'dollar', '-': 'minus',
             '.': 'period', '/': 'slash', '_': 'underscore', '\n': 'Return', '\x1b': 'Escape'}

    def typed(text):
        for ch in text:
            name = names.get(ch, ch);ks = x.x.XStringToKeysym(name.encode());kc = x.x.XKeysymToKeycode(x.dpy, ks)
            x.tap(name, ('Shift_L',) if int(kc2ks(x.dpy, kc, 0)) != int(ks) else ())
            pump(10, 1)

    def screen():
        return log.read_text(errors='replace') if log.exists() else ''
    typed('bash probe.sh\n');pump(60, 8);typed('q')
    report['key_read'] = until(lambda: (files / 'got.txt').exists() and (files / 'got.txt').read_text().strip() == 'got:q')
    typed('tty\n');report['tty'] = until(lambda: '/dev/pts/' in screen())
    typed('dir\n');report['dir'] = until(lambda: ('dir %s ls -l' % ARROW) in screen() and 'notes.txt' in screen())
    typed('top\n');report['top_runs'] = until(lambda: 'load average' in screen() and not rt.at_prompt(real.shell_pid()))
    typed('q');report['top_quits'] = until(lambda: rt.at_prompt(real.shell_pid()))
    typed('vim -u NONE memo.txt\n');pump(80, 12)
    report['vim_runs'] = not rt.at_prompt(real.shell_pid())
    typed('ihello from vim\x1b');pump(60, 4);typed(':wq\n')
    report['vim_saved'] = until(lambda: (files / 'memo.txt').exists() and (files / 'memo.txt').read_text() == 'hello from vim\n')
    until(lambda: rt.at_prompt(real.shell_pid()), 5);pump(60, 6)
    report['bar_said'] = term.run('echo handed by the bar')
    report['bar_ran'] = until(lambda: screen().count('handed by the bar') >= 2)
    host_x = int(host.winId())
    x.tap('grave', ('Super_L',))
    report['hide_key'] = until(lambda: not term.opened and not term.isVisible(), 5)
    pump(60, 6)
    report['focus_back'] = x.focused() in (host_x, 0) and x.focused() != real.client
    report['focus_window'] = [x.focused(), host_x]
    report['still_running'] = real.running()
    term.drop();until(lambda: x.focused() == real.client, 5)
    typed('exit\n');report['exit_puts_away'] = until(lambda: not term.opened and not real.running(), 8)
    (out / 'report.json').write_text(json.dumps(report, default=str))
    return 0


# ---- the X tests ----------------------------------------------------------------------------------------------------------------
class RealTerminalOnX(unittest.TestCase):
    """One driver run under a fresh Xvfb; each test reads one fact of its report."""
    report = None

    @classmethod
    def setUpClass(cls):
        missing = [t for t in ('Xvfb', 'xterm', 'bash', 'vim', 'top') if not shutil.which(t)]
        if missing:raise unittest.SkipTest('missing here: %s' % ', '.join(missing))
        cls.area = Path(tempfile.mkdtemp(prefix='c0-x-'))
        n = 140 + os.getpid() % 50
        cls.xvfb = subprocess.Popen(['Xvfb', ':%d' % n, '-screen', '0', '1366x768x24', '-nolisten', 'tcp'],
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(100):
            if Path('/tmp/.X11-unix/X%d' % n).exists():break
            time.sleep(0.1)
        home = cls.area / 'home';home.mkdir()
        env = dict(os.environ, DISPLAY=':%d' % n, QT_QPA_PLATFORM='xcb', HOME=str(home), XDG_RUNTIME_DIR=str(cls.area / 'run'),
                   XDG_CONFIG_HOME=str(home / '.config'), XDG_CACHE_HOME=str(home / '.cache'))
        (cls.area / 'run').mkdir()
        p = subprocess.run([sys.executable, '-B', __file__, '--x-driver', str(cls.area)], cwd=str(ROOT), env=env,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=240)
        cls.output = p.stdout[-3000:]
        path = cls.area / 'report.json'
        cls.report = json.loads(path.read_text()) if path.exists() else None
        if cls.report is None and 'xcb' in cls.output and 'plugin' in cls.output:
            cls.tearDownClass();raise unittest.SkipTest("Qt's xcb platform cannot start here")

    @classmethod
    def tearDownClass(cls):
        if getattr(cls, 'xvfb', None) is not None:cls.xvfb.terminate();cls.xvfb.wait(5)
        shutil.rmtree(getattr(cls, 'area', ''), ignore_errors=True)

    def fact(self, key):
        self.assertIsNotNone(self.report, 'the driver wrote no report:\n' + self.output)
        return self.report.get(key)

    def test_a_the_drop_down_is_a_real_terminal(self):
        self.assertTrue(self.fact('real'), self.report)
        self.assertTrue(self.fact('prompt'), 'the shell reached its prompt in the embedded xterm')
        self.assertTrue(self.fact('client_in_drop'), 'xterm is inside the drop-down')
        self.assertTrue(self.fact('focus_is_xterm'), 'xterm has the keys while it is down')
        self.assertTrue(self.fact('tty'), 'tty names a pseudo-terminal')

    def test_b_a_program_reads_a_key_and_its_output_appears(self):
        self.assertTrue(self.fact('key_read'))

    def test_c_top_runs_and_q_quits(self):
        self.assertTrue(self.fact('top_runs'));self.assertTrue(self.fact('top_quits'))

    def test_d_vim_opens_edits_and_saves(self):
        self.assertTrue(self.fact('vim_runs'));self.assertTrue(self.fact('vim_saved'))

    def test_e_dir_prints_the_debian_line_and_runs(self):
        self.assertTrue(self.fact('dir'))

    def test_f_win_backtick_hides_it_and_gives_the_keys_back(self):
        self.assertTrue(self.fact('hide_key'));self.assertTrue(self.fact('focus_back'), self.report.get('focus_window'))
        self.assertTrue(self.fact('still_running'), 'put away, the shell keeps running')

    def test_g_a_bar_row_is_typed_into_the_shell_and_exit_puts_it_away(self):
        self.assertTrue(str(self.fact('bar_said')).startswith('In the Terminal'));self.assertTrue(self.fact('bar_ran'))
        self.assertTrue(self.fact('exit_puts_away'))


# ---- the rc in a pseudo-terminal (no X) --------------------------------------------------------------------------------------------
class TheRc(unittest.TestCase):
    def test_h_bash_with_the_rc_shows_dir_as_debian_keeps_the_owners_rc(self):
        if not shutil.which('bash'):self.skipTest('no bash here')
        home = Path(tempfile.mkdtemp(prefix='c0-rc-'));files = home / 'Files';files.mkdir()
        (files / 'notes.txt').write_text('x\n');(home / '.bashrc').write_text("PS1='owner$ '\nalias ll='ls -1'\n")
        before = (home / '.bashrc').read_text()
        path = rc.write_rc(home / 'own', python=sys.executable)
        pid, fd = pty.fork()
        if pid == 0:
            os.chdir(files)
            os.execvpe('bash', ['bash', '--rcfile', str(path), '-i'], dict(HOME=str(home), TERM='xterm', PATH=os.environ.get('PATH', '/usr/bin:/bin')))

        def read(seconds):
            data, end = b'', time.time() + seconds
            while time.time() < end:
                if select.select([fd], [], [], 0.1)[0]:
                    try:data += os.read(fd, 65536)
                    except OSError:break
            return data.decode('utf-8', 'replace')
        try:
            read(2)
            os.write(fd, b'dir\r');shown = read(2.5)
            os.write(fd, b'll\r');own = read(1.5)
            os.write(fd, b'echo plain words\r');plain = read(1.5)
            os.write(fd, b'history\r');up = read(1.5)
            os.write(fd, b'\x15exit\r');read(1)
        finally:
            os.close(fd);os.waitpid(pid, 0)
        self.assertIn('dir %s ls -l' % ARROW, shown);self.assertIn('owner$ ls -l', shown);self.assertIn('notes.txt', shown)
        self.assertIn('notes.txt', own, "the owner's alias works");self.assertNotIn(ARROW, plain);self.assertIn('plain words', plain)
        self.assertRegex(up, r'\d+\s+ls -l\s', 'the history (what Up brings back) holds the Debian command')
        self.assertEqual((home / '.bashrc').read_text(), before, "the owner's rc is untouched")


# ---- the pure pieces -------------------------------------------------------------------------------------------------------------
class Pieces(unittest.TestCase):
    PLACES = {'C': '/', 'D': '/media/stick'}

    def ask(self, line, mode='on', cwd='/srv/demo/Files'):
        return rc.answer(line, cwd, mode=mode, places=self.PLACES, which=lambda name: '/usr/bin/' + name)

    def test_i_dos_lines_become_their_debian_command_others_stay(self):
        said = self.ask('dir /s');self.assertTrue(said['dos']);self.assertEqual(said['shown'][0], 'dir /s %s ls -lR' % ARROW)
        self.assertEqual(said['run'], 'ls -lR')
        self.assertEqual(self.ask('D:')['run'], "cd -- /media/stick");self.assertEqual(self.ask('cls')['run'], 'clear')
        for line in ('ls -la', 'echo hello', 'vim notes.txt', 'top', 'sudo apt update'):
            self.assertFalse(self.ask(line)['dos'], line)
        self.assertEqual(self.ask('format c:')['run'], '');self.assertIn('never run', ' '.join(self.ask('format c:')['shown']))

    def test_j_show_me_only_and_off(self):
        said = self.ask('dir', mode='show');self.assertEqual(said['run'], '');self.assertIn(rc.SHOWN_ONLY, said['shown'])
        self.assertFalse(self.ask('dir', mode='off')['dos'])

    def test_k_del_goes_to_the_bin_and_everything_asks_first(self):
        folder = Path(tempfile.mkdtemp(prefix='c0-del-'));(folder / 'a.tmp').write_text('a');(folder / 'b.tmp').write_text('b')
        said = self.ask('del a.tmp', cwd=str(folder));self.assertEqual(said['run'], 'gio trash -- a.tmp')
        said = self.ask('del *.*', cwd=str(folder));self.assertTrue(said['run'].startswith('__graphite_sure 2 '))
        self.assertIn('gio trash -- a.tmp b.tmp', said['run']);self.assertNotIn('rm ', said['run'])
        self.assertEqual(self.ask('del none.tmp', cwd=str(folder))['run'], '')

    def test_l_the_rc_reads_the_owners_bashrc_first_and_binds_enter(self):
        text = rc.rc_text(python='/usr/bin/python3', script='/opt/graphite/workbench/real_terminal_rc.py')
        self.assertLess(text.index('. "$HOME/.bashrc"'), text.index('bind -m'))
        for mode in ('emacs', 'vi-insert'):self.assertIn('for __graphite_map in emacs vi-insert', text)
        self.assertIn('"\\C-m": "\\C-x\\C-g\\C-d\\C-x\\C-g\\C-a"', text);self.assertIn('"\\e[24;8~"', text)
        self.assertNotIn('>> "$HOME', text);self.assertNotIn('> "$HOME', text)

    def test_m_xterm_follows_the_look_and_runs_bash_with_the_rc(self):
        from PySide6.QtWidgets import QApplication
        self.app = QApplication.instance() or QApplication([])
        from workbench import real_terminal_qt as rt
        line = rt.argv(1234, '/bin/bash', '/run/g/graphite-terminal.bashrc')
        ground, words, _, _ = rt.look()
        self.assertEqual(line[:3], ['xterm', '-into', '1234']);self.assertEqual(line[line.index('-bg') + 1], ground)
        self.assertEqual(line[line.index('-fg') + 1], words);self.assertTrue(line[line.index('-fa') + 1].startswith('IBM Plex Mono'))
        self.assertEqual(line[-4:], ['/bin/bash', '--rcfile', '/run/g/graphite-terminal.bashrc', '-i'])
        self.assertEqual(rt.argv(1, '/usr/bin/zsh', '/x')[-2:], ['-e', '/usr/bin/zsh'])
        self.assertEqual(rt.why_not(platform='offscreen'), 'not on X');self.assertEqual(rt.why_not(platform='xcb', which=lambda n: None), 'xterm is not installed')


if __name__ == '__main__':
    if sys.argv[1:2] == ['--x-driver']:
        sys.exit(driver(sys.argv[2]))
    unittest.main()
