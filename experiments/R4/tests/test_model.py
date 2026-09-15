import unittest
from r4lib import model

class CoreContract(unittest.TestCase):
    def test_public_solver_contract(self):
        self.assertTrue(callable(getattr(model, 'Solver', None)), 'Missing coupled refresh solver')
    def test_public_probability_contract(self):
        self.assertTrue(callable(getattr(model, 'mismatch', None)), 'Missing binary flip probability')

if __name__=='__main__': unittest.main()

class ModelBehavior(unittest.TestCase):
    def spec(self):
        return dict(hazards=[.1,.1,.1], weights=[[1,1,0],[0,0,1],[1,1,1]],
            transition=[[.8,.1,.1],[.1,.8,.1],[.1,.1,.8]], price=.05, step_cap=4,
            packets=[dict(id='s0',cover=[0],cost=2),dict(id='s1',cover=[1],cost=2),
              dict(id='s2',cover=[2],cost=2),dict(id='p01',cover=[0,1],cost=3),dict(id='p12',cover=[1,2],cost=3)])
    def test_probability(self):
        self.assertAlmostEqual(model.mismatch(0,.2),0)
        self.assertAlmostEqual(model.mismatch(2,.2),.32)
        self.assertAlmostEqual(model.mismatch(10,0),0)
    def test_invalid_probability(self):
        for a,h in [(-1,.1),(2,-.1),(1,.7)]:
            with self.assertRaises(ValueError):model.mismatch(a,h)
    def test_budget_and_overlap(self):
        s=model.Solver(self.spec())
        self.assertEqual(len(s.actions(0)),1)
        self.assertTrue(all(a.cost<=3 for a in s.actions(3)))
        p=next(a for a in s.actions(3) if a.ids==('p01',))
        self.assertEqual(p.cover,(0,1));self.assertEqual(p.cost,3)
        self.assertFalse(any(a.ids==('s0','s1') for a in s.actions(3)))
    def test_no_independent_double_refresh_charge(self):
        s=model.Solver(self.spec());a=next(a for a in s.actions(3) if a.ids==('p01',))
        ages,remaining=s.after((4,5,2),4,a)
        self.assertEqual(ages,(1,1,3));self.assertEqual(remaining,1)
    def test_joint_one_step_equals_myopic(self):
        s=model.Solver(self.spec())
        for q in range(3):
            self.assertEqual(s.choose('recheck_joint',1,(2,3,4),q,4),s.choose('bundle_myopic',1,(2,3,4),q,4))
    def test_exhaustive_small(self):
        s=model.Solver(self.spec())
        def brute(h,ages,q,b):
            if h==0:return 0.
            vals=[]
            for a in s.actions(b):
                nxt,nb=s.after(ages,b,a)
                vals.append(s.loss(ages,q,a)+s.price*a.cost+sum(s.P[q][k]*brute(h-1,nxt,k,nb) for k in range(3)))
            return min(vals)
        self.assertAlmostEqual(s.value(3,(1,2,1),0,4),brute(3,(1,2,1),0,4),places=11)
    def test_rules_are_feasible(self):
        s=model.Solver(self.spec())
        for method in model.METHODS:
            for b in range(6):
                a=s.choose(method,3,(1,2,4),2,b)
                self.assertLessEqual(a.cost,b);self.assertLessEqual(a.cost,4)
    def test_joint_model_not_worse_than_baselines(self):
        s=model.Solver(self.spec())
        val=s.value(4,(1,1,1),0,5)
        for method in model.METHODS:
            self.assertLessEqual(val,s.evaluate(method,4,(1,1,1),0,5)+1e-10)
    def test_rollout_not_worse_than_its_base_model(self):
        s=model.Solver(self.spec())
        self.assertLessEqual(s.evaluate('bundle_rollout',4,(1,1,1),2,4),s.evaluate('age_paced',4,(1,1,1),2,4)+1e-10)
    def test_no_budget_loss_accumulates(self):
        s=model.Solver(self.spec())
        self.assertGreater(s.value(3,(1,1,1),2,0),s.value(1,(1,1,1),2,0))
    def test_duplicate_packets_rejected(self):
        spec=self.spec();spec['packets'].append(spec['packets'][0])
        with self.assertRaises(ValueError):model.Solver(spec)
