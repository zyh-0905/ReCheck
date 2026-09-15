
import unittest,tempfile,json,copy
from pathlib import Path
from r7clib.experiment import run_episode
from r7clib.cases import make_cases,rule_action
from r7clib.prompts import strict_object
from r7clib.goals import evaluate

class Fake:
 def __init__(self,loop=False,bad=False):self.n=0;self.loop=loop;self.bad=bad
 def complete(self,logical_id,messages,meta=None):
  self.n+=1
  pub=json.loads(messages[1]['content']);hist=[]
  for a,b in zip(messages[2::2],messages[3::2]):
   action=json.loads(a['content'])
   if 'tool' in action:hist.append({**action,'response':json.loads(b['content'].removeprefix('TOOL_RESULT '))})
  obj={'tool':'get_cellular_service_status','arguments':{}} if self.loop else rule_action(pub,hist,'resolve')
  if self.bad:obj={'tool':'__import__','arguments':{'name':'os'}}
  return {'text':json.dumps(obj),'request_sha256':'fixture','status':'ok'}
class WorkflowTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.cs=make_cases()
 def test_rule_dialogue_all_cases(self):
  for c in self.cs:
   with tempfile.TemporaryDirectory() as d:
    r=run_episode(c,{'episode_id':'test','phase':'primary','case_id':c['id'],'arm':'inherited'},Fake(),Path(d))
    self.assertTrue(r['score']['safe_success'],(c['id'],r));self.assertTrue(r['terminated'])
 def test_eight_call_cap(self):
  with tempfile.TemporaryDirectory() as d:
   f=Fake(loop=True);r=run_episode(self.cs[0],{'episode_id':'test','phase':'primary','case_id':'c00','arm':'inherited'},f,Path(d))
   self.assertEqual(f.n,8);self.assertFalse(r['terminated']);self.assertFalse(r['score']['safe_success'])
 def test_disallowed_calls_never_execute(self):
  with tempfile.TemporaryDirectory() as d:
   f=Fake(bad=True);r=run_episode(self.cs[0],{'episode_id':'test','phase':'primary','case_id':'c00','arm':'inherited'},f,Path(d))
   self.assertFalse(r['score']['safe_success']);self.assertFalse(r['score']['wrong_write'])
 def test_output_contains_all_turns(self):
  with tempfile.TemporaryDirectory() as d:
   r=run_episode(self.cs[0],{'episode_id':'test','phase':'primary','case_id':'c00','arm':'resolve_rule'},Fake(),Path(d))
   q=json.loads((Path(d)/'episodes/test.json').read_text());self.assertEqual(r,q)
   self.assertEqual(len(r['turns']),3)
 def test_case_is_not_mutated(self):
  c=copy.deepcopy(self.cs[2]);before=copy.deepcopy(c)
  with tempfile.TemporaryDirectory() as d:run_episode(c,{'episode_id':'test','phase':'primary','case_id':c['id'],'arm':'stateless'},Fake(),Path(d))
  self.assertEqual(before,c)
