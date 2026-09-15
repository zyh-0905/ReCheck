import unittest,importlib,tempfile,copy,json, pathlib,socket
from r6lib import acquisition as a,data

def mod(t,name):
    try:return importlib.import_module('r6lib.'+name)
    except ImportError as e:t.fail(name+' not implemented: '+str(e))

class RuntimeTests(unittest.TestCase):
    def setup_run(self):
        p=data.protocol();p['calibration_panels']=1;p['streams_per_condition']=1;p['steps']=2
        o=a.PaidOracle([6100221]);l=a.Learner(o);l.initialize_singles();s=l.snapshot()
        return p,s,data.cases(p)[0]
    def test_real_budget_and_outputs(self):
        r=mod(self,'runtime');p,s,c=self.setup_run();sol=r.planner(p,'shared',s,'single_only');out=r.run_one(c,p,'shared','single_only',s,sol)
        b=p['budget']
        for rec,e in zip(out['records'],c['steps']):
            self.assertEqual(rec['budget_after'],b-rec['credits']);b-=rec['credits']
            self.assertGreaterEqual(b,0);self.assertLessEqual(rec['credits'],p['step_cap'])
            self.assertEqual(rec['answer'],data.independent_execute(c['rows'],e['task'],rec['memory_after'],e['true_mode']))
        sol.clear()
    def test_only_chosen_model_predicts_each_policy(self):
        r=mod(self,'runtime');p,s,c=self.setup_run();sol=r.planner(p,'shared',s,'single_only');out=r.run_one(c,p,'shared','single_only',s,sol)
        self.assertEqual(out['calibration_fingerprint'],s['model_fingerprint']);sol.clear()
    def test_strict_state_has_no_true_mode_field(self):
        r=mod(self,'runtime');p,s,c=self.setup_run()
        import inspect
        self.assertEqual(list(inspect.signature(r.planner(p,'shared',s,'single_only').choose).parameters),['method','h','ages','q','memory','budget'])
    def test_immutable_write(self):
        st=mod(self,'storage')
        with tempfile.TemporaryDirectory() as td:
            f=pathlib.Path(td)/'a.json';st.write_once(f,{'a':1});st.write_once(f,{'a':1})
            with self.assertRaises(ValueError):st.write_once(f,{'a':2})
    def test_network_blocked(self):
        st=mod(self,'storage')
        with st.no_network():
            with self.assertRaises(RuntimeError):socket.create_connection(('example.com',443))
    def test_source_tamper_detected(self):
        st=mod(self,'storage')
        with tempfile.TemporaryDirectory() as td:
            root=pathlib.Path(td);(root/'hello.py').write_text('x=1');st.make_manifest(root)
            self.assertTrue(st.verify_source(root)['pass']);(root/'hello.py').write_text('x=2')
            self.assertFalse(st.verify_source(root)['pass'])
    def test_reference_mean_not_money(self):
        mod(self,'runtime');p=data.protocol()
        self.assertIn('NOT_money',p['calibration_cost_sensitivity']['unit'])
    def test_gold_does_not_change_selected_action(self):
        r=mod(self,'runtime');p,s,c=self.setup_run();sol=r.planner(p,'shared',s,'single_only')
        a0=sol.choose('exact',2,(1,1,1),0,0,8)
        c['rows'][0]['physical']+=10000
        a1=sol.choose('exact',2,(1,1,1),0,0,8)
        self.assertEqual(a0,a1);sol.clear()

if __name__=='__main__':unittest.main()
