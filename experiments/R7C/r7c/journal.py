"""One attempt per logical call; no retries, fallback, or synthetic live responses."""
from __future__ import annotations
import json,time,urllib.request,urllib.error
from pathlib import Path
from urllib.parse import urlsplit
from .core import canonical,digest,read,write,write_once,utcnow,strict_json,TOTAL_CAP
class Paused(RuntimeError):pass
class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*args,**kwargs):return None

def validate_response(b,identity):
 try:
  if not isinstance(b,dict) or not isinstance(b.get('id'),str):raise ValueError('Missing response ID')
  if b.get('model')!='deepseek-flash':raise ValueError('Returned model label changed')
  now={'model':b.get('model'),'system_fingerprint':b.get('system_fingerprint')}
  if identity is not None and identity!=now:raise ValueError('Identity metadata changed')
  choices=b['choices']
  if len(choices)!=1 or choices[0].get('finish_reason')!='stop':raise ValueError('Non-stop completion or multiple choices')
  text=choices[0]['message']['content']
  if type(text) is not str:raise ValueError('Missing textual completion')
  x=strict_json(text);u=b['usage']
  for k in ('prompt_tokens','completion_tokens','total_tokens'):
   if type(u.get(k)) is not int or u[k]<0:raise ValueError('Missing/invalid token usage')
  if u['total_tokens']!=u['prompt_tokens']+u['completion_tokens']:raise ValueError('Inconsistent total usage')
  n=u.get('completion_tokens_details',{}).get('reasoning_tokens')
  if n is not None and (type(n) is not int or not 0<=n<=u['completion_tokens']):raise ValueError('Invalid reasoning token count')
  for k in ('prompt_cache_hit_tokens','prompt_cache_miss_tokens'):
   if k in u and (type(u[k]) is not int or not 0<=u[k]<=u['prompt_tokens']):raise ValueError('Invalid cache usage')
  if 'prompt_cache_hit_tokens' in u and 'prompt_cache_miss_tokens' in u and u['prompt_cache_hit_tokens']+u['prompt_cache_miss_tokens']!=u['prompt_tokens']:raise ValueError('Inconsistent cache totals')
  return x,now
 except (KeyError,TypeError,ValueError,IndexError) as e:raise Paused(str(e)) from None

def payload(messages,protocol):
 return {'model':protocol['model'],'messages':messages,'max_tokens':protocol['max_tokens'],
         'thinking':protocol['thinking'],'reasoning_effort':protocol['reasoning_effort'],
         'stream':False,'response_format':protocol['response_format']}

class Journal:
 def __init__(self,root,protocol,secret='',endpoint=None,fixture=False):
  self.root=Path(root);self.protocol=protocol;self.secret=secret;self.fixture=fixture
  self.endpoint=endpoint or protocol['base_url'];self.last_end=0
  if fixture:
   if urlsplit(self.endpoint).hostname not in ('localhost','127.0.0.1','::1'):raise ValueError('Fixture must be loopback')
  elif self.endpoint!=protocol['base_url']:raise ValueError('Frozen endpoint changed')
  self.opener=urllib.request.build_opener(NoRedirect())
  for folder in ('calls','attempts'):(self.root/folder).mkdir(parents=True,exist_ok=True)
 def redact(self,x):
  if isinstance(x,str):return x.replace(self.secret,'[REDACTED]') if self.secret else x
  if isinstance(x,list):return [self.redact(v) for v in x]
  if isinstance(x,dict):return {k:self.redact(v) for k,v in x.items()}
  return x
 def complete(self,logical_id,messages,metadata):
  p=payload(messages,self.protocol)
  if len(canonical(p).encode())>60000:raise Paused('Input exceeds frozen 60KB request bound; no request sent')
  if self.secret and self.secret in canonical(p):raise Paused('Credential in payload; no request sent')
  filename=self.root/'calls'/(digest(logical_id)+'.json')
  if filename.exists():raise Paused('Logical call already exists; no resampling allowed')
  starts=sorted((self.root/'attempts').glob('*_start.json'))
  if any(read(f)['logical_id']==logical_id for f in starts):raise Paused('Previously registered attempt cannot be retried')
  if len(starts)>=TOTAL_CAP:raise Paused('Global request-count cap reached')
  idx=len(starts)+1;ident_path=self.root/'endpoint_identity.json'
  old_ident=read(ident_path) if ident_path.exists() else None
  rec={'attempt':idx,'logical_id':logical_id,'metadata':metadata,'payload':p,'payload_sha256':digest(p),
       'endpoint':self.endpoint,'registered_utc':utcnow(),'evidence_kind':'SOFTWARE_TEST_NOT_RESEARCH' if self.fixture else 'USER_LIVE_ENDPOINT',
       'registration_proves_remote_receipt':False}
  write_once(self.root/'attempts'/f'{idx:06d}_start.json',rec)
  delay=self.protocol['min_interval_seconds']-(time.monotonic()-self.last_end)
  if delay>0 and not self.fixture:time.sleep(delay)
  h={'Content-Type':'application/json','Accept':'application/json'}
  if self.secret:h['Authorization']='Bearer '+self.secret
  req=urllib.request.Request(self.endpoint+'/chat/completions',data=canonical(p).encode(),headers=h,method='POST')
  write_once(self.root/'attempts'/f'{idx:06d}_send_intent.json',{'attempt':idx,'logical_id':logical_id,'utc':utcnow(),'proves_remote_receipt':False})
  tic=time.perf_counter();raw_text=None
  try:
   with self.opener.open(req,timeout=self.protocol['timeout_seconds']) as r:
    raw=r.read(8_000_001)
    if len(raw)>8_000_000:raise ValueError('Response too large')
    raw_text=raw.decode('utf-8');b=json.loads(raw_text)
   result={**rec,'transport':'response','response':b,'raw_response_text':raw_text,'elapsed_seconds':time.perf_counter()-tic,'ended_utc':utcnow(),'money_cost':'UNKNOWN'}
  except Exception as e:
   result={**rec,'transport':'error','error_type':type(e).__name__,'http_status':getattr(e,'code',None),
           'ended_utc':utcnow(),'elapsed_seconds':time.perf_counter()-tic,'billing_unknown':True}
   if raw_text is not None:result['raw_response_text']=self.redact(raw_text)
   if isinstance(e,urllib.error.HTTPError):
    try:result['http_error_body']=self.redact(e.read(4096).decode('utf-8','replace'))
    except Exception:result['http_error_body']='unavailable'
   write_once(self.root/'attempts'/f'{idx:06d}_result.json',result)
   raise Paused('Transport error; raw attempt retained; no automatic retry') from None
  finally:self.last_end=time.monotonic()
  result=self.redact(result)
  write_once(self.root/'attempts'/f'{idx:06d}_result.json',result);write_once(filename,result)
  x,identity=validate_response(result['response'],old_ident);write_once(ident_path,identity)
  print(f'[{idx}/{TOTAL_CAP}] {logical_id} | {result["elapsed_seconds"]:.2f}s',flush=True)
  return x,result
