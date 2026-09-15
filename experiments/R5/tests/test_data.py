
import unittest, importlib, copy
import numpy as np
from r5lib import data, calibration

class DataAndCalibrationTests(unittest.TestCase):
    def test_catalog_deterministic(self):
        self.assertEqual(data.make_rows(11), data.make_rows(11))
        self.assertNotEqual(data.make_rows(11), data.make_rows(12))
    def test_profiles(self):
        rows=data.make_rows(11, 'reservation_free_clustered')
        self.assertTrue(all(r['reserved']==0 for r in rows))
        self.assertEqual([r['category'] for r in rows],sorted(r['category'] for r in rows))
    def test_modes_roundtrip(self):
        for x in range(8):
            self.assertEqual(data.encode(data.decode(x)),x)
            self.assertEqual(data.encode_memory(data.memory(x)),x)
    def test_invalid_modes(self):
        with self.assertRaises(ValueError):data.decode(8)
        with self.assertRaises(ValueError):data.decode(True)
        with self.assertRaises(ValueError):data.encode((0,1,2))
    def test_task_public_no_mode(self):
        rows=data.make_rows(11)
        t=data.make_task(4,rows,13)
        self.assertEqual(t['minimum'],22)
        self.assertNotIn('modes',t)
        self.assertNotIn('rows',t)
    def test_evaluation_seeds_disjoint(self):
        p=data.load_protocol()
        ids=data.split_ids(p)
        self.assertFalse(set(ids['calibration'])&set(ids['validation']))
        self.assertFalse(set(ids['evaluation'])&(set(ids['calibration'])|set(ids['validation'])))
    def test_calibration_diagonal_and_shape(self):
        a=calibration.fit([110,111])
        x=np.asarray(a['table'])
        self.assertEqual(x.shape,(5,8,8))
        self.assertTrue(np.all((x>=0)&(x<=1)))
        self.assertTrue(np.all(x[:,np.arange(8),np.arange(8)]==0))
        self.assertEqual(a['independent_catalogs'],2)
    def test_directional_pagination_loss(self):
        rows=[
          {'sku':f'S{i}','category':'B' if i<3 else 'A','active':True,'physical':10,'reserved':2}
          for i in range(6)]
        task={'type':0,'category':'A','skus':[],'minimum':3}
        # true page 0, cache page 1: miss B only, no task loss
        a=calibration.single_failure(rows,task,cached=1,true=0)
        # true page 1, cache page 0: PAGE_BEFORE_FIRST
        b=calibration.single_failure(rows,task,cached=0,true=1)
        self.assertEqual(a,0)
        self.assertEqual(b,1)
    def test_predictor_does_not_receive_test_rows(self):
        a=calibration.fit([110])
        self.assertEqual(set(a)-{'schema','seeds','independent_catalogs','task_classes','table','failure_counts','fingerprint'},set())
    def test_single_effect_ablation_bounds(self):
        t=np.asarray(calibration.fit([110])['table'])
        x=calibration.single_effect(t)
        self.assertTrue(np.all((0<=x)&(x<=1)))
        self.assertTrue(np.all(x[:,range(8),range(8)]==0))
    def test_empty_calibration_rejected(self):
        with self.assertRaises(ValueError):calibration.fit([])
