"""Start ARC-1 Workbench from a shortcut (no console window).

Opens the R10 Qt window, or the classic Tk desktop if PySide6 is missing.
Adds compiler folders recorded by setup (install.json) to PATH, so Build
works even when LLVM is not on the system PATH. A failure shows a message
box and writes launch-error.log next to install.json instead of vanishing.

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


def install_info():
    try:
        data = json.loads(INSTALL.read_text(encoding='utf-8'))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def extend_path(info):
    extra = [p for p in info.get('extra_path', []) if isinstance(p, str) and Path(p).is_dir()]
    if extra:
        os.environ['PATH'] = os.pathsep.join(extra + [os.environ.get('PATH', '')])
    return extra


def choose_frontend():
    try:
        import PySide6  # noqa: F401
        return 'qt'
    except ImportError:
        return 'tk'


def alert(title, text):
    if os.name == 'nt':
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(None, text, title, 0x10)
            return
        except Exception:  # noqa: BLE001 - last resort below
            pass
    sys.stderr.write('%s: %s\n' % (title, text))


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


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    os.chdir(APP)
    if str(APP) not in sys.path:
        sys.path.insert(0, str(APP))
    extend_path(install_info())
    front = choose_frontend()
    windows_identity(front)
    try:
        if front == 'qt':
            from workbench.qt_app import make_app, WorkbenchWindow
            if '--check' in argv:
                app = make_app(['arc1-check'])
                w = WorkbenchWindow(restore=False)
                ok = w.badge.text() == 'HOST SIM · BOARD OFFLINE'
                w.deleteLater()
                app.processEvents()
                print('ARC1_LAUNCH_OK qt' if ok else 'ARC1_LAUNCH_FAIL qt')
                return 0 if ok else 1
            from workbench.qt_app import main as run
        else:
            if '--check' in argv:
                import tkinter  # noqa: F401
                print('ARC1_LAUNCH_OK tk')
                return 0
            from workbench.app import main as run
        return run() or 0
    except Exception:  # noqa: BLE001 - shown to the user, then logged
        text = traceback.format_exc()
        try:
            (INSTALL.parent / 'launch-error.log').write_text(text, encoding='utf-8')
        except OSError:
            pass
        alert('ARC-1 Workbench could not start',
              text.strip().splitlines()[-1] + '\n\nDetails: %s' % (INSTALL.parent / 'launch-error.log'))
        return 1


if __name__ == '__main__':
    sys.exit(main())
