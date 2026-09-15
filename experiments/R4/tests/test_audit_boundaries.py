import unittest, tempfile, json, copy
from pathlib import Path
from unittest.mock import patch
from pilot.common import read_json,write_json,strict_json_object,digest,request_payload
from r4lib import protocol,worker,environment,experiment,review,session,storage
ROOT=Path(__file__).resolve().parents[1]

class BoundaryTests(unittest.TestCase):
    def test_duplicate_json_keys_rejected(self):
        with self.assertRaises(ValueError):strict_json_object('{"page":0,"page":1}')
    def test_nonfinite_json_rejected(self):
        with self.assertRaises(ValueError):strict_json_object('{"x":NaN}')
    def test_rule_not_gold(self):
        w=environment.World([{'sku':'X','category':'A','active':True,'physical':9,'reserved':4}]);w.set_modes((0,0,1))
        task={'type':1,'category':'A','minimum':0,'skus':['X'],'modes':[0,0,1]}
        view=worker.make_view(task,dict(first_page=0,active_code=1,stock_semantics='net'))
        answer,_=worker.execute(w,view,worker.rule_plan(view))
        self.assertNotEqual(answer,environment.gold(w.rows,task))
    def test_secret_not_payload(self):
        cfg=read_json(ROOT/'config.example.json')
        with tempfile.TemporaryDirectory() as d:
            c=session.Client(cfg,d,secret='TEST_SECRET_VALUE',cap=1)
            with self.assertRaises(Exception):c.complete('x',[{'role':'user','content':'TEST_SECRET_VALUE'}])
            self.assertEqual(c.budget()['attempts'],0)
    def test_unapproved_remote_fixture_rejected(self):
        cfg=read_json(ROOT/'config.example.json');cfg['backend_kind']='test_fixture'
        with self.assertRaises(ValueError):session.validate_r4_config(cfg)
    def test_budget_step_cap_even_with_large_episode_budget(self):
        world=environment.World([]);packets=[{'id':f's{i}','cover':[i],'cost':2} for i in range(3)]
        b=environment.ProbeBudget(world,packets,100,4)
        with self.assertRaises(ValueError):b.read(('s0','s1','s2'))
        self.assertEqual(b.remaining,100)
    def test_empty_action_does_not_query(self):
        world=environment.World([]);b=environment.ProbeBudget(world,[],8,4)
        with patch.object(world,'calibration_packet',side_effect=AssertionError('queried')):
            self.assertEqual(b.read(()),[]);self.assertEqual(b.remaining,8)
    def test_no_private_modes_or_names_in_model_payloads(self):
        p=protocol.load_protocol()
        for c in p['streams']:
            for k in ['data_seed','task_seed','world_seed']:c[k]+=9000000
        # Keep all predefined cells but software-only seeds disjoint from the user protocol.
        class Fake:
            def __init__(self):self.ids=[];self.messages=[]
            def complete(self,lid,msgs,meta=None):
                v=json.loads(msgs[-1]['content']);self.ids.append(lid);self.messages.append(v)
                return {'text':json.dumps(worker.rule_plan(v))}
        f=Fake();cfg=read_json(ROOT/'config.example.json')
        with tempfile.TemporaryDirectory() as d, patch.object(environment,'gold',side_effect=AssertionError('online gold access')):
            experiment.run(f,cfg,Path(d),p)
            self.assertEqual(len(f.ids),408)
            for v in f.messages:
                flat=json.dumps(v)
                for key in ['world_seed','actual_hazard','gold','recheck_joint','bundle_rollout','credit','checked_at']:
                    self.assertNotIn(key,flat)
            records=[read_json(x) for x in (Path(d)/'records').glob('*.json')]
            for m in p['methods']:
                for sid in range(12):
                    rr=[r for r in records if r['method']==m and r['stream']==sid and r['replicate']=='primary']
                    self.assertLessEqual(sum(r['credits_spent'] for r in rr),8)
            for r in records:
                if r['replicate']=='repeat':self.assertEqual(r['credits_spent'],0)
    def test_legacy_freshness_regressions(self):
        report=review.regression_checks();self.assertTrue(report['pass'])
    def test_scientific_judgement_never_automatic(self):
        text=(ROOT/'r4lib/review.py').read_text()
        self.assertIn('PENDING_RESEARCHER_REVIEW',text)
