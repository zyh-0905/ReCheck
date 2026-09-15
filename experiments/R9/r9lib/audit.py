"""Offline whole-episode reconstruction. No new model responses are generated."""
from pathlib import Path
import csv,json,math
from pilot.common import read_json,write_json,digest,request_payload,response_text
from .artifacts import verify_distribution,source_hashes
from .prompts import initial_messages,decode_action,tool_result_message,episode_schedule
from .experiment import SCHEMA_ERROR
from .timeline import Timeline
from .scoring import grade
from .accounting import normalize_usage
from .identity import response_identity

def audit_episode(case,r,cfg,runroot):
 if r['case_sha256']!=digest(case) or r['public_input_sha256']!=digest(case['public']):raise ValueError('Case binding')
 messages=initial_messages(case['public'],r['arm'])
 if r['initial_messages']!=messages:raise ValueError('Initial prompt changed')
 if not 1<=len(r['turns'])<=10:raise ValueError('Turn cap')
 timeline=Timeline(case,replay_events=r['events']);consumed=[];terminated=False;done=None
 for n,t in enumerate(r['turns']):
  lid=r['episode_id']+f'/turn_{n:02d}'
  if t['turn']!=n or t['logical_id']!=lid:raise ValueError('Turn order')
  call=read_json(Path(runroot)/'calls'/(digest(lid)+'.json'))
  expected=request_payload(cfg,messages)
  if digest(call['payload'])!=digest(expected):raise ValueError('Request mismatch')
  if call['metadata']!={'episode_id':r['episode_id'],'phase':r['phase'],'turn':n}:raise ValueError('Metadata mismatch')
  if call['request_sha256']!=digest({'endpoint':cfg['base_url'],'payload':expected}) or t['request_sha256']!=call['request_sha256']:raise ValueError('Request hash')
  if call['text']!=t['response_text'] or call['text']!=response_text(call['response']):raise ValueError('Response mismatch')
  consumed.append(lid);messages.append({'role':'assistant','content':call['text']})
  try:kind,a=decode_action(call['text'])
  except ValueError:
   if t['kind']!='schema_error' or t['observation']!=SCHEMA_ERROR:raise ValueError('Schema response mismatch')
   messages.append(tool_result_message(SCHEMA_ERROR));continue
  if t['kind']!=kind or digest(t['action'])!=digest(a):raise ValueError('Action mismatch')
  if kind=='done':
   if n!=len(r['turns'])-1:raise ValueError('Calls after done')
   terminated=True;done=a['done'];break
  start=len(timeline.events);obs=timeline.call(a['tool'],a['arguments'])
  if start!=t['event_start'] or len(timeline.events)!=t['event_end']:raise ValueError('Event range mismatch')
  if obs!=t['observation']:raise ValueError('Native observation mismatch')
  messages.append(tool_result_message(obs))
 if len(timeline.events)!=len(r['events']):raise ValueError('Unaccounted event')
 for actual,saved in zip(timeline.events,r['events']):
  project=lambda e:{k:v for k,v in e.items() if k!='elapsed_seconds'}
  if digest(project(actual))!=digest(project(saved)):raise ValueError('Native event mismatch')
  if 'elapsed_seconds' in saved and (type(saved['elapsed_seconds']) not in (int,float) or not math.isfinite(saved['elapsed_seconds']) or saved['elapsed_seconds']<0):raise ValueError('Bad timing')
 if digest(r['after_world'])!=digest(timeline.world()) or digest(r['final_snapshot'])!=digest(timeline.snapshot()):raise ValueError('Final state mismatch')
 if r['exposure']!=timeline.exposure():raise ValueError('Exposure mismatch')
 if type(r['terminated']) is not bool or r['terminated']!=terminated or r['done_text']!=done:raise ValueError('Termination mismatch')
 if r['stop_reason']!=('done' if terminated else 'turn_cap'):raise ValueError('Stop reason mismatch')
 if r['model_calls']!=len(r['turns']) or r['tool_calls']!=sum(e['scope']=='agent' for e in timeline.events):raise ValueError('Count mismatch')
 if r['environment_operations']!=sum(e['scope']=='environment' for e in timeline.events):raise ValueError('Environment count mismatch')
 if digest(r['score'])!=digest(grade(case['contract'],case['world_before'],timeline.events,timeline.world())):raise ValueError('Scoring mismatch')
 return consumed

def csv_write(p,rows):
 if not rows:return
 with Path(p).open('w',encoding='utf8',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def audit(root):
 root=Path(root);issues=[];rows=[];calls=[];consumed=set();total=0;states={};results={}
 try:source=verify_distribution(root)
 except Exception as e:source=None;issues.append('source: '+str(e))
 prepared=read_json(root/'PREPARED.json') if (root/'PREPARED.json').exists() else None
 cfg=prepared['config'] if prepared else None
 if prepared and prepared['fingerprint']!=digest({'config':cfg,'protocol':read_json(root/'protocol.json'),'source':source_hashes(root)}):issues.append('prepared binding')
 cases={c['id']:c for c in read_json(root/'fixtures/cases.json')};allowed={s['episode_id']:s for s in episode_schedule()}
 uncertain=[]
 for name,cap in (('R9_smoke',1),('R9_main',360)):
  d=root/'runs'/name
  if not d.exists():continue
  state=read_json(d/'status.json') if (d/'status.json').exists() else {'status':'unknown'};states[name]=state['status']
  if prepared and (d/'manifest.json').exists():
   m=read_json(d/'manifest.json')
   if m['prepared_fingerprint']!=prepared['fingerprint'] or m['config']!=cfg or m['protocol']!=prepared['protocol'] or m['source']!=prepared['source']:issues.append(name+': manifest')
  starts=sorted((d/'attempts').glob('*_start.json'));total+=len(starts);seen=set()
  if len(starts)>cap:issues.append(name+': cap exceeded')
  if state.get('registered_requests',len(starts))!=len(starts):issues.append(name+': request count')
  for index,p in enumerate(starts,1):
   s=read_json(p);lid=s['logical_id']
   if s['attempt']!=index or p.name!=f'{index:06d}_start.json' or lid in seen:issues.append(name+': attempt order/duplicate')
   seen.add(lid);rp=d/'attempts'/f'{index:06d}_result.json';sp=d/'attempts'/f'{index:06d}_send_intent.json';cp=d/'calls'/(digest(lid)+'.json')
   if digest(s['payload'])!=s['payload_sha256'] or digest({'endpoint':cfg['base_url'],'payload':s['payload']})!=s['request_sha256']:issues.append(name+': start hash')
   if sp.exists() and read_json(sp)['logical_id']!=lid:issues.append(name+': send intent binding')
   if not rp.exists():uncertain.append(name+'/'+str(index));continue
   r=read_json(rp)
   if any(r.get(k)!=s.get(k) for k in ('logical_id','attempt','payload','request_sha256','started_utc','metadata')):issues.append(name+': response journal')
   if cp.exists() and digest(read_json(cp))!=digest(r):issues.append(name+': cached response')
   if r['status']=='ok':
    if state['status']=='completed':
     if not cp.exists() or not sp.exists():issues.append(name+': completed missing ledger')
     try:
      if response_identity(cfg,r['response'])!=read_json(d/'endpoint_identity.json'):raise ValueError('identity')
      if r['response']['choices'][0]['finish_reason']!='stop':raise ValueError('finish')
      from .prompts import strict_object
      strict_object(r['text'])
     except Exception as e:issues.append(name+': '+str(e))
    u=normalize_usage(r['response'].get('usage'));entry={'run':name,'logical_id':lid,'phase':s['metadata'].get('phase','smoke'),'attempt':index}
    entry.update({k:u[k] for k in ('prompt_tokens','completion_tokens','cached_input_tokens','reasoning_tokens')})
    entry.update(latency_seconds=r['latency_seconds'],requested_model=r['payload']['model'],returned_model=r['response'].get('model'),currency_cost='UNKNOWN')
    if state['status']=='completed' and (u['issues'] or u['prompt_tokens'] is None or u['completion_tokens'] is None):issues.append(name+': usage')
    calls.append(entry)
  all_results={p.stem.split('_')[0] for p in (d/'attempts').glob('*_result.json')}
  if not all_results.issubset({f'{i:06d}' for i in range(1,len(starts)+1)}):issues.append(name+': orphan response')
  if name=='R9_smoke' and state['status']=='completed':
   try:
    c=read_json(d/'calls'/(digest('smoke')+'.json'))
    msg=[{'role':'system','content':'Return exactly one JSON object: {"done":"ready"}.'},{'role':'user','content':'Check the JSON-only interface.'}]
    if c['payload']!=request_payload(cfg,msg) or json.loads(c['text'])!={'done':'ready'}:raise ValueError('smoke mismatch')
   except Exception as e:issues.append(str(e))
  if name=='R9_main':
   if state['status']=='completed':
    try:
     if read_json(d/'endpoint_identity.json')!=read_json(root/'runs/R9_smoke/endpoint_identity.json'):issues.append('cross-run identity')
    except Exception as e:issues.append(str(e))
   for p in sorted((d/'episodes').glob('*.json')):
    r=read_json(p);spec=allowed.get(r['episode_id']);case=cases.get(r['case_id'])
    try:
     if spec is None or any(type(r[k])!=type(v) or r[k]!=v for k,v in spec.items()) or p.stem!=r['episode_id']:raise ValueError('schedule binding')
     consumed.update(audit_episode(case,r,cfg,d));results[r['episode_id']]=r
    except Exception as e:issues.append(p.name+': '+str(e))
    row={k:r[k] for k in ('episode_id','case_id','phase','arm','model_calls','tool_calls','terminated','stop_reason')}
    row.update(family=case['family'],variant=case['variant'],event_triggered=r['exposure']['triggered'],event_scheduled=r['exposure']['scheduled'],unexposed_reason=r['exposure']['reason'])
    row.update({k:r['score'][k] for k in ('tool_success_proxy','goal_final','final_state_clean','trace_safe_success','wrong_write','goal_only_false_accept','final_clean_false_accept','tool_errors')});rows.append(row)
   if state['status']=='completed':
    if len([r for r in rows if r['phase']=='primary'])!=32 or len([r for r in rows if r['phase']=='repeat'])!=4:issues.append('completed missing episodes')
    if consumed!={c['logical_id'] for c in calls if c['run']=='R9_main'}:issues.append('unaccounted calls')
    if {p.stem for p in (d/'calls').glob('*.json')}!={digest(s) for s in seen}:issues.append('orphan cache')
 if total>361:issues.append('combined cap')
 summaries=[]
 for phase in ('primary','repeat'):
  for arm in ('inherited','verify_confirm'):
   subset=[r for r in rows if r['phase']==phase and r['arm']==arm]
   if not subset:continue
   g={'phase':phase,'arm':arm,'completed':len(subset),'planned':16 if phase=='primary' else 2}
   for k in ('tool_success_proxy','goal_final','final_state_clean','trace_safe_success','wrong_write','goal_only_false_accept','final_clean_false_accept','tool_errors','model_calls','tool_calls','event_triggered'):g[k]=sum(r[k] for r in subset)
   summaries.append(g)
 repeats=[]
 for cid in ('n02','n10'):
  for arm in ('inherited','verify_confirm'):
   p=results.get(f'primary_{cid}_{arm}');r=results.get(f'repeat_{cid}_{arm}')
   if p and r:repeats.append({'case_id':cid,'arm':arm,'same_initial_prompt':p['initial_messages']==r['initial_messages'],
    'same_tool_actions':[t['action'] for t in p['turns'] if t['kind']=='tool']==[t['action'] for t in r['turns'] if t['kind']=='tool'],
    'primary_safe':p['score']['trace_safe_success'],'repeat_safe':r['score']['trace_safe_success']})
 out=root/'offline_reports';out.mkdir(exist_ok=True)
 report={'task_id':'R9_LIVE_CONTINUATION_DIAGNOSIS_01','mechanical_pass':not issues,
  'execution_complete':not issues and states.get('R9_smoke')=='completed' and states.get('R9_main')=='completed',
  'source':source,'issues':issues,'states':states,'registered_requests':total,'reconstructed_research_requests':len(consumed),
  'completed_primary':sum(r['phase']=='primary' for r in rows),'completed_repeat':sum(r['phase']=='repeat' for r in rows),
  'planned_primary':32,'planned_repeat':4,'uncertain_attempts':uncertain,'summary':summaries,
  'scientific_gate':'PENDING_RESEARCHER_REVIEW','new_remote_calls_in_audit':0,
  'limits':'Four constructed families, one endpoint; no new method or official benchmark score; untriggered scheduled events not dropped; missing episodes not scored as failures/successes.'}
 write_json(out/'AUDIT.json',report);csv_write(out/'episodes.csv',rows);csv_write(out/'calls.csv',calls);csv_write(out/'summary.csv',summaries);csv_write(out/'repeats.csv',repeats)
 return report
