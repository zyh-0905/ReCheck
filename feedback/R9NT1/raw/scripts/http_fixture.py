#!/usr/bin/env python3
"""SOFTWARE FIXTURE ONLY: actual HTTP on loopback, never remote model calls."""
from pathlib import Path
import sys,json,threading,shutil,argparse,tempfile,hashlib
from http.server import HTTPServer,BaseHTTPRequestHandler
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/toolsandbox')]
from nt.common import read,write,sha,no_network
from nt.runtime import prepare,run_study,export
from nt.audit import audit
from nt.contract import canonical,validate_history
from legacy.rules import rule_action,parse

def history(messages):
 public=json.loads(messages[1]['content']);pending={};out=[]
 for m in messages[2:]:
  if m['role']=='assistant':
   for c in m.get('tool_calls') or []:pending[c['id']]=c['function']
  elif m['role']=='tool':
   c=pending[m['tool_call_id']]
   out.append({'tool':c['name'],'arguments':json.loads(c['arguments']),'response':json.loads(m['content'])})
 return public,out

def fixture_response(payload,n,mode):
 validate_history(payload['messages'])
 assert 'response_format' not in payload and payload['tool_choice']=='auto' and payload['model']=='deepseek-flash'
 assert payload['thinking']=={'type':'enabled'} and payload['max_tokens']==16384
 assert payload['tools']
 public,hist=history(payload['messages']);cmds=None;text=None
 if mode=='cap':cmds=[{'tool':'get_wifi_status','arguments':{}}]*4
 elif mode=='bad_batch' or (mode=='late_bad_batch' and n==2):
  cmds=[{'tool':'get_wifi_status','arguments':{}},{'tool':'run_shell','arguments':{}}]
 elif mode=='prose':text='I have executed all tools successfully. (Software fixture; no tool calls.)'
 else:
  action=rule_action(public,hist,'post_confirm')
  if 'done' in action:text=action['done']
  else:cmds=[action]
  if mode=='batch' and not hist:
   target=parse(public);old=public['historical_evidence']['response']['value']
   if target['kind']=='person':cmds=[{'tool':'search_contacts','arguments':{'name':target['name']}},
     {'tool':'send_message_with_phone_number','arguments':{'phone_number':old[0]['phone_number'],'content':target['content']}}]
   elif target['kind']=='reminder':cmds=[{'tool':'search_reminder','arguments':{'content':target['title']}},
     {'tool':'modify_reminder','arguments':{'reminder_id':old[0]['reminder_id'],'reminder_timestamp':target['timestamp']}}]
 calls=None if cmds is None else [{'id':f'fixture_{n}_{i}','type':'function','function':{'name':c['tool'],'arguments':canonical(c['arguments'])}} for i,c in enumerate(cmds)]
 return {'id':f'software_response_{n}','model':'deepseek-flash','system_fingerprint':'local_fixture_metadata',
  'choices':[{'index':0,'finish_reason':'tool_calls' if calls else 'stop',
  'message':{'role':'assistant','content':text,'tool_calls':calls,'reasoning_content':f'Software fixture reasoning {n}; not LLM evidence.'}}],
  'usage':{'prompt_tokens':100,'completion_tokens':30,'total_tokens':130,
   'completion_tokens_details':{'reasoning_tokens':12},'prompt_cache_hit_tokens':0,'prompt_cache_miss_tokens':100}}

def run_fixture(destination,mode,*,reuse=False):
 destination=Path(destination)
 if not reuse:
  shutil.copytree(ROOT,destination,ignore=shutil.ignore_patterns('runs','uploads','__pycache__','.venv','.git','PREPARED.json','.run.lock'))
 state={'requests':0,'mode':mode}
 class Handler(BaseHTTPRequestHandler):
  def do_POST(self):
   n=int(self.headers['Content-Length']);body=self.rfile.read(n);payload=json.loads(body);state['requests']+=1
   response=fixture_response(payload,state['requests'],mode);raw=json.dumps(response).encode()
   self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
  def log_message(self,*args):pass
 server=HTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
 try:
  prepare(destination)
  from unittest.mock import patch
  with patch('nt.journal.time.sleep',lambda seconds:None):
   result=run_study(destination,360,'local-fixture-key-not-real',test_endpoint=f'http://127.0.0.1:{server.server_port}/v1/chat/completions')
 finally:server.shutdown();thread.join();server.server_close()
 # HTTP phase and replay/export phase are separate to preserve completed calls if a shell times out.
 write(destination/'runs/FIXTURE_EXECUTION.json',{'evidence_kind':'SOFTWARE_TEST_NOT_RESEARCH','mode':mode,'http_requests':state['requests'],'loopback_request_pacing_skipped':True,'status':result['status']})
 return result

def finish_fixture(destination):
 destination=Path(destination);result=audit(destination)
 if not result['mechanical_pass']:raise AssertionError(result)
 before={str(p.relative_to(destination)):sha(p.read_bytes()) for p in (destination/'runs/main').rglob('*') if p.is_file()}
 try:run_study(destination,360)
 except Exception:
  if result['status']=='completed':raise
 after={str(p.relative_to(destination)):sha(p.read_bytes()) for p in (destination/'runs/main').rglob('*') if p.is_file()}
 assert before==after
 out=export(destination)
 check={**read(destination/'runs/FIXTURE_EXECUTION.json'),'audit':result,'completed_or_paused_no_resampling':True,'feedback':out}
 write(destination/'runs/FIXTURE_VERIFICATION.json',check);return check

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('destination');ap.add_argument('--mode',choices=['rule','cap','batch','bad_batch','late_bad_batch','prose'],default='rule');ap.add_argument('--stage',choices=['execute','finish'],default='execute');args=ap.parse_args()
 print(json.dumps(run_fixture(args.destination,args.mode) if args.stage=='execute' else finish_fixture(args.destination),indent=2))
