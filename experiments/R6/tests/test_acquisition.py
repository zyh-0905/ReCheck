import importlib, unittest
import numpy as np

def modules(test):
    try:return importlib.import_module('r6lib.data'),importlib.import_module('r6lib.acquisition')
    except ImportError as e:test.fail('paid calibration implementation missing: '+str(e))

class AcquisitionTests(unittest.TestCase):
    def test_canonical_cell_counts(self):
        d,a=modules(self)
        self.assertEqual(len(a.single_cells()),82)
        self.assertEqual(len(a.interaction_cells()),100)
        self.assertEqual(len(set(a.single_cells()+a.interaction_cells())),182)
    def test_irrelevant_coordinates_are_publicly_invariant(self):
        d,a=modules(self)
        for q in range(5):
            for m in range(8):
                for z in range(8):
                    c=a.canonical_cell((q,m,z))
                    rows=d.make_rows(6123456);task=d.make_task(q,rows,100+q)
                    from vendor.r4 import environment,worker
                    vals=[]
                    for mm,zz in [(m,z),(c[1],c[2])]:
                        w=environment.World(rows);w.set_modes(d.decode(zz))
                        v=worker.make_view(task,d.memory(mm))
                        vals.append(worker.execute(w,v,worker.rule_plan(v))[0])
                    self.assertEqual(vals[0],vals[1])
    def test_single_only_never_queries_interactions(self):
        d,a=modules(self);o=a.PaidOracle([6100099,6100100]);learner=a.Learner(o)
        learner.initialize_singles()
        self.assertEqual(o.label_executions,82*2)
        self.assertEqual(o.reference_executions,5*2)
        self.assertEqual(len(learner.observed),82)
        self.assertTrue(all((r['m']^r['z']).bit_count()==1 for r in o.events if r['kind']=='label'))
        self.assertTrue(np.isfinite(learner.table()).all())
    def test_duplicate_label_purchase_is_not_reexecuted(self):
        d,a=modules(self);o=a.PaidOracle([6100001]);r1=o.purchase((0,0,1));n=len(o.events)
        r2=o.purchase((0,0,1));self.assertEqual(r1,r2);self.assertEqual(n,len(o.events))
    def test_single_and_full_costs_include_reference_runs(self):
        d,a=modules(self);o=a.PaidOracle([6100011]);l=a.Learner(o);l.initialize_singles()
        self.assertEqual(o.total_workflows,87)
        for c in a.interaction_cells():l.buy(c)
        self.assertEqual(o.label_executions,182);self.assertEqual(o.total_workflows,187)
    def test_checkpoint_is_not_mutated_by_later_purchase(self):
        d,a=modules(self);o=a.PaidOracle([6100061]);l=a.Learner(o);l.initialize_singles()
        first=l.snapshot();l.buy(a.interaction_cells()[0]);second=l.snapshot()
        self.assertEqual(len(first['observed']),82);self.assertEqual(len(second['observed']),83)
        self.assertEqual(first['cost']['label_executions'],82)
    def test_reference_answers_and_every_label_match_independent_math(self):
        d,a=modules(self);o=a.PaidOracle([6100031]);l=a.Learner(o);l.initialize_singles()
        for c in a.interaction_cells():l.buy(c)
        for r in o.events:
            rows=d.make_rows(r['seed']);task=d.make_task(r['q'],rows,r['seed']*100+r['q'])
            if r['kind']=='label':
                ans=d.independent_execute(rows,task,r['m'],r['z'])
                self.assertEqual(ans,r['answer']);self.assertEqual(int(ans!=d.correct_answer(rows,task)),r['failure'])
    def test_bad_cells_and_seed_reuse_rejected(self):
        d,a=modules(self)
        with self.assertRaises(ValueError):a.PaidOracle([1,1])
        with self.assertRaises(ValueError):a.canonical_cell((True,0,1))
        with self.assertRaises(ValueError):a.canonical_cell((0,0,9))
    def test_data_seed_sets_disjoint(self):
        d,a=modules(self);p=d.protocol();sets=d.split_ids(p)
        cal=set(sum(sets['calibration'],[]));ev=set(sets['evaluation'])
        self.assertFalse(cal&ev);self.assertEqual(len(cal),64);self.assertEqual(len(ev),128)
    def test_known_diagonal_zero_without_buying_labels(self):
        d,a=modules(self);l=a.Learner(a.PaidOracle([6100010]));l.initialize_singles();t=l.table()
        for q in range(5):
            for m in range(8):self.assertEqual(t[q,m,m],0)

if __name__=='__main__':unittest.main()
