"""Start Ledger & Slate from a shortcut or a START_*.sh script (no console window).

Opens the Qt window. PySide6 is required; there is no older UI fallback.
Adds compiler folders recorded by setup (install.json) to PATH, so Build
works even when LLVM is not on the system PATH. A failure prints the traceback,
writes launch-error.log under ${XDG_STATE_HOME:-~/.local/state}/ledger-slate/
(falling back to the folder next to install.json), shows a message that names
only a log that was actually written, and exits 1 instead of vanishing.

    python -m workbench.launch [--check]    # --check: start, verify, exit (used by setup tests)
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import traceback

APP = Path(__file__).resolve().parents[1]
INSTALL = APP.parent / 'install.json'
try:
    from workbench.version import NAME as PRODUCT
except Exception:  # noqa: BLE001 - the failure message must work even when the package is damaged
    PRODUCT = 'Graphite'


def install_info():
    try:
        data = json.loads(INSTALL.read_text(encoding='utf-8'))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def extend_path(info):
    extra = [p for p in info.get('extra_path', []) if isinstance(p, str) and Path(p).is_dir()]
    # Finder does not inherit the interactive terminal's PATH. These are the
    # conventional locations for the official Node package / Homebrew tools.
    if sys.platform == 'darwin':
        extra += [p for p in ('/usr/local/bin', '/opt/homebrew/bin')
                  if Path(p).is_dir() and p not in extra]
    if extra:
        os.environ['PATH'] = os.pathsep.join(extra + [os.environ.get('PATH', '')])
    return extra


def choose_frontend():
    try:
        import PySide6  # noqa: F401
        return 'qt'
    except ImportError:
        raise RuntimeError('PySide6 is required for %s. Run bash INSTALL_LEDGER.sh --quick to repair the Qt runtime.' % PRODUCT)


def alert(title, text):
    if os.name == 'nt':
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(None, text, title, 0x10)
            return
        except Exception:  # noqa: BLE001 - last resort below
            pass
    sys.stderr.write('%s: %s\n' % (title, text))


def error_log_candidates(environ=None):
    """Where launch-error.log is tried, in order: the XDG state folder, then next to install.json."""
    environ = os.environ if environ is None else environ
    state = environ.get('XDG_STATE_HOME')
    try:
        base = Path(state) if state else Path.home() / '.local' / 'state'
    except (OSError, RuntimeError):
        base = None
    first = [base / 'ledger-slate' / 'launch-error.log'] if base else []
    return first + [INSTALL.parent / 'launch-error.log']


def write_error_log(text, candidates=None):
    """Write the traceback to the first location that accepts it; return that path, or None when none did."""
    for path in error_log_candidates() if candidates is None else candidates:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding='utf-8')
            return path
        except OSError:
            continue
    return None


def windows_identity(front):
    """Own taskbar button and icon (not Python's); sharp Tk text on scaled displays."""
    if os.name != 'nt':
        return
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('ARC1.Workbench')
        if front == 'tk':
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except (AttributeError, OSError):
        pass


def startup_screen():
    """GRAPHITE-01: GRAPHITE under the sharpened point on graphite ground while the window is built, closed when the window
    (or any other window) is shown. It never blocks or fails the start: on any error there is simply no startup screen."""
    try:
        from PySide6.QtWidgets import QApplication
        from workbench.graphite_brand import startup_screen as show
        return show(QApplication.instance() or QApplication(sys.argv))  # qt_app.make_app takes this instance over
    except Exception:  # noqa: BLE001 - the start goes on without it
        return None


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if '--version' in argv:
        sys.path.insert(0, str(APP));from workbench.version import NAME, VERSION
        print(NAME + ' ' + VERSION);return 0
    if '--doctor' in argv:
        sys.path.insert(0, str(APP))
        from workbench.doctor import main as doctor
        return doctor([x for x in argv if x != '--doctor'])
    os.chdir(APP)
    if str(APP) not in sys.path:
        sys.path.insert(0, str(APP))
    extend_path(install_info())
    splash = None
    try:
        from prepare_release import prepare
        prepare(APP)
        front = choose_frontend()
        windows_identity(front)
        if front == 'qt':
            if '--check' not in argv:splash = startup_screen()
            from workbench.qt_app import make_app, WorkbenchWindow
            if '--check' in argv:
                app = make_app(['arc1-check'])
                from workbench.locations import default_root
                w = WorkbenchWindow(root=default_root(), restore=False)
                ok = w.badge.text() == 'HOST SIM · BOARD OFFLINE'
                w.deleteLater()
                app.processEvents()
                print('ARC1_LAUNCH_OK qt' if ok else 'ARC1_LAUNCH_FAIL qt')
                return 0 if ok else 1
            from workbench.qt_app import main as run
        return run() or 0
    except Exception:  # noqa: BLE001 - shown to the user, then logged
        try:
            if splash is not None:splash.close()  # the failure message is never under the startup screen
        except Exception:  # noqa: BLE001
            pass
        text = traceback.format_exc()
        sys.stderr.write(text)
        written = write_error_log(text)
        detail = 'Details: %s' % written if written else 'No log file could be written; the traceback above is the only record.'
        alert('%s could not start' % PRODUCT, text.strip().splitlines()[-1] + '\n\n' + detail)
        return 1


if __name__ == '__main__':
    sys.exit(main())
