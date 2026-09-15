import unittest,tempfile,copy
from pathlib import Path
from core.common import read
from core.cases import make_cases
from core.schema import TOOLS
from core.prompts import messages,ARMS
from core.contract import canonical,validate_response,ContractError
from core.engine import run_episode

class FixtureClient:
 def __init__(self,replies):self.replies=replies;self.payloads=[];self.config={'model':'deepseek-flash'}
 def complete(self,logical_id,payload,metadata,tools,used_ids):
  i=len(self.payloads);self.payloads.append(copy.deepcopy(payload));x=self.replies[i]
  if isinstance(x,str):msg={'role':'assistant','content':x,'reasoning_content':'test only'};finish='stop'
  else:msg={'role':'assistant','content':None,'reasoning_content':'test only','tool_calls':[{'id':f'call_{i}_{j}','type':'function','function':{'name':name,'arguments':canonical(a)}} for j,(name,a) in enumerate(x)]};finish='tool_calls'
  body={'id':f'response_{i}','model':'deepseek-flash','system_fingerprint':'software_fixture','choices':[{'index':0,'message':msg,'finish_reason':finish}],'usage':{'prompt_tokens':10,'completion_tokens':5,'total_tokens':15}}
  return {'attempt':i+1,'logical_id':logical_id,'response':body,'latency_seconds':0,'validated':validate_response(body,tools,used_ids)}

class EngineTests(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
 def tearDown(self):self.tmp.cleanup()
 def case(self,i):
  c=make_cases()[i];c['historical_observation']={'value':{'id':c['target_id']},'source':'a prior legitimate query'};return c
 def spec(self,c,arm='generic'):return {'episode_id':c['id']+'_'+arm,'case_id':c['id'],'arm':arm,'phase':'primary'}
 def test_arm_user_inputs_identical(self):
  c=self.case(3);self.assertEqual(len({canonical(messages(c,a)[1]) for a in ARMS}),1)
 def test_no_hidden_case_label_in_payload(self):
  c=self.case(3);x=canonical(messages(c,'both'));self.assertNotIn('"change"',x);self.assertNotIn('"selection"',x);self.assertNotIn('alternate_id',x)
 def test_stable_full_chain(self):
  c=self.case(0);client=FixtureClient([[('resolve_service',{'service':c['key']})],[('update_config',{'id':c['target_id'],'max_attempts':5})],[('get_config',{'id':c['target_id']})],[('finish_task',{'status':'completed','message':'checked'})]])
  r=run_episode(c,self.spec(c),client,self.root);self.assertTrue(r['score']['trace_safe_success']);self.assertEqual(r['model_calls'],4);self.assertEqual(r['database_tool_calls'],3);self.assertTrue(r['terminated'])
 def test_same_batch_read_then_write_sees_injected_change(self):
  c=self.case(3);client=FixtureClient([[('resolve_service',{'service':c['key']}),('update_config',{'id':c['target_id'],'max_attempts':5})],[('finish_task',{'status':'completed','message':'done'})]])
  r=run_episode(c,self.spec(c),client,self.root);self.assertTrue(r['score']['wrong_write']);self.assertEqual([e['kind'] for e in r['events']],['tool','environment','tool']);self.assertTrue(r['false_completion_claim'])
 def test_tool_reply_ids_and_reasoning_preserved(self):
  c=self.case(0);cl=FixtureClient([[('get_config',{'id':c['target_id']})],[('finish_task',{'status':'incomplete','message':'stop'})]])
  run_episode(c,self.spec(c),cl,self.root);m=cl.payloads[1]['messages'];self.assertEqual(m[-1]['role'],'tool');self.assertEqual(m[-1]['tool_call_id'],'call_0_0');self.assertEqual(m[-2]['reasoning_content'],'test only')
 def test_bad_second_call_prevents_whole_batch(self):
  c=self.case(0);cl=FixtureClient([[('get_config',{'id':c['target_id']}),('arbitrary_sql',{})]])
  with self.assertRaises(ContractError):run_episode(c,self.spec(c),cl,self.root)
  partial=read(self.root/'episodes'/(self.spec(c)['episode_id']+'.partial.json'));self.assertEqual(partial['events'],[])
 def test_plain_final_records_unstructured_not_fake_tool(self):
  c=self.case(0);cl=FixtureClient(['I queried everything and completed it.']);r=run_episode(c,self.spec(c),cl,self.root);self.assertEqual(r['database_tool_calls'],0);self.assertFalse(r['score']['goal_final']);self.assertEqual(r['completion_claim'],'unstructured')
 def test_rejection_returned_not_fabricated_success(self):
  c=self.case(2);cl=FixtureClient([[('resolve_service',{'service':c['key']})],[('update_config',{'id':c['target_id'],'max_attempts':5,'expected_version':1})],[('finish_task',{'status':'incomplete','message':'conflict'})]])
  r=run_episode(c,self.spec(c),cl,self.root);self.assertFalse(r['score']['goal_final']);self.assertEqual(r['score']['conflicts'],1);self.assertIn('ROW_VERSION_CONFLICT',cl.payloads[-1]['messages'][-1]['content'])
 def test_turn_cap_no_extra_call(self):
  c=self.case(0);cl=FixtureClient([[('get_config',{'id':c['target_id']})]]*8);r=run_episode(c,self.spec(c),cl,self.root);self.assertEqual(r['model_calls'],8);self.assertFalse(r['terminated'])
 def test_finish_before_write_in_batch_rejected(self):
  c=self.case(0);cl=FixtureClient([[('finish_task',{'status':'completed','message':'done'}),('update_config',{'id':c['target_id'],'max_attempts':5})]])
  with self.assertRaises(ContractError):run_episode(c,self.spec(c),cl,self.root)
 def test_completed_repeat_refuses_reexecute(self):
  c=self.case(0);cl=FixtureClient([[('finish_task',{'status':'incomplete','message':'done'})]]);a=run_episode(c,self.spec(c),cl,self.root);b=run_episode(c,self.spec(c),cl,self.root);self.assertEqual(a,b);self.assertEqual(len(cl.payloads),1)
if __name__=='__main__':unittest.main()
