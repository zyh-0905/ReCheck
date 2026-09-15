import unittest,importlib,tempfile,pathlib,shutil,json,copy,zipfile
from r6lib import data,storage

def mod(t,name):
    try:return importlib.import_module('r6lib.'+name)
    except ImportError as e:t.fail(name+' missing: '+str(e))

class StudyTests(unittest.TestCase):
    def test_calibration_cost_accounting(self):
        review=mod(self,'review');p=data.protocol()
        self.assertEqual(review.expected_model_workflows('single_only',16),1392)
        self.assertEqual(review.expected_model_workflows('full_joint',16),2992)
        for method in ['decision_16','random_16','occupancy_16']:self.assertEqual(review.expected_model_workflows(method,16),1648)
        for method in ['decision_32','random_32','occupancy_32']:self.assertEqual(review.expected_model_workflows(method,16),1904)
        self.assertEqual(review.expected_model_workflows('never',16),0)
    def test_exact_integer_cost_units(self):
        review=mod(self,'review')
        self.assertEqual(review.cost_units(3,8),68)
        with self.assertRaises(ValueError):review.cost_units(True,8)
    def test_modified_raw_answer_rejected(self):
        review=mod(self,'review');p=data.protocol();p['steps']=2;p['calibration_panels']=1;p['streams_per_condition']=1
        from r6lib import acquisition as a,runtime
        l=a.Learner(a.PaidOracle([6100711]));l.initialize_singles();s=l.snapshot();c=data.cases(p)[0]
        tr=runtime.run_one(c,p,'shared','single_only',s)
        self.assertFalse(review.check_task_trace(tr,c,p))
        tr['records'][0]['answer']={'skus':['tampered']}
        self.assertTrue(review.check_task_trace(tr,c,p))
    def test_modified_budget_rejected(self):
        review=mod(self,'review');p=data.protocol();p['steps']=2;p['calibration_panels']=1;p['streams_per_condition']=1
        from r6lib import acquisition as a,runtime
        l=a.Learner(a.PaidOracle([6100711]));l.initialize_singles();c=data.cases(p)[0];tr=runtime.run_one(c,p,'shared','single_only',l.snapshot())
        tr['records'][0]['budget_after']+=1;self.assertTrue(review.check_task_trace(tr,c,p))
    def test_reference_and_runtime_labels_do_not_share_cases(self):
        study=mod(self,'study');p=data.protocol();ids=data.split_ids(p)
        self.assertFalse(set(sum(ids['calibration'],[])) & set(ids['evaluation']))
    def test_amortized_cost_has_explicit_units_and_startup(self):
        review=mod(self,'review')
        self.assertAlmostEqual(review.amortized(2.,1000,100,.01),2.4)
    def test_original_protocol_marked_development(self):
        study=mod(self,'study');self.assertEqual(data.protocol()['phase'],'development_offline_not_confirmatory')

if __name__=='__main__':unittest.main()
