import unittest
from supplement import run_case
class ReminderHarnessRegression(unittest.TestCase):
    def test_original_reminder_correct_uses_documented_read(self):
        result = run_case('modify_reminder_with_recency_latest','correct')
        self.assertEqual(result['official_evaluation']['similarity'], 1.0)
        self.assertTrue(result['terminal_valid'])
        self.assertTrue(all(e['response']['ok'] for e in result['events']))
