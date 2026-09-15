import unittest
import native_study as ns

class NativeGate(unittest.TestCase):
 def test_native_components(self):
  self.assertEqual(ns.capabilities(),{'native_context':True,'native_execution':True,'native_evaluation':True})

class NativeIntegration(unittest.TestCase):
 def test_official_walkthroughs(self):
  for name in ns.OFFICIAL_CASES:
   with self.subTest(name=name):self.assertAlmostEqual(ns.run_original(name)['official_evaluation']['similarity'],1)
 def test_stable(self):
  for method in ns.METHODS:
   with self.subTest(method=method):self.assertTrue(ns.run_fixture('stable','none',method)['score']['safe_success'])
 def test_unrelated_change(self):self.assertTrue(ns.run_fixture('unrelated','none','cached_reactive')['score']['safe_success'])
 def test_unmapped_silent_success(self):
  r=ns.run_fixture('moved','none','cached_reactive');self.assertTrue(r['policy_return']['reported_sent']);self.assertEqual(r['score']['wrong_writes'],1)
 def test_reassigned(self):
  r=ns.run_fixture('reassigned','none','query_on_error');self.assertFalse(r['score']['target_reached']);self.assertEqual(r['recipient_ids'],[ns.OTHER_ID])
 def test_fresh_lookup_resolves(self):self.assertTrue(ns.run_fixture('reassigned','none','always_resolve')['score']['safe_success'])
 def test_current_feedback_reuse(self):
  a=ns.run_fixture('reassigned','post_change','reuse_observed_then_resolve');b=ns.run_fixture('reassigned','post_change','always_resolve')
  self.assertTrue(a['score']['safe_success']);self.assertEqual(b['runtime_calls']-a['runtime_calls'],1)
 def test_old_feedback_not_safe(self):self.assertFalse(ns.run_fixture('reassigned','pre_change','reuse_observed_then_resolve')['score']['safe_success'])
 def test_explicit_error_recovery(self):
  r=ns.run_fixture('cellular_off','none','cached_reactive');self.assertTrue(r['score']['safe_success']);self.assertEqual(r['score']['new_writes'],1)
 def test_error_trigger_can_resolve_composite(self):
  r=ns.run_fixture('combined','none','query_on_error');self.assertTrue(r['score']['safe_success'])
 def test_posthoc_lookup_does_not_undo(self):
  r=ns.run_fixture('reassigned','none','cached_reactive',posthoc=True);self.assertEqual(r['score']['wrong_writes'],1);self.assertFalse(r['score']['safe_success'])
 def test_snapshot_roundtrip(self):self.assertTrue(ns.check_snapshot_roundtrip())
 def test_unknown_function_blocked(self):
  with self.assertRaises(ValueError):ns.check_invalid_call('__import__',{})
 def test_mutation_denied_to_policy(self):
  with self.assertRaises(ValueError):ns.check_invalid_call('remove_contact',{'person_id':ns.TARGET_ID})
 def test_explicit_number_goal_not_person_goal(self):
  r=ns.run_explicit_phone_boundary();self.assertTrue(r['phone_goal']['safe_success']);self.assertFalse(r['person_goal']['safe_success'])
 def test_empty_or_ambiguous_lookup_rejected(self):
  with self.assertRaises(ValueError):ns.select_exact_contact([],ns.TARGET)
  with self.assertRaises(ValueError):ns.select_exact_contact([{'name':ns.TARGET},{'name':ns.TARGET}],ns.TARGET)
class ExecutionBoundaryRegression(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  from diagnose_execution import diagnostics
  cls.report=diagnostics()
 def test_syntax_error_class_survives_python_format_difference(self):
  x=self.report['test_execution_environment_syntax_error']
  self.assertTrue(x['original_assertion_failed'])
  self.assertIn('SyntaxError: invalid syntax',x['last_messages'][-1]['tool_call_exception'])
 def test_local_parallel_dependency_uses_no_external_service(self):
  x=self.report['local_parallel_dependency']
  self.assertTrue(x['first_failed']);self.assertEqual(x['first_tool'],'set_wifi_status')
  self.assertFalse(x['settings'][0]['wifi'])
if __name__=='__main__':unittest.main()
