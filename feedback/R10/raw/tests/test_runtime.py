import unittest,tempfile,shutil,json
from pathlib import Path
from core.common import write,read,sha,source_paths
from core.runtime import prepare,run_study,export
from core.audit import audit
from core.contract import ContractError
from scripts.fixture_model import build_exchange
ROOT=Path(__file__).resolve().parents[1]

def clone(dest):
 for d in ('core','fixtures','scripts'):shutil.copytree(ROOT/d,dest/d,ignore=shutil.ignore_patterns('__pycache__'))
 for f in ('config.json','protocol.json'):shutil.copy2(ROOT/f,dest/f)
 write(dest/'SOURCE_MANIFEST.json',{'files':{p.relative_to(dest).as_posix():{'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in source_paths(dest)}})
 return dest

class RuntimeTests(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.root=clone(Path(self.tmp.name)/'kit')
 def tearDown(self):self.tmp.cleanup()
 def test_prepare_has_no_model_calls(self):
  result=prepare(self.root);self.assertEqual(result['new_model_calls'],0);self.assertFalse((self.root/'runs').exists())
 def test_wrong_cap_before_key(self):
  prepare(self.root)
  with self.assertRaises(ContractError):run_study(self.root,100,secret='fixture')
 def test_whole_study_and_replay(self):
  prepare(self.root);x,n=build_exchange();s=run_study(self.root,384,secret='fixture-not-secret',exchange=x)
  self.assertEqual(s['status'],'completed');self.assertEqual(len(s['completed_episodes']),48);self.assertLessEqual(n[0],384)
  a=audit(self.root);self.assertTrue(a['mechanical_pass']);self.assertEqual(a['primary_episodes'],48)
  count=n[0];same=run_study(self.root,384,secret='fixture-not-secret',exchange=x);self.assertEqual(same,s);self.assertEqual(count,n[0])
  self.assertTrue(Path(export(self.root)).is_file())
 def test_bad_batch_retains_prefix(self):
  prepare(self.root);x,n=build_exchange('late_bad');s=run_study(self.root,384,secret='fixture-not-secret',exchange=x);self.assertEqual(s['status'],'paused');self.assertEqual(n[0],2)
  a=audit(self.root);self.assertTrue(a['mechanical_pass']);self.assertEqual(a['primary_episodes'],0);self.assertGreaterEqual(a['partial_database_events'],1)
  with self.assertRaises(ContractError):run_study(self.root,384,secret='fixture-not-secret',exchange=x)
  self.assertEqual(n[0],2)
 def test_prose_no_tools_not_a_success(self):
  prepare(self.root);x,n=build_exchange('prose');s=run_study(self.root,384,secret='fixture-not-secret',exchange=x);self.assertEqual(s['status'],'completed');self.assertEqual(n[0],48);self.assertFalse(any(e['score']['trace_safe_success'] for e in s['completed_episodes']))
 def test_modified_config_rejected(self):
  c=read(self.root/'config.json');c['max_attempts']=1000;write(self.root/'config.json',c)
  with self.assertRaises(ContractError):prepare(self.root)
 def test_fabricated_score_rejected(self):
  prepare(self.root);x,n=build_exchange('prose');run_study(self.root,384,secret='fixture-not-secret',exchange=x)
  p=next((self.root/'runs/main/episodes').glob('*.json'));data=read(p)
  if p.name.endswith('.partial.json'):p=Path(str(p).replace('.partial.json','.json'));data=read(p)
  data['score']['goal_final']=True;write(p,data)
  with self.assertRaises(ContractError):audit(self.root)
 def test_source_mutation_rejected(self):
  with (self.root/'core/cases.py').open('a') as f:f.write('\n# changed\n')
  with self.assertRaises(ContractError):prepare(self.root)
if __name__=='__main__':unittest.main()
