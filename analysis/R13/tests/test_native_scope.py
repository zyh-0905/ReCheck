import unittest
from native_scope_cases import run_case
class NativeScopeTests(unittest.TestCase):
 def test_official_correct_revision(self):
  r=run_case('correct_revision');self.assertEqual(r['official_evaluation']['similarity'],1.0);self.assertIs(r['scoped_contract'],True);self.assertIs(r['blanket_all_goals_terminal'],False);self.assertEqual(r['tool_errors'],0)
 def test_missing_final_revision(self):
  r=run_case('missing_final_revision');self.assertIs(r['scoped_contract'],False);self.assertLess(r['official_evaluation']['similarity'],1)
 def test_undo_latest_goal(self):
  r=run_case('undo_latest_goal');self.assertEqual(r['official_evaluation']['similarity'],1.0);self.assertIs(r['scoped_contract'],False)
 def test_final_state_alone_insufficient(self):
  r=run_case('no_effect');self.assertIs(r['latest_terminal_only'],True);self.assertIs(r['scoped_contract'],False);self.assertLess(r['official_evaluation']['similarity'],1)
 def test_legitimate_error_not_violation(self):
  r=run_case('redundant_error_then_revision');self.assertEqual(r['tool_errors'],1);self.assertIs(r['scoped_contract'],True);self.assertEqual(r['official_evaluation']['similarity'],1.0)
if __name__=='__main__':unittest.main()
