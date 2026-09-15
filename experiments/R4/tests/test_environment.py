import itertools, unittest, copy
from r4lib import environment as e, worker as w

class EnvironmentTests(unittest.TestCase):
    def test_public_contract(self):
        self.assertTrue(callable(getattr(e,'World',None)))
        self.assertTrue(callable(getattr(w,'make_view',None)))
    def rows(self):
        return [dict(sku=f'S{i:02}',category='A' if i%2==0 else 'B',active=i%3!=0,physical=7+i,reserved=i%5) for i in range(11)]
    def test_all_modes_rule_matches_independent_truth(self):
        for modes in itertools.product((0,1),repeat=3):
            world=e.World(self.rows());world.set_modes(modes)
            mem=e.decode_receipts(world.initial_calibration())
            for q in range(3):
                task=dict(type=q,category='A',minimum=8,skus=['S00','S03','S10'])
                view=w.make_view(task,mem);plan=w.rule_plan(view)
                self.assertTrue(w.valid_plan(plan,view))
                out,trace=w.execute(world,view,plan)
                self.assertEqual(out,e.gold(self.rows(),task))
                self.assertGreater(len(trace),0)
    def test_pagination_really_fetches_multiple_pages(self):
        world=e.World(self.rows());world.set_modes((0,0,0));mem=e.decode_receipts(world.initial_calibration())
        task=dict(type=0,category='A',minimum=0,skus=[]);v=w.make_view(task,mem)
        out,trace=w.execute(world,v,w.rule_plan(v))
        self.assertGreater(sum(t['path']=='/catalog/items' for t in trace),1)
    def test_private_state_not_in_view(self):
        t=dict(type=2,category='A',minimum=8,skus=[],modes=[1,1,1],seed=88,gold={'bad':True})
        mem=dict(first_page=0,active_code=1,stock_semantics='net')
        a=w.make_view(t,mem);b=w.make_view({**t,'modes':[0,0,0],'gold':None},mem)
        self.assertEqual(a,b)
        self.assertNotIn('modes',str(a));self.assertNotIn('checked_at',str(a))
    def test_bad_unused_field_is_not_silently_fixed(self):
        t=dict(type=0,category='A',minimum=8,skus=[])
        v=w.make_view(t,dict(first_page=0,active_code=1,stock_semantics='net'))
        p=w.rule_plan(v);p['stock_semantics']='net'
        self.assertFalse(w.valid_plan(p,v))
    def test_bool_page_rejected(self):
        t=dict(type=0,category='A',minimum=0,skus=[])
        v=w.make_view(t,dict(first_page=0,active_code=1,stock_semantics='net'));p=w.rule_plan(v);p['first_page']=False
        self.assertFalse(w.valid_plan(p,v))
    def test_budget_rejects_before_query(self):
        world=e.World(self.rows());packets=[dict(id='p01',cover=[0,1],cost=3)]
        bank=e.ProbeBudget(world,packets,2,4)
        with self.assertRaises(ValueError):bank.read(('p01',))
        self.assertEqual(bank.remaining,2);self.assertEqual(bank.transactions,[])
    def test_bundle_charged_once_and_scoped(self):
        world=e.World(self.rows());world.set_modes((1,0,1))
        packets=[dict(id='p01',cover=[0,1],cost=3)]
        bank=e.ProbeBudget(world,packets,8,4);r=bank.read(('p01',))
        self.assertEqual(bank.remaining,5)
        decoded=e.decode_receipts(r);self.assertEqual(set(decoded),{'first_page','active_code'})
        self.assertEqual(decoded,dict(first_page=1,active_code=1))
    def test_invalid_packet_never_executes(self):
        bank=e.ProbeBudget(e.World(self.rows()),[dict(id='s0',cover=[0],cost=2)],8,4)
        with self.assertRaises(ValueError):bank.read(('s0','s0'))
        self.assertEqual(bank.remaining,8)
    def test_counterexample_stale_not_always_wrong(self):
        rows=[dict(sku='X',category='A',active=True,physical=5,reserved=0)]
        world=e.World(rows);world.set_modes((0,0,1))
        t=dict(type=1,category='A',minimum=0,skus=['X']);v=w.make_view(t,dict(first_page=0,active_code=1,stock_semantics='net'))
        out,_=w.execute(world,v,w.rule_plan(v))
        self.assertEqual(out,e.gold(rows,t),'Net vs gross can coincide with zero reserved stock')
