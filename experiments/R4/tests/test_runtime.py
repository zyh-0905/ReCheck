import unittest,tempfile,threading,json,copy,shutil,io,contextlib,zipfile
from pathlib import Path
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from pilot.common import read_json,write_json,digest
from r4lib import session,storage,review
import r4
from unittest.mock import patch
from r4lib import protocol
ROOT=Path(__file__).resolve().parents[1]

class Handler(BaseHTTPRequestHandler):
 def log_message(self,*args):pass
 def do_POST(self):
  body=json.loads(self.rfile.read(int(self.headers['Content-Length'])));s=self.server;s.count+=1
  if len(body['messages'])==1:answer={'ok':True}
  else:
   from r4lib.worker import rule_plan
   v=json.loads(body['messages'][1]['content']);answer=rule_plan(v)
  text=json.dumps(answer);finish='stop'
  if s.mode=='length':finish='length';text=''
  if s.mode=='bad_json':text='not json'
  fingerprint='CHANGED' if s.mode=='identity' else 'FIXTURE_ONLY'
  response={'id':f'fixture-{s.count}','model':body['model'],'system_fingerprint':fingerprint,
   'choices':[{'message':{'content':text},'finish_reason':finish}],
   'usage':{'prompt_tokens':100,'completion_tokens':10,'total_tokens':110,'prompt_tokens_details':{'cached_tokens':0},'completion_tokens_details':{'reasoning_tokens':0}},
   'evidence_label':'SOFTWARE_TEST_NOT_RESEARCH'}
  data=json.dumps(response).encode();self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)

class LiveTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory();cls.root=Path(cls.tmp.name)/'kit';cls.root.mkdir()
  for f in storage.source_paths(ROOT):
   dst=cls.root/f.relative_to(ROOT);dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,dst)
  write_json(cls.root/'SOURCE_MANIFEST.json',{'sha256':storage.source_hashes(cls.root)})
  cls.server=ThreadingHTTPServer(('127.0.0.1',0),Handler);cls.server.count=0;cls.server.mode='normal'
  cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
  cls.cfg=read_json(ROOT/'config.example.json');cls.cfg.update(base_url=f'http://127.0.0.1:{cls.server.server_port}',local_no_auth=True,backend_kind='test_fixture',min_interval_seconds=0)
  write_json(cls.root/'config.local.json',cls.cfg);cls.capture=io.StringIO()
  load=protocol.load_protocol
  def fixture_protocol():
   p=load()
   for c in p['streams']:
    for k in ['task_seed','world_seed','data_seed']:c[k]+=8000000
   p['phase']='SOFTWARE_TEST_NOT_RESEARCH'
   return p
  with patch.object(protocol,'load_protocol',side_effect=fixture_protocol), patch.object(r4.offline,'factorial_report',return_value={'test_note':'separate full grid verification'}), contextlib.redirect_stdout(cls.capture):
   cls.prepared=r4.prepare(cls.root)
   try:r4.run_paid('run',408,cls.root)
   except ValueError:cls.blocked_before_smoke=True
   else:cls.blocked_before_smoke=False
   cls.smoke_rc=r4.run_paid('smoke',1,cls.root);cls.main_rc=r4.run_paid('run',408,cls.root)
   cls.count=cls.server.count;cls.resume_rc=r4.run_paid('run',408,cls.root);cls.count_after=cls.server.count
   cls.audits=r4._audit_existing(cls.root)
  # Retain an evidence summary only if explicitly requested by test harness.
  cls.bundle=storage.export_bundle(cls.root)
  import os
  target=os.environ.get('R4_TEST_REPORT')
  if target:
   write_json(target,{'label':'SOFTWARE_TEST_NOT_RESEARCH','smoke_calls':1,'main_calls':408,'total_local_http_fixture_calls':cls.count,
    'primary_records':cls.audits['R4_recheck']['completed_primary_records'],'repeat_records':cls.audits['R4_recheck']['completed_repeat_records'],
    'replay':cls.audits['R4_recheck']['replay_audit'],'budget_violations':cls.audits['R4_recheck']['budget_violations'],
    'source_snapshot_mismatches':cls.audits['R4_recheck']['source_snapshot_mismatches'],
    'no_resampling':cls.count_after==cls.count,'smoke_required':cls.blocked_before_smoke,
    'prices_unknown':all(x['price_estimate'] is None for x in cls.audits['R4_recheck']['methods']),
    'scientific_gate':cls.audits['R4_recheck']['scientific_gate'],'bundle':storage.verify_bundle(cls.bundle),
    'fixture_task_world_data_seeds_disjoint':True,'remote_llm_calls':0})
 @classmethod
 def tearDownClass(cls):cls.server.shutdown();cls.server.server_close();cls.thread.join();cls.tmp.cleanup()
 def test_smoke_required(self):self.assertTrue(self.blocked_before_smoke)
 def test_calls(self):self.assertEqual(self.count,409)
 def test_cli_completes(self):self.assertEqual((self.smoke_rc,self.main_rc),(0,0))
 def test_no_resampling(self):self.assertEqual(self.count_after,self.count);self.assertEqual(self.resume_rc,0)
 def test_replay(self):
  r=self.audits['R4_recheck']['replay_audit'];self.assertTrue(r['pass'],r);self.assertEqual(r['request_bodies_checked'],408)
 def test_record_counts(self):
  s=self.audits['R4_recheck'];self.assertEqual(s['completed_primary_records'],384);self.assertEqual(s['completed_repeat_records'],24)
 def test_repeat_inputs_not_outputs_reused(self):
  rs=self.audits['R4_recheck']['repeat_diagnostics'];self.assertEqual(len(rs),24);self.assertTrue(all(r['same_payload'] for r in rs))
 def test_snapshot_complete(self):self.assertEqual(self.audits['R4_recheck']['source_snapshot_mismatches'],[])
 def test_bundle(self):self.assertTrue(storage.verify_bundle(self.bundle)['pass'])
 def test_fixture_not_real_research(self):self.assertEqual(self.audits['R4_recheck']['evidence_label'],'SOFTWARE_TEST_NOT_RESEARCH')
 def test_prices_unknown(self):self.assertTrue(all(x['price_estimate'] is None for x in self.audits['R4_recheck']['methods']))
 def test_no_grading_live_api(self):self.assertEqual(self.server.count,409)
 def test_same_seed_no_result_cherry_pick(self):
  p=self.audits['R4_recheck']['paired_treatments'];self.assertEqual(len([x for x in p if x['replicate']=='primary']),288)
 def test_prepare_cannot_rewrite_after_run(self):
  with self.assertRaises(ValueError):r4.prepare(self.root)
 def test_consent_exact(self):
  with self.assertRaises(ValueError):r4.require_call_consent(400,408)
 def test_audit_command_expected_total(self):self.assertEqual(self.audits['R4_recheck']['completed_records'],408)

class PauseTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.server=ThreadingHTTPServer(('127.0.0.1',0),Handler);self.server.count=0;self.server.mode='length'
  self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
  self.cfg=read_json(ROOT/'config.example.json');self.cfg.update(base_url=f'http://127.0.0.1:{self.server.server_port}',local_no_auth=True,backend_kind='test_fixture',min_interval_seconds=0)
 def tearDown(self):self.server.shutdown();self.server.server_close();self.thread.join();self.tmp.cleanup()
 def test_truncation_saved_no_retry(self):
  c=session.Client(self.cfg,self.root,cap=1)
  with self.assertRaises(Exception):c.complete('one',[{'role':'user','content':'Return JSON'}])
  self.assertEqual(len(list((self.root/'calls').glob('*.json'))),1)
  with self.assertRaises(Exception):c.complete('one',[{'role':'user','content':'Return JSON'}])
  self.assertEqual(self.server.count,1)
 def test_invalid_json_no_retry(self):
  self.server.mode='bad_json';c=session.Client(self.cfg,self.root,cap=1)
  with self.assertRaises(Exception):c.complete('one',[{'role':'user','content':'Return JSON'}])
  self.assertEqual(self.server.count,1);self.assertEqual(c.budget()['attempts'],1)
 def test_uncertain_attempt_never_resent(self):
  from pilot.common import request_payload
  payload=request_payload(self.cfg,[{'role':'user','content':'X'}]);(self.root/'attempts').mkdir()
  write_json(self.root/'attempts/000001_start.json',{'attempt':1,'logical_id':'one','request_sha256':digest({'endpoint':self.cfg['base_url'],'payload':payload})})
  c=session.Client(self.cfg,self.root,cap=2)
  with self.assertRaises(Exception):c.complete('one',[{'role':'user','content':'X'}])
  self.assertEqual(self.server.count,0)
 def test_identity_pause(self):
  self.server.mode='normal';c=session.Client(self.cfg,self.root,cap=2);c.complete('one',[{'role':'user','content':'X'}]);self.server.mode='identity'
  with self.assertRaises(Exception):c.complete('two',[{'role':'user','content':'X'}])
  self.assertEqual(self.server.count,2);self.assertEqual(len(list((self.root/'calls').glob('*.json'))),2)

if __name__=='__main__':unittest.main()
