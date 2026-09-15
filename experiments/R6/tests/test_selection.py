import importlib,unittest,copy
import numpy as np
from r6lib import acquisition as a,data

def mod(t):
    try:return importlib.import_module('r6lib.selection')
    except ImportError as e:t.fail('selector not implemented: '+str(e))

class SelectionTests(unittest.TestCase):
    def small(self):
        p=data.protocol();p['selection']['design_ages']=[[1,1,1],[3,3,3]];p['selection']['design_budgets']=[3,8]
        return p
    def test_features_equal_exact_myopic_stage(self):
        s=mod(self);p=self.small();d=s.Design(p)
        l=a.Learner(a.PaidOracle([6100199]));l.initialize_singles();table=l.table();scores=d.action_scores(table)
        from vendor.planner import Planner
        for i in [0,len(d.states)//2,len(d.states)-1]:
            state=d.states[i]
            pl=Planner(table,hazards=p['hazards'],transition=data.transition(p['persistence']),price=p['credit_price'],budget=p['budget'],step_cap=p['step_cap'],shared=state['shared'])
            raw=pl.scores('myopic',1,tuple(state['ages']),state['budget'])[:,state['q'],state['memory']]
            np.testing.assert_allclose(raw,scores[i,:len(raw)],atol=1e-14,rtol=0);pl.clear()
    def test_acquisition_scores_without_oracle_argument(self):
        s=mod(self);d=s.Design(self.small());l=a.Learner(a.PaidOracle([6100017]));l.initialize_singles()
        before=len(l.oracle.events);values=d.rank(l.table(),a.interaction_cells(),'decision')
        self.assertEqual(len(l.oracle.events),before);self.assertEqual(len(values),100)
        self.assertTrue(all(np.isfinite(score) and score>=0 for _,score in values))
    def test_budgets_share_prefix_but_not_future_labels(self):
        s=mod(self);p=self.small();d=s.Design(p)
        r=s.learn_panel([6100555],p,d,'decision',[2,4],seed=7)
        c2=r['checkpoints']['2'];c4=r['checkpoints']['4']
        self.assertEqual(len(c2['observed']),84);self.assertEqual(len(c4['observed']),86)
        self.assertEqual(c2['cost']['total_workflows'],89);self.assertEqual(c4['cost']['total_workflows'],91)
        self.assertEqual(len(r['selection']),4)
        self.assertEqual(c2['selected_cells'],c4['selected_cells'][:2])
    def test_selection_deterministic_at_fixed_seed(self):
        s=mod(self);p=self.small();d=s.Design(p)
        x=s.learn_panel([6100551],p,d,'random',[2],seed=2)
        y=s.learn_panel([6100551],p,d,'random',[2],seed=2)
        self.assertEqual(x['checkpoints']['2']['selected_cells'],y['checkpoints']['2']['selected_cells'])
    def test_single_model_ignores_labels_of_future_unbought_cells(self):
        s=mod(self);o=a.PaidOracle([6100019]);l=a.Learner(o);l.initialize_singles();before=l.table().copy()
        # Training environment still contains unqueried behavior, but learner never reads it.
        self.assertEqual(o.label_executions,82)
        d=s.Design(self.small());d.rank(before,a.interaction_cells(),'occupancy')
        np.testing.assert_array_equal(before,l.table());self.assertEqual(o.label_executions,82)
    def test_every_added_atom_has_equal_workflow_cost(self):
        s=mod(self);p=self.small();d=s.Design(p)
        for method in ['random','occupancy','decision']:
            x=s.learn_panel([6100038,6100039],p,d,method,[2],seed=1)
            self.assertEqual(x['checkpoints']['2']['cost']['label_executions'],168)
    def test_unknown_selector_rejected(self):
        s=mod(self);d=s.Design(self.small())
        with self.assertRaises(ValueError):d.rank(np.zeros((5,8,8)),a.interaction_cells(),'cheat')

if __name__=='__main__':unittest.main()
