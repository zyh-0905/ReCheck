"""Local HTTP fixture tests. This is NOT an LLM and never contributes research data."""
import contextlib,copy,io,json,os,re,tempfile,threading,unittest,zipfile
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from pilot.common import default_config,validate_config,freeze_run,read_json,write_json
from pilot.client import JournalClient,RunStopped
from pilot import recheck,readiness
from pilot.report import summarize,export

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def do_POST(self):
        body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        self.server.requests.append(body)
        text=body['messages'][-1]['content']
        if text=='BAD_JSON':answer='not json'
        elif text=='FAIL_HTTP':
            self.send_response(503);self.end_headers();self.wfile.write(b'fixture outage');return
        elif text.startswith('Return exactly'):answer=json.dumps({'ok':True})
        else:
            x=json.loads(text);stage=x['stage']
            if stage=='memory_write':
                answer={'amount_divisor':int(x['calibration'][0]['raw_amount']), 'endpoint_inclusive':bool(x['calibration'][1]['returned_count'])}
            elif stage=='plan':
                fields=x['task']['requested_fields'];mem=x['memory'];cut=x['task']['cutoff']
                answer={'amount_divisor':mem['amount_divisor'] if 'total' in fields else None,
                        'time_bound':(cut if mem['endpoint_inclusive'] else cut+1) if cut is not None else None}
            elif stage=='answer':
                r=x['tool_result'];p=x['executed_plan']
                answer={'total':r['sum_amount_raw']/p['amount_divisor'] if 'sum_amount_raw' in r else None,
                        'count':r.get('count_before',r.get('count_all'))}
            elif stage=='artifact':
                rule=x['specification']['rule'];m=re.search(r'as (\d+) plus (\d+) times the value of (\w+)',rule)
                v=int(m[1])+int(m[2])*x['current_sources'][m[3]];threshold=int(re.search(r'at least (\d+)',rule)[1])
                answer={'metric':v,'flag':'high' if v>=threshold else 'low'}
            elif stage=='select_repair':
                answer={'artifact_ids':[s['id'] for s in x['specifications'] if 'value of tariff.' in s['rule']]}
            else:raise ValueError(stage)
            answer=json.dumps(answer)
        response={'id':'fixture_response','model':'TEST_FIXTURE_NOT_LLM','choices':[{'message':{'content':answer},'finish_reason':'stop'}],
                  'usage':{'prompt_tokens':100,'completion_tokens':20}}
        raw=json.dumps(response).encode();self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)

class Integration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),Handler);cls.server.requests=[]
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
    @classmethod
    def tearDownClass(cls):cls.server.shutdown();cls.server.server_close()
    def cfg(self):
        d=default_config();d.update(base_url=f'http://127.0.0.1:{self.server.server_port}/v1',model='fixture',backend_kind='test_fixture',local_no_auth=True,min_interval_seconds=0)
        return validate_config(d)
    def test_resume_no_resampling(self):
        with tempfile.TemporaryDirectory() as d,contextlib.redirect_stdout(io.StringIO()):
            c=JournalClient(self.cfg(),d);msg=[{'role':'user','content':'Return exactly {"ok":true}'}]
            a=c.complete('a',msg);b=c.complete('a',msg)
            self.assertEqual(a,b);self.assertEqual(c.budget()['attempts'],1)
            with self.assertRaises(RunStopped):c.complete('a',[{'role':'user','content':'different'}])
    def test_model_error_not_retried(self):
        with tempfile.TemporaryDirectory() as d,contextlib.redirect_stdout(io.StringIO()):
            c=JournalClient(self.cfg(),d);msg=[{'role':'user','content':'BAD_JSON'}]
            self.assertEqual(c.complete('a',msg)['text'],'not json');c.complete('a',msg)
            self.assertEqual(c.budget()['attempts'],1)
    def test_hard_request_cap(self):
        with tempfile.TemporaryDirectory() as d,contextlib.redirect_stdout(io.StringIO()):
            cfg=self.cfg();cfg['max_requests']=1;c=JournalClient(cfg,d);m=[{'role':'user','content':'Return exactly {}'}]
            c.complete('a',m)
            with self.assertRaises(RunStopped):c.complete('b',m)
            self.assertEqual(c.budget()['attempts'],1)
    def test_failed_requests_preserved(self):
        with tempfile.TemporaryDirectory() as d,contextlib.redirect_stdout(io.StringIO()):
            c=JournalClient(self.cfg(),d);m=[{'role':'user','content':'FAIL_HTTP'}]
            with self.assertRaises(RunStopped):c.complete('a',m)
            with self.assertRaises(RunStopped):c.complete('a',m)
            self.assertEqual(c.budget()['attempts'],1);self.assertEqual(c.budget()['unknown_or_unbilled_attempts'],1)
    def test_manifest_freeze(self):
        with tempfile.TemporaryDirectory() as d:
            cfg=self.cfg();freeze_run(d,cfg,'smoke',{'phase':'test'})
            self.assertEqual(freeze_run(d,cfg,'smoke',{'phase':'test'})['evidence_label'],'SOFTWARE_TEST_NOT_RESEARCH')
            cfg['model']='other'
            with self.assertRaises(ValueError):freeze_run(d,cfg,'smoke',{'phase':'test'})
    def test_recheck_end_to_end_and_resume(self):
        with tempfile.TemporaryDirectory() as d,contextlib.redirect_stdout(io.StringIO()):
            cfg=self.cfg();spec=recheck.protocol(2,3);freeze_run(d,cfg,'recheck',spec);client=JournalClient(cfg,d)
            before=len(self.server.requests);recheck.run(client,cfg,d,spec)
            self.assertEqual(client.budget()['attempts'],50)
            recheck.run(client,cfg,d,spec);self.assertEqual(client.budget()['attempts'],50)
            sm=summarize(d);self.assertEqual(sm['completed_records'],24);self.assertFalse(sm['source_snapshot_mismatches'])
            rows=[read_json(p) for p in (Path(d)/'records').glob('*.json')]
            for s in range(2):self.assertEqual(len({r['prefix_sha256'] for r in rows if r['stream']==s}),1)
            for req in self.server.requests[before:]:
                wire=json.dumps(req)
                for forbidden in ['"modes"','"gold"','"evaluator_rules"','"regime"','"method"','SELECT SUM']:
                    self.assertNotIn(forbidden,wire)
    def test_readiness_end_to_end_no_gold_and_prefix_identical(self):
        with tempfile.TemporaryDirectory() as d,contextlib.redirect_stdout(io.StringIO()):
            cfg=self.cfg();spec=readiness.protocol(4);freeze_run(d,cfg,'repairlens_readiness',spec);client=JournalClient(cfg,d)
            before=len(self.server.requests);readiness.run(client,cfg,d,spec);sm=summarize(d)
            self.assertEqual(sm['completed_records'],12);self.assertEqual(client.budget()['attempts'],34)
            rows=[read_json(p) for p in (Path(d)/'records').glob('*.json')]
            for i in range(4):self.assertEqual(len({r['prefix_sha256'] for r in rows if r['case']==i}),1)
            for req in self.server.requests[before:]:self.assertNotIn('evaluator_rules',json.dumps(req))
            self.assertTrue(all(m['success_rate']==1 for m in sm['methods'] if m['method']!='keep_stale'))
    def test_export_excludes_key_files(self):
        with tempfile.TemporaryDirectory() as d,contextlib.redirect_stdout(io.StringIO()):
            root=Path(d)/'run';cfg=self.cfg();freeze_run(root,cfg,'smoke',{'phase':'test'})
            (root/'.env').write_text('API_KEY=secret-value');(root/'config.local.json').write_text('{"api_key":"secret-value"}')
            z=export(root,Path(d)/'upload.zip','secret-value')
            with zipfile.ZipFile(z) as f:
                self.assertNotIn('.env',f.namelist());self.assertNotIn('config.local.json',f.namelist());self.assertIn('manifest.json',f.namelist())
