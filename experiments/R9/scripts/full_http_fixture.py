"""Local software-test server only. This is NOT a researcher-callable remote LLM mode."""
from pathlib import Path
import sys,os,json,shutil,threading
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'vendor/toolsandbox')]
from pilot.common import read_json,write_json
from r9lib.rules import rule_action,history_from_messages
from r9lib.artifacts import source_hashes,verify_bundle,export_bundle
from r9lib.runtime import prepare,smoke,run
from r9lib.audit import audit
class Service:
 def __init__(self,mode):self.mode=mode;self.n=0
 def __enter__(self):
  outer=self
  class H(BaseHTTPRequestHandler):
   def log_message(self,*a):pass
   def do_POST(self):
    body=json.loads(self.rfile.read(int(self.headers['Content-Length'])));outer.n+=1
    if len(body['messages'])==2 and 'Return exactly one JSON object:' in body['messages'][0]['content']:obj={'done':'ready'}
    elif outer.mode=='cap':obj={'tool':'get_cellular_service_status','arguments':{}}
    else:
     public,hist=history_from_messages(body['messages']);mode='post_confirm' if 'After a successful mutation' in body['messages'][0]['content'] else 'once'
     obj=rule_action(public,hist,mode)
    response={'id':f'software-only-{outer.n}','model':'fixture','system_fingerprint':'r9-software-v1','choices':[{'finish_reason':'stop','message':{'role':'assistant','content':json.dumps(obj)}}],
      'usage':{'prompt_tokens':100,'completion_tokens':10,'total_tokens':110}}
    raw=json.dumps(response).encode();self.send_response(200);self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
  self.s=ThreadingHTTPServer(('127.0.0.1',0),H);self.t=threading.Thread(target=self.s.serve_forever,daemon=True);self.t.start();return self
 def __exit__(self,*a):self.s.shutdown();self.s.server_close();self.t.join()
def main(out,mode):
 dst=Path(out)
 if dst.exists():raise ValueError('Fresh software fixture directory required')
 shutil.copytree(ROOT,dst,ignore=shutil.ignore_patterns('__pycache__','.pytest_cache','runs','uploads','offline_reports','PREPARED.json'))
 with Service(mode) as server:
  cfg=read_json(dst/'config.example.json');cfg.update(backend_kind='test_fixture',model='fixture',base_url=f'http://127.0.0.1:{server.s.server_port}',min_interval_seconds=0)
  prepare(dst,fixture_config=cfg)
  assert smoke(dst,1,secret='local-fixture-token')['status']=='completed'
  assert run(dst,360,secret='local-fixture-token')['status']=='completed'
  before=server.n;assert run(dst,360,secret='local-fixture-token')['status']=='completed';assert server.n==before
  # After server context exits, no endpoint is available for reconstruction.
  count=server.n
 report=audit(dst);assert report['mechanical_pass'] and report['execution_complete'],report
 assert report['registered_requests']==count
 bundle=export_bundle(dst);verify_bundle(bundle)
 result={'kind':'SOFTWARE_TEST_NOT_LLM_RESULT','mode':mode,'local_http_requests':count,'completed_primary':report['completed_primary'],
  'completed_repeat':report['completed_repeat'],'reconstructed_research_requests':report['reconstructed_research_requests'],
  'execution_complete':True,'no_completed_run_resampling':True,'bundle':str(bundle)}
 write_json(dst/'FIXTURE_VERIFICATION.json',result);print(json.dumps(result,indent=2))
if __name__=='__main__':main(sys.argv[1],sys.argv[2])
