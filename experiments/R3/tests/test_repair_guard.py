import unittest
from r3lib import repair_guard
class GuardTests(unittest.TestCase):
 def setUp(self):self.assertTrue(hasattr(repair_guard,'select_route'),'Cost guard missing')
 def test_unknown_defaults_recompute(self):self.assertEqual(repair_guard.select_route(None,.5,1.)['route'],'direct_recompute')
 def test_more_expensive_diagnosis(self):self.assertEqual(repair_guard.select_route(.8,.6,1.)['route'],'direct_recompute')
 def test_possible_savings(self):self.assertEqual(repair_guard.select_route(.1,.5,1.)['route'],'diagnose_then_repair')
 def test_equality_is_not_gain(self):self.assertEqual(repair_guard.select_route(.5,.5,1.)['route'],'direct_recompute')
 def test_negative_rejected(self):
  with self.assertRaises(ValueError):repair_guard.select_route(-1,.5,1.)
 def test_prior_data_fail_guard(self):
  r=repair_guard.prior_diagnostic();self.assertEqual(r['new_llm_calls'],0);self.assertEqual(r['currency_route']['route'],'direct_recompute')
if __name__=='__main__':unittest.main()
