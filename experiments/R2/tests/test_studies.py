import copy, json, tempfile, unittest
from pathlib import Path
import numpy as np
from pilot.recheck import World,make_cases,valid_plan,public_task,protocol
from pilot.readiness import make_cases as make_repairs,selected_ids,artifact_valid
from pilot.report import reference_artifact,artifact_correct,recheck_correct
from pilot.common import digest
from vendor.recheck_core import solve_refresh_dp,mismatch_probability

class TestStudies(unittest.TestCase):
    def test_recheck_manifest_call_count(self):self.assertEqual(protocol()['logical_calls'],260)
    def test_frozen_generator(self):self.assertEqual(make_cases(4,8),make_cases(4,8))
    def test_no_drift_control(self):
        for case in make_cases(4,8):
            if case['regime']=='no_drift':self.assertTrue(all(x['modes']==case['initial_modes'] for x in case['tasks']))
    def test_hidden_mode_not_in_public_task(self):
        a={'type':2,'cutoff':10,'modes':[0,0]};b={**a,'modes':[1,1]}
        self.assertEqual(public_task(a),public_task(b))
    def test_world_changes_semantics_not_schema(self):
        w=World([100,200,300]);schema=w.db.execute("SELECT sql FROM sqlite_master ORDER BY name").fetchall()
        for modes in ([0,0],[1,1],[0,1],[1,0]):
            w.set_modes(modes);self.assertEqual(w.db.execute("SELECT sql FROM sqlite_master ORDER BY name").fetchall(),schema)
        w.close()
    def test_scoped_calibration(self):
        w=World([100,200,300])
        for modes in ([0,0],[1,1]):
            w.set_modes(modes);self.assertEqual(w.probe(0)['raw_amount'],100 if modes[0] else 1)
            self.assertEqual(w.probe(1)['returned_count'],modes[1])
        w.close()
    def test_exact_tool_boundary(self):
        w=World([100,200,300]);task={'type':2,'cutoff':1}
        for unit in range(2):
            for inc in range(2):
                w.set_modes([unit,inc]);p={'amount_divisor':100 if unit else 1,'time_bound':1 if inc else 2}
                out,calls=w.execute(task,p);self.assertEqual(out['count_before'],2)
                self.assertAlmostEqual(out['sum_amount_raw']/p['amount_divisor'],6);self.assertEqual(calls,2)
                self.assertNotIn('modes',json.dumps(out));self.assertNotIn('SELECT',json.dumps(out))
        w.close()
    def test_invalid_plan_does_not_execute(self):
        w=World([100]);count=w.calls
        out,calls=w.execute({'type':2,'cutoff':1},{'amount_divisor':True,'time_bound':1})
        self.assertIn('error',out);self.assertEqual(w.calls,count);w.close()
    def test_no_generated_code_execution(self):
        self.assertFalse(valid_plan({'sql':'DROP TABLE orders'},{'type':0,'cutoff':1}))
    def test_offline_evaluator_correct(self):
        c=make_cases(1,1)[0];c['tasks'][0]['type']=0
        r={'step':0,'plan_schema_valid':True,'answer':{'total':sum(c['cents'])/100,'count':None}}
        self.assertTrue(recheck_correct(r,c));r['answer']['total']+=1;self.assertFalse(recheck_correct(r,c))
    def test_dp_never_queries_hidden_state(self):
        sol=solve_refresh_dp(np.array([[1.]]),np.array([[1.]]),np.array([.2]),np.array([.1]),3)
        self.assertTrue(sol.action(3,np.array([1]),0)[0])
    def test_repair_selection_rejects_unknown_or_duplicate(self):
        for x in ({'artifact_ids':['bad']},{'artifact_ids':['cost_note','cost_note']},{'artifact_ids':'cost_note'}):self.assertIsNone(selected_ids(x))
        self.assertEqual(selected_ids({'artifact_ids':[]}),[])
    def test_artifact_schema(self):
        self.assertTrue(artifact_valid({'metric':1,'flag':'low'}));self.assertFalse(artifact_valid({'metric':True,'flag':'low'}))
    def test_readiness_has_noop_revision(self):
        c=make_repairs(4)[3]
        self.assertTrue(all(reference_artifact(r,c['old_sources'])==reference_artifact(r,c['new_sources']) for r in c['evaluator_rules']))
    def test_readiness_changes_all_three(self):
        c=make_repairs(4)[2]
        self.assertTrue(all(reference_artifact(r,c['old_sources'])!=reference_artifact(r,c['new_sources']) for r in c['evaluator_rules']))
    def test_wrong_metric_not_hidden_by_flag(self):
        self.assertFalse(artifact_correct({'metric':9,'flag':'high'},{'metric':10,'flag':'high'}))
