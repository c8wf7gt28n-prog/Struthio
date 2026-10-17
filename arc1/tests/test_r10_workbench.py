"""ARC-1 Workbench R10 tests.

Part 1 needs only Python: engine, File Manager operations, session memory.
Part 2 drives the real Qt window (PySide6, offscreen platform) through the
owner's acceptance workflow: find a file, open, edit, save, build the relevant
target, read the compiler error, go back to the source line, run the
simulator; then reopen to check what Workbench remembered. Part 2 is skipped,
loudly, when PySide6 is not installed. It is not Windows qualification.

    python3 tests/test_r10_workbench.py
"""
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from workbench import agent, engine, fileops, resources  # noqa: E402
from workbench.session import LAYOUT_VERSION, Session  # noqa: E402

try:
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    import PySide6  # noqa: F401
    HAVE_QT = True
except ImportError:
    HAVE_QT = False

IGNORE = shutil.ignore_patterns('build', 'reports', '__pycache__', '.git', '*.pyc')


def type_over(ed, text):
    """Replaces the document the way a person does (select all, type), so the
    modified flag and Undo behave as they do for real editing."""
    from PySide6.QtGui import QTextCursor
    c = ed.textCursor()
    c.select(QTextCursor.Document)
    c.insertText(text)
    ed.setTextCursor(c)


def project_copy(tmp):
    dest = Path(tmp) / 'arc1'
    shutil.copytree(ROOT, dest, ignore=IGNORE, symlinks=True)
    return dest


# ============================================================================ part 1: no Qt

class EngineTests(unittest.TestCase):
    def test_agent_and_gui_share_one_command_table(self):
        self.assertIs(agent.ACTIONS, engine.AGENT_ACTIONS)
        for tid in ('f133', 'd213', 'lcd'):
            self.assertIn(engine.plan('build', tid).argv, engine.AGENT_ACTIONS.values())
        self.assertEqual(engine.plan('build', 'game').argv, engine.AGENT_ACTIONS['build.game'])
        self.assertEqual(engine.plan('test', 'game').argv, engine.AGENT_ACTIONS['test.game'])

    def test_relevant_target_follows_the_open_file(self):
        game_file = ROOT / 'examples' / 'hello_arc1' / 'src' / 'main.c'
        p = engine.plan('build', 'f133', game_file)
        self.assertEqual((p.target, p.project, p.argv), ('game', 'examples/hello_arc1', ['build', 'examples/hello_arc1']))
        self.assertIn('open file belongs', p.reason)
        fw = engine.plan('build', 'lcd', ROOT / 'firmware' / 'f133' / 'src' / 'lcd_status.c')
        self.assertEqual(fw.argv, ['firmware', 'build', '--target', 'status-lcd'])
        run = engine.plan('run', 'f133', None)
        self.assertEqual(run.argv[:2], ['sim', 'examples/hello_arc1'])
        with self.assertRaises(ValueError):
            engine.plan('flash', 'f133')

    def test_problem_paths_resolve_inside_project_only(self):
        game = engine.plan('build', 'game')
        self.assertEqual(engine.resolve_problem_path('src/main.c', game),
                         (ROOT / 'examples/hello_arc1/src/main.c').resolve())
        absolute = str(ROOT / 'firmware/f133/src/lcd_status.c')
        self.assertEqual(engine.resolve_problem_path('  FAIL FW-BUILD compiler returned 1: ' + absolute),
                         Path(absolute).resolve())
        self.assertIsNone(engine.resolve_problem_path('/usr/include/stdio.h'))
        self.assertIsNone(engine.resolve_problem_path('src/does_not_exist.c', game))

    def test_quick_open_ranking(self):
        files = ['a/main.c', 'b/domain.c', 'c/main.c.bak', 'docs/main_notes.md', 'x/y/z.c']
        self.assertEqual(engine.find_files('main.c', files=files), ['a/main.c', 'c/main.c.bak', 'b/domain.c'])
        self.assertEqual(engine.find_files('y/z', files=files), ['x/y/z.c'])
        self.assertIn('examples/hello_arc1/src/main.c', engine.find_files('main.c'))

    def test_navigator_is_logical_and_truthful(self):
        labels = [n[0] for n in engine.NAVIGATOR]
        self.assertEqual(labels[:7], ['Firmware', 'SDK', 'FPGA', 'Games', 'Cartridges', 'Hardware', 'Tests'])
        fpga = dict((n[0], n) for n in engine.NAVIGATOR)['FPGA']
        self.assertIsNone(fpga[1])  # there are no FPGA sources here; it must not pretend otherwise
        self.assertFalse(engine.device_status()['connected'])


class FileOpsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / 'src').mkdir()
        (self.root / 'src' / 'main.c').write_text('int main(void){return 0;}\n')
        (self.root / 'passes' / 'P1').mkdir(parents=True)
        (self.root / 'passes' / 'P1' / 'pass.json').write_text('{}')

    def tearDown(self):
        self.tmp.cleanup()

    def test_windows_naming_rules(self):
        for bad in ('', ' ', 'a/b', 'a\\b', 'a:b', 'what?', 'x*', 'CON', 'com1.txt', 'nul', 'trailing.', 'trailing ',
                    '.hidden', '..'):
            with self.subTest(name=bad), self.assertRaises(fileops.FileOpError):
                fileops.validate_name(bad)
        self.assertEqual(fileops.validate_name('lcd status v2.c'), 'lcd status v2.c')

    def test_create_never_overwrites_case_insensitively(self):
        fileops.new_file(self.root, self.root / 'src', 'util.c', 'x')
        with self.assertRaises(fileops.FileOpError):
            fileops.new_file(self.root, self.root / 'src', 'MAIN.C')
        with self.assertRaises(fileops.FileOpError):
            fileops.new_folder(self.root, self.root / 'src', 'Util.c')
        self.assertEqual((self.root / 'src' / 'main.c').read_text(), 'int main(void){return 0;}\n')

    def test_rename_duplicate_delete(self):
        p = fileops.rename(self.root, self.root / 'src' / 'main.c', 'game.c')
        self.assertTrue(p.is_file())
        d1 = fileops.duplicate(self.root, p)
        d2 = fileops.duplicate(self.root, p)
        self.assertEqual((d1.name, d2.name), ('game - Copy.c', 'game - Copy (2).c'))
        with self.assertRaises(fileops.FileOpError):
            fileops.rename(self.root, d1, 'game.c')
        with self.assertRaises(fileops.FileOpError):
            fileops.delete_file(self.root, self.root / 'src')
        fileops.delete_file(self.root, d2)
        self.assertFalse(d2.exists())

    def test_evidence_and_escapes_are_refused(self):
        rec = self.root / 'passes' / 'P1' / 'pass.json'
        for op in (lambda: fileops.delete_file(self.root, rec), lambda: fileops.rename(self.root, rec, 'x.json'),
                   lambda: fileops.new_file(self.root, rec.parent, 'note.txt')):
            with self.assertRaises(fileops.FileOpError):
                op()
        with self.assertRaises(fileops.FileOpError):
            fileops.new_file(self.root, self.root / '..', 'escape.txt')
        outside = Path(self.tmp.name).parent / ('arc1-outside-%d.c' % os.getpid())
        link = self.root / 'src' / 'link.c'
        try:
            outside.write_text('x')
            link.symlink_to(outside)
            with self.assertRaises(fileops.FileOpError):
                fileops.delete_file(self.root, link)
            self.assertTrue(outside.exists())
        finally:
            if outside.exists():
                outside.unlink()

    def test_listing_folders_first(self):
        (self.root / 'src' / 'zdir').mkdir()
        rows = fileops.listing(self.root, self.root / 'src')
        self.assertEqual([r['name'] for r in rows], ['zdir', 'main.c'])
        self.assertEqual(rows[1]['type'], 'C source')


class SessionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'session.json'

    def tearDown(self):
        self.tmp.cleanup()

    def test_round_trip(self):
        s = Session(self.path, project='/p')
        s.remember_documents([('firmware/a.c', 12, 3), ('sdk/b.h', 1, 1)], 'sdk/b.h')
        s.touch_recent('firmware/a.c')
        s.set_target('d213')
        s.set_layout(navigator_width=250, output_visible=True, dock_state='AAAA', geometry='AAAA')
        s.save()
        t = Session(self.path, project='/p')
        self.assertEqual(t.state['documents'][0], {'path': 'firmware/a.c', 'line': 12, 'column': 3})
        self.assertEqual((t.state['active'], t.state['target']), ('sdk/b.h', 'd213'))
        self.assertEqual((t.layout['navigator_width'], t.layout['output_visible'], t.layout['dock_state']),
                         (250, True, 'AAAA'))

    def test_hostile_values_are_ignored(self):
        self.path.write_text(json.dumps({
            'schema': 'arc1.workbench-session/1', 'project': None,
            'documents': [{'path': '../../etc/passwd'}, {'path': '/etc/hosts'}, {'path': 'C:\\x.c'},
                          {'path': 'ok.c', 'line': -4}, {'path': 'good.c', 'line': 2, 'column': 5}],
            'target': 'rm -rf', 'recent': ['..\\..\\secret', 'fine.c'],
            'layout': {'navigator_width': 5000, 'output_visible': 'yes', 'dock_state': 'not base64!!',
                       'version': LAYOUT_VERSION}}))
        s = Session(self.path)
        self.assertEqual(s.state['documents'], [{'path': 'good.c', 'line': 2, 'column': 5}])
        self.assertEqual((s.state['target'], s.state['recent']), (engine.DEFAULT_TARGET, ['fine.c']))
        self.assertEqual((s.layout['navigator_width'], s.layout['output_visible'], s.layout['dock_state']),
                         (236, False, None))

    def test_old_layout_version_is_not_applied(self):
        self.path.write_text(json.dumps({'schema': 'arc1.workbench-session/1',
                                         'layout': {'dock_state': 'AAAA', 'version': LAYOUT_VERSION - 1}}))
        self.assertIsNone(Session(self.path).layout['dock_state'])

    def test_other_project_starts_clean_and_reset_keeps_documents(self):
        s = Session(self.path, project='/one')
        s.remember_documents([('a.c', 1, 1)], 'a.c')
        s.set_layout(output_visible=True, dock_state='AAAA')
        s.save()
        self.assertEqual(Session(self.path, project='/two').state['documents'], [])
        s.reset_layout()
        self.assertEqual((s.layout['dock_state'], s.layout['output_visible'], len(s.state['documents'])),
                         (None, False, 1))

    def test_oversized_file_ignored(self):
        self.path.write_text('{"schema": "arc1.workbench-session/1", "pad": "' + 'x' * 200000 + '"}')
        self.assertEqual(Session(self.path).state['documents'], [])


class ResourceBudgetTests(unittest.TestCase):
    """The Inspector's budget bars: every figure cited, unknowns stay unknown."""

    def test_every_number_quotes_its_source(self):
        data = resources.load()
        rows = data['frame_stages'] + data['links']
        with_value = [r for r in rows if r.get('ms') is not None or r.get('mbps') is not None]
        self.assertTrue(with_value)
        for r in with_value:
            with self.subTest(row=r['id']):
                self.assertTrue(r['cited'], r)
                self.assertNotEqual(r['evidence'], 'NONE')
        unknown = [r['id'] for r in data['frame_stages'] if r['ms'] is None]
        self.assertEqual(unknown, ['f133_logic', 'fpga12_jobs', 'd213_setup', 'present'])
        self.assertTrue(all(r['ms'] <= 1000 / 60 for r in data['frame_stages'] if r['ms'] is not None))
        self.assertEqual(sum(m['mib'] for m in data['memory']), 228)
        self.assertFalse(any(m['shared'] for m in data['memory']))

    def test_a_number_without_its_quote_is_dropped(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shutil.copytree(ROOT / 'hardware', root / 'hardware')
            p = root / 'hardware' / 'budgets' / 'r10_resources.json'
            d = json.loads(p.read_text(encoding='utf-8'))
            d['frame_stages'][3]['quote'] = 'a sentence the gate report never says'
            d['links'][0]['mbps'] = 999
            d['links'][0]['quote'] = 'invented'
            p.write_text(json.dumps(d), encoding='utf-8')
            data = resources.load(root)
            self.assertIsNone(data['frame_stages'][3]['ms'])
            self.assertIn('CITATION MISSING', data['frame_stages'][3]['note'])
            self.assertIsNone(data['links'][0]['mbps'])

    def test_agent_gets_the_same_figures(self):
        out = agent.handle({'method': 'inspect.resources'})
        self.assertEqual(out, resources.load(ROOT))
        self.assertIn('inspect.resources', agent.handle({'method': 'capabilities'})['methods'])


# ============================================================================ part 2: the real Qt window

@unittest.skipUnless(HAVE_QT, 'PySide6 is not installed: the Qt acceptance workflow was NOT run')
class AcceptanceWorkflowTests(unittest.TestCase):
    """The owner's R10 acceptance test, driven through the window's own actions."""

    @classmethod
    def setUpClass(cls):
        from workbench.qt_app import make_app
        cls.app = make_app(['test'])
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = project_copy(cls.tmp.name)
        cls.cfg = Path(cls.tmp.name) / 'config'

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def window(self):
        from workbench.qt_app import WorkbenchWindow
        w = WorkbenchWindow(root=self.root, session=Session(self.cfg / 'session.json', project=self.root))
        self.dialogs = []
        w.message = lambda title, text, error=False: self.dialogs.append((title, text))
        w.confirm = lambda title, text: True
        w.ask_save = lambda name: 'save'
        w.resize(1366, 768)
        w.show()
        self.pump(200)
        return w

    def pump(self, ms=50):
        from PySide6.QtCore import QEventLoop, QTimer
        loop = QEventLoop()
        QTimer.singleShot(ms, loop.quit)
        loop.exec()

    def wait_idle(self, w, timeout=180):
        from PySide6.QtCore import QProcess
        end = time.time() + timeout
        self.pump(100)
        while (w.process.state() != QProcess.NotRunning or w.after_build is not None) and time.time() < end:
            self.pump(100)
        self.pump(200)
        self.assertEqual(w.process.state(), QProcess.NotRunning, 'command did not finish in time')

    def test_1_default_screen_is_simple(self):
        w = self.window()
        menus = [a.text().replace('&', '') for a in w.menuBar().actions()]
        self.assertEqual(menus, ['File', 'Edit', 'View', 'Project', 'Build', 'Debug', 'Cartridge', 'Tools', 'Help'])
        self.assertTrue(w.nav_dock.isVisible())
        self.assertTrue(200 <= w.nav_dock.width() <= 260, w.nav_dock.width())
        for dock in (w.output_dock, w.inspector_dock, w.cart_dock):
            self.assertFalse(dock.isVisible(), dock.objectName())
        self.assertEqual(w.tabs.tabText(0), 'Start')
        self.assertEqual(w.badge.text(), 'HOST SIM · BOARD OFFLINE')
        self.assertEqual(w.device_label.text(), 'No physical device connected')
        top = w.nav.topLevelItem(0)
        self.assertEqual([top.child(i).text(0) for i in range(top.childCount())][:7],
                         ['Firmware', 'SDK', 'FPGA', 'Games', 'Cartridges', 'Hardware', 'Tests'])
        fpga = top.child(2)
        self.assertTrue(fpga.isDisabled())
        w.close()

    def test_2_acceptance_workflow(self):
        from workbench.qt_app import CodeEditor, PreviewTab
        t0 = time.time()
        w = self.window()
        # Find a file.
        hits = engine.find_files('main.c', root=self.root)
        self.assertIn('examples/hello_arc1/src/main.c', hits)
        path = self.root / 'examples/hello_arc1/src/main.c'
        # Open it.
        ed = w.open_document(path)
        self.assertIsInstance(ed, CodeEditor)
        self.assertEqual(w.tabs.tabText(w.tabs.currentIndex()), 'main.c')
        # Edit: break the code on a known line.
        lines = ed.toPlainText().split('\n')
        n = next(i for i, l in enumerate(lines) if 'arc1_input_poll();' in l) + 2   # 1-based line after it
        lines.insert(n - 1, '        this_is_not_c;')
        type_over(ed, '\n'.join(lines))
        self.assertTrue(ed.document().isModified())
        # Save.
        w.a_save.trigger()
        self.assertFalse(ed.document().isModified())
        self.assertIn('this_is_not_c', path.read_text())
        # Build the relevant target (the open file belongs to the host game, whatever target is selected).
        w.set_target('f133')
        w.a_build.trigger()
        self.wait_idle(w)
        self.assertEqual((w.plan.target, w.plan.project), ('game', 'examples/hello_arc1'))
        self.assertNotEqual(w.router.exit_code, 0)
        # Read the compiler error.
        self.assertTrue(w.output_dock.isVisible())
        self.assertTrue(w.output_tabs.tabText(w.output_tabs.currentIndex()).startswith('Problems'))
        errors = [(p, f) for p, f in w.problems if p.severity == 'error']
        self.assertTrue(errors, w.router.raw[-2000:])
        prob, resolved = errors[0]
        self.assertEqual(resolved, path.resolve())
        self.assertEqual(prob.line, n)
        self.assertIn('this_is_not_c', prob.message)
        # Navigate back to the source line (F8 = next problem).
        w.tabs.setCurrentIndex(0)
        w.a_next.trigger()
        self.pump()
        cur = w.current_editor()
        self.assertIs(cur, ed)
        self.assertEqual(cur.position()[0], n)
        self.assertEqual(cur.problem_line, n)
        # Fix, save, rebuild clean.
        lines = ed.toPlainText().split('\n')
        del lines[n - 1]
        type_over(ed, '\n'.join(lines))
        ed.undo()                                   # Undo restores the broken line...
        self.assertIn('this_is_not_c', ed.toPlainText())
        ed.redo()                                   # ...and Redo removes it again
        self.assertNotIn('this_is_not_c', ed.toPlainText())
        w.a_save.trigger()
        w.a_build.trigger()
        self.wait_idle(w)
        self.assertEqual(w.router.exit_code, 0, w.router.raw[-2000:])
        self.assertEqual(w.problems, [])
        # Run the simulator (F5): builds if needed, then simulates and opens the preview.
        w.a_run.trigger()
        self.wait_idle(w)
        self.assertEqual(w.plan.op, 'run')
        self.assertEqual(w.router.exit_code, 0, w.router.raw[-2000:])
        preview = w.tabs.currentWidget()
        self.assertIsInstance(preview, PreviewTab)
        self.assertEqual([n_ for n_, _ in preview.frames], [0, 30, 60, 90, 119])
        self.assertFalse(preview.image.pixmap().isNull())
        # Truthful status after a successful simulation.
        self.assertEqual(w.badge.text(), 'HOST SIM · BOARD OFFLINE')
        self.assertEqual(w.device_label.text(), 'No physical device connected')
        self.elapsed = time.time() - t0
        w.tabs.setCurrentWidget(ed)
        ed.go_to(7, 3)
        w.close()
        AcceptanceWorkflowTests.workflow_seconds = self.elapsed

    def test_3_reopen_remembers_and_reset_restores(self):
        from workbench.qt_app import CodeEditor
        w = self.window()
        ed = w.current_editor()
        self.assertIsInstance(ed, CodeEditor, 'last document was not reopened')
        self.assertEqual(ed.path.name, 'main.c')
        self.assertEqual(ed.position(), (7, 3))
        self.assertEqual(w.session.state['recent'][0], 'examples/hello_arc1/src/main.c')
        # Lose track of the panels, close, reopen: the mess is remembered...
        w.nav_dock.hide()
        w.output_dock.show()
        w.inspector_dock.show()
        w.close()
        w = self.window()
        self.assertFalse(w.nav_dock.isVisible())
        self.assertTrue(w.output_dock.isVisible())
        self.assertTrue(w.inspector_dock.isVisible())
        # ...and one command restores the factory layout without closing documents.
        w.a_reset.trigger()
        self.pump(200)
        self.assertTrue(w.nav_dock.isVisible())
        for dock in (w.output_dock, w.inspector_dock, w.cart_dock):
            self.assertFalse(dock.isVisible(), dock.objectName())
        self.assertEqual(w.current_editor().path.name, 'main.c')
        w.close()

    def test_4_firmware_error_navigation(self):
        w = self.window()
        src = self.root / 'firmware/f133/src/lcd_status.c'
        original = src.read_text()
        try:
            ed = w.open_document(src)
            type_over(ed, 'int broken = ;\n' + original)
            w.a_save.trigger()
            w.set_target('lcd')
            w.a_build.trigger()
            self.wait_idle(w)
            self.assertEqual(w.plan.argv, ['firmware', 'build', '--target', 'status-lcd'])
            self.assertNotEqual(w.router.exit_code, 0)
            # The error the user caused (line 1) must survive in the report and be listed first.
            first, first_path = w.problems[0]
            self.assertEqual((first_path, first.line, first.severity), (src.resolve(), 1, 'error'), w.router.raw[:1500])
            w.a_next.trigger()
            self.assertEqual(w.current_editor().path, src.resolve())
            self.assertEqual(w.current_editor().position()[0], 1)
        finally:
            ed = w.document_for(src)
            type_over(ed, original)
            w.a_save.trigger()
            w.close()

    def test_5_browse_and_read_only_evidence(self):
        from workbench.qt_app import BrowseTab
        w = self.window()
        top = w.nav.topLevelItem(0)
        firmware = top.child(0)
        w._nav_clicked(firmware)
        tab = w.tabs.currentWidget()
        self.assertIsInstance(tab, BrowseTab)
        self.assertEqual(tab.pane.folder, (self.root / 'firmware').resolve())
        w.browse(self.root / 'sdk')
        self.assertEqual(sum(isinstance(w.tabs.widget(i), BrowseTab) for i in range(w.tabs.count())), 1)
        w.a_dual.setChecked(True)
        w.toggle_dual()
        self.assertIsNotNone(tab.right)
        handoff = next((self.root / 'passes').glob('ARC1-PASS-*/HANDOFF.md'))
        ed = w.open_document(handoff)
        self.assertTrue(ed.isReadOnly())
        self.assertFalse(w.save_document(ed))
        w.close()

    def test_6_resource_budgets_in_inspector(self):
        w = self.window()
        self.assertFalse(w.inspector_dock.isVisible())
        w.a_budgets.trigger()
        self.pump(200)
        self.assertTrue(w.inspector_dock.isVisible())
        self.assertEqual(w.inspector_tabs.tabText(w.inspector_tabs.currentIndex()), 'Resources')
        frame, links, memory = w.budget_charts
        self.assertEqual(sum(1 for r in frame.rows if r['value'] is None), 4)   # drawn as "not measured"
        self.assertEqual([r['value'] for r in frame.rows if r['value'] is not None], [9.0, 13.0])
        self.assertIsNotNone(links.marker)
        self.assertIn('Source: r10_gates', frame.rows[3]['tip'])
        self.assertFalse(frame.grab().isNull())
        w.close()


if __name__ == '__main__':
    result = unittest.main(exit=False, verbosity=2).result
    secs = getattr(AcceptanceWorkflowTests, 'workflow_seconds', None)
    if secs is not None:
        print('Acceptance workflow (find, open, edit, save, build, error, navigate, fix, rebuild, run): %.1f s' % secs)
    elif not HAVE_QT:
        print('NOTE: PySide6 missing; the Qt acceptance workflow did not run.')
    sys.exit(0 if result.wasSuccessful() else 1)
