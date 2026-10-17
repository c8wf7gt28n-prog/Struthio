"""CLI-level integration tests for firmware project commands."""
import json, sys, subprocess, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def cli(*args):
    return subprocess.run([sys.executable,str(ROOT/"arc1"),*args,"--json"],cwd=str(ROOT),capture_output=True,text=True,timeout=150)
class FirmwareWorkbenchTests(unittest.TestCase):
    def test_status(self):
        p=cli("firmware","status")
        self.assertEqual(p.returncode,0,p.stderr)
        d=json.loads(p.stdout)
        self.assertFalse(d["details"]["device_flash_enabled"])
        self.assertFalse(d["details"]["target_binary_linked"])
    def test_build(self):
        p=cli("firmware","build","--target","status-lcd")
        self.assertEqual(p.returncode,0,p.stdout+p.stderr)
        d=json.loads(p.stdout)
        self.assertTrue(d["artifacts"])
        self.assertIn("relocatable",d["details"]["artifact_kind"])
    def test_tests(self):
        p=cli("firmware","test")
        self.assertEqual(p.returncode,0,p.stdout+p.stderr)
        d=json.loads(p.stdout)
        self.assertEqual(d["test_count"],4)  # R05+ adds 2 more portable host tests
        self.assertEqual(d["failed_count"],0)
    def test_flash_gated(self):
        p=cli("device","deploy")
        self.assertNotEqual(p.returncode,0)
        d=json.loads(p.stdout)
        self.assertEqual(d["verdict"],"NOT_AVAILABLE")
if __name__=="__main__": unittest.main()
