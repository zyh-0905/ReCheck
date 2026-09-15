#!/usr/bin/env python3
"""R7C public entry point. Only smoke/run send paid model requests."""
import argparse,getpass,json,os,sys,time,shutil,platform
from pathlib import Path
os.environ.setdefault('POLARS_MAX_THREADS','1');os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
from r7c.core import ROOT,read,write,write_once,file_sha,digest,verify_sources,utcnow

def runtime_check():
 if sys.version_info[:2]!=(3,11):raise ValueError('Use Python 3.11.x for these pinned native dependencies; do not reuse R5/R6 environment')
 from importlib.metadata import version
 required={}
 for ln in (ROOT/'requirements.txt').read_text().splitlines():
  if '==' in ln:
   n,v=ln.split('==');required[n]=v
 for n,v in required.items():
  if version(n)!=v:raise ValueError('Dependency mismatch: '+n+' expected '+v)
 return {n:version(n) for n in required}

def prepare():
 from r7c.native import Session
 versions=runtime_check();src=verify_sources();run=ROOT/'runs/R7C'
 if (run/'attempts').exists() and list((run/'attempts').glob('*_start.json')):raise ValueError('Do not re-prepare after model attempts')
 cases=read(ROOT/'fixtures/cases.json')
 if len(cases)!=24:raise ValueError('Case count mismatch')
 # Compatibility checks only; the substantive scripted experiments were already run by the research side.
 s=Session(cases[0]);r=s.call('get_cellular_service_status',{})
 if not r['ok'] or r['value'] is not True:raise ValueError('Native read compatibility check failed')
 record={'source_manifest_sha256':src['manifest_sha256'],'cases_sha256':file_sha(ROOT/'fixtures/cases.json'),
         'protocol_sha256':file_sha(ROOT/'configs/protocol.json'),'versions':versions,'python':platform.python_version(),
         'platform':platform.platform(),'scope':'ENVIRONMENT_COMPATIBILITY_NOT_NEW_RESEARCH_SAMPLE'}
 write_once(ROOT/'PREPARED.json',record);print('PREPARED. No model requests; fixed offline cases and tools verified.')
 return record

def bound_run():
 runtime_check();src=verify_sources();prep=read(ROOT/'PREPARED.json')
 if src['manifest_sha256']!=prep['source_manifest_sha256'] or prep['cases_sha256']!=file_sha(ROOT/'fixtures/cases.json') or prep['protocol_sha256']!=file_sha(ROOT/'configs/protocol.json'):raise ValueError('Prepared bindings changed')
 run=ROOT/'runs/R7C';run.mkdir(parents=True,exist_ok=True)
 if not (run/'manifest.json').exists():
  write_once(run/'manifest.json',{'prepared':prep,'evidence_kind':'USER_LIVE_ENDPOINT','created_utc':utcnow()})
  for rel in read(ROOT/'SOURCE_MANIFEST.json')['files']:
   dest=run/'code_snapshot'/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/rel,dest)
  write_once(run/'status.json',{'state':'new'})
 elif read(run/'manifest.json')['prepared']!=prep:raise ValueError('Run binding differs')
 return run

def paid(which,confirmation):
 from r7c.journal import Journal,Paused
 from r7c.actor import SMOKE_MESSAGES
 from r7c.experiment import schedule,episode
 expected=1 if which=='smoke' else 432
 if confirmation!=expected:raise ValueError('Explicit --confirm-calls '+str(expected)+' required')
 run=bound_run();status=read(run/'status.json')['state']
 if which=='smoke' and status in ('ready','completed'):
  print('Smoke already completed; no new requests.');return
 if which=='run' and status=='completed':print('Run already completed; no resampling.');return
 if (which=='smoke' and status!='new') or (which=='run' and status!='ready'):raise ValueError('Run state does not allow this action. Audit/export; do not unlock or retry.')
 if which=='run':
  from r7c.journal import validate_response,payload
  from r7c.actor import SMOKE_MESSAGES
  proto=read(ROOT/'configs/protocol.json');sr=read(run/'calls'/(digest('smoke')+'.json'))
  obj,identity=validate_response(sr['response'],None)
  if obj!={'ok':True} or sr['payload']!=payload(SMOKE_MESSAGES,proto) or identity!=read(run/'endpoint_identity.json') or len(list((run/'attempts').glob('*_start.json')))!=1:
   raise ValueError('Smoke evidence or attempt state is not eligible for main run')
 lock=run/'.write.lock'
 fd=os.open(str(lock),os.O_CREAT|os.O_EXCL|os.O_WRONLY);os.write(fd,str(os.getpid()).encode());os.close(fd)
 start=utcnow();tic=time.perf_counter()
 try:
  secret=os.environ.get('LLM_API_KEY') or getpass.getpass('API key (hidden; not saved): ')
  if not secret or any(ch in secret for ch in '\r\n'):raise ValueError('Missing or invalid local API key')
  protocol=read(ROOT/'configs/protocol.json');client=Journal(run,protocol,secret)
  write(run/'status.json',{'state':'running','phase':which,'started_utc':start})
  if which=='smoke':
   obj,_=client.complete('smoke',SMOKE_MESSAGES,{'phase':'smoke'})
   if obj!={'ok':True}:raise Paused('Smoke object mismatch')
   write(run/'smoke_result.json',{'json_ok':True});state='ready'
  else:
   cases=read(ROOT/'fixtures/cases.json');lookup={c['id']:c for c in cases}
   for cid,method in schedule(cases,protocol['schedule_seed']):
    episode(lookup[cid],method,client,run/'episodes'/f'{cid}__{method}.json')
   state='completed'
  write(run/'status.json',{'state':state,'phase':which,'started_utc':start,'ended_utc':utcnow(),'phase_wall_seconds':time.perf_counter()-tic})
 except BaseException as e:
  write(run/'status.json',{'state':'paused','phase':which,'started_utc':start,'ended_utc':utcnow(),'exception_type':type(e).__name__,
                          'instruction':'Preserve evidence; audit/export. No retries or parameter changes.'})
  raise
 finally:
  if lock.exists():lock.unlink()

def main():
 p=argparse.ArgumentParser();p.add_argument('command',choices=['prepare','smoke','run','audit','export','verify']);p.add_argument('path',nargs='?');p.add_argument('--confirm-calls',type=int)
 a=p.parse_args()
 try:
  if a.command=='prepare':prepare()
  elif a.command in ('smoke','run'):paid(a.command,a.confirm_calls)
  elif a.command=='audit':
   from r7c.review import audit
   report=audit();print(json.dumps(report,ensure_ascii=False,indent=2));return 0 if report['mechanical_pass'] else 2
  elif a.command=='export':
   from r7c.storage import export
   print(export())
  else:
   from r7c.storage import verify_bundle
   if not a.path:raise ValueError('Feedback ZIP path required')
   print(verify_bundle(a.path))
  return 0
 except (Exception,KeyboardInterrupt) as e:
  # Do not print secrets, user environment or arbitrary HTTP error bodies.
  print('STOP: '+type(e).__name__+'. Preserve directory; audit/export for review.',file=sys.stderr)
  if isinstance(e,(ValueError,FileNotFoundError,ModuleNotFoundError)):print(str(e),file=sys.stderr)
  return 2
if __name__=='__main__':raise SystemExit(main())
