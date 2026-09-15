
import unittest,copy
from r7clib.prompts import initial_messages,decode_action,episode_schedule
class ProtocolTests(unittest.TestCase):
 def test_schedule(self):
  s=episode_schedule()
  self.assertEqual(len(s),48)
  self.assertEqual(sum(x['phase']=='primary' for x in s),42)
  self.assertEqual(sum(x['phase']=='repeat' for x in s),6)
  self.assertEqual(len({x['episode_id'] for x in s}),48)
 def test_cap(self):self.assertEqual(len(episode_schedule())*8+1,385)
 def test_order_deterministic(self):self.assertEqual(episode_schedule(),episode_schedule())
 def test_stateless_ablation(self):
  p={'user_request':'hi','historical_memory':{'SECRET_PRIOR':1},'preceding_task_observations':[1]}
  m=initial_messages(p,'stateless');self.assertNotIn('SECRET_PRIOR',str(m));self.assertEqual(m[-1]['role'],'user')
 def test_inherited_rule_same_data(self):
  p={'user_request':'hi','historical_memory':{'x':1},'preceding_task_observations':[]}
  self.assertEqual(initial_messages(p,'inherited')[-1],initial_messages(p,'resolve_rule')[-1])
 def test_read_does_not_mutate(self):
  p={'user_request':'hi','historical_memory':{'x':1},'preceding_task_observations':[]};q=copy.deepcopy(p)
  initial_messages(p,'stateless');self.assertEqual(p,q)
 def test_no_unknown_arm(self):
  with self.assertRaises(ValueError):initial_messages({},'oracle')
 def test_actions(self):
  self.assertEqual(decode_action('{"tool":"search_contacts","arguments":{"name":"x"}}')[0],'tool')
 def test_done(self):self.assertEqual(decode_action('{"done":"done"}')[0],'done')
 def test_bad_schema(self):
  for x in ('{"tool":"a","arguments":{},"answer":1}','{"done":3}','{"tool":3,"arguments":{}}'):
   with self.subTest(x=x),self.assertRaises(ValueError):decode_action(x)
 def test_no_json_repair(self):
  for x in ('```json\\n{}\\n```','[]','{"done":"a","done":"b"}','{"x":NaN}'):
   with self.subTest(x=x),self.assertRaises(ValueError):decode_action(x)

class FiniteJSONTests(unittest.TestCase):
 def test_numeric_overflow_is_rejected(self):
  from r7clib.prompts import strict_object
  with self.assertRaises(ValueError):strict_object('{"tool":"x","arguments":{"x":1e999}}')
