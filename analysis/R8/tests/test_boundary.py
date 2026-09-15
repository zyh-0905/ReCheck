import sys,unittest,socket
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'code'))
import bootstrap
from boundary import run_case,score_write
class Contracts(unittest.TestCase):
 def test_stable_person(self):self.assertTrue(run_case()['safe_success'])
 def test_stable_literal(self):self.assertTrue(run_case('literal')['safe_success'])
 def test_stable_reminder(self):self.assertTrue(run_case('reminder')['safe_success'])
 def test_person_gap_is_wrong(self):self.assertTrue(run_case('person','binding','after_resolve')['wrong_write'])
 def test_reminder_gap_is_wrong(self):self.assertTrue(run_case('reminder','binding','after_resolve')['wrong_write'])
 def test_literal_gap_is_not_wrong(self):self.assertTrue(run_case('literal','binding','after_resolve')['safe_success'])
 def test_person_before_check_is_safe(self):self.assertTrue(run_case('person','binding','before_resolve')['safe_success'])
 def test_reminder_before_check_is_safe(self):self.assertTrue(run_case('reminder','binding','before_resolve')['safe_success'])
 def test_person_after_commit_stays_valid(self):self.assertTrue(run_case('person','binding','after_use')['safe_success'])
 def test_reminder_after_commit_stays_valid(self):self.assertTrue(run_case('reminder','binding','after_use')['safe_success'])
 def test_global_blocks_unrelated(self):self.assertEqual(run_case('person','unrelated','after_resolve','global_guard')['rejections'],1)
 def test_scoped_allows_unrelated(self):self.assertTrue(run_case('person','unrelated','after_resolve','scoped_guard')['safe_success'])
 def test_global_blocks_nonbinding(self):self.assertEqual(run_case('reminder','nonbinding','after_resolve','global_guard')['rejections'],1)
 def test_scoped_allows_nonbinding(self):self.assertTrue(run_case('reminder','nonbinding','after_resolve','scoped_guard')['safe_success'])
 def test_scoped_blocks_person(self):
  r=run_case('person','binding','after_resolve','scoped_guard');self.assertEqual((r['safe_success'],r['wrong_write'],r['rejections']),(False,False,1))
 def test_scoped_blocks_reminder(self):self.assertEqual(run_case('reminder','binding','after_resolve','scoped_guard')['rejections'],1)
 def test_retry_person(self):
  r=run_case('person','binding','after_resolve','scoped_retry1');self.assertTrue(r['safe_success']);self.assertEqual(r['rejections'],1)
 def test_retry_reminder(self):self.assertTrue(run_case('reminder','binding','after_resolve','scoped_retry1')['safe_success'])
 def test_churn_retry_exhaustion(self):
  r=run_case('person','binding','after_resolve','scoped_retry1',True);self.assertEqual((r['safe_success'],r['wrong_write'],r['rejections']),(False,False,2))
 def test_no_network(self):
  with self.assertRaisesRegex(RuntimeError,'R8_OFFLINE'):socket.create_connection(('example.com',443))
 def test_invalid_intent(self):
  with self.assertRaises(ValueError):run_case('not_an_intent')
 def test_invalid_policy(self):
  with self.assertRaises(ValueError):run_case(policy='invented')
 def test_invalid_timing(self):
  with self.assertRaises(ValueError):run_case('person','binding','none')
 def test_stable_no_irrelevant_writes(self):self.assertFalse(run_case('person')['invariant_error'])

class ScorerNegativeCases(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  import copy
  cls.p=run_case('person');cls.r=run_case('reminder')
 def check(self,row,before=None,after=None):
  w=row['writes'][0]
  return score_write(row['intent'],row['request'],before if before is not None else w['before_world'],after if after is not None else w['after_world'])
 def test_correct_native_write_scores(self):self.assertTrue(self.check(self.p))
 def test_wrong_phone_rejected(self):
  import copy
  a=copy.deepcopy(self.p['writes'][0]['after_world']);a['messaging'][-1]['recipient_phone_number']='+12025550199';self.assertFalse(self.check(self.p,after=a))
 def test_duplicate_new_message_rejected(self):
  import copy
  a=copy.deepcopy(self.p['writes'][0]['after_world']);new=list((__import__('boundary').rowbag(a['messaging'])-__import__('boundary').rowbag(self.p['writes'][0]['before_world']['messaging'])).elements())[0]
  a['messaging'].append(__import__('json').loads(new));self.assertFalse(self.check(self.p,after=a))
 def test_history_deletion_rejected(self):
  import copy
  a=copy.deepcopy(self.p['writes'][0]['after_world']);a['messaging']=[];self.assertFalse(self.check(self.p,after=a))
 def test_unrelated_contact_write_rejected(self):
  import copy
  a=copy.deepcopy(self.p['writes'][0]['after_world']);a['contact'][0]['name']='Changed';self.assertFalse(self.check(self.p,after=a))
 def test_wrong_reminder_time_rejected(self):
  import copy
  a=copy.deepcopy(self.r['writes'][0]['after_world'])
  for row in a['reminder']:row['reminder_timestamp']=0.0
  self.assertFalse(self.check(self.r,after=a))
 def test_extra_reminder_change_rejected(self):
  import copy
  a=copy.deepcopy(self.r['writes'][0]['after_world'])
  for row in a['reminder']:row['content']='Changed'
  self.assertFalse(self.check(self.r,after=a))
 def test_literal_does_not_require_person_identity(self):
  r=run_case('literal','binding','after_resolve');self.assertTrue(self.check(r))
 def test_guard_reject_does_not_equal_success(self):
  r=run_case('person','binding','after_resolve','scoped_guard');self.assertFalse(r['safe_success']);self.assertFalse(r['wrong_write']);self.assertEqual(len(r['writes']),0)
 def test_actual_query_count_guard(self):self.assertEqual(run_case('person',policy='scoped_guard')['tool_calls'],3)
 def test_actual_query_count_retry(self):self.assertEqual(run_case('person','binding','after_resolve','scoped_retry1')['tool_calls'],5)
 def test_all_fixed_specs_count(self):self.assertEqual(len(list(__import__('boundary').all_specs())),120)

if __name__=='__main__':unittest.main()
