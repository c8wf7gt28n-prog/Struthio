import json, subprocess, sys, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'sdk'/'cli'))
from arc1cli import branding
from arc1cli.core import Result

class BrandingTests(unittest.TestCase):
    def test_manifest_and_assets(self):
        r=Result('arc1 brand','STATIC_CHECK')
        branding.inspect_brand(r)
        self.assertEqual(r.verdict,'PASS',r.failures)
        self.assertEqual(len(r.artifacts),3)
    def test_lcd_sizes(self):
        obj=branding.identity()
        self.assertEqual(obj['display_name'],'ARC-1')
        for state,rows in obj['lcd']['states'].items():
            self.assertEqual(len(rows),2,state)
            self.assertTrue(all(len(s)<=16 and s.isascii() for s in rows),state)
    def test_command_json(self):
        p=subprocess.run([sys.executable,str(ROOT/'arc1'),'brand','--json'],capture_output=True,text=True,timeout=30)
        self.assertEqual(p.returncode,0,p.stderr)
        r=json.loads(p.stdout)
        self.assertEqual(r['verdict'],'PASS')
        self.assertEqual(r['evidence_level'],'STATIC_CHECK')
        self.assertFalse(r['details']['hardware_lcd_verified'])

if __name__=='__main__':unittest.main()
