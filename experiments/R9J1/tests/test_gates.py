import unittest, tempfile, json
from pathlib import Path
from pilot.common import read_json,write_json
from pilot.client import RunStopped
from r9lib.identity import response_identity
from r9lib.runtime import can_start
from r9lib.transport import validate_config_profile
ROOT=Path(__file__).resolve().parents[1]
class Gates(unittest.TestCase):
 def test_two_explicit_return_labels_only(self):
  cfg=read_json(ROOT/'config.example.json')
  for x in ('deepseek-v4-flash','deepseek-flash'):
   r=response_identity(cfg,{'model':x,'system_fingerprint':'f'});self.assertFalse(r['weight_identity_verified'])
  with self.assertRaises(RunStopped):response_identity(cfg,{'model':'deepseek-other','system_fingerprint':'f'})
 def test_fingerprint_required(self):
  cfg=read_json(ROOT/'config.example.json')
  for x in (None,'', '  ',1):
   with self.assertRaises(RunStopped):response_identity(cfg,{'model':'deepseek-flash','system_fingerprint':x})
 def test_output_budget_not_changed_by_attempt_budget(self):
  c=read_json(ROOT/'config.example.json');validate_config_profile(c)
  self.assertEqual(c['max_output_tokens'],16384);self.assertEqual(c['max_requests'],360)
 def test_paused_not_resumed(self):
  with tempfile.TemporaryDirectory() as d:
   write_json(Path(d)/'runs/R9_main/status.json',{'status':'paused'})
   with self.assertRaises(ValueError):can_start(d,'R9_main')
 def test_running_not_resumed(self):
  with tempfile.TemporaryDirectory() as d:
   write_json(Path(d)/'runs/R9_main/status.json',{'status':'running'})
   with self.assertRaises(ValueError):can_start(d,'R9_main')
 def test_completed_not_repeated(self):
  with tempfile.TemporaryDirectory() as d:
   write_json(Path(d)/'runs/R9_main/status.json',{'status':'completed'})
   self.assertFalse(can_start(d,'R9_main'))
 def test_orphan_call_not_repeated(self):
  with tempfile.TemporaryDirectory() as d:
   write_json(Path(d)/'runs/R9_main/calls/a.json',{})
   with self.assertRaises(ValueError):can_start(d,'R9_main')
