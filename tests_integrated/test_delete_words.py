"""0.8.3, DELETE: the owner, 14 November 2026, "I want trash called DELETE."

The words hold together: DELETE is the place (capitals, a name, no article: "in DELETE"), Delete sends a thing there,
restore brings it back, and Erase takes words out of a page or records away for good, so Delete and Erase never mean each
other. The operations underneath keep their names (files.trash, the .trash folder). The can says DELETE, spaced a little,
and its box is exactly what it draws; searching for "trash" still finds it.
"""
import ast
import os
import re
import unittest
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from tests_integrated.kasandra_window_probe import probe

ROOT = Path(__file__).resolve().parents[1]
WORKBENCH = ROOT / 'workbench'


def strings(path):
    """The string constants of a module that are not docstrings."""
    tree = ast.parse(path.read_text(encoding='utf-8'));docs = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.body:
            first = node.body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):docs.add(id(first.value))
    return [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in docs]


class TheCan(unittest.TestCase):
    TIP = 'DELETE · what you delete waits here, and restore puts it back where it was · drop files here to delete them'

    def check(self, out, spacing):
        self.assertEqual(out['word'], 'DELETE');self.assertEqual(out['name'], 'DELETE');self.assertEqual(out['tip'], self.TIP)
        self.assertAlmostEqual(out['spacing'], spacing, delta=0.01);self.assertTrue(out['absolute'])      # Qt keeps it in 1/64 px
        self.assertEqual(out['size'], out['expected'], 'its box is exactly what it draws')

    def test_the_can_says_DELETE_in_kasandra(self):
        out = probe('kasandra', 1920, 1200, 'delete')
        self.check(out, 1.0);self.assertEqual(out['size'], [120, 29]);self.assertEqual(out['rect'], [218, 1094, 120, 29])

    def test_the_can_says_DELETE_in_graphite(self):
        self.check(probe('graphite', 1366, 768, 'delete'), 0.8)


class TheWords(unittest.TestCase):
    def test_no_Trash_is_shown(self):
        for path in sorted(WORKBENCH.glob('*.py')):
            if path.name in ('version.py', 'qt_app.py'):continue      # the release history; the legacy rooms' keys list (to be removed)
            for text in strings(path):
                if (path.name, text) == ('shell2.py', 'Trash'):continue      # shell2.ALSO: typing the old word still finds DELETE
                self.assertIsNone(re.search(r'\bTrash\b', text), '%s: %r' % (path.name, text[:120]))
                self.assertIsNone(re.search(r'\bthe DELETE\b', text), '%s: %r' % (path.name, text[:120]))

    def test_Delete_and_Erase_never_meet(self):
        tree = ast.parse((WORKBENCH / 'context_menu.py').read_text(encoding='utf-8'))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and getattr(node.func, 'id', None) == 'Entry' and len(node.args) >= 2 \
                    and all(isinstance(a, ast.Constant) for a in node.args[:2]):
                key, label = node.args[0].value, node.args[1].value
                if label == 'Delete':self.assertEqual(key, 'trash')
                if key == 'edit:delete':self.assertEqual(label, 'Erase')
        from workbench import context_menu as cm
        rows = {(kind, key) for _, word, kind, key in cm.FOLDED if word == 'Delete'}
        self.assertTrue(rows and rows <= {('file', 'trash'), ('passage', 'edit:delete')}, rows)
        memory = (WORKBENCH / 'memory_qt.py').read_text(encoding='utf-8')
        self.assertIn('Erase profile and feedback', memory);self.assertNotIn('Delete profile', memory)
        self.assertIn('Erase every recorded instruction and outcome?', (WORKBENCH / 'office_building_qt.py').read_text(encoding='utf-8'))

    def test_DELETE_is_a_search_place(self):
        from workbench.shell2 import OneBox
        box = SimpleNamespace(host=SimpleNamespace(actions=lambda: []))
        self.assertEqual([label for label, _, _ in OneBox.commands(box, 'trash')], ['DELETE'], 'the old word still finds it')
        self.assertIn('DELETE', [label for label, _, _ in OneBox.commands(box, 'dele')])

    def test_the_words_say_DELETE(self):
        from workbench import stacy_hand, tail_words
        self.assertEqual(tail_words.WORDS['files.trash'], 'Deleted (in DELETE)')
        self.assertEqual(tail_words.WORDS['files.restore'], 'Restored from DELETE')
        self.assertIn('DELETE, once emptied, cannot be brought back', strings(WORKBENCH / 'stacy_hand.py'))


if __name__ == '__main__':
    unittest.main()
