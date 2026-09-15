import copy,json,unittest
from pathlib import Path
from saved_check import check
ROOT=Path(__file__).resolve().parents[1]
def fixture():
 return json.loads((ROOT/'results/revision_run1/trajectories/correct_revision.json').read_text())
class SavedTests(unittest.TestCase):
 def test_genuine_records(self):
  for f in (ROOT/'results/revision_run1/trajectories').glob('*.json'):
   d=json.loads(f.read_text());self.assertEqual(check(d)['scoped_contract'],d['scoped_contract'])
 def rejects(self,mutate):
  r=fixture();mutate(r)
  with self.assertRaises(ValueError):check(r)
 def test_wrong_target(self):self.rejects(lambda d:d['target_ids_bound_at_initial_friend_query'].pop())
 def test_wrong_scope(self):self.rejects(lambda d:d['first_goal_active_interval'].__setitem__(1,len(d['states'])-1))
 def test_changed_observation(self):self.rejects(lambda d:d['states'][-1]['contacts'][0].__setitem__('relationship','friend'))
 def test_wrong_native_args(self):self.rejects(lambda d:d['events'][1]['arguments'].__setitem__('relationship','boss'))
 def test_wrong_native_ok(self):self.rejects(lambda d:d['events'][1]['response'].__setitem__('ok',False))
 def test_wrong_reported_count(self):self.rejects(lambda d:d.__setitem__('native_tool_calls',999))
 def test_wrong_outcome(self):self.rejects(lambda d:d.__setitem__('scoped_contract',False))
 def test_changed_snapshot(self):self.rejects(lambda d:d['final_snapshot']['_dbs']['CONTACT'][-1].__setitem__('phone_number','wrong'))
 def test_duplicate_event(self):self.rejects(lambda d:d['events'].append(copy.deepcopy(d['events'][0])))
 def test_wrong_marker(self):self.rejects(lambda d:d.__setitem__('evidence_kind','LLM_RESULT'))
 def test_score_metadata_changed(self):self.rejects(lambda d:d['official_evaluation'].__setitem__('similarity',-1))
if __name__=='__main__':unittest.main()
