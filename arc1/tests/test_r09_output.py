from pathlib import Path
import sys,unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from workbench.output_router import OutputRouter,parse_problems
class Tests(unittest.TestCase):
 def test_gcc_and_msvc(self):
  rows=parse_problems('src/a.c:12:4: error: bad token\nC:\\proj\\a.c(37,12): warning C4018: signed mismatch\nsrc/x.h:9: note: expanded from macro')
  self.assertEqual([(p.line,p.severity) for p in rows],[(12,'error'),(37,'warning'),(9,'note')])
 def test_unknown_failure_not_success(self):
  o=OutputRouter();o.start('firmware image');o.append('unknown failure\n')
  o.finish(6)
  self.assertIn('Command failed',o.summary());self.assertIn('EXIT: 6',o.summary())
 def test_clean_build_and_reset(self):
  o=OutputRouter();o.start('F133');o.append('successful');o.finish(0)
  self.assertIn('No recognized compiler errors',o.summary())
  o.start('D213');self.assertEqual(o.raw,'');self.assertIsNone(o.exit_code)
 def test_source_structure(self):
  qt=(ROOT/'workbench'/'qt_app.py').read_text()
  tk=(ROOT/'workbench'/'app.py').read_text()
  self.assertIn('def toggle_output',qt)
  self.assertIn('def toggle_output',tk)
  self.assertIn("'F10'",qt)
  self.assertIn("'<F10>'",tk)
  self.assertIn('self.router.finish',qt)
  self.assertIn('self.router.finish',tk)
  self.assertIn('Agent Activity',qt)
  self.assertIn('Agent Activity',tk)
if __name__=='__main__':unittest.main()
