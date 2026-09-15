import unittest,tempfile,json,copy
from pathlib import Path
from helpers import *
from nt.engine import run_episode,initial_messages
from nt.contract import ContractError

class EngineTests(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
 def tearDown(self):self.tmp.cleanup()
 def run_seq(self,c,seq,arm='inherited'):
  w=SequenceWire(seq);cl=client(self.root,w);r=run_episode(c,spec(c,arm),cl,self.root);return r,w
 def test_public_prompt_variants_equal(self):
  for fam in ('person','phone','reminder','wifi'):
   a=initial_messages(case(fam,'stable'),'inherited')
   for v in ('pre_relevant','post_relevant','post_unrelated'):self.assertEqual(a,initial_messages(case(fam,v),'inherited'))
 def test_prompt_no_private_labels(self):
  c=case();m=initial_messages(c,'inherited');text=json.dumps(m)
  for k in ('relevant_operations','world_before','snapshot','post_relevant','scheduled','triggered','correct_answer'):self.assertNotIn(k,text)
  self.assertNotEqual(m,initial_messages(c,'verify_confirm'))
 def test_unknown_arm(self):
  with self.assertRaises((ValueError,ContractError)):initial_messages(case(),'wrong')
 def test_native_end_to_end_real_reply(self):
  c=case('phone');r,w=self.run_seq(c,[[('get_cellular_service_status',{})],[('send_message_with_phone_number',{'phone_number':c['contract']['phone_number'],'content':c['contract']['content']})],None])
  self.assertEqual(r['model_calls'],3);self.assertEqual(r['tool_calls'],2);self.assertTrue(r['score']['trace_safe_success']);self.assertTrue(r['terminated'])
  m=w.payloads[1]['messages'];self.assertEqual(m[-1]['role'],'tool');self.assertEqual(json.loads(m[-1]['content'])['value'],True)
  self.assertIn('reasoning_content',m[-2]);self.assertTrue(all('tools' in p and 'response_format' not in p for p in w.payloads))
 def test_read_event_write_inside_one_model_response(self):
  c=case('person','post_relevant');r,w=self.run_seq(c,[[('search_contacts',{'name':c['contract']['name']}),('send_message_with_phone_number',{'phone_number':c['old_phone'],'content':c['contract']['content']})],None])
  self.assertTrue(r['score']['wrong_write']);self.assertFalse(r['score']['goal_final']);self.assertTrue(r['exposure']['triggered'])
  self.assertEqual([e['scope'] for e in r['events']],['agent','environment','environment','agent'])
  self.assertEqual(r['turns'][0]['executions'][0]['event_start'],0);self.assertEqual(r['turns'][0]['executions'][1]['event_start'],3)
  msgs=w.payloads[1]['messages'];tools=[m for m in msgs if m['role']=='tool'];self.assertEqual(len(tools),2)
  self.assertEqual(json.loads(tools[0]['content'])['value'][0]['phone_number'],c['old_phone'])
  self.assertNotIn('scope',tools[0]['content']);self.assertEqual(r['model_calls'],2)
 def test_event_between_responses_second_read_sees_change(self):
  c=case('person','post_relevant')
  def seq(n,p):
   if n<=2:return [('search_contacts',{'name':c['contract']['name']})]
   if n==3:return [('send_message_with_phone_number',{'phone_number':json.loads(p['messages'][-1]['content'])['value'][0]['phone_number'],'content':c['contract']['content']})]
   return None
  r,w=self.run_seq(c,seq);self.assertTrue(r['score']['trace_safe_success']);self.assertEqual(r['environment_operations'],2)
 def test_skip_anchor_keeps_unexposed(self):
  c=case('person','post_relevant');r,_=self.run_seq(c,[[('send_message_with_phone_number',{'phone_number':c['old_phone'],'content':c['contract']['content']})],[('search_contacts',{'name':c['contract']['name']})],None])
  self.assertFalse(r['exposure']['triggered']);self.assertTrue(r['exposure']['missed_before_primary_write']);self.assertTrue(r['score']['trace_safe_success'])
 def test_pre_event_not_in_public_input(self):
  c=case('person','pre_relevant');r,_=self.run_seq(c,[[('search_contacts',{'name':c['contract']['name']})],None]);self.assertEqual(r['events'][0]['scope'],'environment');self.assertFalse(r['score']['goal_final'])
 def test_batch_all_validated_before_first_tool(self):
  c=case();w=SequenceWire([[('get_cellular_service_status',{}),('run_shell',{'command':'ignored'})]])
  with self.assertRaises(ContractError):run_episode(c,spec(c),client(self.root,w),self.root)
  b=read(self.root/'partial'/spec(c)['episode_id']/'boundary.json');self.assertEqual(b['events'],[])
  self.assertFalse((self.root/'episodes'/(spec(c)['episode_id']+'.json')).exists())
 def test_duplicate_ids_abort_batch(self):
  c=case()
  def bad(n,p):return (200,json.dumps(reply(n,[native_call('get_cellular_service_status',{},'same'),native_call('get_wifi_status',{},'same')])).encode())
  with self.assertRaises(ContractError):self.run_seq(c,bad)
 def test_four_tools_per_response_and_ten_requests(self):
  c=case('wifi');r,w=self.run_seq(c,lambda n,p:[('get_wifi_status',{})]*4)
  self.assertEqual(r['model_calls'],10);self.assertEqual(r['tool_calls'],40);self.assertEqual(w.n,10);self.assertFalse(r['terminated']);self.assertEqual(r['stop_reason'],'request_cap')
 def test_five_tools_rejected_without_dispatch(self):
  with self.assertRaises(ContractError):self.run_seq(case(),[[('get_wifi_status',{})]*5])
 def test_finish_claim_is_not_success(self):
  r,w=self.run_seq(case(),[None]);self.assertTrue(r['terminated']);self.assertFalse(r['score']['trace_safe_success']);self.assertEqual(r['tool_calls'],0)
 def test_tool_error_returns_then_recovery(self):
  c=case('wifi','post_relevant');r,w=self.run_seq(c,[[('get_low_battery_mode_status',{})],[('set_wifi_status',{'on':True})],[('set_low_battery_mode_status',{'on':False}),('set_wifi_status',{'on':True})],None])
  self.assertTrue(r['score']['trace_safe_success']);self.assertEqual(r['score']['tool_errors'],1)
  self.assertFalse(json.loads(w.payloads[2]['messages'][-1]['content'])['ok'])
 def test_success_at_cap_not_terminated(self):
  c=case('phone');r,w=self.run_seq(c,lambda n,p:[('get_cellular_service_status',{})] if n<10 else [('send_message_with_phone_number',{'phone_number':c['contract']['phone_number'],'content':c['contract']['content']})])
  self.assertTrue(r['score']['trace_safe_success']);self.assertFalse(r['terminated']);self.assertEqual(r['model_calls'],10)
 def test_wrong_then_correct_does_not_erase(self):
  c=case('person','post_relevant')
  r,w=self.run_seq(c,[[('search_contacts',{'name':c['contract']['name']})],[('send_message_with_phone_number',{'phone_number':c['old_phone'],'content':c['contract']['content']})],[('search_contacts',{'name':c['contract']['name']})],[('send_message_with_phone_number',{'phone_number':c['new_phone'],'content':c['contract']['content']})],None])
  self.assertTrue(r['score']['goal_final']);self.assertTrue(r['score']['wrong_write']);self.assertFalse(r['score']['trace_safe_success'])
if __name__=='__main__':unittest.main()
