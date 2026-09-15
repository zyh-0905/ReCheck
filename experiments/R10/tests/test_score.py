import unittest,tempfile,copy
from pathlib import Path
from core.cases import make_cases
from core.db import Store
from core.score import grade,target_id

class ScoreTests(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.stores=[]
 def tearDown(self):
  for s in self.stores:s.close()
  self.tmp.cleanup()
 def store(self,i):
  c=make_cases()[i];s=Store(c,Path(self.tmp.name)/f'{i}-{len(self.stores)}.sqlite');self.stores.append(s);return c,s
 def resolve(self,c,s):
  if c['goal_mode']=='literal':return s.call('get_config' if c['family']=='routing' else 'get_batch',{'id':c['target_id']})['value']
  return (s.call('resolve_service',{'service':c['key']}) if c['family']=='routing' else s.call('select_batch',{'lane':c['key'],'min_units':4}))['value']['record']
 def update(self,c,s,r,**extra):return s.call('update_config' if c['family']=='routing' else 'update_batch',{'id':r['id'],('max_attempts' if c['family']=='routing' else 'ready_after'):c['wanted'],**extra})
 def score(self,c,s):return grade(c,s.initial,s.events,s.world())
 def test_clean_update_is_success(self):
  c,s=self.store(0);r=self.resolve(c,s);self.update(c,s,r);g=self.score(c,s);self.assertTrue(g['trace_safe_success']);self.assertTrue(g['final_state_clean'])
 def test_zero_writes_is_not_success(self):
  c,s=self.store(0);g=self.score(c,s);self.assertFalse(g['goal_final']);self.assertFalse(g['wrong_write'])
 def test_lost_update_goal_true_state_and_trace_false(self):
  c,s=self.store(2);r=self.resolve(c,s);self.update(c,s,r,owner=r['owner']);g=self.score(c,s);self.assertTrue(g['goal_final']);self.assertFalse(g['final_state_clean']);self.assertTrue(g['wrong_write']);self.assertEqual(g['protected_field_changes'],1)
 def test_minimal_write_preserves_external_update(self):
  c,s=self.store(2);r=self.resolve(c,s);self.update(c,s,r);g=self.score(c,s);self.assertTrue(g['trace_safe_success']);self.assertTrue(g['final_state_clean'])
 def test_wrong_route_target_not_success(self):
  c,s=self.store(3);r=self.resolve(c,s);self.update(c,s,r);g=self.score(c,s);self.assertTrue(g['wrong_write']);self.assertFalse(g['goal_final'])
 def test_literal_target_does_not_follow_changed_route(self):
  c,s=self.store(4);r=self.resolve(c,s);self.update(c,s,r);self.assertTrue(self.score(c,s)['trace_safe_success'])
 def test_row_CAS_reject_is_not_completion(self):
  c,s=self.store(2);r=self.resolve(c,s);self.update(c,s,r,expected_version=r['version']);g=self.score(c,s);self.assertFalse(g['trace_safe_success']);self.assertFalse(g['wrong_write']);self.assertEqual(g['conflicts'],1)
 def test_reread_resolves_current_winner(self):
  c,s=self.store(9);self.resolve(c,s);r=self.resolve(c,s);self.update(c,s,r);self.assertTrue(self.score(c,s)['trace_safe_success'])
 def test_full_old_dispatch_overwrites_protected_carrier(self):
  c,s=self.store(8);r=self.resolve(c,s);self.update(c,s,r,carrier=r['carrier']);g=self.score(c,s);self.assertTrue(g['goal_final']);self.assertTrue(g['wrong_write']);self.assertFalse(g['final_state_clean'])
 def test_restore_wrong_field_does_not_erase_history(self):
  c,s=self.store(2);r=self.resolve(c,s);self.update(c,s,r,owner=r['owner']);s.call('update_config',{'id':r['id'],'owner':'operator-new'});g=self.score(c,s);self.assertTrue(g['final_state_clean']);self.assertFalse(g['trace_safe_success'])
 def test_final_business_state_excludes_version_only(self):
  c,s=self.store(0);r=self.resolve(c,s);self.update(c,s,r);self.update(c,s,r);self.assertTrue(self.score(c,s)['final_state_clean'])
 def test_event_cannot_legalize_earlier_actor_change(self):
  c,s=self.store(2)
  # Synthetic transcript mutation: an actor changes a protected row, then an
  # environment changes a different field. Delta-only reference must retain it.
  before=copy.deepcopy(s.initial);bad=copy.deepcopy(before);bad['configs'][2]['note']='bad'
  evafter=copy.deepcopy(bad);evafter['configs'][0]['owner']='operator-new'
  last=copy.deepcopy(evafter);last['configs'][0]['max_attempts']=5
  events=[{'index':0,'kind':'tool','name':'update_config','arguments':{'id':c['other_id'],'note':'bad'},'result':{'ok':True},'before':before,'after':bad},
   {'index':1,'kind':'environment','before':bad,'after':evafter},
   {'index':2,'kind':'tool','name':'update_config','arguments':{'id':c['target_id'],'max_attempts':5},'result':{'ok':True},'before':evafter,'after':last}]
  g=grade(c,before,events,last);self.assertFalse(g['final_state_clean']);self.assertTrue(g['wrong_write'])
 def test_broken_state_chain_rejected(self):
  c,s=self.store(0);self.resolve(c,s);bad=copy.deepcopy(s.events);bad[0]['before']['configs'][0]['note']='tampered'
  with self.assertRaises(ValueError):grade(c,s.initial,bad,s.world())
 def test_environment_delta_ownership_not_whole_world(self):
  c,s=self.store(2);self.resolve(c,s);g=self.score(c,s);self.assertFalse(g['wrong_write']);self.assertEqual(g['environment_events'],1)

if __name__=='__main__':unittest.main()
