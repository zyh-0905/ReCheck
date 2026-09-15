"""Read-only response replay into temporary state; no new model responses."""
from pathlib import Path
import copy,csv,tempfile,math
from .common import read,write,digest,sha,no_network
from .contract import canonical,strict_json,validate_response,usage_counts,ContractError

def equal(a,b,label):
 if canonical(a)!=canonical(b):raise ContractError('Mismatch: '+label)
def projection(v):
 if isinstance(v,dict):return {k:projection(x) for k,x in v.items() if k!='elapsed_seconds'}
 if isinstance(v,list):return [projection(x) for x in v]
 return v

def csv_write(path,rows):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
 fields=list(dict.fromkeys(k for r in rows for k in r))
 with path.open('w',newline='',encoding='utf-8') as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)

def response_ledger(run,binding,tools,schedule):
 attempts=run/'attempts';reqfiles=sorted(attempts.glob('*_request.json'))
 if len(reqfiles)>360:raise ContractError('Global request cap exceeded')
 specmap={s['episode_id']:s for s in schedule};requests={};responses={};rawfiles=set();ids=set();identity=None;failures=[];usage=[]
 for i,f in enumerate(reqfiles,1):
  if f.name!=f'{i:06d}_request.json':raise ContractError('Request attempt numbering is not consecutive')
  st=read(f);equal(st['attempt'],i,'attempt index');logical=st['logical_id'];meta=st['metadata']
  if logical in requests:raise ContractError('Duplicate logical request')
  sp=specmap.get(meta.get('episode_id'))
  if sp is None or type(meta.get('turn')) is not int or not 0<=meta['turn']<10:raise ContractError('Unknown episode or turn')
  equal(meta,{'episode_id':sp['episode_id'],'phase':sp['phase'],'case_id':sp['case_id'],'arm':sp['arm'],'turn':meta['turn']},'metadata')
  equal(logical,sp['episode_id']+f'/turn_{meta["turn"]:02d}','logical binding')
  equal(st['payload_sha256'],digest(st['payload']),'payload hash')
  equal(st['request_sha256'],digest({'endpoint':binding['config']['endpoint'],'payload':st['payload']}),'endpoint hash')
  requests[logical]=st;rawfiles.add(f.name)
  send=attempts/f'{i:06d}_send_intent.json';rp=attempts/f'{i:06d}_response.json';rawp=rp.with_suffix('.raw')
  if send.exists():equal(read(send)['attempt'],i,'send intent');rawfiles.add(send.name)
  if not rp.exists():
   if rawp.exists():raise ContractError('Raw response without corresponding record')
   failures.append({'logical_id':logical,'reason':'No response record; completion/billing unknown'});continue
  if not send.exists() or not rawp.exists():raise ContractError('Incomplete response journal')
  rawfiles.update([rp.name,rawp.name]);rec=read(rp);responses[logical]=rec
  for k in st:equal(st[k],rec[k],'request/response '+k)
  raw=rawp.read_bytes();equal(sha(raw),rec['raw_stored_sha256'],'response raw hash')
  if not rec['secret_redacted']:equal(sha(raw),rec['raw_original_sha256'],'unredacted response bytes')
  if rec['response'] is not None:equal(strict_json(raw.decode()),rec['response'],'parsed raw response')
  elapsed=rec.get('latency_seconds')
  if type(elapsed) not in (int,float) or not math.isfinite(elapsed) or elapsed<0:raise ContractError('Invalid latency')
  if type(rec.get('response')) is dict and rec['response'].get('usage') is not None:
   try:u=usage_counts(rec['response']['usage'])
   except ContractError:pass
   else:usage.append({'logical_id':logical,'phase':sp['phase'],'arm':sp['arm'],**u,'latency_seconds':elapsed,'monetary_cost':'UNKNOWN'})
  try:
   if rec['status']!='received' or rec['http_status']!=200 or rec['secret_redacted']:raise ContractError('Transport/secret-redaction failure retained')
   v=validate_response(rec['response'],tools,expected_identity=identity)
   rid=rec['response']['id']
   if rid in ids:raise ContractError('Duplicate response ID')
   ids.add(rid);identity=v['identity']
  except ContractError as exc:failures.append({'logical_id':logical,'reason':str(exc)})
 existing={p.name for p in attempts.iterdir() if p.is_file()}
 equal(sorted(existing),sorted(rawfiles),'unmatched journal file')
 idfile=run/'endpoint_identity.json'
 if identity is not None:equal(identity,read(idfile),'recorded response identity')
 elif idfile.exists():raise ContractError('Identity file without a valid response')
 return requests,responses,identity,failures,usage

class ReplayClient:
 def __init__(self,binding,tools,requests,responses,identity):
  self.config=binding['config'];self.tools=tools;self.req=requests;self.res=responses;self.identity=identity;self.consumed=[]
 def complete(self,logical,payload,metadata,tools,used_ids):
  if logical not in self.req:raise ContractError('No recorded next request; stop replay')
  st=self.req[logical];equal(st['payload'],payload,'rebuilt request '+logical);equal(st['metadata'],metadata,'rebuilt metadata')
  if logical in self.consumed:raise ContractError('Replay attempted duplicate request')
  self.consumed.append(logical)
  if logical not in self.res:raise ContractError('Registered request without response; do not regenerate')
  r=self.res[logical]
  if r['status']!='received' or r['http_status']!=200 or r['secret_redacted']:raise ContractError('Retained transport/secret error')
  v=validate_response(r['response'],tools,used_ids,self.identity)
  return {**r,'validated':v}

def exposure_row(result):
 events=result['events'];links={}
 for t in result['turns']:
  for c in t['executions']:
   for i in range(c['event_start'],c['event_end']):links[i]={'model_turn':t['turn'],'batch_index':c['batch_index'],'tool_call_id':c['tool_call_id']}
 env=[i for i,e in enumerate(events) if e['scope']=='environment']
 writes=[i for i,e in enumerate(events) if e['scope']=='agent' and e['tool'] in ('send_message_with_phone_number','modify_reminder','set_wifi_status')]
 after=[i for i in writes if env and i>env[-1]]
 same=None
 if env and after and env[0] in links and after[0] in links:same=links[env[0]]['model_turn']==links[after[0]]['model_turn']
 return {'episode_id':result['episode_id'],'phase':result['phase'],'case_id':result['case_id'],'arm':result['arm'],
  **result['exposure'],'environment_operations':len(env),'event_indices':canonical(env),
  'first_primary_write_index':writes[0] if writes else None,'write_after_event_same_model_response':same}

def _audit(root):
 from .runtime import checked
 from .engine import run_episode
 root=Path(root);b=checked(root);run=root/'runs/main';sp=run/'status.json'
 prep=read(root/'PREPARED.json');equal(prep['binding'],b['binding'],'preparation')
 if not sp.exists():
  if run.exists() and any(run.iterdir()):raise ContractError('Orphan run without status')
  return {'mechanical_pass':True,'execution_complete':False,'status':'absent','recorded_requests':0,'new_remote_model_calls':0}
 status=read(sp);equal(read(run/'manifest.json')['binding'],b['binding'],'run source binding')
 tools=read(root/'fixtures/tools.json');schedule=read(root/'fixtures/schedule.json');cases={c['id']:c for c in read(root/'fixtures/cases.json')}
 req,res,identity,failures,usage=response_ledger(run,b,tools,schedule)
 replay=ReplayClient(b,tools,req,res,identity);results=[];summaries=[];seen_results=set();partial_seen=False;partial_prefixes=[]
 with tempfile.TemporaryDirectory(prefix='r9nt-replay-') as td:
  temp=Path(td)
  for spec in schedule:
   eid=spec['episode_id'];path=run/'episodes'/(eid+'.json');part=run/'partial'/eid
   if not path.exists() and not part.exists():continue
   if partial_seen:raise ContractError('A later episode exists after an incomplete episode')
   complete=path.exists();saved=read(path) if complete else read(part/'boundary.json')
   if len(saved['turns'])>10:raise ContractError('Per-episode request limit')
   if complete:
    for k,v in spec.items():equal(saved[k],v,'episode schedule binding')
    # Reject mismatched sidecars before expensive native replay; same acceptance rule.
    for j,t in enumerate(saved['turns']):equal(t,read(part/f'turn_{j:02d}.json'),'turn sidecar')
    r=run_episode(cases[spec['case_id']],spec,replay,temp,replay_events=saved['events'])
    equal(projection(r),projection(saved),'replayed episode '+eid)
    expected_progress=temp/'partial'/eid/'tool_progress.json'
    saved_progress=part/'tool_progress.json'
    equal(expected_progress.exists(),saved_progress.exists(),'tool-progress presence')
    if expected_progress.exists():equal(projection(read(expected_progress)),projection(read(saved_progress)),'last tool-progress checkpoint')
    for j,t in enumerate(saved['turns']):equal(t,read(part/f'turn_{j:02d}.json'),'turn sidecar')
    results.append(r);seen_results.add(path.name)
    summaries.append({**spec,'score':r['score'],'model_calls':r['model_calls'],'tool_calls':r['tool_calls'],'terminated':r['terminated'],'exposure':r['exposure']})
   else:
    partial_seen=True;exc=None
    try:run_episode(cases[spec['case_id']],spec,replay,temp,replay_events=saved['events'])
    except Exception as e:exc=e
    if exc is None:raise ContractError('Partial episode replays to a full result; inconsistent artifact boundary')
    rebuilt=read(temp/'partial'/eid/'boundary.json')
    equal(projection(rebuilt),projection(saved),'partial replay boundary')
    progress=part/'tool_progress.json'
    if progress.exists():
     p=read(progress)
     if len(p['events'])>len(saved['events']):raise ContractError('Interrupted in-flight tool batch needs manual review; additional progress preserved')
    expected_progress=temp/'partial'/eid/'tool_progress.json'
    equal(expected_progress.exists(),progress.exists(),'partial tool-progress presence')
    if progress.exists():equal(projection(read(expected_progress)),projection(read(progress)),'partial tool-progress checkpoint')
    for j,t in enumerate(saved['turns']):equal(t,read(part/f'turn_{j:02d}.json'),'partial turn sidecar')
    partial_prefixes.append({**spec,'completed_model_turns':len(saved['turns']),
      'native_tool_events':sum(e['scope']=='agent' for e in saved['events']),
      'environment_operations':sum(e['scope']=='environment' for e in saved['events']),
      'exposure':saved['exposure'],'not_a_completed_outcome':True})
 equal(replay.consumed,list(req),'chronological request coverage')
 existing={p.name for p in (run/'episodes').glob('*.json')};equal(sorted(existing),sorted(seen_results),'unknown results')
 known={s['episode_id'] for s in schedule};existing_part={p.name for p in (run/'partial').iterdir()} if (run/'partial').exists() else set()
 if not existing_part<=known:raise ContractError('Unknown partial episode')
 equal(status.get('completed_episodes'),summaries,'status summaries')
 equal(status.get('recorded_attempts'),len(req),'attempt total')
 if status['status']=='completed':
  if len(results)!=36 or partial_seen or failures:raise ContractError('False completed status')
  if [r['episode_id'] for r in results]!=[s['episode_id'] for s in schedule]:raise ContractError('Incomplete ordered schedule')
 if sum(r['tool_calls'] for r in results)+sum(p['native_tool_events'] for p in partial_prefixes)>1440:raise ContractError('Global outer-tool cap')
 report=root/'runs/review';episode_rows=[]
 for r in results:
  c=cases[r['case_id']]
  episode_rows.append({k:r[k] for k in ('episode_id','phase','case_id','arm','model_calls','tool_calls','terminated','stop_reason')}|
   {'family':c['family'],'variant':c['variant'],**{k:v for k,v in r['score'].items() if k!='violations'},**r['exposure']})
 exposures=[exposure_row(r) for r in results]
 summaries_table=[]
 for phase in ('primary','repeat'):
  for arm in ('inherited','verify_confirm'):
   rows=[x for x in episode_rows if x['phase']==phase and x['arm']==arm]
   us=[x for x in usage if x['phase']==phase and x['arm']==arm]
   summaries_table.append({'phase':phase,'arm':arm,'planned_episodes':16 if phase=='primary' else 2,'completed_episodes':len(rows),
    **{k:sum(r[k] for r in rows) for k in ('tool_success_proxy','goal_final','final_state_clean','trace_safe_success','wrong_write','goal_only_false_accept','final_clean_false_accept','tool_errors','tool_calls','terminated','triggered')},
    'recorded_model_requests':len([r for r in req.values() if r['metadata']['phase']==phase and r['metadata']['arm']==arm]),
    **{k:sum(x[k] for x in us if x.get(k) is not None) for k in ('prompt_tokens','completion_tokens','total_tokens','latency_seconds')},'monetary_cost':'UNKNOWN'})
 pairs=[]
 for c in cases.values():
  arms={r['arm']:r for r in results if r['phase']=='primary' and r['case_id']==c['id']}
  if len(arms)!=2:continue
  a,z=arms['inherited'],arms['verify_confirm'];pairs.append({'case_id':c['id'],'family':c['family'],'variant':c['variant'],
   **{f'{arm}_{k}':r['score'][k] for arm,r in arms.items() for k in ('goal_final','final_state_clean','trace_safe_success','wrong_write')},
   'same_exposure':a['exposure']==z['exposure'],'tool_difference':z['tool_calls']-a['tool_calls'],'model_request_difference':z['model_calls']-a['model_calls']})
 repeats=[]
 for c in ('n02','n10'):
  for arm in ('inherited','verify_confirm'):
   matched=[r for r in results if r['case_id']==c and r['arm']==arm]
   if len(matched)!=2:continue
   a=next(r for r in matched if r['phase']=='primary');z=next(r for r in matched if r['phase']=='repeat')
   seq=lambda r:[(e['tool'],e['arguments']) for e in r['events'] if e['scope']=='agent']
   repeats.append({'case_id':c,'arm':arm,'same_initial_messages':a['initial_messages']==z['initial_messages'],
    'same_tools_and_arguments':seq(a)==seq(z),'same_final_prose':a['done_text']==z['done_text'],
    'primary_trace_safe':a['score']['trace_safe_success'],'repeat_trace_safe':z['score']['trace_safe_success']})
 for name,rows in [('episodes',episode_rows),('calls',usage),('summary',summaries_table),('exposure',exposures),('paired',pairs),('repeats',repeats)]:csv_write(report/(name+'.csv'),rows)
 write(report/'scores.json',[{'episode_id':r['episode_id'],'score':r['score']} for r in results])
 return {'mechanical_pass':True,'execution_complete':status['status']=='completed','status':status['status'],
  'recorded_requests':len(req),'reconstructed_requests':len(replay.consumed),
  'primary_episodes':sum(r['phase']=='primary' for r in results),'repeat_episodes':sum(r['phase']=='repeat' for r in results),
  'native_tool_events':sum(r['tool_calls'] for r in results)+sum(p['native_tool_events'] for p in partial_prefixes),
  'completed_native_tool_events':sum(r['tool_calls'] for r in results),
  'partial_native_tool_events':sum(p['native_tool_events'] for p in partial_prefixes),
  'environment_operations':sum(r['environment_operations'] for r in results)+sum(p['environment_operations'] for p in partial_prefixes),
  'verified_partial_prefixes':partial_prefixes,
  'retained_response_failures':failures,'new_remote_model_calls':0,'currency_cost':'UNKNOWN',
  'uncompleted_are_not_zero_scores':True,'scientific_superiority_claim':False,'automatic_next_batch_authorized':False,
  'limitation':'Same-assistant saved-response and native-engine replay, not independent human review or model-weight authentication.'}

def audit(root):
 root=Path(root)
 try:
  with no_network():result=_audit(root)
 except Exception as exc:
  result={'mechanical_pass':False,'execution_complete':False,'error_type':type(exc).__name__,'error':str(exc),
   'new_remote_model_calls':0,'instruction':'Preserve original records and export; do not change hashes or rerun to improve results.'}
 write(root/'runs/AUDIT.json',result);return result
