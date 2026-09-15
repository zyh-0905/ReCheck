
import unittest, itertools
import numpy as np
from r5lib.model import Planner, actions, posterior
from r5lib import data,calibration

def kwargs():
    return dict(hazards=(.12,.12,.12), transition=np.asarray(data.transition(.8)),
                price=.05,budget=4,step_cap=4,shared=True)
def brute(pl,h,ages,q,m,b):
    if not h:return 0.
    zprob=posterior(ages,pl.hazards)[m]
    values=[]
    for a in pl.actions:
        if a.cost>b:continue
        v=pl.price*a.cost
        nxt=tuple(1 if a.mask&(1<<j) else ages[j]+1 for j in range(3))
        for z,p in enumerate(zprob):
            mp=(m&~a.mask)|(z&a.mask)
            v+=p*pl.table[q,mp,z]
            if h>1:
                v+=p*sum(pl.P[q,k]*brute(pl,h-1,nxt,k,mp,b-a.cost) for k in range(pl.qn))
        values.append(v)
    return min(values)

class PlannerTests(unittest.TestCase):
    def setUp(self):
        self.tab=calibration.semantic_table(binary=True)
    def test_probabilities(self):
        p=posterior((0,2,7),(.1,.2,.3))
        np.testing.assert_allclose(p.sum(axis=1),1)
        self.assertTrue(np.all(p>=0))
        for m in range(8):
            self.assertEqual(sum(p[m,z] for z in range(8) if (m^z)&1),0)
    def test_invalid_posterior(self):
        for ages,hs in [((-1,0,0),(.1,)*3),((0,0,0),(.8,)*3)]:
            with self.assertRaises(ValueError):posterior(ages,hs)
    def test_shared_cost(self):
        aa=actions(True,4)
        self.assertEqual(next(a.cost for a in aa if a.mask==3),3)
        self.assertEqual(next(a.cost for a in actions(False,4) if a.mask==3),4)
    def test_no_probe_observation_identity(self):
        p=Planner(self.tab,**kwargs())
        loss,T=p.stage((2,3,4),p.actions[0])
        np.testing.assert_allclose(T,np.eye(8),atol=1e-14)
        self.assertGreater(loss.max(),0)
    def test_observation_changes_memory(self):
        p=Planner(self.tab,**kwargs())
        a=next(a for a in p.actions if a.mask==3)
        loss,T=p.stage((2,3,4),a)
        np.testing.assert_allclose(T.sum(axis=1),1)
        self.assertGreater(T[0,1],0)
        self.assertEqual(T[0,4],0)
        self.assertTrue(np.allclose(loss[0],0))
    def test_exact_matches_exhaustive(self):
        p=Planner(self.tab[:2],**{**kwargs(),'transition':np.asarray(data.transition(.8,2))})
        for m in (0,3,7):
            for q in (0,1):
                self.assertAlmostEqual(p.values('exact',2,(1,2,1),4)[q,m],
                                       brute(p,2,(1,2,1),q,m,4),places=12)
    def test_h1_myopic_exact(self):
        p=Planner(self.tab,**kwargs())
        np.testing.assert_allclose(p.scores('exact',1,(2,3,1),4),
                                   p.scores('myopic',1,(2,3,1),4))
    def test_no_budget_never(self):
        p=Planner(self.tab,**kwargs())
        self.assertEqual(p.choose('exact',3,(2,2,2),0,0,0).cost,0)
    def test_free_observation_never_worse(self):
        p=Planner(self.tab,**{**kwargs(),'price':0.})
        a=p.choose('exact',1,(2,2,2),0,0,4)
        self.assertEqual(a.mask,3)
    def test_zero_loss_never(self):
        p=Planner(np.zeros_like(self.tab),**kwargs())
        self.assertTrue(all(p.choose('exact',3,(2,2,2),q,m,4).cost==0 for q in range(5) for m in range(8)))
    def test_cached_direction_can_change_choice(self):
        tab=np.zeros((1,8,8))
        for m in range(8):
            for z in range(8):tab[0,m,z]=int(not(m&1) and bool(z&1))
        p=Planner(tab,**{**kwargs(),'transition':np.ones((1,1))})
        self.assertEqual(p.choose('exact',1,(3,3,3),0,0,4).mask,1)
        self.assertEqual(p.choose('exact',1,(3,3,3),0,1,4).cost,0)
    def test_policy_only_public_state(self):
        import inspect
        self.assertEqual(list(inspect.signature(Planner.choose).parameters),
                         ['self','method','h','ages','q','memory','budget'])
    def test_objective_validate(self):
        with self.assertRaises(ValueError):Planner(np.zeros((5,8,7)),**kwargs())
        with self.assertRaises(ValueError):Planner(np.full((5,8,8),-1.),**kwargs())
    def test_actual_evaluation_equals_exact_value(self):
        p=Planner(self.tab,**kwargs())
        v=p.evaluate('exact',3,(1,1,1),4,self.tab,p.hazards)
        np.testing.assert_allclose(v,p.values('exact',3,(1,1,1),4),atol=1e-12)
    def test_rollout_not_better_than_exact_in_model(self):
        p=Planner(self.tab,**kwargs())
        a=p.evaluate('rollout2',3,(1,1,1),4,self.tab,p.hazards)
        b=p.values('exact',3,(1,1,1),4)
        self.assertTrue(np.all(a>=b-1e-12))
    def test_budget_rejection(self):
        p=Planner(self.tab,**kwargs())
        with self.assertRaises(ValueError):p.choose('exact',1,(1,1,1),0,0,-1)

class FixedPolicyEfficiencyTests(unittest.TestCase):
    def test_never_tail_does_not_expand_unchosen_actions(self):
        p=Planner(calibration.semantic_table(True),**kwargs())
        p.values('never',4,(1,1,1),4)
        self.assertLessEqual(p.cache_info()['stage_kernels'],4)
    def test_fixed_tail_matches_fixed_policy_evaluator(self):
        p=Planner(calibration.semantic_table(True),**kwargs())
        np.testing.assert_allclose(p.values('age_paced',4,(1,1,1),4),
             p.evaluate('age_paced',4,(1,1,1),4,p.table,p.hazards),atol=1e-12)
