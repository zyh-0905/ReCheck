import unittest,copy,json,tempfile
from pathlib import Path
import numpy as np
from r3lib import protocol,offline,worker
from vendor.recheck_core import solve_refresh_dp,mismatch_probability

class ProtocolTests(unittest.TestCase):
 def setUp(self): self.assertTrue(hasattr(protocol,'load_protocol'),'R3 frozen protocol not implemented')
 def test_counts(self):
  p=protocol.load_protocol();self.assertEqual(len(p['streams']),16);self.assertEqual(p['main_calls'],416)
  self.assertEqual(p['primary_records'],384);self.assertEqual(p['replicate_records'],32)
 def test_initial_tasks_balanced(self):
  p=protocol.load_protocol()
  for c in range(4):self.assertEqual([x['initial_task'] for x in p['streams'][4*c:4*c+4]],list(range(4)))
 def test_case_deterministic(self):
  p=protocol.load_protocol()
  for c in p['streams']:
   for k in ['task_seed','world_seed','data_seed']:c[k]+=7000000
  self.assertEqual(protocol.make_cases(p),protocol.make_cases(p))
 def test_world_rng_does_not_change_public_tasks(self):
  p=protocol.load_protocol();c=p['streams'][0];q=protocol.task_types(c,p);d=copy.deepcopy(c);d['world_seed']+=77
  self.assertEqual(q,protocol.task_types(d,p))
 def test_policy_view_excludes_world(self):
  p=protocol.load_protocol();v=protocol.policy_spec(p['streams'][0],p)
  self.assertTrue(set(v).isdisjoint({'actual_hazard','world_seed','modes','gold','data_seed'}))
 def test_main_ids_unique(self):
  ids=protocol.logical_ids(protocol.load_protocol());self.assertEqual(len(ids),416);self.assertEqual(len(set(ids)),416)

class ExactTests(unittest.TestCase):
 def setUp(self):self.assertTrue(hasattr(offline,'expected_policy'),'Exact evaluator missing')
 def spec(self,H=3):
  return {'steps':H,'weights':[[1,0],[0,1],[1,1],[0,0]],'transition':[[.7,.1,.1,.1],[.1,.7,.1,.1],[.1,.1,.7,.1],[.1,.1,.1,.7]],'assumed_hazards':[.12,.12],'probe_price':[.22,.22],'ttl_age':3}
 def test_dp_matches_bellman(self):
  s=self.spec();d=protocol.solve(s);v=offline.expected_policy('recheck',s,.12)
  self.assertAlmostEqual(v['objective'],d.value[3,1].sum(axis=1).mean(),12)
 def test_always(self):
  s=self.spec();v=offline.expected_policy('always',s,.12);self.assertEqual(v['semantic_loss'],0.);self.assertAlmostEqual(v['probe_count'],6.)
 def test_never_no_drift(self):
  v=offline.expected_policy('never',self.spec(),0.);self.assertEqual(v['objective'],0.)
 def test_one_step_dp_myopic(self):
  s=self.spec(1);self.assertEqual(offline.expected_policy('recheck',s,.12),offline.expected_policy('myopic',s,.12))
 def test_actual_hazard_changes_loss_not_probes(self):
  s=self.spec();a=offline.expected_policy('recheck',s,0);b=offline.expected_policy('recheck',s,.24)
  self.assertEqual(a['probe_count'],b['probe_count']);self.assertLess(a['semantic_loss'],b['semantic_loss'])
 def test_all_grid_cells_retained(self):
  r=offline.factorial_report(horizons=(3,))
  self.assertEqual(len(r['rows']),144);self.assertEqual(r['remote_model_calls'],0)
 def test_opportunity_no_hidden_rng(self):
  p=protocol.load_protocol();c=p['streams'][0];a=offline.opportunity(c,p);d=copy.deepcopy(c);d['world_seed']+=7
  self.assertEqual(a,offline.opportunity(d,p))
 def test_zero_drift_no_semantic_opportunity(self):
  p=protocol.load_protocol();c=copy.deepcopy(p['streams'][0]);c['actual_hazard']=0
  self.assertEqual(offline.opportunity(c,p)['expected_relevant_semantic_differences'],0.)

class WorkerTests(unittest.TestCase):
 def setUp(self):self.assertTrue(hasattr(worker,'make_view'),'Hybrid worker missing')
 def mem(self):return {'amount_divisor':100,'endpoint_inclusive':True,'checked_at':[8,8]}
 def test_count_schema_has_no_amount(self):
  t={'type':1,'cutoff':8};v=worker.make_view(t,self.mem());self.assertEqual(v['allowed_keys'],['time_bound'])
  self.assertNotIn('amount_divisor',json.dumps(v));self.assertNotIn('checked_at',json.dumps(v))
 def test_all_schema_empty(self):
  self.assertTrue(worker.valid_plan({}, {'type':3,'cutoff':8}));self.assertFalse(worker.valid_plan({'time_bound':None},{'type':3,'cutoff':8}))
 def test_unused_amount_is_invalid_not_silently_fixed(self):
  self.assertFalse(worker.valid_plan({'time_bound':8,'amount_divisor':1},{'type':1,'cutoff':8}))
 def test_valid_count(self):self.assertTrue(worker.valid_plan({'time_bound':9},{'type':1,'cutoff':8}))
 def test_bool_not_bound(self):self.assertFalse(worker.valid_plan({'time_bound':True},{'type':1,'cutoff':0}))
 def test_amount(self):self.assertTrue(worker.valid_plan({'amount_divisor':100},{'type':0,'cutoff':8}))
 def test_stale_value_legal_but_not_fresh(self):
  a=worker.freshness({'type':0},self.mem(),[0,1]);self.assertTrue(a['relevant_stale']);self.assertTrue(a['relevant_legal'])
 def test_irrelevant_stale_not_counted(self):self.assertFalse(worker.freshness({'type':1},self.mem(),[0,1])['relevant_stale'])
 def test_count_render_never_reinterprets(self):
  a=worker.render({'type':1},{'time_bound':8},{'count_before':9});self.assertEqual(a,{'total':None,'count':9})
 def test_total_render_selected_divisor(self):
  a=worker.render({'type':0},{'amount_divisor':100},{'sum_amount_raw':1023.35});self.assertAlmostEqual(a['total'],10.2335)
 def test_counterfactual_is_not_used(self):
  v=worker.make_view({'type':2,'cutoff':8,'modes':[0,0],'gold':999},self.mem());text=json.dumps(v)
  for k in ['modes','gold','checked_at','current_round','price','method']:self.assertNotIn(k,text)
 def test_normative_error_stays_wrong(self):
  case={'cents':[100]*20};t={'type':0,'cutoff':8,'modes':[0,1]}
  r=worker.score({'total':.2,'count':None},t,case);self.assertFalse(r['success'])

if __name__=='__main__':unittest.main()
