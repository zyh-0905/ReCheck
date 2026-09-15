import unittest,tempfile,copy,json,itertools
from pathlib import Path
import numpy as np
from r3lib import protocol,offline,worker,storage,session,review
from pilot.common import read_json,write_json
ROOT=Path(__file__).resolve().parents[1]

class Boundaries(unittest.TestCase):
 def test_live_model_frozen(self):
  c=read_json(ROOT/'config.example.json');c['model']='silently-other-model'
  with self.assertRaises(ValueError):session.validate_r3_config(c)
 def test_live_endpoint_frozen(self):
  c=read_json(ROOT/'config.example.json');c['base_url']='https://example.com/v1'
  with self.assertRaises(ValueError):session.validate_r3_config(c)
 def test_main_paused_no_new_calls(self):
  # Static guard is supplemented by the full CLI tests; no credentials read on paused runs.
  import inspect,r3
  text=inspect.getsource(r3.run_paid)
  self.assertLess(text.index('("paused","running")'),text.index('key=_secret(cfg)'))
 def test_six_r2_cases_are_not_relabelled(self):
  r=review.regression_checks();self.assertTrue(r['pass']);self.assertEqual(len(r['checks']),6)
 def test_snapshot_license_with_manifest(self):
  self.assertIn('LICENSE',storage.source_hashes(ROOT))
 def test_precise_renderer_handles_tool_error(self):
  self.assertEqual(worker.render({'type':1},{},{'error':'INVALID_TOOL_PLAN'}),{'total':None,'count':None})
 def test_renderer_type_bool_is_not_correct(self):
  self.assertFalse(worker.score({'total':None,'count':True},{'type':3},{'cents':[100]})['success'])
 def test_future_cost_matters_two_steps(self):
  p=protocol.load_protocol();s=protocol.policy_spec(p['streams'][0],p);s['steps']=2;dp=protocol.solve(s)
  self.assertTrue(protocol.choose('recheck',[2,2],0,2,dp,s)[0]);self.assertFalse(protocol.choose('myopic',[2,2],0,2,dp,s)[0])
 def test_exact_expectation_vs_all_paths(self):
  # Independently enumerate both task transitions and bit flips for one channel, H=3.
  p=protocol.load_protocol();s=protocol.policy_spec(p['streams'][0],p);s['steps']=3;dp=protocol.solve(s);W=np.array(s['weights']);P=np.array(s['transition']);h=.12
  for method in ['recheck','myopic','always','ttl','never']:
   total=0.
   for j in range(2):
    for tasks in itertools.product(range(4),repeat=3):
     qt=.25*P[tasks[0],tasks[1]]*P[tasks[1],tasks[2]]
     for flips in itertools.product([0,1],repeat=3):
      prob=qt*np.prod([h if f else 1-h for f in flips]);mode=0;memo=0;age=0;cost=0.
      for t,(q,f) in enumerate(zip(tasks,flips)):
       mode^=f;age+=1;take=protocol.choose(method,[age,age],q,3-t,dp,s)[j]
       if take:memo=mode;age=0;cost+=s['probe_price'][j]
       cost+=W[q,j]*(memo!=mode)
      total+=prob*cost
   self.assertAlmostEqual(total,offline.expected_policy(method,s,h)['objective'],10)
 def test_no_drift_is_kept_when_recheck_loses(self):
  f=offline.preflight();rows={x['condition']:x for x in f['conditions']};self.assertLess(rows['no_drift']['relative_reduction'],0);self.assertTrue(f['pass'])
 def test_isolated_score_not_online(self):
  import inspect
  from r3lib import experiment
  self.assertNotIn('worker.score(',inspect.getsource(experiment.run))

if __name__=='__main__':unittest.main()
