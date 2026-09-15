"""Software-only model surrogate; uses only the request payload, not private cases."""
import json,re,threading
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from contextlib import contextmanager

def decide(p):
 if p['messages'][-1]['content']=='Return {"ok":true} exactly.':return {'ok':True}
 q=json.loads(p['messages'][-1]['content']);task=q['task'];h=q['action_history']
 def tool(tool_name,**args):return {'action':'tool','name':tool_name,'arguments':args}
 def done():return {'action':'finish','summary':'Finished according to observed tool results.'}
 def last(name,ok=None):
  rows=[x for x in h if x['action']['name']==name and (ok is None or x['observation']['ok']==ok)]
  return rows[-1] if rows else None
 if 'Send exactly one message' in task:
  if last('send_message_with_phone_number',True):return done()
  if last('send_message_with_phone_number',False) and not last('set_cellular_service_status',True):return tool('set_cellular_service_status',on=True)
  lit=re.search(r'the phone number (\+\d+)',task);name=re.search(r'message to (.*?) at her current',task)
  if lit:phone=lit.group(1)
  else:
   rr=last('search_contacts',True)
   if not rr:return tool('search_contacts',name=name.group(1))
   phone=next(r for r in rr['observation']['value'] if r['name']==name.group(1))['phone_number']
  return tool('send_message_with_phone_number',phone_number=phone,content=re.search(r'exactly "(.*?)"',task).group(1))
 if 'current reminder' in task:
  if last('modify_reminder',True):return done()
  name=re.search(r'exactly "(.*?)"',task).group(1);r=last('search_reminder',True)
  if not r:return tool('search_reminder',content=name)
  rid=next(x for x in r['observation']['value'] if x['content']==name)['reminder_id']
  return tool('modify_reminder',reminder_id=rid,reminder_timestamp=float(re.search(r'timestamp (\d+)',task).group(1)))
 if last('set_wifi_status',True):return done()
 r=last('get_wifi_status',True)
 if not r:return tool('get_wifi_status')
 if r['observation']['value']:return done()
 r=last('get_low_battery_mode_status',True)
 if not r:return tool('get_low_battery_mode_status')
 if r['observation']['value'] and not last('set_low_battery_mode_status',True):return tool('set_low_battery_mode_status',on=False)
 return tool('set_wifi_status',on=True)

@contextmanager
def server(mode='ok'):
 state={'requests':[]}
 class Handler(BaseHTTPRequestHandler):
  def log_message(self,*a):pass
  def do_POST(self):
   p=json.loads(self.rfile.read(int(self.headers['Content-Length'])));state['requests'].append(p);n=len(state['requests'])
   obj=decide(p);content=json.dumps(obj)
   if mode=='invalid_json':content='not json'
   b={'id':'software-fixture-'+str(n),'model':'deepseek-flash','system_fingerprint':'software-only',
      'choices':[{'finish_reason':'length' if mode=='length' else 'stop','message':{'role':'assistant','content':content}}],
      'usage':{'prompt_tokens':10,'completion_tokens':5,'total_tokens':15,'completion_tokens_details':{'reasoning_tokens':1}}}
   raw=json.dumps(b).encode();self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
 http=ThreadingHTTPServer(('127.0.0.1',0),Handler);t=threading.Thread(target=http.serve_forever,daemon=True);t.start()
 try:yield 'http://127.0.0.1:'+str(http.server_port),state
 finally:http.shutdown();http.server_close();t.join()
