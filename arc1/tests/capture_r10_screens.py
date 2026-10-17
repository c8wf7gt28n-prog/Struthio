"""Regenerates the R10 Workbench screenshots in docs/assets (real Qt window, offscreen).

Works on a temporary copy of the project, so nothing in the repository is edited
except the PNG files. Clip's Google calls are replaced by canned answers: the
pictures show the bubbles, not a live Gemini reply.

    QT_QPA_PLATFORM=offscreen python3 tests/capture_r10_screens.py
"""
import os
from pathlib import Path
import sys
import tempfile
import time
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tests'))
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ.pop('GEMINI_API_KEY', None)

from test_r10_workbench import project_copy, type_over  # noqa: E402
from workbench import clip  # noqa: E402
from workbench.session import Session  # noqa: E402

ASSETS = ROOT / 'docs' / 'assets'


def main():
    from PySide6.QtCore import QEventLoop, QProcess, QTimer
    from workbench import qt_app

    def pump(ms=60):
        loop = QEventLoop()
        QTimer.singleShot(ms, loop.quit)
        loop.exec()

    def idle(w, timeout=180):
        end = time.time() + timeout
        pump(100)
        while (w.process.state() != QProcess.NotRunning or w.after_build is not None) and time.time() < end:
            pump(100)
        pump(300)

    def shot(w, name):
        pump(150)
        w.grab().save(str(ASSETS / name))
        print('wrote docs/assets/' + name)

    with tempfile.TemporaryDirectory() as tmp:
        os.environ['ARC1_WORKBENCH_CONFIG_HOME'] = str(Path(tmp) / 'config')
        root = project_copy(tmp)
        app = qt_app.make_app(['arc1-capture'])
        w = qt_app.WorkbenchWindow(root=root, session=Session(Path(tmp) / 'session.json', project=root))
        w.message = lambda *a, **k: None
        w.confirm = lambda *a: True
        w.ask_save = lambda name: 'save'
        w.resize(1366, 768)
        w.show()
        pump(300)
        shot(w, 'workbench_r10_1_start.png')

        w.open_document(root / 'firmware/f133/src/lcd_status.c')
        main_c = root / 'examples/hello_arc1/src/main.c'
        ed = w.open_document(main_c)
        ed.go_to(17, 5)
        shot(w, 'workbench_r10_2_editor.png')

        good = ed.toPlainText()
        lines = good.split('\n')
        n = next(i for i, line in enumerate(lines) if 'arc1_input_poll();' in line) + 2
        lines.insert(n - 1, '        this_is_not_c;')
        type_over(ed, '\n'.join(lines))
        w.a_save.trigger()
        w.a_build.trigger()
        idle(w)
        w.a_next.trigger()
        shot(w, 'workbench_r10_3_build_error.png')

        type_over(ed, good)
        w.a_save.trigger()
        w.browse(root / 'sdk')
        shot(w, 'workbench_r10_4_browse.png')

        w.a_run.trigger()
        idle(w)
        shot(w, 'workbench_r10_5_run_preview.png')

        w.tabs.setCurrentWidget(ed)
        w.output_dock.hide()
        w.show_budgets()
        shot(w, 'workbench_r10_6_resources.png')
        w.inspector_dock.hide()

        w.tabs.setCurrentWidget(w.open_document(root / 'firmware/f133/src/lcd_status.c'))
        reply = ("It never calls `lcd_status_init()`. Add it before the main loop:\n\n"
                 "```c\nlcd_status_init();\n```")
        with mock.patch.object(clip, 'check_key', lambda k: 'gemini-flash-latest'), \
                mock.patch.object(clip, 'ask', lambda s, h: reply):
            w.open_clip()
            pump(300)
            shot(w, 'workbench_r10_8_clip_setup.png')
            o = w.clip_overlay
            o.clear()
            o.input.setText('AIzaSy' + 'Q' * 33)
            o.send()
            pump(600)
            o.input.setText('Why is the LCD blank after boot?')
            o.send()
            pump(600)
            shot(w, 'workbench_r10_7_clip.png')
        w.close()
        del app


if __name__ == '__main__':
    main()
