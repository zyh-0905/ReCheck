import unittest,tempfile
from pathlib import Path
from core.cases import make_cases
from core.db import Store

class NativeDBTests(unittest.TestCase):
 def setUp(self): self.tmp=tempfile.TemporaryDirectory();self.stores=[]
 def tearDown(self):
  for s in self.stores:s.close()
  self.tmp.cleanup()
 def store(self,i):
  c=make_cases()[i];s=Store(c,Path(self.tmp.name)/f'{i}-{len(self.stores)}.sqlite');self.stores.append(s);return c,s
 def resolve(self,c,s):
  return s.call('resolve_service',{'service':c['key']}) if c['family']=='routing' else s.call('select_batch',{'lane':c['key'],'min_units':4})
 def patch(self,c,s,row,**extra):
  n='update_config' if c['family']=='routing' else 'update_batch';field='max_attempts' if c['family']=='routing' else 'ready_after'
  return s.call(n,{'id':row['id'],field:c['wanted'],**extra})
 def test_native_resolver_returns_target(self):
  c,s=self.store(0);r=self.resolve(c,s);self.assertTrue(r['ok']);self.assertEqual(r['value']['record']['id'],c['target_id'])
 def test_actual_file_backed_sqlite(self):
  c,s=self.store(0);self.assertEqual(Path(s.path).read_bytes()[:16],b'SQLite format 3\x00')
 def test_two_real_connections(self):
  c,s=self.store(0);self.assertIsNot(s.agent,s.environment);self.assertEqual(s.agent.execute('select count(*) from configs').fetchone()[0],3)
 def test_selection_change_after_read_keeps_old_receipt(self):
  c,s=self.store(3);r=self.resolve(c,s);self.assertEqual(r['value']['record']['id'],c['target_id']);self.assertEqual(self.resolve(c,s)['value']['record']['id'],c['alternate_id']);self.assertEqual(len([e for e in s.events if e['kind']=='environment']),1)
 def test_protected_change_full_write_loses_owner(self):
  c,s=self.store(2);r=self.resolve(c,s)['value']['record'];self.assertTrue(self.patch(c,s,r,owner=r['owner'],note=r['note'],label=r['label'])['ok']);self.assertEqual(s.world()['configs'][0]['owner'],r['owner'])
 def test_minimal_preserves_new_owner(self):
  c,s=self.store(2);r=self.resolve(c,s)['value']['record'];self.assertTrue(self.patch(c,s,r)['ok']);self.assertEqual(s.world()['configs'][0]['owner'],'operator-new')
 def test_row_CAS_blocks_changed_record_without_writing(self):
  c,s=self.store(2);r=self.resolve(c,s)['value']['record'];before=s.world();ans=self.patch(c,s,r,expected_version=r['version']);self.assertFalse(ans['ok']);self.assertEqual(ans['error'],'ROW_VERSION_CONFLICT');self.assertEqual(before,s.world())
 def test_row_CAS_does_not_check_external_route(self):
  c,s=self.store(3);r=self.resolve(c,s)['value']['record'];self.assertTrue(self.patch(c,s,r,expected_version=r['version'])['ok'])
 def test_selection_condition_rejects_changed_route(self):
  c,s=self.store(3);v=self.resolve(c,s)['value'];before=s.world();ans=self.patch(c,s,v['record'],expected_version=v['record']['version'],service=c['key'],expected_selection_token=v['selection_token']);self.assertFalse(ans['ok']);self.assertEqual(ans['error'],'SELECTION_CONFLICT');self.assertEqual(before,s.world())
 def test_dispatch_query_uses_eligibility_not_only_priority(self):
  c,s=self.store(6);r=self.resolve(c,s);self.assertEqual(r['value']['record']['id'],c['target_id']);self.assertGreater(s.world()['batches'][2]['priority'],r['value']['record']['priority'])
 def test_dispatch_alternate_priority_changes_target(self):
  c,s=self.store(9);r=self.resolve(c,s)['value']['record'];self.assertEqual(r['id'],c['target_id']);self.assertEqual(self.resolve(c,s)['value']['record']['id'],c['alternate_id'])
 def test_dispatch_selection_condition(self):
  c,s=self.store(9);v=self.resolve(c,s)['value'];ans=self.patch(c,s,v['record'],expected_version=v['record']['version'],lane_query=c['key'],min_units_query=4,expected_selection_token=v['selection_token']);self.assertFalse(ans['ok']);self.assertEqual(ans['error'],'SELECTION_CONFLICT')
 def test_dispatch_full_overwrites_carrier(self):
  c,s=self.store(8);r=self.resolve(c,s)['value']['record'];self.assertTrue(self.patch(c,s,r,carrier=r['carrier'])['ok']);self.assertEqual(s.world()['batches'][0]['carrier'],'carrier-old')
 def test_dispatch_minimal_preserves_carrier(self):
  c,s=self.store(8);r=self.resolve(c,s)['value']['record'];self.patch(c,s,r);self.assertEqual(s.world()['batches'][0]['carrier'],'carrier-new')
 def test_literal_read_triggers_but_target_should_remain_literal(self):
  c,s=self.store(4);r=s.call('get_config',{'id':c['target_id']})['value'];self.assertTrue(s.triggered);self.patch(c,s,r);self.assertEqual(s.world()['configs'][0]['max_attempts'],5)
 def test_no_qualifying_read_no_forced_injection(self):
  c,s=self.store(3);self.patch(c,s,{'id':c['target_id']});self.assertFalse(s.triggered);self.resolve(c,s);self.assertFalse(s.triggered);self.assertTrue(s.opportunity_closed)
 def test_no_repeat_event_after_multiple_reads(self):
  c,s=self.store(3)
  for _ in range(4):self.resolve(c,s)
  self.assertEqual(sum(e['kind']=='environment' for e in s.events),1)
 def test_read_only_does_not_change_business_data_in_stable(self):
  c,s=self.store(0);before=s.world();self.resolve(c,s);self.assertEqual(before,s.world())
 def test_unknown_function_has_no_effect(self):
  c,s=self.store(0);before=s.world();r=s.call('execute_sql',{'sql':'drop table configs'});self.assertFalse(r['ok']);self.assertEqual(before,s.world())
 def test_missing_selection_parameters_is_rejected(self):
  c,s=self.store(0);r=self.resolve(c,s)['value']['record'];before=s.world();ans=self.patch(c,s,r,expected_selection_token='bad');self.assertFalse(ans['ok']);self.assertEqual(before,s.world())
 def test_always_reresolve_can_complete_after_single_event(self):
  for i in range(12):
   c,s=self.store(i)
   if c['goal_mode']=='current': self.resolve(c,s);r=self.resolve(c,s)['value']['record']
   else:
    n='get_config' if c['family']=='routing' else 'get_batch';s.call(n,{'id':c['target_id']});r=s.call(n,{'id':c['target_id']})['value']
   self.assertTrue(self.patch(c,s,r,expected_version=r['version'])['ok'])

if __name__=='__main__':unittest.main()
