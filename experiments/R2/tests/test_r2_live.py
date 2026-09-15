
import contextlib,io,json,tempfile,threading,unittest
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from pathlib import Path
from pilot.common import default_config,read_json,write_json
from pilot.client import RunStopped
from r2lib import session,experiment,protocol

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def do_POST(self):
        p=json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        self.server.requests.append(p);text=p["messages"][-1]["content"];finish="stop"
        if text=="FAIL":
            self.send_response(503);self.end_headers();return
        if text=="BAD":answer="not JSON"
        elif text=="TRUNCATED":answer="";finish="length"
        elif text.startswith("Return exactly"):answer='{"ok":true}'
        else:
            x=json.loads(text);stage=x["stage"]
            if stage=="memory_write":
                a={"amount_divisor":int(x["calibration"][0]["raw_amount"]),"endpoint_inclusive":bool(x["calibration"][1]["returned_count"])}
            elif stage=="plan":
                fields=x["task"]["requested_fields"];m=x["memory"];cut=x["task"]["cutoff"]
                a={"amount_divisor":m["amount_divisor"] if "total" in fields else None,
                   "time_bound":cut+(not m["endpoint_inclusive"]) if cut is not None else None}
            elif stage=="answer":
                t=x["tool_result"];pl=x["executed_plan"]
                a={"total":t["sum_amount_raw"]/pl["amount_divisor"] if "sum_amount_raw" in t else None,
                   "count":t.get("count_before",t.get("count_all"))}
            else:raise ValueError(stage)
            answer=json.dumps(a)
        body={"id":"fixture_"+str(len(self.server.requests)),"model":p["model"],"system_fingerprint":getattr(self.server,"fingerprint","fixture_only"),
              "choices":[{"message":{"content":answer},"finish_reason":finish}],
              "usage":{"prompt_tokens":120,"prompt_cache_hit_tokens":0,"prompt_cache_miss_tokens":120,
                       "completion_tokens":20,"completion_tokens_details":{"reasoning_tokens":0}}}
        raw=json.dumps(body).encode()
        self.send_response(200);self.send_header("Content-Length",str(len(raw)));self.end_headers();self.wfile.write(raw)

class LiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=ThreadingHTTPServer(("127.0.0.1",0),Handler);cls.server.requests=[]
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
    @classmethod
    def tearDownClass(cls):cls.server.shutdown();cls.server.server_close()
    def cfg(self):
        cfg=default_config();cfg.update(base_url=f"http://127.0.0.1:{self.server.server_port}/v1",
           model="SOFTWARE_TEST_NOT_LLM",backend_kind="test_fixture",local_no_auth=True,min_interval_seconds=0,
           max_output_tokens=16384,max_requests=484)
        return cfg
    def client(self,d,cap=484):
        self.assertTrue(callable(getattr(session,"Client",None)),"Client missing")
        return session.Client(self.cfg(),d,cap=cap)
    def msg(self,s):return [{"role":"user","content":s}]
    def test_success_resume_not_resampled(self):
        with tempfile.TemporaryDirectory() as d,contextlib.redirect_stdout(io.StringIO()):
            c=self.client(d);a=c.complete("one",self.msg('Return exactly {"ok":true}'))
            b=c.complete("one",self.msg('Return exactly {"ok":true}'))
            self.assertEqual(a,b);self.assertEqual(c.budget()["attempts"],1)
    def test_different_request_same_id_blocked(self):
        with tempfile.TemporaryDirectory() as d,contextlib.redirect_stdout(io.StringIO()):
            c=self.client(d);c.complete("one",self.msg('Return exactly {"ok":true}'))
            with self.assertRaises(RunStopped):c.complete("one",self.msg('Return exactly {"ok":false}'))
    def test_truncation_saved_and_pauses_on_resume(self):
        with tempfile.TemporaryDirectory() as d,contextlib.redirect_stdout(io.StringIO()):
            c=self.client(d)
            for _ in range(2):
                with self.assertRaises(RunStopped):c.complete("one",self.msg("TRUNCATED"))
            self.assertEqual(c.budget()["attempts"],1);self.assertEqual(len(list((Path(d)/"calls").glob("*.json"))),1)
    def test_invalid_json_saved_no_retry(self):
        with tempfile.TemporaryDirectory() as d,contextlib.redirect_stdout(io.StringIO()):
            c=self.client(d)
            for _ in range(2):
                with self.assertRaises(RunStopped):c.complete("one",self.msg("BAD"))
            self.assertEqual(c.budget()["attempts"],1)
    def test_http_error_pauses_and_no_retry(self):
        with tempfile.TemporaryDirectory() as d,contextlib.redirect_stdout(io.StringIO()):
            c=self.client(d)
            for _ in range(2):
                with self.assertRaises(RunStopped):c.complete("one",self.msg("FAIL"))
            self.assertEqual(c.budget()["attempts"],1)
    def test_uncertain_start_does_not_retry(self):
        from pilot.common import digest,request_payload
        with tempfile.TemporaryDirectory() as d:
            c=self.client(d);msg=self.msg('Return exactly {"ok":true}');pl=request_payload(self.cfg(),msg)
            write_json(Path(d)/"attempts/000001_start.json",{"attempt":1,"logical_id":"one",
                "request_sha256":digest({"endpoint":self.cfg()["base_url"],"payload":pl})})
            with self.assertRaises(RunStopped):c.complete("one",msg)
            self.assertEqual(c.budget()["attempts"],1)
    def test_hard_cap_before_transmission(self):
        with tempfile.TemporaryDirectory() as d,contextlib.redirect_stdout(io.StringIO()):
            c=self.client(d,cap=1);c.complete("one",self.msg('Return exactly {"ok":true}'))
            with self.assertRaises(RunStopped):c.complete("two",self.msg('Return exactly {"ok":true}'))
            self.assertEqual(c.budget()["attempts"],1)
    def test_registered_and_send_intent_are_separate(self):
        with tempfile.TemporaryDirectory() as d,contextlib.redirect_stdout(io.StringIO()):
            c=self.client(d);c.complete("one",self.msg('Return exactly {"ok":true}'))
            e=read_json(Path(d)/"attempts/000001_send_intent.json")
            self.assertFalse(e["proves_remote_receipt"])
            from pilot.common import digest
            st=read_json(Path(d)/"attempts/000001_start.json")
            self.assertEqual(st.get("payload_sha256"),digest(st["payload"]))
    def test_real_secret_not_in_model_payload(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertTrue(callable(getattr(session,"Client",None)))
            c=session.Client(self.cfg(),d,secret="secret123",cap=1)
            with self.assertRaises(RunStopped):c.complete("one",self.msg("secret123"))
            self.assertEqual(c.budget()["attempts"],0)
    def test_full_protocol_and_no_private_fields(self):
        self.assertTrue(callable(getattr(experiment,"run",None)),"experiment.run missing")
        with tempfile.TemporaryDirectory() as d,contextlib.redirect_stdout(io.StringIO()):
            cfg=self.cfg();s=protocol.load_protocol();start=len(self.server.requests)
            c=self.client(d);experiment.run(c,cfg,Path(d),s)
            self.assertEqual(c.budget()["attempts"],484)
            self.assertEqual(len(list((Path(d)/"records").glob("*.json"))),240)
            for req in self.server.requests[start:]:
                text=json.dumps(req)
                for forbidden in ['"modes"','"actual_hazard"','"gold"','"probe_price"','"method"','"regime"']:
                    self.assertNotIn(forbidden,text)
            experiment.run(c,cfg,Path(d),s)
            self.assertEqual(c.budget()["attempts"],484)
            rows=[read_json(x) for x in (Path(d)/"records").glob("*.json")]
            for i in range(4):self.assertEqual(len({r["prefix_sha256"] for r in rows if r["stream"]==i}),1)

    def test_controller_arguments_exclude_private_generation_fields(self):
        from unittest.mock import patch
        original=experiment.choose
        seen=[]
        def guard(method,age,q,remaining,dp,cell,s):
            seen.append(1)
            self.assertNotIn("actual_hazard",cell)
            self.assertNotIn("world_seed",cell)
            self.assertNotIn("streams",s)
            return original(method,age,q,remaining,dp,cell,s)
        with tempfile.TemporaryDirectory() as d,contextlib.redirect_stdout(io.StringIO()):
            spec=protocol.load_protocol()
            # Software-only tiny prefix; not a live-run config exposed by the CLI.
            spec["streams"]=spec["streams"][:1];spec["steps"]=1;spec["logical_calls"]=11
            c=self.client(d)
            with patch.object(experiment,"choose",guard):
                experiment.run(c,self.cfg(),Path(d),spec)
            self.assertTrue(seen)

    def test_identity_metadata_change_is_retained_and_paused(self):
        with tempfile.TemporaryDirectory() as d,contextlib.redirect_stdout(io.StringIO()):
            c=self.client(d);c.complete("one",self.msg('Return exactly {"ok":true}'))
            self.server.fingerprint="changed_fixture"
            try:
                with self.assertRaises(RunStopped):c.complete("two",self.msg('Return exactly {"ok":true}'))
                self.assertEqual(c.budget()["attempts"],2)
                self.assertEqual(len(list((Path(d)/"calls").glob("*.json"))),2)
            finally:self.server.fingerprint="fixture_only"
