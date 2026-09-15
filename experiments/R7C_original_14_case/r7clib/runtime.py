
"""Research lifecycle. Paid requests only in smoke/run after explicit caps.
Tests can supply a loopback profile through library calls; no CLI fixture switch exists.
"""
from pathlib import Path
import json,platform,time,os
from contextlib import contextmanager
from pilot.common import read_json,write_json,digest,utcnow,redact
from .artifacts import verify_distribution,source_hashes,export_bundle
from .transport import Client,validate_config_profile
from .prompts import episode_schedule,strict_object
from .experiment import run_episode
from .audit import audit
def prepare(root,fixture_config=None):
 root=Path(root);source=verify_distribution(root)
 if (root/'PREPARED.json').exists():
  old=read_json(root/'PREPARED.json')
  if old['source']!=source_hashes(root):raise ValueError('Source changed after prepare')
  return old
 if any((root/'runs').rglob('*_start.json')) if (root/'runs').exists() else False:
  raise ValueError('Cannot prepare after calls')
 cfg=fixture_config or read_json(root/'config.example.json');validate_config_profile(cfg)
 import numpy,polars
 if platform.python_version_tuple()[:2]!=('3','11'):raise ValueError('Use Python 3.11.x in a new environment')
 if numpy.__version__!='1.26.4' or polars.__version__!='0.20.31':raise ValueError('Pinned native dependencies required')
 from .native import NativeSession
 cs=read_json(root/'fixtures/cases.json')
 for c in cs:
  if NativeSession(c['snapshot']).world()!=c['world_before']:raise ValueError('Frozen native snapshot mismatch')
 contract={'config':cfg,'protocol':read_json(root/'protocol.json'),'source':source_hashes(root)}
 p={**contract,'fingerprint':digest(contract),'created_utc':utcnow(),
    'environment':{'python':platform.python_version(),'system':platform.system(),'machine':platform.machine(),
        'numpy':numpy.__version__,'polars':polars.__version__},
    'evidence_label':'SOFTWARE_TEST_NOT_RESEARCH' if cfg['backend_kind']=='test_fixture' else 'REAL_MODEL_TASK_DIAGNOSTIC'}
 write_json(root/'PREPARED.json',p);return p
@contextmanager
def locked(root):
 path=Path(root)/'.run.lock'
 fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
 os.write(fd,json.dumps({'pid':os.getpid(),'created_utc':utcnow()}).encode());os.close(fd)
 try:yield
 finally:path.unlink(missing_ok=True)
def prepared_checked(root):
 root=Path(root);verify_distribution(root)
 p=read_json(root/'PREPARED.json')
 c={'config':p['config'],'protocol':read_json(root/'protocol.json'),'source':source_hashes(root)}
 if p['fingerprint']!=digest(c):raise ValueError('Prepared binding changed')
 validate_config_profile(p['config']);return p
def status(root,name):
 p=Path(root)/'runs'/name/'status.json'
 return read_json(p) if p.exists() else {'status':'absent'}
def can_start(root,name):
 st=status(root,name)
 if st['status'] in ('paused','running'):raise ValueError('Existing partial run must be reviewed; no automatic resume')
 if st['status']=='completed':return False
 d=Path(root)/'runs'/name
 if any((d/'attempts').glob('*_start.json')) or any((d/'calls').glob('*.json')) or any((d/'episodes').glob('*.json')):
  raise ValueError('Orphaned existing evidence without status; export for review, do not resume')
 return True
def secret_for(cfg):
 value=os.environ.get(cfg['key_env'])
 if not value:
  import getpass
  value=getpass.getpass('LLM API key (hidden, current process only): ')
 if not value:raise ValueError('No key supplied; no call sent')
 return value
def _manifest(root,name,prep):
 d=Path(root)/'runs'/name;d.mkdir(parents=True,exist_ok=True)
 write_json(d/'manifest.json',{'prepared_fingerprint':prep['fingerprint'],'config':prep['config'],
  'source':prep['source'],'protocol':prep['protocol'],'evidence_label':prep['evidence_label'],
  'created_utc':utcnow()})
 return d
def smoke(root,confirm_calls,secret=None):
 if confirm_calls!=1:raise ValueError('smoke requires --confirm-calls 1')
 root=Path(root);p=prepared_checked(root)
 if not can_start(root,'R7C_smoke'):return status(root,'R7C_smoke')
 with locked(root):
  d=_manifest(root,'R7C_smoke',p);key=secret if secret is not None else secret_for(p['config'])
  write_json(d/'status.json',{'status':'running','started_utc':utcnow()})
  try:
   c=Client(p['config'],d,key,cap=1)
   r=c.complete('smoke',[{'role':'system','content':'Return exactly one JSON object: {"done":"ready"}.'},
      {'role':'user','content':'Check the JSON-only interface.'}],meta={'phase':'smoke'})
   obj=strict_object(r['text'])
   if obj!={'done':'ready'}:raise ValueError('Smoke must return the requested JSON object')
   write_json(d/'smoke_result.json',{'json_ok':True,'shape_ok':True,'request_sha256':r['request_sha256']})
   write_json(d/'status.json',{'status':'completed','ended_utc':utcnow()})
  except Exception as e:
   write_json(d/'status.json',{'status':'paused','error':redact(type(e).__name__+': '+str(e),key),'ended_utc':utcnow()})
  return status(root,'R7C_smoke')
def run(root,confirm_calls,secret=None):
 if confirm_calls!=384:raise ValueError('run requires --confirm-calls 384 (upper bound, not target)')
 root=Path(root);p=prepared_checked(root)
 if status(root,'R7C_smoke')['status']!='completed':raise ValueError('Current-kit smoke must complete first')
 sm=root/'runs/R7C_smoke'
 if read_json(sm/'manifest.json')['prepared_fingerprint']!=p['fingerprint']:raise ValueError('Smoke binding changed')
 if not read_json(sm/'smoke_result.json')['json_ok']:raise ValueError('Smoke failed')
 if not can_start(root,'R7C_main'):return status(root,'R7C_main')
 with locked(root):
  d=_manifest(root,'R7C_main',p);key=secret if secret is not None else secret_for(p['config'])
  identity=read_json(sm/'endpoint_identity.json');write_json(d/'endpoint_identity.json',identity)
  start=utcnow();tic=time.perf_counter()
  write_json(d/'status.json',{'status':'running','started_utc':start})
  client=Client(p['config'],d,key,cap=384)
  cases={c['id']:c for c in read_json(root/'fixtures/cases.json')}
  try:
   for spec in episode_schedule():
    r=run_episode(cases[spec['case_id']],spec,client,d)
    print(f"Episode completed: {spec['episode_id']}; calls={r['model_calls']}",flush=True)
   write_json(d/'status.json',{'status':'completed','started_utc':start,'ended_utc':utcnow(),
      'wall_seconds':time.perf_counter()-tic,'registered_requests':len(client.starts())})
  except Exception as e:
   write_json(d/'status.json',{'status':'paused','started_utc':start,'ended_utc':utcnow(),
      'wall_seconds':time.perf_counter()-tic,'error':redact(type(e).__name__+': '+str(e),key),
      'registered_requests':len(client.starts())})
  return status(root,'R7C_main')
