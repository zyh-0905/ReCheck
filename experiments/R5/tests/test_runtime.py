
import unittest,tempfile,pathlib,json,copy
import numpy as np
from r5lib import runtime,storage,data,calibration,evaluator
from vendor.r4 import worker,environment

class ExecutionTests(unittest.TestCase):
    def test_independent_evaluator_all_modes(self):
        rows=data.make_rows(731)
        for q in range(5):
            task=data.make_task(q,rows,810+q)
            for m in range(8):
                for z in range(8):
                    w=environment.World(rows);w.set_modes(data.decode(z))
                    v=worker.make_view(task,data.memory(m))
                    answer,_=worker.execute(w,v,worker.rule_plan(v))
                    self.assertEqual(answer,evaluator.independently_execute(rows,task,m,z))
    def test_same_world_menu_pairing(self):
        p=data.load_protocol();p['streams_per_condition']=1;p['steps']=3
        cases=data.make_cases(p)
        before=copy.deepcopy(cases)
        k=calibration.fit([830])
        a=runtime.run_one(cases[0],p,'single','task_myopic',k)
        b=runtime.run_one(cases[0],p,'shared','task_myopic',k)
        self.assertEqual(cases,before)
        self.assertEqual(a['case_sha256'],b['case_sha256'])
    def test_budget_and_correct_replay(self):
        p=data.load_protocol();p['streams_per_condition']=1;p['steps']=3
        case=data.make_cases(p)[0];k=calibration.fit([830])
        a=runtime.run_one(case,p,'shared','task_exact',k)
        b=runtime.run_one(case,p,'shared','task_exact',k)
        self.assertEqual(runtime.science(a),runtime.science(b))
        self.assertTrue(all(r['credits']<=p['step_cap'] for r in a['records']))
        self.assertLessEqual(sum(r['credits'] for r in a['records']),p['budget'])
        for r,t in zip(a['records'],case['steps']):
            self.assertEqual(r['answer'],evaluator.independently_execute(case['rows'],t['task'],r['memory_after'],t['true_mode']))
    def test_source_hash_changed_blocks(self):
        with tempfile.TemporaryDirectory() as d:
            p=pathlib.Path(d);(p/'a.py').write_text('x=1')
            storage.make_manifest(p)
            self.assertTrue(storage.verify_source(p)['pass'])
            (p/'a.py').write_text('x=2')
            self.assertFalse(storage.verify_source(p)['pass'])
    def test_write_once(self):
        with tempfile.TemporaryDirectory() as d:
            p=pathlib.Path(d)/'x.json'
            storage.write_once(p,{'x':1});storage.write_once(p,{'x':1})
            with self.assertRaises(ValueError):storage.write_once(p,{'x':2})
    def test_lock_refuses_existing(self):
        with tempfile.TemporaryDirectory() as d:
            p=pathlib.Path(d)
            with storage.lock(p):
                with self.assertRaises(FileExistsError):
                    with storage.lock(p):pass
            self.assertFalse((p/'.write.lock').exists())
    def test_no_network_guard(self):
        import socket
        with storage.no_network():
            with self.assertRaises(RuntimeError):socket.socket()
    def test_archive_rejects_bad_paths(self):
        import zipfile
        with tempfile.TemporaryDirectory() as d:
            z=pathlib.Path(d)/'bad.zip'
            with zipfile.ZipFile(z,'w') as f:f.writestr('../x','bad')
            with self.assertRaises(ValueError):storage.verify_bundle(z)
    def test_run_has_no_test_scores(self):
        p=data.load_protocol();p['steps']=1;p['streams_per_condition']=1
        a=runtime.run_one(data.make_cases(p)[0],p,'shared','never',calibration.fit([1]))
        for r in a['records']:
            self.assertFalse({'gold','true_mode','success','failure'}&set(r))

class IsolationRegressionTests(unittest.TestCase):
    def test_current_hidden_rows_do_not_change_policy(self):
        p=data.load_protocol();p['steps']=3;p['streams_per_condition']=1
        a=data.make_cases(p)[0];b=copy.deepcopy(a)
        for r in b['rows']:
            r['physical']=0;r['reserved']=0;r['active']=False
        k=calibration.fit([830])
        x=runtime.run_one(a,p,'shared','task_exact',k)
        y=runtime.run_one(b,p,'shared','task_exact',k)
        self.assertEqual([r['packets'] for r in x['records']],[r['packets'] for r in y['records']])
    def test_future_tape_not_read_at_first_choice(self):
        p=data.load_protocol();p['steps']=3;p['streams_per_condition']=1
        a=data.make_cases(p)[0];b=copy.deepcopy(a)
        for e in b['steps'][1:]:e['q']=4;e['true_mode']^=7
        k=calibration.fit([830])
        x=runtime.run_one(a,p,'shared','task_exact',k)
        y=runtime.run_one(b,p,'shared','task_exact',k)
        self.assertEqual(x['records'][0]['packets'],y['records'][0]['packets'])
    def test_export_excludes_unregistered_local_config(self):
        import zipfile
        with tempfile.TemporaryDirectory() as d:
            p=pathlib.Path(d);(p/'a.py').write_text('x=1')
            storage.make_manifest(p)
            (p/'config.local.json').write_text('{"not_to_export":"private"}')
            storage.bundle(p,p/'out.zip')
            with zipfile.ZipFile(p/'out.zip') as z:
                self.assertNotIn('kit_source/config.local.json',z.namelist())
    def test_sensitive_record_blocks_export(self):
        with tempfile.TemporaryDirectory() as d:
            p=pathlib.Path(d);(p/'a.py').write_text('x=1')
            storage.make_manifest(p)
            f=p/'runs/R5_offline/status.json';f.parent.mkdir(parents=True)
            f.write_text('{"api_key":"sk-'+'A'*40+'"}')
            with self.assertRaises(ValueError):storage.bundle(p,p/'out.zip')
            self.assertFalse((p/'out.zip').exists())
    def test_reject_negative_or_nonfinite_cost(self):
        from r5lib.model import Planner
        tab=calibration.semantic_table(True)
        for price in (-1,float('nan'),float('inf')):
            with self.assertRaises(ValueError):
                Planner(tab,hazards=(.12,)*3,transition=data.transition(.85),
                        price=price,budget=8,step_cap=4,shared=True)

class ExportPositiveTests(unittest.TestCase):
    def test_export_contains_registered_trajectory_and_license(self):
        import zipfile
        with tempfile.TemporaryDirectory() as d:
            r=pathlib.Path(d);(r/'LICENSE').write_text('MIT')
            storage.make_manifest(r)
            f=r/'runs/R5_offline/trajectories/000_shared_task_exact.json'
            f.parent.mkdir(parents=True);f.write_text('{"stream":0}')
            storage.bundle(r,r/'x.zip')
            with zipfile.ZipFile(r/'x.zip') as z:
                self.assertIn('run/trajectories/000_shared_task_exact.json',z.namelist())
                self.assertIn('kit_source/LICENSE',z.namelist())
