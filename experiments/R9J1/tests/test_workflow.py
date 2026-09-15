import unittest,tempfile,json,copy
from pathlib import Path
from r9lib.experiment import run_episode
from r9lib.scenarios import build_cases
from r9lib.rules import rule_action,history_from_messages
from r9lib.prompts import episode_schedule
class Fake:
 def __init__(self,mode='extra_read',bad=False):self.n=0;self.mode=mode;self.bad=bad
 def complete(self,lid,messages,meta=None):
  self.n+=1;pub,hist=history_from_messages(messages)
  if self.bad:obj={'tool':'__import__','arguments':{'name':'os'}}
  elif self.mode=='loop':obj={'tool':'get_cellular_service_status','arguments':{}}
  else:obj=rule_action(pub,hist,self.mode)
  return {'text':json.dumps(obj),'request_sha256':'fixture'}
class Workflow(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.cs=build_cases()
 def runit(self,c,mode='extra_read',bad=False):
  with tempfile.TemporaryDirectory() as d:
   return run_episode(c,{'episode_id':'test','phase':'primary','case_id':c['id'],'arm':'inherited'},Fake(mode,bad),d)
 def test_extraread_has_solvable_all_fixed_cases(self):
  for c in self.cs:
   r=self.runit(c);self.assertTrue(r['score']['trace_safe_success'],(c['id'],r['score']));self.assertTrue(r['terminated'])
 def test_model_is_not_frozen_after_first_write(self):
  c=next(c for c in self.cs if c['family']=='reminder' and c['variant']=='post_relevant');r=self.runit(c,'post_confirm')
  self.assertTrue(r['score']['goal_final']);self.assertTrue(r['score']['final_state_clean']);self.assertFalse(r['score']['trace_safe_success']);self.assertTrue(r['terminated'])
 def test_cap_no_hidden_extra_request(self):
  r=self.runit(self.cs[0],'loop');self.assertEqual(r['model_calls'],10);self.assertFalse(r['terminated'])
 def test_disallowed_no_execution(self):
  r=self.runit(self.cs[0],bad=True);self.assertFalse(r['score']['wrong_write']);self.assertFalse(r['score']['trace_safe_success'])
 def test_rule_action_only_public(self):
  from inspect import signature
  self.assertEqual(list(signature(rule_action).parameters),['public','hist','mode'])
 def test_case_not_mutated(self):
  c=copy.deepcopy(self.cs[2]);old=copy.deepcopy(c);self.runit(c);self.assertEqual(old,c)
 def test_counts_and_repeats(self):
  ss=episode_schedule();self.assertEqual(len(ss),36);self.assertEqual(sum(s['phase']=='primary' for s in ss),32);self.assertEqual(len({s['episode_id'] for s in ss}),36)
