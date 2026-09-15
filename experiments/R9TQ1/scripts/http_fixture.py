
"""SOFTWARE TEST ONLY: loopback HTTP, synthetic responses, native simulator execution."""
from pathlib import Path
import argparse,sys,threading,json,shutil
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/"vendor/toolsandbox"),str(ROOT/"tests")]
from helpers import model_fixture,freeze
from tq.runtime import prepare,qualify,audit,export
from tq.common import read,write
from tq.contract import validate_history
def main():
 p=argparse.ArgumentParser();p.add_argument("--mode",choices=["normal","cap","prose","bad_batch"],required=True)
 p.add_argument("--out",required=True);a=p.parse_args()
 out=Path(a.out)
 if out.exists():raise RuntimeError("Fixture output already exists")
 shutil.copytree(ROOT,out,ignore=shutil.ignore_patterns("runs","uploads",".venv","__pycache__","PREPARED.json",".run.lock"))
 freeze(out);received=[]
 class Handler(BaseHTTPRequestHandler):
  def log_message(self,*args):pass
  def do_POST(self):
   raw=self.rfile.read(int(self.headers["Content-Length"]));payload=json.loads(raw)
   assert "tools" in payload and payload["tool_choice"]=="auto" and payload["model"]=="deepseek-flash"
   assert "response_format" not in payload and "extra_body" not in payload and "parallel_tool_calls" not in payload
   validate_history(payload["messages"])
   received.append(payload)
   b=json.dumps(model_fixture(payload,len(received),a.mode)).encode()
   self.send_response(200);self.send_header("Content-Type","application/json");self.send_header("Content-Length",str(len(b)));self.end_headers();self.wfile.write(b)
 server=ThreadingHTTPServer(("127.0.0.1",0),Handler);t=threading.Thread(target=server.serve_forever,daemon=True);t.start()
 try:
  prepare(out)
  st=qualify(out,12,secret="dummy-loopback-credential",test_endpoint=f"http://127.0.0.1:{server.server_port}/chat/completions")
  first=len(received)
  if st["status"] in ("completed","completed_not_qualified"):
   qualify(out,12,secret="not_used",test_endpoint=f"http://127.0.0.1:{server.server_port}/chat/completions")
  else:
   try:qualify(out,12,secret="not_used",test_endpoint=f"http://127.0.0.1:{server.server_port}/chat/completions")
   except Exception:pass
  assert len(received)==first
 finally:server.shutdown();server.server_close();t.join()
 ar=audit(out);bundle=export(out)
 v={"evidence_kind":"SOFTWARE_TEST_NOT_RESEARCH","mode":a.mode,"requests":len(received),
    "status":st,"audit":ar,"no_resampling":True,"feedback_bundle":str(bundle)}
 write(out/"runs/SOFTWARE_FIXTURE.json",v)
 print(json.dumps(v,indent=2))
 if not ar["mechanical_pass"]:raise SystemExit(2)
if __name__=="__main__":main()
