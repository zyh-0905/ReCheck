import unittest,tempfile,json,copy,hashlib,zipfile
from pathlib import Path
from pilot.common import read_json,write_json,digest,request_payload
from r4lib import session,storage,protocol,experiment,worker,review
ROOT=Path(__file__).resolve().parents[1]

class SupportTests(unittest.TestCase):
 def test_r4_cap(self):
  self.assertTrue(hasattr(session,'validate_r4_config'));c=read_json(ROOT/'config.example.json');self.assertEqual(session.validate_r4_config(c)['max_requests'],408)
 def test_no_cap_edit(self):
  self.assertTrue(hasattr(session,'validate_r4_config'));c=read_json(ROOT/'config.example.json');c['max_requests']=999
  with self.assertRaises(ValueError):session.validate_r4_config(c)
 def test_no_thinking_edit(self):
  self.assertTrue(hasattr(session,'validate_r4_config'));c=read_json(ROOT/'config.example.json');c['extra_body']={}
  with self.assertRaises(ValueError):session.validate_r4_config(c)
 def test_r4_cli_registered(self):self.assertIn('r4.py',[p.name for p in storage.source_paths(ROOT)])
 def test_export_snapshot_license(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);f=r/'runs/R4_recheck/code_snapshot/LICENSE';f.parent.mkdir(parents=True);f.write_text('Research license')
   write_json(r/'runs/R4_recheck/manifest.json',{'source_hashes':{'LICENSE':hashlib.sha256(f.read_bytes()).hexdigest()}})
   out=storage.export_bundle(r)
   with zipfile.ZipFile(out) as z:self.assertIn('runs/R4_recheck/code_snapshot/LICENSE',z.namelist())
 def test_feedback_no_configs(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);(r/'config.local.json').write_text('secret config');(r/'.env').write_text('private')
   out=storage.export_bundle(r)
   with zipfile.ZipFile(out) as z:self.assertFalse(any('config.local' in x or '.env' in x for x in z.namelist()))

