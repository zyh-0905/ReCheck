"""JSON mode is a disclosed request change, not lenient parsing or answer repair."""
from pathlib import Path
import unittest,copy,json,tempfile
from pilot.common import read_json,request_payload
from r9lib.transport import Client,validate_config_profile
from r9lib.prompts import strict_object,decode_action,initial_messages,episode_schedule
from pilot.client import RunStopped
ROOT=Path(__file__).resolve().parents[1]
class JSONAmendmentTests(unittest.TestCase):
 def config(self):return read_json(ROOT/'config.example.json')
 def test_json_output_explicitly_requested(self):self.assertEqual(self.config()['extra_body'].get('response_format'),{'type':'json_object'})
 def test_format_at_top_level(self):
  p=request_payload(self.config(),[{'role':'user','content':'JSON'}]);self.assertEqual(p.get('response_format'),{'type':'json_object'});self.assertNotIn('extra_body',p)
 def test_missing_format_refused(self):
  c=self.config();c['extra_body'].pop('response_format',None)
  with self.assertRaises(ValueError):validate_config_profile(c)
 def test_text_mode_refused(self):
  c=self.config();c['extra_body']['response_format']={'type':'text'}
  with self.assertRaises(ValueError):validate_config_profile(c)
 def test_strict_schema_not_silently_enabled(self):
  c=self.config();c['extra_body']['response_format']={'type':'json_schema','schema':{}}
  with self.assertRaises(ValueError):validate_config_profile(c)
 def test_no_task_shape_change(self):
  cases=read_json(ROOT/'fixtures/cases.json');s=episode_schedule();self.assertEqual(len(cases),16);self.assertEqual(len(s),36);self.assertEqual(s[0]['episode_id'],'primary_n06_verify_confirm')
 def test_all_prompts_have_json_and_examples(self):
  for case in read_json(ROOT/'fixtures/cases.json'):
   for arm in ('inherited','verify_confirm'):
    p=request_payload(self.config(),initial_messages(case['public'],arm));text=p['messages'][0]['content'];self.assertIn('JSON',text);self.assertIn('{"tool":',text);self.assertIn('{"done":',text)
 def test_observed_multiaction_still_rejected(self):
  txt=(ROOT/'tests/observed_invalid_output.txt').read_text()
  with self.assertRaises(ValueError):strict_object(txt)
 def test_observed_raw_response_still_pauses(self):
  txt=(ROOT/'tests/observed_invalid_output.txt').read_text()
  with tempfile.TemporaryDirectory() as d:
   body={'model':'deepseek-flash','system_fingerprint':'test','choices':[{'finish_reason':'stop','message':{'content':txt}}],'usage':{'prompt_tokens':2630,'completion_tokens':128,'total_tokens':2758}}
   with self.assertRaisesRegex(RunStopped,'Invalid JSON'):Client(self.config(),d)._validate_saved({'status':'ok','response':body,'text':txt})
 def test_valid_json_does_not_bypass_action_contract(self):
  with self.assertRaises(ValueError):decode_action('{"tool":"get_wifi_status","arguments":{},"done":"ok"}')
 def test_array_of_actions_rejected(self):
  with self.assertRaises(ValueError):strict_object('[{"tool":"get_wifi_status","arguments":{}}]')
 def test_duplicate_keys_rejected(self):
  with self.assertRaises(ValueError):strict_object('{"done":"a","done":"b"}')
 def test_empty_still_rejected(self):
  with self.assertRaises(ValueError):strict_object('')
 def test_output_and_turn_caps_unchanged(self):
  c=self.config();self.assertEqual(c['max_output_tokens'],16384);self.assertEqual(c['max_requests'],360);p=read_json(ROOT/'protocol.json');self.assertEqual(p['max_calls_per_episode'],10);self.assertEqual(p['combined_attempt_cap'],361)
if __name__=='__main__':unittest.main()
