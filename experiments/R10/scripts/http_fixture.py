"""Full native HTTP qualification against loopback ONLY. Never model evidence."""
import sys,json,threading,http.server,tempfile,shutil
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from core.runtime import prepare,run_study,export
from core.audit import audit
from core.common import read,write
from scripts.fixture_model import build_exchange

def main(mode,out):
 out=Path(out)
 if out.exists():raise ValueError('Do not overwrite evidence')
 out.mkdir(parents=True)
 original=Path(__file__).resolve().parents[1]
 root=out/'kit';shutil.copytree(original,root,ignore=shutil.ignore_patterns('runs','uploads','.venv','__pycache__','.git','PREPARED.json'))
 exchange,count=build_exchange(mode)
 class Handler(http.server.BaseHTTPRequestHandler):
  def log_message(self,*a):pass
  def do_POST(self):
   raw=self.rfile.read(int(self.headers['Content-Length']));body=json.loads(raw)
   assert body['model']=='deepseek-flash' and 'tools' in body and 'response_format' not in body
   status,data=exchange(body);self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
 server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
 try:
  prepare(root)
  with patch('core.journal.time.sleep',lambda *_:None):
   result=run_study(root,384,secret='fixture-not-a-real-key',test_endpoint=f'http://127.0.0.1:{server.server_port}/v1/chat/completions')
  a=audit(root);before=count[0]
  if result['status']=='completed':run_study(root,384,secret='fixture-not-a-real-key',test_endpoint=f'http://127.0.0.1:{server.server_port}')
  else:
   from core.contract import ContractError
   try:run_study(root,384,secret='fixture-not-a-real-key',test_endpoint=f'http://127.0.0.1:{server.server_port}')
   except ContractError:pass
   else:raise AssertionError('Paused run restarted')
  assert count[0]==before
  write(out/'verification.json',{'kind':'SOFTWARE_TEST_NOT_RESEARCH','mode':mode,'http_requests':count[0],'pacing_skipped_only_in_fixture':True,'status':result['status'],'audit':a,'no_resampling':True,'export':export(root)})
  print(json.dumps(read(out/'verification.json'),indent=2))
 finally:server.shutdown();server.server_close();thread.join(timeout=5)
if __name__=='__main__':main(sys.argv[1],sys.argv[2])
