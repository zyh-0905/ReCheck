
import unittest,tempfile,json,zipfile,copy
from pathlib import Path
from r9lib.artifacts import source_hashes,verify_distribution,export_bundle,verify_bundle
class ArtifactTests(unittest.TestCase):
 def test_license_in_source(self):
  h=source_hashes(Path(__file__).resolve().parents[1])
  self.assertIn('vendor/toolsandbox/LICENSE',h)
 def test_snapshot_cannot_import_dill(self):
  from r9lib.native import NativeSession,base_snapshot
  x=copy.deepcopy(base_snapshot());x['interactive_console']='not trusted'
  with self.assertRaises(ValueError):NativeSession(x)
 def test_missing_manifest_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaises(ValueError):verify_distribution(Path(d))
 def test_export_empty_partial(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'protocol.json').write_text('{}');(p/'r9.py').write_text('# empty')
   b=export_bundle(p);self.assertTrue(verify_bundle(b)['pass'])
 def test_export_no_config_or_env(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'config.local.json').write_text('secret');(p/'.env').write_text('secret')
   b=export_bundle(p)
   with zipfile.ZipFile(b) as z:self.assertFalse(any('config.local' in n or '.env' in n for n in z.namelist()))
 def test_symlink_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'r9lib').mkdir();(p/'outside.py').write_text('x');(p/'r9lib/x.py').symlink_to(p/'outside.py')
   with self.assertRaises(ValueError):export_bundle(p)
 def test_credential_pattern_blocks(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'runs/R9_main').mkdir(parents=True);(p/'runs/R9_main/status.json').write_text('"sk-'+'X'*30+'"')
   with self.assertRaises(ValueError):export_bundle(p)
 def test_extra_archive_entry_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);b=export_bundle(p)
   with zipfile.ZipFile(b,'a') as z:z.writestr('unregistered','x')
   with self.assertRaises(ValueError):verify_bundle(b)
