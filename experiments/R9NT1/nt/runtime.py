"""One fixed native research batch. No smoke, implicit restart, or hidden retries."""
from pathlib import Path
import os,sys,platform,time,zipfile,re
from .common import read,write,sha,digest,now,verify_source,locked,no_network
from .contract import ContractError

EXPECTED_CONFIG={'endpoint':'https://api.deepseek.com/v1/chat/completions','model':'deepseek-flash',
 'accepted_response_labels':['deepseek-flash','deepseek-v4-flash'],'max_tokens':16384,
 'thinking':{'type':'enabled'},'reasoning_effort':'high','tool_choice':'auto','stream':False,
 'max_attempts':360,'max_tools_per_response':4,'timeout_seconds':120,'min_interval_seconds':0.4,
 'max_response_bytes':8000000,'key_env':'LLM_API_KEY'}

def checked(root):
 root=Path(root);source=verify_source(root);cfg=read(root/'config.json');proto=read(root/'protocol.json')
 if cfg!=EXPECTED_CONFIG:raise ContractError('Frozen request profile changed')
 required={'task_id':'R9NT1_LIVE_NATIVE_TOOL_CONTINUATION_01','version':'r9nt-1.0.0','cases':16,
  'arms':['inherited','verify_confirm'],'primary_episodes':32,'repeat_episodes':4,
  'max_requests_per_episode':10,'max_tools_per_response':4,'max_tools_per_episode':40,
  'main_request_cap':360,'main_outer_tool_cap':1440,'smoke_request_cap':0}
 if any(proto.get(k)!=v for k,v in required.items()):raise ContractError('Frozen protocol changed')
 cases=read(root/'fixtures/cases.json');schedule=read(root/'fixtures/schedule.json')
 if len(cases)!=16 or len(schedule)!=36 or len({s['episode_id'] for s in schedule})!=36:raise ContractError('Frozen case/schedule shape')
 if sum(s['phase']=='primary' for s in schedule)!=32:raise ContractError('Wrong primary count')
 return {'source_manifest_sha256':source,'config':cfg,'protocol':proto,
  'binding':digest({'source':source,'config':cfg,'protocol':proto})}

def prepare(root):
 root=Path(root);b=checked(root)
 if sys.version_info[:2]!=(3,11):raise ContractError('Use Python 3.11.x with the fixed native dependencies')
 p=root/'PREPARED.json'
 if p.exists():
  old=read(p)
  if old['binding']!=b['binding']:raise ContractError('Preparation binding changed')
  return old
 if (root/'runs').exists():raise ContractError('Run exists without preparation; preserve and export')
 from legacy.native import NativeSession,FUNCTIONS
 import polars,numpy
 if polars.__version__!='0.20.31' or numpy.__version__!='1.26.4':raise ContractError('Wrong native dependency versions')
 tools=read(root/'fixtures/tools.json')
 if {t['function']['name'] for t in tools}!=set(FUNCTIONS):raise ContractError('Tool schema/dispatch mismatch')
 with no_network():
  for c in read(root/'fixtures/cases.json'):
   if NativeSession(c['snapshot']).world()!=c['world_before']:raise ContractError('Frozen snapshot mismatch')
 result={**b,'prepared_utc':now(),'environment':{'python':platform.python_version(),
  'system':platform.system(),'machine':platform.machine(),'numpy':numpy.__version__,'polars':polars.__version__},
  'new_model_calls':0,'new_smoke_required':False}
 write(p,result,once=True);return result

def run_study(root,confirm_calls,secret=None,exchange=None,test_endpoint=None):
 root=Path(root);b=checked(root)
 if confirm_calls!=360:raise ContractError('run requires --confirm-calls 360 (total maximum, not required usage)')
 prep=read(root/'PREPARED.json')
 if prep['binding']!=b['binding']:raise ContractError('Preparation binding mismatch')
 run=root/'runs/main';sp=run/'status.json'
 if sp.exists():
  prior=read(sp)
  if prior['status']=='completed':return prior
  raise ContractError('Paused/incomplete batch cannot restart. Audit/export, do not delete the lock or clone to resample.')
 if run.exists() and any(run.iterdir()):raise ContractError('Orphan records; do not re-run')
 if (root/'.run.lock').exists():raise ContractError('Run lock exists; do not delete')
 if secret is None:
  import getpass
  secret=os.environ.get('LLM_API_KEY') or getpass.getpass('LLM API key (hidden, not saved): ')
 if not secret:raise ContractError('No API key; no request sent')
 from .journal import Client
 from .engine import run_episode
 run.mkdir(parents=True,exist_ok=True);start=now();tic=time.perf_counter();completed=[]
 with locked(root):
  write(run/'manifest.json',{**b,'created_utc':start,'evidence_kind':
   'SOFTWARE_TEST_NOT_RESEARCH' if exchange or test_endpoint else 'REAL_ENDPOINT_NATIVE_CONTINUATION'},once=True)
  write(sp,{'status':'running','started_utc':start,'completed_episodes':[]})
  client=Client(b['config'],run,read(root/'fixtures/tools.json'),secret,exchange,test_endpoint)
  cases={c['id']:c for c in read(root/'fixtures/cases.json')}
  try:
   for spec in read(root/'fixtures/schedule.json'):
    result=run_episode(cases[spec['case_id']],spec,client,run)
    completed.append({**spec,'score':result['score'],'model_calls':result['model_calls'],
      'tool_calls':result['tool_calls'],'terminated':result['terminated'],'exposure':result['exposure']})
    write(sp,{'status':'running','started_utc':start,'completed_episodes':completed,
      'recorded_attempts':len(client.requests())})
   result={'status':'completed','completed_episodes':completed}
  except (Exception,KeyboardInterrupt) as exc:
   msg=str(exc) if isinstance(exc,ContractError) else 'Local runtime/interrupt error; preserve all evidence for review'
   if secret in msg:msg=msg.replace(secret,'[REDACTED]')
   result={'status':'paused','error_type':type(exc).__name__,'error':msg,'completed_episodes':completed}
  result.update(started_utc=start,ended_utc=now(),elapsed_seconds=time.perf_counter()-tic,
    recorded_attempts=len(client.requests()),automatic_next_batch_authorized=False)
  write(sp,result)
 return result

def export(root):
 root=Path(root)
 if (root/'.run.lock').exists():raise ContractError('Active or orphan lock; do not export changing files or delete lock')
 source=read(root/'SOURCE_MANIFEST.json')['files']
 candidates=[root/p for p in source]+[root/'SOURCE_MANIFEST.json']
 if (root/'PREPARED.json').exists():candidates.append(root/'PREPARED.json')
 if (root/'runs').exists():candidates += [p for p in (root/'runs').rglob('*') if p.is_file()]
 files={};patterns=[re.compile(rb'(?i)Bearer\s+[a-zA-Z0-9._\-]{16,}'),re.compile(rb'\bsk-[a-zA-Z0-9]{20,}\b')]
 for p in sorted(set(candidates)):
  if p.is_symlink() or not p.resolve().is_relative_to(root.resolve()):raise ContractError('Unsafe export path')
  raw=p.read_bytes()
  if any(rx.search(raw) for rx in patterns):raise ContractError('Possible credential in export; no ZIP created')
  files[p.relative_to(root).as_posix()]=raw
 manifest={k:{'bytes':len(v),'sha256':sha(v)} for k,v in files.items()}
 folder=root/'uploads';folder.mkdir(exist_ok=True)
 path=folder/('R9NT1_feedback_'+now().replace(':','').replace('-','').replace('+0000','Z')+'.zip')
 with zipfile.ZipFile(path,'x',compression=zipfile.ZIP_DEFLATED) as z:
  for name,raw in files.items():z.writestr(name,raw)
  z.writestr('BUNDLE_MANIFEST.json',__import__('json').dumps({'files':manifest},sort_keys=True,indent=2))
 return str(path)
