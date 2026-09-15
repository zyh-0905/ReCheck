
import tempfile,unittest,json,shutil,copy
from pathlib import Path
from r7clib.runtime import prepare,smoke,run,status
from r7clib.artifacts import source_hashes
from r7clib.audit import audit
from tests.test_transport import Service
ROOT=Path(__file__).resolve().parents[1]
def copy_kit(out):
 out=Path(out)
 shutil.copytree(ROOT,out,dirs_exist_ok=True,ignore=shutil.ignore_patterns('runs','uploads','offline_reports','PREPARED.json','__pycache__','verification'))
 (out/'SOURCE_MANIFEST.json').write_text(json.dumps({'sha256':source_hashes(out)}))
 return out
class RuntimeTests(unittest.TestCase):
 def test_run_before_smoke_blocked(self):
  with tempfile.TemporaryDirectory() as d:
   p=copy_kit(d);prepare(p)
   with self.assertRaises(ValueError):run(p,384,secret='not_sent')
 def test_invalid_confirmation_blocked(self):
  with tempfile.TemporaryDirectory() as d:
   p=copy_kit(d)
   with self.assertRaises(ValueError):run(p,400,secret='not_sent')
 def test_prepare_frozen_and_no_api(self):
  with tempfile.TemporaryDirectory() as d:
   p=copy_kit(d);a=prepare(p);b=prepare(p);self.assertEqual(a,b)
   self.assertFalse((p/'runs').exists())
 def test_smoke_once(self):
  with Service() as s,tempfile.TemporaryDirectory() as d:
   p=copy_kit(d);prepare(p,s.cfg);self.assertEqual(smoke(p,1,secret='nonpublic-test-credential')['status'],'completed')
   smoke(p,1,secret='nonpublic-test-credential');self.assertEqual(s.n,1)
 def test_bad_smoke_blocks_batch(self):
  with Service(['invalid']) as s,tempfile.TemporaryDirectory() as d:
   p=copy_kit(d);prepare(p,s.cfg);self.assertEqual(smoke(p,1,secret='nonpublic-test-credential')['status'],'paused')
   with self.assertRaises(ValueError):run(p,384,secret='nonpublic-test-credential')
   with self.assertRaises(ValueError):smoke(p,1,secret='nonpublic-test-credential')
   self.assertEqual(s.n,1)
 def test_changed_source_blocks(self):
  with tempfile.TemporaryDirectory() as d:
   p=copy_kit(d);prepare(p);(p/'protocol.json').write_text('{}')
   with self.assertRaises(ValueError):smoke(p,1,secret='not_sent')

class OrphanTests(unittest.TestCase):
 def test_orphan_starts_without_status_blocked(self):
  from r7clib.runtime import can_start
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'runs/R7C_main/attempts';p.mkdir(parents=True)
   (p/'000001_start.json').write_text('{}')
   with self.assertRaises(ValueError):can_start(d,'R7C_main')
