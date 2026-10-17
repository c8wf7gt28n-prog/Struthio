"""R08 meaningful Qt-adjacent tests that do not pretend PySide6 is installed."""
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from workbench.qt_contract import editable_file, verify_drop
from workbench.cartridge import CartridgeError


class R08Contract(unittest.TestCase):
    def test_bounded_source_inside_project(self):
        self.assertEqual(editable_file(ROOT/'firmware'/'stage'/'f133_stage.c'),(ROOT/'firmware'/'stage'/'f133_stage.c').resolve())
        with self.assertRaises(ValueError): editable_file(Path('/etc/hosts'))
        with self.assertRaises(ValueError): editable_file(ROOT/'branding'/'ARC1_ENCLOSURE_CONCEPT.jpg')

    def test_symlink_and_size(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'tests') as folder:
            d=Path(folder)
            outside=d/'source.c';outside.write_text('hello',encoding='utf-8')
            link=d/'link.c';link.symlink_to(outside)
            with self.assertRaises(ValueError):editable_file(link)
            big=d/'big.c';big.write_bytes(b'A'*(2*1024*1024+1))
            with self.assertRaises(ValueError):editable_file(big)

    def test_verified_cartridge(self):
        report=verify_drop(ROOT/'cartridges'/'hello_arc1.arc1cart')
        self.assertTrue(report['valid'])
        self.assertFalse(report['executable_included'])
        with self.assertRaises(CartridgeError):verify_drop(ROOT/'firmware'/'stage'/'entry.S')
        with tempfile.TemporaryDirectory() as folder:
            corrupt=Path(folder)/'bad.arc1cart';corrupt.write_bytes(b'Not a valid cartridge')
            with self.assertRaises(CartridgeError):verify_drop(corrupt)

    def test_qt_source_is_syntactically_sound(self):
        import ast
        ast.parse((ROOT/'workbench'/'qt_app.py').read_text(encoding='utf-8'))
        ast.parse((ROOT/'workbench'/'qt_theme.py').read_text(encoding='utf-8'))
        visual=(ROOT/'workbench'/'qt_theme.py').read_text(encoding='utf-8')
        self.assertIn('QDockWidget',visual)
        # R10 Classic (owner decision): light ivory/gray surfaces with a restrained
        # orange accent replace R08's dark graphite. Subtle toolbar/button
        # gradients are now intended ("subtle material depth").
        from workbench.qt_theme import ORANGE, IVORY, SURFACE
        self.assertIn('border-top: 2px solid %s' % ORANGE, visual)
        for colour in (IVORY, SURFACE):
            self.assertIn(colour, visual)
        self.assertNotIn('#22272b', visual)   # R08 dark window background is gone


if __name__=='__main__': unittest.main()
