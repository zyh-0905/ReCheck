"""Read-only saved-response replay plus artifact/receipt integrity checks.
Re-executes real SQLite tools offline, NEVER the remote model. Not peer review.
"""
import copy,tempfile,csv
from pathlib import Path
from .contract import ContractError,canonical,strict_json,validate_response,usage_counts
from .common import read,write,sha,digest,no_network
from .runtime import checked
from .engine import run_episode
from .schema import TOOLS

def projection(r):
 r=copy.deepcopy(r)
 for e in r.get('events',[]):e.pop('elapsed_seconds',None)
 return r

class SavedClient:
 def __init__(self,config,lookup,identity):self.config=config;self.lookup=lookup;self.identity=identity;self.used=set()
 def complete(self,logical,payload,metadata,tools,used_ids):
  if logical not in self.lookup:raise ContractError('Replay reached an unrecorded request')
  req,res=self.lookup[logical];self.used.add(logical)
  if req['payload']!=payload or req['metadata']!=metadata:raise ContractError('Recorded request cannot be reconstructed')
  if res.get('status')!='received' or res.get('http_status')!=200:raise ContractError('Retained transport failure')
  if res.get('secret_redacted'):raise ContractError('Retained credential-echo failure')
  validated=validate_response(res.get('response'),tools,used_ids,self.identity)
  return {**res,'validated':validated}

def audit(root):
 root=Path(root);b=checked(root);run=root/'runs/main';status=read(run/'status.json') if (run/'status.json').exists() else {'status':'not_started'}
 if not run.exists():return {'mechanical_pass':True,'execution_complete':False,'status':'not_started','primary_episodes':0,'new_remote_model_calls':0}
 if read(root/'PREPARED.json')['binding']!=b['binding'] or read(run/'manifest.json')['binding']!=b['binding']:raise ContractError('Run binding mismatch')
 requests=sorted((run/'attempts').glob('*_request.json'));lookup={};response_ids=set();callrows=[];retained=[]
 identity=read(run/'endpoint_identity.json') if (run/'endpoint_identity.json').exists() else None
 if len(requests)>384:raise ContractError('Request budget exceeded')
 for n,p in enumerate(requests,1):
  req=read(p);prefix=f'{n:06d}';rp=run/'attempts'/(prefix+'_response.json');rawp=run/'attempts'/(prefix+'_response.raw');ip=run/'attempts'/(prefix+'_send_intent.json')
  if req['attempt']!=n or p.name!=prefix+'_request.json':raise ContractError('Non-contiguous attempt ledger')
  if req['payload_sha256']!=digest(req['payload']) or req['request_sha256']!=digest({'endpoint':b['config']['endpoint'],'payload':req['payload']}):raise ContractError('Request digest mismatch')
  if not rp.exists():raise ContractError('Orphan request: remote outcome unknown; manual partial review required')
  if not ip.exists() or read(ip)['attempt']!=n:raise ContractError('Missing send-intent record')
  res=read(rp);raw=rawp.read_bytes()
  if sha(raw)!=res['raw_stored_sha256']:raise ContractError('Response bytes changed')
  if not res.get('secret_redacted') and sha(raw)!=res['raw_original_sha256']:raise ContractError('Original raw digest changed')
  for k,v in req.items():
   if res.get(k)!=v:raise ContractError('Request/response ledger mismatch')
  try:parsed=strict_json(raw.decode())
  except (ValueError,UnicodeError):parsed=None
  if parsed!=res.get('response'):raise ContractError('Parsed response does not match raw bytes')
  body=res.get('response') or {};rid=body.get('id')
  if rid and rid in response_ids:raise ContractError('Duplicate response ID')
  if rid:response_ids.add(rid)
  if req['logical_id'] in lookup:raise ContractError('Repeated logical input was sampled twice')
  lookup[req['logical_id']]=(req,res)
  try:v=validate_response(body,TOOLS,expected_identity=identity);u=v['usage'];failure=None
  except ContractError as e:u={};failure=str(e);retained.append({'logical_id':req['logical_id'],'error':failure})
  callrows.append({'attempt':n,'logical_id':req['logical_id'],'latency_seconds':res['latency_seconds'],'response_error':failure,**u})
 cases={c['id']:c for c in read(root/'fixtures/cases.json')};schedule=read(root/'fixtures/schedule.json')
 client=SavedClient(b['config'],lookup,identity);rows=[];partial_events=0;recorded_prefix=[]
 with no_network(),tempfile.TemporaryDirectory(prefix='r10-replay-') as d:
  for spec in schedule:
   ep=run/'episodes'/(spec['episode_id']+'.json');pp=run/'episodes'/(spec['episode_id']+'.partial.json')
   if not ep.exists() and not pp.exists():continue
   if ep.exists():
    replay=run_episode(cases[spec['case_id']],spec,client,Path(d));saved=read(ep)
    if projection(replay)!=projection(saved):raise ContractError('Episode actions, receipts, states or score changed')
    rows.append({**spec,**{k:v for k,v in saved['score'].items() if k!='violations'},'model_calls':saved['model_calls'],'visible_tool_calls':saved['visible_tool_calls'],'completion_claim':saved['completion_claim'],'false_completion_claim':saved['false_completion_claim'],'terminated':saved['terminated']})
    recorded_prefix.append(spec['episode_id'])
   else:
    # Replay up to the same retained bad response, not beyond it.
    try:run_episode(cases[spec['case_id']],spec,client,Path(d))
    except ContractError:pass
    else:raise ContractError('Partial record unexpectedly replays to completion')
    made=Path(d)/'episodes'/pp.name
    if not made.exists() or projection(read(made))!=projection(read(pp)):raise ContractError('Partial prefix needs manual reconciliation')
    partial_events+=sum(e['kind']=='tool' for e in read(pp)['events'])
 if client.used!=set(lookup):raise ContractError('Unmatched or extra recorded request')
 expected_schedule=[s['episode_id'] for s in schedule]
 if recorded_prefix!=expected_schedule[:len(recorded_prefix)]:raise ContractError('Completed episodes are not the frozen schedule prefix')
 if [x['episode_id'] for x in status.get('completed_episodes',[])]!=recorded_prefix:raise ContractError('Status summary differs from recorded outcomes')
 for s,r in zip(status.get('completed_episodes',[]),rows):
  raw=read(run/'episodes'/(s['episode_id']+'.json'))
  if s['score']!=raw['score']:raise ContractError('Status score mismatch')
 complete=status['status']=='completed' and len(rows)==48
 if status['status']=='completed' and not complete:raise ContractError('False completed status')
 def table(name,data):
  if data:
   fields=list(dict.fromkeys(k for row in data for k in row))
   with (run/name).open('w',newline='',encoding='utf-8') as f:w=csv.DictWriter(f,fields);w.writeheader();w.writerows(data)
 table('calls.csv',callrows);table('episodes.csv',rows)
 summary=[]
 for arm in b['protocol']['arms']:
  group=[r for r in rows if r['arm']==arm]
  summary.append({'arm':arm,'planned':12,'completed':len(group),**{k:sum(int(r[k]) for r in group) for k in ('goal_final','final_state_clean','trace_safe_success','wrong_write','false_completion_claim','model_calls','tool_calls','conflicts')}})
 table('summary.csv',summary)
 result={'mechanical_pass':True,'execution_complete':complete,'status':status['status'],'primary_episodes':len(rows),'recorded_requests':len(requests),'reconstructed_requests':len(client.used),'database_tool_events':sum(r['tool_calls'] for r in rows),'partial_database_events':partial_events,'retained_response_failures':retained,'new_remote_model_calls':0,'cost_currency':'UNKNOWN','scientific_superiority_claim':False,'automatic_next_batch_authorized':False}
 write(run/'AUDIT.json',result);return result
