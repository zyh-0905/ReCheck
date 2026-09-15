import unittest,importlib,copy,math

def mod(t):
    try:return importlib.import_module('r6lib.equivalence')
    except ImportError as e:t.fail('typed equivalence implementation missing: '+str(e))

class EquivalenceTests(unittest.TestCase):
    def base(self):return {'stream':1,'calibration_fingerprint':'abc','execution_seconds':1.,'records':[{'step':0,'budget_after':6,'packets':['s0'],'plan':{'first_page':0},'answer':{'skus':['x']},'predicted_task_error_after_receipts':0.2256,'planning_seconds':.1}]}
    def compare(self,change):
        m=mod(self);a=self.base();b=copy.deepcopy(a);change(b);return m.compare(a,b)
    def test_one_ulp_only_at_prediction_path_passes(self):
        self.assertTrue(self.compare(lambda b:b['records'][0].update(predicted_task_error_after_receipts=math.nextafter(.2256,1)))['pass'])
    def test_probability_delta_too_large_fails(self):self.assertFalse(self.compare(lambda b:b['records'][0].update(predicted_task_error_after_receipts=.226))['pass'])
    def test_probability_nan_fails(self):self.assertFalse(self.compare(lambda b:b['records'][0].update(predicted_task_error_after_receipts=float('nan')))['pass'])
    def test_probability_outside_unit_interval_fails(self):self.assertFalse(self.compare(lambda b:b['records'][0].update(predicted_task_error_after_receipts=1.01))['pass'])
    def test_probability_integer_type_fails(self):self.assertFalse(self.compare(lambda b:b['records'][0].update(predicted_task_error_after_receipts=0))['pass'])
    def test_answer_tiny_difference_not_tolerated(self):self.assertFalse(self.compare(lambda b:b['records'][0].update(answer={'value':1e-16}))['pass'])
    def test_budget_bool_not_equal_to_int(self):self.assertFalse(self.compare(lambda b:b.update(stream=True))['pass'])
    def test_packet_change_not_tolerated(self):self.assertFalse(self.compare(lambda b:b['records'][0].update(packets=['s1']))['pass'])
    def test_prediction_name_elsewhere_not_exempt(self):
        m=mod(self);a=self.base();a['predicted_task_error_after_receipts']=.1;b=copy.deepcopy(a);b['predicted_task_error_after_receipts']=.100000000000001
        self.assertFalse(m.compare(a,b)['pass'])
    def test_timing_not_compared_but_original_not_changed(self):
        m=mod(self);a=self.base();before=copy.deepcopy(a);b=copy.deepcopy(a);b['execution_seconds']=123.
        self.assertTrue(m.compare(a,b)['pass']);self.assertEqual(a,before)
    def test_missing_record_fails(self):self.assertFalse(self.compare(lambda b:b.update(records=[]))['pass'])
    def test_reference_digest_typed_strict_and_float_sidecar(self):
        m=mod(self);a=self.base();ref=m.reference(a);b=copy.deepcopy(a)
        b['records'][0]['predicted_task_error_after_receipts']=math.nextafter(.2256,1)
        self.assertTrue(m.check_reference(ref,b)['pass']);b['records'][0]['budget_after']=5
        self.assertFalse(m.check_reference(ref,b)['pass'])

if __name__=='__main__':unittest.main()
