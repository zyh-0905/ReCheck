"""Response-label regression. Uses archived response locally, never sends it."""
import copy,json,tempfile,unittest
from pathlib import Path
from r7clib.transport import Client
from pilot.client import RunStopped
from pilot.common import read_json
ROOT=Path(__file__).resolve().parents[1]
def cfg():return read_json(ROOT/'config.example.json')
def record(label='deepseek-flash',fp='fixture-fingerprint'):
 return {'status':'ok','text':'{"done":"ready"}','response':{'model':label,'system_fingerprint':fp,'choices':[{'finish_reason':'stop','message':{'content':'{"done":"ready"}'}}],'usage':{'prompt_tokens':48,'completion_tokens':21,'total_tokens':69,'completion_tokens_details':{'reasoning_tokens':15}}}}
class IdentityAmendmentTests(unittest.TestCase):
 def test_observed_response_label_accepted_and_both_labels_saved(self):
  with tempfile.TemporaryDirectory() as d:
   r=record();c=Client(cfg(),d);c._validate_saved(r)
   p=read_json(Path(d)/'endpoint_identity.json');self.assertEqual(p['requested_model'],'deepseek-v4-flash');self.assertEqual(p['returned_model'],'deepseek-flash')
 def test_exact_requested_response_also_accepted_at_smoke(self):
  with tempfile.TemporaryDirectory() as d:Client(cfg(),d)._validate_saved(record('deepseek-v4-flash'))
 def test_unknown_model_rejected(self):
  for name in ('deepseek-v4-pro','deepseek-flash-unknown','fixture','',None,1):
   with self.subTest(name=name),tempfile.TemporaryDirectory() as d:
    with self.assertRaises(RunStopped):Client(cfg(),d)._validate_saved(record(name))
 def test_fingerprint_missing_rejected(self):
  for fp in (None,'',False,[],1):
   with self.subTest(fp=fp),tempfile.TemporaryDirectory() as d:
    with self.assertRaises(RunStopped):Client(cfg(),d)._validate_saved(record(fp=fp))
 def test_allowed_label_cannot_switch_inside_run(self):
  with tempfile.TemporaryDirectory() as d:
   c=Client(cfg(),d);c._validate_saved(record())
   with self.assertRaises(RunStopped):c._validate_saved(record('deepseek-v4-flash'))
 def test_fingerprint_cannot_switch_inside_run(self):
  with tempfile.TemporaryDirectory() as d:
   c=Client(cfg(),d);c._validate_saved(record())
   with self.assertRaises(RunStopped):c._validate_saved(record(fp='different'))
 def test_archived_real_response_regression(self):
  r=read_json(ROOT/'docs/PAUSED_SMOKE_RESPONSE.json');before=copy.deepcopy(r)
  with tempfile.TemporaryDirectory() as d:Client(cfg(),d)._validate_saved(r)
  self.assertEqual(r,before)
 def test_invalid_usage_still_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   r=record();r['response']['usage']['total_tokens']=100
   with self.assertRaises(RunStopped):Client(cfg(),d)._validate_saved(r)
 def test_truncation_still_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   r=record();r['response']['choices'][0]['finish_reason']='length'
   with self.assertRaises(RunStopped):Client(cfg(),d)._validate_saved(r)
 def test_invalid_json_still_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   r=record();r['text']='NOT JSON'
   with self.assertRaises(RunStopped):Client(cfg(),d)._validate_saved(r)
 def test_response_label_missing_does_not_write_identity(self):
  with tempfile.TemporaryDirectory() as d:
   r=record();del r['response']['model']
   with self.assertRaises(RunStopped):Client(cfg(),d)._validate_saved(r)
   self.assertFalse((Path(d)/'endpoint_identity.json').exists())
 def test_request_model_is_not_rewritten(self):
  from pilot.common import request_payload
  c=cfg();before=copy.deepcopy(c)
  with tempfile.TemporaryDirectory() as d:Client(c,d)._validate_saved(record())
  self.assertEqual(c,before);self.assertEqual(request_payload(c,[])['model'],'deepseek-v4-flash')

class IdentityAuditTests(unittest.TestCase):
 def test_smoke_only_cannot_be_completed_research(self):
  from tests.test_transport import Service
  from tests.test_runtime import copy_kit
  from r7clib.runtime import prepare,smoke
  from r7clib.audit import audit
  with Service() as s,tempfile.TemporaryDirectory() as d:
   p=copy_kit(d);prepare(p,s.cfg);smoke(p,1,secret='local-fixture-key')
   a=audit(p);self.assertTrue(a['mechanical_pass']);self.assertFalse(a.get('execution_complete',True));self.assertEqual(a.get('smoke_status'),'completed')
 def test_endpoint_metadata_tamper_is_detected(self):
  from tests.test_transport import Service
  from tests.test_runtime import copy_kit
  from r7clib.runtime import prepare,smoke
  from r7clib.audit import audit
  from pilot.common import write_json
  with Service() as s,tempfile.TemporaryDirectory() as d:
   p=copy_kit(d);prepare(p,s.cfg);smoke(p,1,secret='local-fixture-key')
   f=p/'runs/R7C_smoke/endpoint_identity.json';o=read_json(f);o['system_fingerprint']='tampered';write_json(f,o)
   self.assertFalse(audit(p)['mechanical_pass'])
 def test_missing_endpoint_metadata_is_detected(self):
  from tests.test_transport import Service
  from tests.test_runtime import copy_kit
  from r7clib.runtime import prepare,smoke
  from r7clib.audit import audit
  with Service() as s,tempfile.TemporaryDirectory() as d:
   p=copy_kit(d);prepare(p,s.cfg);smoke(p,1,secret='local-fixture-key')
   (p/'runs/R7C_smoke/endpoint_identity.json').unlink();self.assertFalse(audit(p)['mechanical_pass'])
