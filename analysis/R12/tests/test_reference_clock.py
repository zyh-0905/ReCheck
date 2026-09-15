import unittest,json,datetime
from pathlib import Path
from unittest.mock import patch
from regrade import scenario_for_record
class ReferenceClock(unittest.TestCase):
    def test_reminder_target_date_restored_even_on_another_calendar_day(self):
        path=Path(__file__).resolve().parents[1]/'results/supplement_run2/trajectories/modify_reminder_with_recency_latest__correct.json'
        r=json.loads(path.read_text())
        from tool_sandbox.scenarios import multiple_tool_call_scenarios as module
        with patch.object(module,'get_tomorrow_datetime',return_value=datetime.datetime(2040,1,1)):
            scenario=scenario_for_record(r)
        ts=scenario.evaluation.milestone_matcher.milestones[2].snapshot_constraints[0].target_dataframe['reminder_timestamp'][0]
        self.assertEqual(ts,r['desired'])
    def test_regular_settings_kept(self):
        r={'scenario':'wifi_off'}
        scenario=scenario_for_record(r)
        self.assertEqual(len(scenario.evaluation.milestone_matcher.milestones),2)
