
import unittest,tempfile,threading,json,copy
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from pathlib import Path
from r7clib.transport import Client,validate_config_profile
from pilot.client import RunStopped
from pilot.common import read_json,digest
ROOT=Path(__file__).resolve().parents[1]
class Service:
 def __init__(self,contents=None,finish='stop',usage=True):
  self.contents=contents or ['{"done":"ready"}'];self.finish=finish;self.usage=usage;self.n=0
 def __enter__(self):
  outer=self
  class H(BaseHTTPRequestHandler):
   def log_message(self,*a):pass
   def do_POST(self):
    self.rfile.read(int(self.headers['Content-Length']));outer.n+=1
    body={'id':f'test-{outer.n}','model':'fixture','system_fingerprint':'fixture-v1',
       'choices':[{'finish_reason':outer.finish,'message':{'role':'assistant','content':outer.contents[min(outer.n-1,len(outer.contents)-1)]}}]}
    if outer.usage:body['usage']={'prompt_tokens':10,'completion_tokens':5,'total_tokens':15}
    raw=json.dumps(body).encode();self.send_response(200);self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
  self.s=ThreadingHTTPServer(('127.0.0.1',0),H);self.t=threading.Thread(target=self.s.serve_forever,daemon=True);self.t.start()
  self.cfg=read_json(ROOT/'config.example.json');self.cfg.update(backend_kind='test_fixture',base_url=f'http://127.0.0.1:{self.s.server_port}',model='fixture',min_interval_seconds=0)
  return self
 def __exit__(self,*a):self.s.shutdown();self.s.server_close();self.t.join()
class TransportTests(unittest.TestCase):
 def test_default_profile(self):validate_config_profile(read_json(ROOT/'config.example.json'))
 def test_old_model_is_not_silently_selected(self):
  c=read_json(ROOT/'config.example.json');c['model']='deepseek-flash'
  with self.assertRaises(ValueError):validate_config_profile(c)
 def test_secret_config_field_rejected(self):
  c=read_json(ROOT/'config.example.json');c['api_key']='bad'
  with self.assertRaises(ValueError):validate_config_profile(c)
 def test_call_and_immutable_reuse(self):
  with Service() as s,tempfile.TemporaryDirectory() as d:
   c=Client(s.cfg,d,cap=1);m=[{'role':'user','content':'x'}];r=c.complete('a',m);self.assertEqual(r,c.complete('a',m));self.assertEqual(s.n,1)
   with self.assertRaises(RunStopped):c.complete('a',[{'role':'user','content':'other'}])
 def test_cap_is_attempt_bound(self):
  with Service() as s,tempfile.TemporaryDirectory() as d:
   c=Client(s.cfg,d,cap=1);c.complete('a',[])
   with self.assertRaises(RunStopped):c.complete('b',[])
   self.assertEqual(s.n,1)
 def test_invalid_json_pause_no_retry(self):
  with Service(['not-json']) as s,tempfile.TemporaryDirectory() as d:
   c=Client(s.cfg,d,cap=2)
   for _ in range(2):
    with self.assertRaises(RunStopped):c.complete('a',[])
   self.assertEqual(s.n,1);self.assertEqual(len(list((Path(d)/'calls').glob('*.json'))),1)
 def test_fence_not_auto_stripped(self):
  with Service(['```json\n{"done":"x"}\n```']) as s,tempfile.TemporaryDirectory() as d:
   with self.assertRaises(RunStopped):Client(s.cfg,d).complete('a',[])
 def test_truncation_saved(self):
  with Service(finish='length') as s,tempfile.TemporaryDirectory() as d:
   with self.assertRaises(RunStopped):Client(s.cfg,d).complete('a',[])
   self.assertEqual(read_json(next((Path(d)/'calls').glob('*.json')))['response']['choices'][0]['finish_reason'],'length')
 def test_missing_usage_saved(self):
  with Service(usage=False) as s,tempfile.TemporaryDirectory() as d:
   with self.assertRaises(RunStopped):Client(s.cfg,d).complete('a',[])
 def test_key_not_in_payload(self):
  with Service() as s,tempfile.TemporaryDirectory() as d:
   with self.assertRaises(RunStopped):Client(s.cfg,d,secret='a_secret_key').complete('a',[{'role':'user','content':'a_secret_key'}])
   self.assertEqual(s.n,0)
 def test_start_without_response_not_retried(self):
  from pilot.common import write_json,request_payload
  with Service() as s,tempfile.TemporaryDirectory() as d:
   c=Client(s.cfg,d);payload=request_payload(s.cfg,[])
   write_json(Path(d)/'attempts/000001_start.json',{'attempt':1,'logical_id':'a','request_sha256':digest({'endpoint':s.cfg['base_url'],'payload':payload})})
   with self.assertRaises(RunStopped):c.complete('a',[])
   self.assertEqual(s.n,0)

class MoreTransportTests(unittest.TestCase):
 def test_changed_returned_identity_pauses(self):
  with Service() as s,tempfile.TemporaryDirectory() as d:
   c=Client(s.cfg,d);c.complete('a',[])
   from pilot.common import write_json
   write_json(Path(d)/'endpoint_identity.json',{'returned_model':'fixture','system_fingerprint':'other'})
   with self.assertRaises(RunStopped):c.complete('b',[])
   self.assertEqual(s.n,2)
 def test_unknown_raw_response_is_preserved(self):
  # Structured response with invalid output is persisted rather than reissued.
  with Service(['{"done":"x","done":"y"}']) as s,tempfile.TemporaryDirectory() as d:
   with self.assertRaises(RunStopped):Client(s.cfg,d).complete('a',[])
   r=read_json(next((Path(d)/'calls').glob('*.json')))
   self.assertEqual(r['text'],'{"done":"x","done":"y"}')
