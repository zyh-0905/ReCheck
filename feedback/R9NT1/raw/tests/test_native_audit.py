import unittest,tempfile,shutil,json,copy
from pathlib import Path
from helpers import *
from nt.runtime import prepare,run_study
from nt.audit import audit
from scripts.http_fixture import fixture_response

class NativeAuditTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory();cls.base=Path(cls.tmp.name)/'base'
  shutil.copytree(ROOT,cls.base,ignore=shutil.ignore_patterns('runs','uploads','__pycache__','PREPARED.json','.git','.run.lock'))
  freeze(cls.base);prepare(cls.base);cls.n=0
  def wire(p):
   cls.n+=1;return 200,json.dumps(fixture_response(p,cls.n,'batch')).encode()
  cls.run_result=run_study(cls.base,360,'local-fixture-key-not-real',wire)
 @classmethod
 def tearDownClass(cls):cls.tmp.cleanup()
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)/'kit';shutil.copytree(self.base,self.root)
 def tearDown(self):self.tmp.cleanup()
 def test_native_complete_roundtrip_and_event_replay(self):
  a=audit(self.root);self.assertTrue(a['mechanical_pass'],a);self.assertTrue(a['execution_complete']);self.assertEqual(a['reconstructed_requests'],self.n)
  self.assertEqual(a['primary_episodes'],32);self.assertEqual(a['repeat_episodes'],4);self.assertGreater(a['environment_operations'],0)
 def test_receipt_id_corruption(self):
  f=next((self.root/'runs/main/episodes').glob('*.json'));r=read(f);r['turns'][0]['tool_messages'][0]['tool_call_id']='invented';write(f,r)
  self.assertFalse(audit(self.root)['mechanical_pass'])
 def test_forged_success_state(self):
  f=self.root/'runs/main/episodes/primary_n02_inherited.json';r=read(f);r['score']['wrong_write']=False;write(f,r)
  self.assertFalse(audit(self.root)['mechanical_pass'])
 def test_last_tool_progress_is_verified(self):
  p=self.root/'runs/main/partial/primary_n06_verify_confirm/tool_progress.json'
  r=read(p);r['tool_count']=999;write(p,r)
  self.assertFalse(audit(self.root)['mechanical_pass'])
 def test_event_trigger_corruption(self):
  f=self.root/'runs/main/episodes/primary_n02_inherited.json';r=read(f);r['exposure']['triggered']=False;write(f,r)
  self.assertFalse(audit(self.root)['mechanical_pass'])
 def test_native_tool_parameters_changed(self):
  f=self.root/'runs/main/episodes/primary_n02_inherited.json';r=read(f);r['events'][0]['arguments']['name']='Other';write(f,r)
  self.assertFalse(audit(self.root)['mechanical_pass'])
 def test_same_response_event_link_changed(self):
  f=self.root/'runs/main/episodes/primary_n02_inherited.json';r=read(f);r['turns'][0]['executions'][1]['event_start']=1;write(f,r)
  self.assertFalse(audit(self.root)['mechanical_pass'])
 def test_rewrite_complete_status_to_unmatched_cases(self):
  p=self.root/'runs/main/status.json';r=read(p);r['completed_episodes'].pop();write(p,r)
  self.assertFalse(audit(self.root)['mechanical_pass'])
 def test_reasoning_removed_even_when_hashes_recomputed(self):
  a=self.root/'runs/main/attempts'
  f=next(f for f in sorted(a.glob('*_request.json')) if len(read(f)['payload']['messages'])>2)
  r=read(f);del r['payload']['messages'][2]['reasoning_content'];r['payload_sha256']=digest(r['payload']);r['request_sha256']=digest({'endpoint':CONFIG['endpoint'],'payload':r['payload']});write(f,r)
  p=f.with_name(f.name.replace('_request.json','_response.json'));rr=read(p)
  for k in r:rr[k]=r[k]
  write(p,rr);self.assertFalse(audit(self.root)['mechanical_pass'])
if __name__=='__main__':unittest.main()
