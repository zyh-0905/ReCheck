
"""Offline, response-based reconstruction and independent state scoring.
During audit only, recorded UUID/time values are replay fixtures for nondeterministic
native primitives. Native tool bodies are unchanged; this is not a new model sample.
"""
from pathlib import Path
from contextlib import contextmanager
from datetime import datetime
from types import SimpleNamespace
from uuid import UUID
import json,copy,csv,math
from collections import defaultdict,Counter
from pilot.common import read_json,write_json,digest,request_payload,response_text
from .artifacts import verify_distribution
from .prompts import initial_messages,decode_action,tool_result_message,episode_schedule
from .native import NativeSession
from .goals import evaluate,added
from .accounting import normalize_usage
from .identity import response_identity

@contextmanager
def replay_nondeterminism(e):
 import tool_sandbox.tools.messaging as mm
 import tool_sandbox.tools.reminder as rm
 restore=[]
 if e.get('response',{}).get('ok'):
  ts=None;mod=None
  if e['tool']=='send_message_with_phone_number':
   identifier=e['response']['value'];UUID(identifier)
   rows=added(e['before_world']['messaging'],e['after_world']['messaging'])
   row=next(x for x in rows if x['message_id']==identifier)
   ts=row['creation_timestamp'];mod=mm
   restore.append((mm,'uuid4',mm.uuid4));mm.uuid4=lambda:UUID(identifier)
  elif e['tool']=='modify_reminder':
   row=next(x for x in e['after_world']['reminder'] if x['reminder_id']==e['arguments']['reminder_id'])
   ts=row['creation_timestamp'];mod=rm
  if mod is not None:
   if type(ts) not in (int,float) or not math.isfinite(ts):raise ValueError('Invalid clock fixture')
   class Clock(datetime):
    @classmethod
    def now(cls,tz=None):return datetime.fromtimestamp(ts,tz)
   restore.append((mod,'datetime',mod.datetime));mod.datetime=SimpleNamespace(datetime=Clock)
 try:yield
 finally:
  for mod,n,x in reversed(restore):setattr(mod,n,x)

def audit_episode(case,r,cfg,runroot):
 if r['case_sha256']!=digest(case) or r['public_input_sha256']!=digest(case['public']):raise ValueError('Case binding changed')
 msgs=initial_messages(case['public'],r['arm'])
 if r['initial_messages']!=msgs:raise ValueError('Initial messages changed')
 if not 1<=len(r['turns'])<=8:raise ValueError('Invalid turn count')
 s=NativeSession(case['snapshot']);consumed=[];ei=0;terminal=False
 for n,t in enumerate(r['turns']):
  logical=r['episode_id']+f'/turn_{n:02d}'
  if t['turn']!=n or t['logical_id']!=logical:raise ValueError('Turn binding changed')
  call=read_json(Path(runroot)/'calls'/(digest(logical)+'.json'))
  payload=request_payload(cfg,msgs)
  if call['payload']!=payload:raise ValueError('Request body changed')
  if call['metadata']!={'episode_id':r['episode_id'],'phase':r['phase'],'turn':n}:raise ValueError('Metadata changed')
  if call['request_sha256']!=digest({'endpoint':cfg['base_url'],'payload':payload}):raise ValueError('Request hash mismatch')
  if t['request_sha256']!=call['request_sha256']:raise ValueError('Turn request binding')
  if call['text']!=response_text(call['response']) or t['response_text']!=call['text']:raise ValueError('Response text changed')
  if call['response']['choices'][0]['finish_reason']!='stop':raise ValueError('Non-stop accepted as episode')
  u=normalize_usage(call['response'].get('usage'))
  if u['issues'] or u['prompt_tokens'] is None or u['completion_tokens'] is None:raise ValueError('Bad usage')
  msgs.append({'role':'assistant','content':call['text']});consumed.append(logical)
  try:kind,a=decode_action(call['text'])
  except ValueError:
   if t['kind']!='schema_error':raise ValueError('Schema error mismatch')
   obs={'ok':False,'value':None,'error':'ACTION_SCHEMA: return exactly tool/arguments or done'}
   if t['observation']!=obs:raise ValueError('Schema observation changed')
   msgs.append(tool_result_message(obs));continue
  if t['kind']!=kind or digest(t['action'])!=digest(a):raise ValueError('Action changed')
  if kind=='done':
   if n!=len(r['turns'])-1:raise ValueError('Calls after done')
   terminal=True
   if r['done_text']!=a['done']:raise ValueError('Done text changed')
   break
  event=r['events'][ei]
  if t['event_index']!=ei or event['tool']!=a['tool'] or event['arguments']!=a['arguments']:raise ValueError('Tool binding changed')
  if s.world()!=event['before_world']:raise ValueError('Before state changed')
  with replay_nondeterminism(event):obs=s.call(a['tool'],a['arguments'])
  if obs!=event['response'] or t['observation']!=obs:raise ValueError('Native return changed')
  if s.world()!=event['after_world']:raise ValueError('Native transition changed')
  msgs.append(tool_result_message(obs));ei+=1
 if ei!=len(r['events']) or terminal!=r['terminated']:raise ValueError('Unaccounted events or terminal')
 if type(r['model_calls']) is not int or type(r['tool_calls']) is not int or r['model_calls']!=len(r['turns']) or r['tool_calls']!=ei:raise ValueError('Counts changed')
 if type(r['terminated']) is not bool:raise ValueError('Terminal flag type changed')
 if r['after_world']!=s.world():raise ValueError('Final state changed')
 if r['final_snapshot']!=s.snapshot():raise ValueError('Final native snapshot changed')
 score=evaluate(case['world_before'],s.world(),case['goal'],r['events'])
 if digest(score)!=digest(r['score']):raise ValueError('Score changed (including field types)')
 return consumed

def _csv(path,rows):
 if not rows:return
 with Path(path).open('w',encoding='utf8',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def audit(root):
 root=Path(root);issues=[];source=None
 try:source=verify_distribution(root)
 except Exception as e:issues.append('source: '+str(e))
 prepared=read_json(root/'PREPARED.json') if (root/'PREPARED.json').exists() else None
 cfg=prepared['config'] if prepared else None
 cases=read_json(root/'fixtures/cases.json');bycase={c['id']:c for c in cases}
 report={'scientific_gate':'PENDING_RESEARCHER_REVIEW','new_model_calls':0,
   'source':source,'issues':issues,'evidence_kind':'response_reconstruction_not_new_samples'}
 if prepared:
  expected={'config':cfg,'protocol':read_json(root/'protocol.json'),'source':read_json(root/'SOURCE_MANIFEST.json')['sha256']}
  if digest(expected)!=prepared['fingerprint']:issues.append('prepared binding')
 ep_rows=[];call_rows=[];total_requests=0;consumed=set();episode_results={}
 for name,cap in (('R7C_smoke',1),('R7C_main',384)):
  run=root/'runs'/name
  if not run.exists():continue
  if (run/'manifest.json').exists() and prepared:
   m=read_json(run/'manifest.json')
   if m['prepared_fingerprint']!=prepared['fingerprint']:issues.append(name+': manifest mismatch')
  run_status=read_json(run/'status.json').get('status','unknown') if (run/'status.json').exists() else 'unknown'
  if name=='R7C_smoke':report['smoke_status']=run_status
  if run_status=='completed':
   ip=run/'endpoint_identity.json'
   if not ip.exists():issues.append(name+': completed without pinned response metadata')
   else:
    for cp in sorted((run/'calls').glob('*.json')):
     try:
      saved=read_json(cp);expected_identity=response_identity(cfg,saved['response'])
      if expected_identity!=read_json(ip):raise ValueError('Pinned response metadata differs from raw response')
     except Exception as exc:issues.append(name+': response identity: '+str(exc))
  starts=sorted((run/'attempts').glob('*_start.json'));total_requests+=len(starts)
  if len(starts)>cap:issues.append(name+': budget exceeded')
  ids=set()
  for p in starts:
   st=read_json(p);lid=st['logical_id']
   if lid in ids:issues.append(name+': repeated logical id')
   ids.add(lid);idx=st['attempt']
   if p.name!=f'{idx:06d}_start.json':issues.append('Attempt index binding')
   for tag in ('send_intent','result'):
    f=run/'attempts'/f'{idx:06d}_{tag}.json'
    if not f.exists():
     if tag=='result':report.setdefault('uncertain_attempts',[]).append(name+'/'+str(idx))
     continue
    q=read_json(f)
    if q.get('logical_id')!=lid:issues.append('Journal identity mismatch')
   cp=run/'calls'/(digest(lid)+'.json')
   rp=run/'attempts'/f'{idx:06d}_result.json'
   if cp.exists():
    c=read_json(cp)
    if not rp.exists() or c!=read_json(rp):issues.append('Call/result mismatch')
    if any(c.get(k)!=st.get(k) for k in ('payload','metadata','request_sha256','started_utc')):issues.append('Start/call mismatch')
    u=normalize_usage(c.get('response',{}).get('usage'))
    call_rows.append({'run':name,'logical_id':lid,'phase':c['metadata'].get('phase','smoke'),
      'attempt':idx,'prompt_tokens':u['prompt_tokens'],'completion_tokens':u['completion_tokens'],
      'reasoning_tokens':u['reasoning_tokens'],'latency_seconds':c['latency_seconds'],
      'finish':c.get('response',{}).get('choices',[{}])[0].get('finish_reason'),
      'currency_cost':'UNKNOWN','requested_model':c['payload'].get('model'),
      'returned_model':c.get('response',{}).get('model'),
      'system_fingerprint':c.get('response',{}).get('system_fingerprint')})
  if name=='R7C_main' and cfg:
   allowed={s['episode_id']:s for s in episode_schedule()}
   for p in sorted((run/'episodes').glob('*.json')):
    r=read_json(p)
    try:
     if r['episode_id'] not in allowed or any(r[k]!=v for k,v in allowed[r['episode_id']].items()):raise ValueError('Schedule binding changed')
     ids_used=audit_episode(bycase[r['case_id']],r,cfg,run);consumed.update(ids_used)
     episode_results[r['episode_id']]=r
    except Exception as exc:issues.append(p.name+': '+str(exc))
    ep_rows.append({'episode_id':r['episode_id'],'phase':r['phase'],'case_id':r['case_id'],
      'arm':r['arm'],'family':bycase[r['case_id']]['family'],'variant':bycase[r['case_id']]['variant'],
      'safe_success':r['score']['safe_success'],'goal_achieved':r['score']['goal_achieved'],
      'wrong_write':r['score']['wrong_write'],'terminated':r['terminated'],
      'model_calls':r['model_calls'],'tool_calls':r['tool_calls']})
   status=read_json(run/'status.json') if (run/'status.json').exists() else {}
   report['run_status']=status.get('status','unknown')
   if status.get('status')=='completed':
    if len(ep_rows)!=48:issues.append('Completed with missing episodes')
    live_ids={r['logical_id'] for r in call_rows if r['run']==name}
    if live_ids!=consumed:issues.append('Unaccounted completed calls')
 if total_requests>385:issues.append('Combined cap exceeded')
 repeats=[]
 for a in ('stateless','inherited','resolve_rule'):
  for c in ('c02','c10'):
   p=episode_results.get(f'primary_{c}_{a}');r=episode_results.get(f'repeat_{c}_{a}')
   if p and r:
    repeats.append({'case_id':c,'arm':a,'same_initial_messages':p['initial_messages']==r['initial_messages'],
      'primary_safe_success':p['score']['safe_success'],'repeat_safe_success':r['score']['safe_success'],
      'same_actions':[t.get('action') for t in p['turns']]==[t.get('action') for t in r['turns']]})
 summary=[]
 for phase in ('primary','repeat'):
  for a in ('stateless','inherited','resolve_rule'):
   rows=[r for r in ep_rows if r['phase']==phase and r['arm']==a]
   if rows:summary.append({'phase':phase,'arm':a,'completed_episodes':len(rows),'planned_episodes':14 if phase=='primary' else 2,
      'safe_success':sum(r['safe_success'] for r in rows),'wrong_write':sum(r['wrong_write'] for r in rows),
      'model_calls':sum(r['model_calls'] for r in rows),'tool_calls':sum(r['tool_calls'] for r in rows)})
 report.update(mechanical_pass=not issues,planned_primary_episodes=42,planned_repeat_episodes=6,
  completed_primary=sum(r['phase']=='primary' for r in ep_rows),completed_repeat=sum(r['phase']=='repeat' for r in ep_rows),
  requests_registered=total_requests,reconstructed_requests=len(consumed),summary=summary,
  partial_data_note='Missing/paused episodes are not silently counted as successes or excluded from planned denominators',
  grouping_note='14 constructed cases, three intent templates, two domains; not independent benchmark samples',
  costs='UNKNOWN; tokens/latency are records, not invoices')
 report['execution_complete']=(report.get('smoke_status')=='completed' and report.get('run_status')=='completed' and report['completed_primary']==42 and report['completed_repeat']==6 and not issues)
 report['response_label_policy']='R7C1_RESPONSE_LABELS_V1; smoke establishes a single returned-label/fingerprint cohort, not verified weights'
 out=root/'offline_reports';out.mkdir(exist_ok=True)
 write_json(out/'AUDIT.json',report)
 _csv(out/'episodes.csv',ep_rows);_csv(out/'calls.csv',call_rows);_csv(out/'summary.csv',summary);_csv(out/'repeats.csv',repeats)
 return report
