import unittest,tempfile,pathlib
from r6lib import equivalence as eq,data,review

class AuditHardeningTests(unittest.TestCase):
    def strict(self):
        self.assertTrue(hasattr(eq,'strict_equal'),'missing typed strict equality for calibration evidence')
        return eq.strict_equal
    def test_boolean_not_integer_label(self):self.assertFalse(self.strict()({'failure':1},{'failure':True}))
    def test_integer_not_float_count(self):self.assertFalse(self.strict()({'n':16},{'n':16.0}))
    def test_valid_nested_receipt(self):self.assertTrue(self.strict()({'x':[1,True,0.]},{'x':[1,True,0.]}))
    def test_nan_not_equal_to_itself(self):self.assertFalse(self.strict()({'x':float('nan')},{'x':float('nan')}))
    def test_layout_detects_missing_and_extra(self):
        self.assertTrue(hasattr(review,'layout_issues'),'missing exact experimental layout check')
        with tempfile.TemporaryDirectory() as td:
            r=pathlib.Path(td);(r/'trajectories').mkdir();(r/'trajectories/999_shared_single_only.json').write_text('{}')
            issues=review.layout_issues(r,data.protocol())
            self.assertTrue(any('unexpected' in x for x in issues));self.assertTrue(any('missing' in x for x in issues))
    def test_bad_protocol_price_rejected(self):
        self.assertTrue(hasattr(review,'validate_cost_protocol'),'exact integer accounting must bind .05 protocol price')
        p=data.protocol();p['credit_price']=.1
        with self.assertRaises(ValueError):review.validate_cost_protocol(p)

if __name__=='__main__':unittest.main()
