import unittest,socket
from native_audit import run_case
class NativeControls(unittest.TestCase):
    def test_successful_state_is_kept(self):
        r=run_case('wifi_off','correct')
        self.assertEqual(r['official_evaluation']['similarity'],1.0)
        self.assertFalse(r['final_settings']['wifi'])
    def test_regression_remains_full_original_score(self):
        r=run_case('wifi_off','achieve_then_revert')
        self.assertEqual(r['official_evaluation']['similarity'],1.0)
        self.assertTrue(r['final_settings']['wifi'])
        self.assertFalse(r['terminal_valid'])
    def test_error_then_completion_remains_full(self):
        r=run_case('wifi_off','error_then_correct')
        self.assertEqual(r['native_tool_errors'],1)
        self.assertEqual(r['official_evaluation']['similarity'],1.0)
        self.assertTrue(r['terminal_valid'])
    def test_idempotent_error_after_completion_remains_full(self):
        r=run_case('wifi_off','correct_then_redundant_error')
        self.assertEqual(r['native_tool_errors'],1)
        self.assertEqual(r['official_evaluation']['similarity'],1.0)
    def test_prose_is_not_full_score(self):
        r=run_case('wifi_off','claim_only')
        self.assertLess(r['official_evaluation']['similarity'],1.0)
        self.assertFalse(r['terminal_valid'])
    def test_repaired_regression_is_distinguished_by_terminal_check(self):
        r=run_case('wifi_off','achieve_revert_repair')
        self.assertEqual(r['official_evaluation']['similarity'],1.0)
        self.assertTrue(r['terminal_valid'])
    def test_no_network(self):
        with self.assertRaisesRegex(RuntimeError,'offline network denied'):
            socket.create_connection(('localhost',9))
