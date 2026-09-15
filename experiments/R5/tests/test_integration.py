
import unittest,tempfile,pathlib,copy
from unittest.mock import patch
from r5lib import data,storage,study,review

class IntegrationTests(unittest.TestCase):
    def test_run_audit_export_and_snapshot_change(self):
        p=copy.deepcopy(data.load_protocol())
        p.update(steps=2,streams_per_condition=1,calibration_catalogs=2,validation_catalogs=1,
                 scale_horizons=[2],scale_repeats=1)
        p['statistics']['bootstrap_repetitions']=10
        with tempfile.TemporaryDirectory() as d:
            r=pathlib.Path(d);(r/'LICENSE').write_text('MIT')
            storage.make_manifest(r)
            with patch('r5lib.data.load_protocol',return_value=p), storage.no_network():
                study.prepare(r);study.run(r)
                first=(r/'runs/R5_offline/execution_summary.json').read_bytes()
                study.run(r)
                self.assertEqual(first,(r/'runs/R5_offline/execution_summary.json').read_bytes())
                result=review.audit(r)
                self.assertTrue(result['mechanical_pass'],result['issues'])
                self.assertEqual(result['rows'],128)
                self.assertEqual(result['new_llm_calls'],0)
                exported=storage.bundle(r,r/'clean.zip')
                self.assertTrue(exported['pass'])
                (r/'runs/R5_offline/code_snapshot/LICENSE').write_text('changed')
                result=review.audit(r)
                self.assertFalse(result['mechanical_pass'])
                self.assertIn('snapshot missing/changed LICENSE',result['issues'])
