import unittest,sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from corpus_audit import rebuild,goal,temporal

def call(cid, name='set_wifi_status',args=None):
 return {'id':cid,'type':'function','function':{'name':name,'arguments':json.dumps(args or {'on':False})}}
def receipt(cid, db=None, content='None',name='set_wifi_status'):
 x={'role':'tool','tool_call_id':cid,'name':name,'content':content}
 if db is not None:x['tool_details']={'database_update':db}
 return x

def sample(*messages):return {'trajectory':[list(messages)]}
class Tests(unittest.TestCase):
 def test_replace_not_merge(self):
  s=sample({'role':'user','content':'x','user_details':{'database_update':{'CONTACT':[{'person_id':'a'},{'person_id':'b'}]}}},{'role':'assistant','tool_calls':[call('1','remove_contact')]},receipt('1',{'CONTACT':[{'person_id':'b'}]},name='remove_contact'))
  self.assertEqual(rebuild(s)['points'][-1]['state']['CONTACT'],[{'person_id':'b'}])
 def test_missing_setting_not_false(self):self.assertIsNone(goal('wifi_off',{},{}))
 def test_wifi_false(self):self.assertTrue(goal('wifi_off',{'SETTING':[{'wifi':False}]},{}))
 def test_wifi_true(self):self.assertFalse(goal('wifi_off',{'SETTING':[{'wifi':True}]},{}))
 def test_bool_type_str(self):self.assertIsNone(goal('wifi_off',{'SETTING':[{'wifi':'false'}]},{}))
 def test_non_goal_low_battery(self):self.assertTrue(goal('turn_on_wifi_low_battery_mode',{'SETTING':[{'wifi':True,'low_battery_mode':True}]},{}))
 def test_authorized_final_friend_separate(self):
  ini={'CONTACT':[{'person_id':'a','relationship':'friend'}]}
  fin={'CONTACT':[{'person_id':'a','relationship':'friend'}]}
  self.assertFalse(goal('update_contact_relationship_with_relationship',fin,ini))
  self.assertTrue(goal('phase_friend',fin,ini))
 def test_no_vacuous_empty_friends(self):self.assertIsNone(goal('phase_friend',{'CONTACT':[]},{'CONTACT':[]}))
 def test_missing_target_is_false(self):
  ini={'CONTACT':[{'person_id':'a','relationship':'friend'}]}
  self.assertFalse(goal('phase_friend',{'CONTACT':[]},ini))
 def test_receipt_order_batch(self):
  s=sample({'role':'assistant','tool_calls':[call('a'),call('b')]},receipt('b',{'SETTING':[{'wifi':False}]}),receipt('a'))
  r=rebuild(s);self.assertEqual(len(r['batches']),1);self.assertEqual(r['batches'][0]['receipt_order'],['b','a']);self.assertEqual(len([p for p in r['points'] if p['kind']=='batch_end']),1)
 def test_orphan_receipt(self):self.assertIn('orphan_receipt:x',rebuild(sample(receipt('x')))['issues'])
 def test_missing_receipt(self):self.assertIn('missing_receipt:x',rebuild(sample({'role':'assistant','tool_calls':[call('x')]}))['issues'])
 def test_duplicate_call(self):
  s=sample({'role':'assistant','tool_calls':[call('x'),call('x')]},receipt('x'))
  self.assertIn('duplicate_call:x',rebuild(s)['issues'])
 def test_mutation_without_snapshot_unknown(self):
  r=rebuild(sample({'role':'user','user_details':{'database_update':{'SETTING':[{'wifi':True}]}}},{'role':'assistant','tool_calls':[call('x')]},receipt('x')))
  self.assertNotIn('SETTING',r['points'][-1]['state'])
 def test_tool_error_preserves_known(self):
  r=rebuild(sample({'role':'user','user_details':{'database_update':{'SETTING':[{'wifi':True}]}}},{'role':'assistant','tool_calls':[call('x')]},receipt('x',content='ValueError: Cannot change')))
  self.assertTrue(r['points'][-1]['state']['SETTING'][0]['wifi'])
 def test_conflicting_batch_snapshots_unknown(self):
  r=rebuild(sample({'role':'assistant','tool_calls':[call('x'),call('y')]},receipt('x',{'SETTING':[{'wifi':False}]}),receipt('y',{'SETTING':[{'wifi':True}]})))
  self.assertNotIn('SETTING',r['points'][-1]['state'])
 def test_retreat(self):self.assertTrue(temporal([False,True,False])['observed_regression'])
 def test_regression_repaired(self):
  r=temporal([False,True,False,True]);self.assertTrue(r['observed_regression']);self.assertFalse(r['ever_true_final_false'])
 def test_final_loss(self):self.assertTrue(temporal([None,True,False])['ever_true_final_false'])
 def test_final_unknown(self):self.assertIsNone(temporal([True,None])['ever_true_final_false'])
 def test_never_true(self):self.assertFalse(temporal([False,False])['ever_true_final_false'])
 def test_no_infer_across_unknown(self):self.assertFalse(temporal([True,None,False])['observed_regression'])
if __name__=='__main__':unittest.main()

class SemanticTests(unittest.TestCase):
 def test_relationship_case_is_not_semantic_failure(self):
  ini={'CONTACT':[{'person_id':'a','relationship':'friend'}]}
  self.assertTrue(goal('phase_enemy',{'CONTACT':[{'person_id':'a','relationship':'Enemy'}]},ini))
 def test_friend_set_case(self):
  ini={'CONTACT':[{'person_id':'a','relationship':'Friend'}]}
  self.assertTrue(goal('phase_friend',{'CONTACT':[{'person_id':'a','relationship':'friend'}]},ini))
 def test_name_case_whitespace(self):
  self.assertTrue(goal('add_contact_with_name_and_phone_number',{'CONTACT':[{'person_id':'a','name':'stephen  sondheim','phone_number':'+19876543210'}]},{}))
