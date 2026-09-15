import unittest,copy,json
from pathlib import Path
from evidence_check import latest_rows,check_record
ROOT=Path(__file__).resolve().parents[1]
class EvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.good=json.loads((ROOT/'results/native_run1/trajectories/wifi_off__correct.json').read_text())
        cls.regression=json.loads((ROOT/'results/native_run1/trajectories/wifi_off__achieve_then_revert.json').read_text())
    def test_latest_snapshot(self):
        x={'_dbs':{'SETTING':[{'sandbox_message_index':0,'wifi':None},{'sandbox_message_index':3,'wifi':False},{'sandbox_message_index':7,'wifi':True}]}}
        self.assertEqual(latest_rows(x,'SETTING'),[{'wifi':True}])
    def test_original_success(self): self.assertTrue(check_record(self.good)['terminal_valid'])
    def test_original_regression(self): self.assertTrue(check_record(self.regression)['full_score_terminal_mismatch'])
    def test_swapped_terminal_label_rejected(self):
        r=copy.deepcopy(self.regression);r['terminal_valid']=True
        with self.assertRaises(ValueError):check_record(r)
    def test_stale_final_settings_rejected(self):
        r=copy.deepcopy(self.regression);r['final_settings']['wifi']=False
        with self.assertRaises(ValueError):check_record(r)
    def test_error_counter_rejected(self):
        r=copy.deepcopy(self.good);r['native_tool_errors']=1
        with self.assertRaises(ValueError):check_record(r)
    def test_event_counter_rejected(self):
        r=copy.deepcopy(self.good);r['native_tool_calls']=100
        with self.assertRaises(ValueError):check_record(r)
    def test_invalid_score_rejected(self):
        r=copy.deepcopy(self.good);r['official_evaluation']['similarity']=float('nan')
        with self.assertRaises(ValueError):check_record(r)
    def test_changed_target_rejected(self):
        r=copy.deepcopy(self.good);r['public_task_target']['desired']=True
        with self.assertRaises(ValueError):check_record(r)
    def test_unknown_case_rejected(self):
        r=copy.deepcopy(self.good);r['scenario']='made_up'
        with self.assertRaises(ValueError):check_record(r)
    def test_changed_event_state_rejected(self):
        r=copy.deepcopy(self.good);r['states_after_calls'][-1]['state']['wifi']=True
        with self.assertRaises(ValueError):check_record(r)
    def test_contact_terminal(self):
        r=json.loads((ROOT/'results/supplement_run2/trajectories/update_contact_with_id_and_phone_number__achieve_then_revert.json').read_text())
        self.assertFalse(check_record(r)['terminal_valid'])
    def test_reminder_terminal(self):
        r=json.loads((ROOT/'results/supplement_run2/trajectories/modify_reminder_with_recency_latest__correct.json').read_text())
        self.assertTrue(check_record(r)['terminal_valid'])
