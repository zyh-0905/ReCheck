import unittest,tempfile,json,copy,hashlib,zipfile
from pathlib import Path
from pilot.common import read_json,write_json,digest,request_payload
from r3lib import session,storage,protocol,experiment,worker,review
ROOT=Path(__file__).resolve().parents[1]

class SupportTests(unittest.TestCase):
 def test_r3_cap(self):
  self.assertTrue(hasattr(session,'validate_r3_config'));c=read_json(ROOT/'config.example.json');self.assertEqual(session.validate_r3_config(c)['max_requests'],416)
 def test_no_cap_edit(self):
  self.assertTrue(hasattr(session,'validate_r3_config'));c=read_json(ROOT/'config.example.json');c['max_requests']=999
  with self.assertRaises(ValueError):session.validate_r3_config(c)
 def test_no_thinking_edit(self):
  self.assertTrue(hasattr(session,'validate_r3_config'));c=read_json(ROOT/'config.example.json');c['extra_body']={}
  with self.assertRaises(ValueError):session.validate_r3_config(c)
 def test_r3_cli_registered(self):self.assertIn('r3.py',[p.name for p in storage.source_paths(ROOT)])
 def test_export_snapshot_license(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);f=r/'runs/R3_recheck/code_snapshot/LICENSE';f.parent.mkdir(parents=True);f.write_text('Research license')
   write_json(r/'runs/R3_recheck/manifest.json',{'source_hashes':{'LICENSE':hashlib.sha256(f.read_bytes()).hexdigest()}})
   out=storage.export_bundle(r)
   with zipfile.ZipFile(out) as z:self.assertIn('runs/R3_recheck/code_snapshot/LICENSE',z.namelist())
 def test_feedback_no_configs(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);(r/'config.local.json').write_text('secret config');(r/'.env').write_text('private')
   out=storage.export_bundle(r)
   with zipfile.ZipFile(out) as z:self.assertFalse(any('config.local' in x or '.env' in x for x in z.namelist()))

class RecordingFixture:
 def __init__(self):self.calls=[]
 def complete(self,lid,msgs,meta=None):
  view=json.loads(msgs[1]['content']);e=view['evidence'];task=view['task'];p={}
  if 'amount_divisor' in view['allowed_keys']:p['amount_divisor']=e['amount_divisor']
  if 'time_bound' in view['allowed_keys']:p['time_bound']=task['cutoff']+(0 if e['endpoint_inclusive'] else 1)
  self.calls.append((lid,msgs,meta));return {'logical_id':lid,'text':json.dumps(p)}

class ExperimentTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.ready=hasattr(experiment,'run')
  if cls.ready:
   cls.temp=tempfile.TemporaryDirectory();cls.root=Path(cls.temp.name);cls.fake=RecordingFixture()
   cls.cfg=read_json(ROOT/'config.example.json');cls.fixture_spec=protocol.load_protocol()
   for c in cls.fixture_spec['streams']:
    for k in ['task_seed','data_seed','world_seed']:c[k]+=7000000
   experiment.run(cls.fake,cls.cfg,cls.root,cls.fixture_spec)
 @classmethod
 def tearDownClass(cls):
  if cls.ready:cls.temp.cleanup()
 def setUp(self):self.assertTrue(self.ready,'R3 experiment not implemented')
 def test_counts(self):self.assertEqual(len(self.fake.calls),416);self.assertEqual(len(list((self.root/'records').glob('*.json'))),416)
 def test_distinct_ids(self):self.assertEqual(len(set(c[0] for c in self.fake.calls)),416)
 def test_replicates_payload_identical(self):
  m={lid:(msg,meta) for lid,msg,meta in self.fake.calls}
  for lid,(msg,meta) in m.items():
   if lid.endswith('/repeat'):self.assertEqual(msg,m[lid[:-6]+'primary'][0])
 def test_timestamp_not_in_worker(self):
  self.assertTrue(all('checked_at' not in json.dumps(msgs) for _,msgs,_ in self.fake.calls))
 def test_repeats_not_primary(self):
  rows=[read_json(x) for x in (self.root/'records').glob('*.json')]
  self.assertEqual(sum(x['replicate']=='primary' for x in rows),384);self.assertEqual(sum(x['replicate']=='repeat' for x in rows),32)
 def test_initial_evidence_from_receipts(self):
  rows=[read_json(x) for x in (self.root/'prefixes').glob('*.json')]
  self.assertEqual(len(rows),16);self.assertTrue(all(len(x['calibration'])==2 for x in rows))
 def test_canonical_success_not_100(self):
  cases={c['stream']:c for c in read_json(self.root/'private/recheck_cases.json')};success=[]
  for f in (self.root/'records').glob('*.json'):
   r=read_json(f);c=cases[r['stream']];success.append(worker.score(r['answer'],c['tasks'][r['step']],c)['success'])
  self.assertIn(False,success);self.assertIn(True,success)
 def test_offline_evaluator_not_called_in_online(self):
  old=worker.score;worker.score=lambda *args:(_ for _ in ()).throw(AssertionError('truth leaked'))
  try:
   with tempfile.TemporaryDirectory() as d:experiment.run(RecordingFixture(),self.cfg,Path(d),self.fixture_spec)
  finally:worker.score=old

if __name__=='__main__':unittest.main()
