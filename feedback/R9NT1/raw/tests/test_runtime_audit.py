import copy,json,shutil,tempfile,unittest,zipfile,os
from pathlib import Path
from helpers import *
from nt.runtime import checked,prepare,run_study,export
from nt.audit import audit
from nt.common import read,write
from nt.contract import ContractError
class RuntimeAuditTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)/'kit'
  shutil.copytree(ROOT,self.root,ignore=shutil.ignore_patterns('runs','uploads','__pycache__','PREPARED.json','.git','.run.lock'))
  freeze(self.root)
 def tearDown(self):self.tmp.cleanup()
 def test_prepare_no_paid_exchange(self):
  r=prepare(self.root);self.assertEqual(r['new_model_calls'],0);self.assertFalse((self.root/'runs').exists());self.assertEqual(r,prepare(self.root))
 def test_frozen_parameter_tamper(self):
  cfg=read(self.root/'config.json');cfg['max_attempts']=361;write(self.root/'config.json',cfg);freeze(self.root)
  with self.assertRaises(ContractError):checked(self.root)
 def test_confirmation_is_required(self):
  prepare(self.root);w=SequenceWire([None])
  with self.assertRaises(ContractError):run_study(self.root,12,'local-fixture-key-not-real',w)
  self.assertEqual(w.n,0)
 def test_complete_all_even_failed_goals(self):
  prepare(self.root);w=SequenceWire(lambda n,p:None);r=run_study(self.root,360,'local-fixture-key-not-real',w)
  self.assertEqual(r['status'],'completed');self.assertEqual(w.n,36);self.assertEqual(len(r['completed_episodes']),36)
  a=audit(self.root);self.assertTrue(a['mechanical_pass']);self.assertTrue(a['execution_complete']);self.assertEqual(a['reconstructed_requests'],36)
  self.assertEqual(a['primary_episodes'],32);self.assertEqual(a['repeat_episodes'],4)
  self.assertFalse(any(x['score']['trace_safe_success'] for x in r['completed_episodes']))
  run_study(self.root,360);self.assertEqual(w.n,36)
 def test_malformed_batch_pause_and_export(self):
  prepare(self.root);w=SequenceWire([[('get_wifi_status',{}),('run_shell',{})]])
  r=run_study(self.root,360,'local-fixture-key-not-real',w);self.assertEqual(r['status'],'paused');self.assertEqual(w.n,1)
  a=audit(self.root);self.assertTrue(a['mechanical_pass']);self.assertFalse(a['execution_complete']);self.assertEqual(a['reconstructed_requests'],1)
  self.assertEqual(a['native_tool_events'],0)
  with self.assertRaises(ContractError):run_study(self.root,360,'local-fixture-key-not-real',w)
  out=export(self.root)
  with zipfile.ZipFile(out) as z:
   self.assertIn('BUNDLE_MANIFEST.json',z.namelist());self.assertIn('LICENSE',z.namelist())
   self.assertIn('runs/main/attempts/000001_response.raw',z.namelist())
 def test_identity_change_stops_not_restarts(self):
  prepare(self.root)
  def response(n,p):return (200,json.dumps(reply(n,None,fingerprint='first' if n==1 else 'other')).encode())
  w=SequenceWire(response);r=run_study(self.root,360,'local-fixture-key-not-real',w)
  self.assertEqual(r['status'],'paused');self.assertEqual(w.n,2);self.assertEqual(len(r['completed_episodes']),1)
  a=audit(self.root);self.assertTrue(a['mechanical_pass']);self.assertFalse(a['execution_complete'])
 def test_partial_native_events_are_not_dropped(self):
  prepare(self.root);w=SequenceWire([[('get_cellular_service_status',{})],[('run_shell',{})]])
  r=run_study(self.root,360,'local-fixture-key-not-real',w);self.assertEqual(r['status'],'paused')
  a=audit(self.root);self.assertTrue(a['mechanical_pass'],a)
  self.assertEqual(a['native_tool_events'],1);self.assertEqual(a['environment_operations'],2)
  self.assertEqual(a['partial_native_tool_events'],1);self.assertEqual(a['primary_episodes'],0)
 def test_http_failure_stops_and_preserves(self):
  prepare(self.root);w=SequenceWire(lambda n,p:(429,b'{"error":"quota"}'))
  r=run_study(self.root,360,'local-fixture-key-not-real',w);self.assertEqual(w.n,1);self.assertEqual(r['status'],'paused')
  self.assertTrue(audit(self.root)['mechanical_pass'])
 def test_missing_request_result_not_completed(self):
  prepare(self.root);w=SequenceWire(lambda n,p:None);run_study(self.root,360,'local-fixture-key-not-real',w)
  (self.root/'runs/main/attempts/000001_response.json').unlink()
  self.assertFalse(audit(self.root)['mechanical_pass'])
 def test_forged_tool_reply_and_score_rejected(self):
  prepare(self.root);w=SequenceWire(lambda n,p:None);run_study(self.root,360,'local-fixture-key-not-real',w)
  f=next((self.root/'runs/main/episodes').glob('*.json'));r=read(f);r['score']['goal_final']=True;write(f,r)
  self.assertFalse(audit(self.root)['mechanical_pass'])
 def test_extra_attempt_or_response_rejected(self):
  prepare(self.root);w=SequenceWire(lambda n,p:None);run_study(self.root,360,'local-fixture-key-not-real',w)
  p=self.root/'runs/main/attempts';shutil.copyfile(p/'000001_response.raw',p/'999999_response.raw')
  self.assertFalse(audit(self.root)['mechanical_pass'])
 def test_source_tamper_prevents_model_call(self):
  prepare(self.root);(self.root/'nt/engine.py').write_text('# tampered')
  w=SequenceWire([None])
  with self.assertRaises(ContractError):run_study(self.root,360,'local-fixture-key-not-real',w)
  self.assertEqual(w.n,0)
 def test_active_lock_blocks_export(self):
  (self.root/'.run.lock').write_text('locked')
  with self.assertRaises(ContractError):export(self.root)
 def test_used_run_without_status_is_orphan(self):
  prepare(self.root);d=self.root/'runs/main';d.mkdir(parents=True);(d/'orphan').write_text('x')
  with self.assertRaises(ContractError):run_study(self.root,360,'local-fixture-key-not-real',SequenceWire([None]))
if __name__=='__main__':unittest.main()
