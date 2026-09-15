"""Read-only audit of recorded SAP/TED ToolSandbox JSON, not native replay.
Only snapshots at response-batch boundaries are inspected. Reports never change
source metrics. No eval/pickle/network/LLM code is used.
"""
from __future__ import annotations
import argparse,copy,csv,hashlib,json,re,collections
from pathlib import Path

SETTINGS={'wifi_off':('wifi',False),'cellular_off':('cellular',False),
 'turn_on_wifi_low_battery_mode':('wifi',True),
 'turn_on_cellular_low_battery_mode':('cellular',True),
 'turn_on_location_low_battery_mode':('location_service',True)}
TARGET_ID='9e137f06-916a-5310-8174-cf0b7e9f7054'
PHONE='+19876543210'
STATIC=set(SETTINGS)|{'add_contact_with_name_and_phone_number','update_contact_with_id_and_phone_number','remove_contact_with_id','remove_contact_by_phone','update_contact_relationship_with_relationship'}
SEQUENTIAL='update_contact_relationship_with_relationship_twice_multiple_user_turn'
MUTATIONS={'add_contact':'CONTACT','modify_contact':'CONTACT','remove_contact':'CONTACT',
 'add_reminder':'REMINDER','modify_reminder':'REMINDER','remove_reminder':'REMINDER',
 'send_message_with_phone_number':'MESSAGING',
 **{x:'SETTING' for x in ['set_wifi_status','set_cellular_service_status','set_low_battery_mode_status','set_location_service_status']}}
ERROR=re.compile(r'(?m)(?:^|\n)(?:[A-Za-z_][A-Za-z_0-9]*Error|Exception):')
def dump(p,obj):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def update_of(m):
 for k in ('user_details','tool_details'):
  x=m.get(k)
  if isinstance(x,dict) and 'database_update' in x:return x['database_update']
 return {}
def rebuild(sample):
 state={};initial={};points=[];batches=[];issues=[];seen=set();users=[];batch=None
 def save(kind,t,j):points.append({'kind':kind,'turn':t,'message':j,'state':copy.deepcopy(state)})
 def apply(up):
  for ns,rows in up.items():
   if isinstance(rows,list) and all(isinstance(r,dict) for r in rows):state[ns]=copy.deepcopy(rows)
   else:state.pop(ns,None);issues.append('invalid_snapshot:'+ns)
 def close():
  nonlocal batch
  if batch is None:return
  ids=[c.get('id') for c in batch['calls']];rids=[r.get('tool_call_id') for r in batch['receipts']]
  batch['receipt_order']=rids
  for cid in ids:
   if cid not in rids:issues.append('missing_receipt:'+str(cid))
  for cid in rids:
   if cid not in ids:issues.append('orphan_receipt:'+str(cid))
   if rids.count(cid)>1:issues.append('duplicate_receipt:'+str(cid))
  per=collections.defaultdict(list)
  for r in batch['receipts']:
   for ns,v in update_of(r).items():per[ns].append(v)
  for c in batch['calls']:
   ns=MUTATIONS.get((c.get('function') or {}).get('name'))
   matched=[r for r in batch['receipts'] if r.get('tool_call_id')==c.get('id')]
   proven_error=len(matched)==1 and bool(ERROR.search(str(matched[0].get('content',''))))
   if ns and ns not in per and not proven_error:
    state.pop(ns,None);issues.append('mutation_without_snapshot:'+str(c.get('id')))
  for ns,vs in per.items():
   if any(v!=vs[0] for v in vs[1:]):
    state.pop(ns,None);issues.append('ambiguous_batch_snapshots:'+ns)
   else:apply({ns:vs[0]})
  save('batch_end',batch['turn'],batch['last_message']);batches.append(batch);batch=None
 traj=sample.get('trajectory')
 if not isinstance(traj,list) or not all(isinstance(t,list) for t in traj):return {'points':[],'batches':[],'issues':['bad_trajectory'],'initial':{},'users':[]}
 for t,messages in enumerate(traj):
  for j,m in enumerate(messages):
   if not isinstance(m,dict):issues.append('bad_message');continue
   if m.get('role')!='tool':close()
   if m.get('role')=='user':
    users.append({'turn':t,'message':j,'text':m.get('content','')});apply(update_of(m))
    if not points:initial=copy.deepcopy(state)
    save('user',t,j)
   if m.get('tool_calls'):
    calls=m['tool_calls']
    for c in calls:
     cid=c.get('id')
     if cid in seen:issues.append('duplicate_call:'+str(cid))
     seen.add(cid)
    batch={'turn':t,'message':j,'last_message':j,'calls':calls,'receipts':[]}
   elif m.get('role')=='tool':
    if batch is None:issues.append('orphan_receipt:'+str(m.get('tool_call_id')))
    else:batch['receipts'].append(m);batch['last_message']=j
  close();save('turn_end',t,len(messages)-1)
 return {'points':points,'initial':initial,'batches':batches,'issues':issues,'users':users}

def norm(x):return ' '.join(x.casefold().split()) if isinstance(x,str) else x

def goal(sid,state,initial):
 if sid in SETTINGS:
  field,expected=SETTINGS[sid];v=state.get('SETTING')
  if not isinstance(v,list) or len(v)!=1 or type(v[0].get(field)) is not bool:return None
  return v[0][field] is expected
 rows=state.get('CONTACT')
 if not isinstance(rows,list):return None
 if len({r.get('person_id') for r in rows})!=len(rows) or any('person_id' not in r for r in rows):return None
 if sid=='update_contact_with_id_and_phone_number':return any(r['person_id']==TARGET_ID and r.get('phone_number')==PHONE for r in rows)
 if sid=='add_contact_with_name_and_phone_number':return any(norm(r.get('name'))=='stephen sondheim' and r.get('phone_number')==PHONE for r in rows)
 if sid in ('remove_contact_with_id','remove_contact_by_phone'):
  ir=initial.get('CONTACT')
  if not isinstance(ir,list):return None
  targets={r['person_id'] for r in ir if r.get('person_id')==TARGET_ID} if sid.endswith('with_id') else {r['person_id'] for r in ir if r.get('phone_number')=='+12453344098'}
  if not targets:return None
  return not targets & {r['person_id'] for r in rows}
 if sid in ('update_contact_relationship_with_relationship','phase_enemy','phase_friend'):
  ir=initial.get('CONTACT')
  if not isinstance(ir,list):return None
  targets={r['person_id'] for r in ir if norm(r.get('relationship'))=='friend'}
  if not targets:return None
  expected='friend' if sid=='phase_friend' else 'enemy'
  mapping={r['person_id']:r for r in rows}
  return all(i in mapping and norm(mapping[i].get('relationship'))==expected for i in targets)
 return None

def temporal(values):
 final=values[-1] if values else None
 # Adjacent *observed checkpoints* only. Unknown cuts the chain.
 reg=any(a is True and b is False for a,b in zip(values,values[1:]))
 return {'observed_regression':reg,'ever_true':any(v is True for v in values),
         'final':final,'ever_true_final_false':None if final is None else (any(v is True for v in values) and final is False)}

def csvout(path,rows):
 if not rows:return
 with path.open('w',encoding='utf8',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def analyze(raw,out,split):
 out.mkdir(parents=True,exist_ok=False)
 results=[];details=[];inventory=[];linkrows=[];missing=[]
 modelmap={'gpt_4_1':'azure/gpt-4.1','gpt_4o':'azure/gpt-4o','gpt_4o_mini':'azure/gpt-4o-mini','gpt_5':'azure/gpt-5','mistral_large_2411':'azure/mistral-large-2411','mistral_nemo':'azure/mistral-nemo'}
 reference_ids=None
 for p in sorted(raw.glob('toolsandbox/*/*/trial_*_results.json')):
  trial=int(p.name.split('_')[1]);
  if (split=='dev' and trial>1) or (split=='heldout' and trial<2):continue
  data=json.loads(p.read_text());rel=p.relative_to(raw).as_posix();model=p.parts[-3];persona=p.parts[-2]
  assert data['trial_id']==trial and data['agent_model']==modelmap[model] and data['user_proxy_persona']==persona
  samples=data['samples'];ids=[s['sample_id'] for s in samples];assert len(ids)==len(set(ids));assert data['total_samples']==len(samples)
  if reference_ids is None and len(ids)==37:reference_ids=set(ids)
  if reference_ids is not None and set(ids)!=reference_ids:missing.append({'source':rel,'missing':sorted(reference_ids-set(ids)),'extra':sorted(set(ids)-reference_ids)})
  inventory.append({'source':rel,'trial':trial,'model':model,'persona':persona,'samples':len(samples),'sha256':sha(p)})
  for i,s in enumerate(samples):
   sid=s['sample_id']; rec=rebuild(s);key=f'{model}/{persona}/{trial}/{sid}';metrics=s.get('metrics') or {};rates=metrics.get('progress_rates') or []
   cps=[pt for pt in rec['points'] if pt['kind']!='user'];vals=[goal(sid,pt['state'],rec['initial']) for pt in cps] if sid in STATIC else []
   tt=temporal(vals);ng=sum(1 for g in metrics.get('subgoal_validations',[]) if g.get('is_completed'))
   nsub=len(metrics.get('subgoal_validations',[]))
   structural=[x for x in rec['issues'] if x.startswith(('duplicate_','missing_receipt:','orphan_receipt:','bad_'))]
   final=tt['final'] if not structural else None
   row={'key':key,'source':rel,'sample_index':i,'sample_id':sid,'model':model,'persona':persona,'trial':trial,'split':'dev' if trial<2 else 'heldout',
        'status':s.get('status'),'outer_turns':len(s.get('trajectory') or []),'declared_turns':s.get('total_turns'),
        'calls':sum(len(b['calls']) for b in rec['batches']),'receipts':sum(len(b['receipts']) for b in rec['batches']),
        'batches':len(rec['batches']),'multi_batches':sum(len(b['calls'])>1 for b in rec['batches']),
        'reordered_batches':sum([c.get('id') for c in b['calls']]!=b['receipt_order'] for b in rec['batches']),
        'recorded_updates':sum(len(update_of(r)) for b in rec['batches'] for r in b['receipts']),
        'structural_issues':';'.join(structural),'state_issues':';'.join(x for x in rec['issues'] if x not in structural),
        'goal_supported':sid in STATIC,'goal_known':final is not None,'effect_final':final,
        'effect_ever_true':tt['ever_true'] if sid in STATIC else None,'observed_regression_candidate':tt['observed_regression'] if sid in STATIC else None,
        'ever_true_final_false_candidate':tt['ever_true_final_false'] if sid in STATIC else None,
        'ted_final_progress':rates[-1] if rates else None,'ted_final_full':bool(rates and rates[-1]==1.0),
        'ted_auc':metrics.get('auc_score'),'ted_ppt':metrics.get('ppt_score'),
        'completed_subgoals':ng,'subgoals':nsub,
        'reported_full_effect_false_candidate':bool(rates and rates[-1]==1.0 and final is False),
        'raw_effect_progress':json.dumps(vals),'recorded_progress':json.dumps(rates)}
   results.append(row)
   for k,b in enumerate(rec['batches']):
    linkrows.append({'key':key,'batch':k,'turn':b['turn'],'message':b['message'],'tool_names':json.dumps([c.get('function',{}).get('name') for c in b['calls']]),'call_ids':json.dumps([c.get('id') for c in b['calls']]),'receipt_ids':json.dumps(b['receipt_order']), 'ns_updates':json.dumps(sorted({ns for r in b['receipts'] for ns in update_of(r)}))})
   if sid in STATIC or sid==SEQUENTIAL:
    relevant='SETTING' if sid in SETTINGS else 'CONTACT'
    details.append({'key':key,'row':row,'users':rec['users'],'initial':{relevant:rec['initial'].get(relevant)},
      'points':[{'kind':pt['kind'],'turn':pt['turn'],'message':pt['message'],'state':{relevant:pt['state'].get(relevant)},'goal':goal(sid,pt['state'],rec['initial']) if sid in STATIC else {'enemy':goal('phase_enemy',pt['state'],rec['initial']),'friend':goal('phase_friend',pt['state'],rec['initial'])}} for pt in rec['points']],
      'subgoals':[{'details':g['subgoal']['details'],'completed':g.get('is_completed')} for g in metrics.get('subgoal_validations',[])]})
 csvout(out/'episodes.csv',results);csvout(out/'files.csv',inventory);csvout(out/'receipt_batches.csv',linkrows);dump(out/'scoped_evidence.json',details);dump(out/'missing_records.json',missing)
 summary={'split':split,'source_files':len(inventory),'episodes':len(results),'task_ids':len({r['sample_id'] for r in results}),
   'status_counts':dict(collections.Counter(r['status'] for r in results)),
   'calls':sum(r['calls'] for r in results),'receipts':sum(r['receipts'] for r in results),'batches':sum(r['batches'] for r in results),
   'multi_batches':sum(r['multi_batches'] for r in results),'reordered_batches':sum(r['reordered_batches'] for r in results),
   'structural_issue_episodes':sum(bool(r['structural_issues']) for r in results),'supported':sum(r['goal_supported'] for r in results),
   'known':sum(r['goal_known'] for r in results),'effect_true':sum(r['effect_final'] is True for r in results),'effect_false':sum(r['effect_final'] is False for r in results),
   'regression_candidates':sum(r['observed_regression_candidate'] is True for r in results),
   'lost_goal_candidates':sum(r['ever_true_final_false_candidate'] is True for r in results),
   'full_effect_false_candidates':sum(r['reported_full_effect_false_candidate'] for r in results),
   'all_ted_full':sum(r['ted_final_full'] for r in results),'missing':missing,'new_llm_calls':0}
 dump(out/'summary.json',summary);print(json.dumps(summary,ensure_ascii=False,indent=2))

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--raw',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--split',choices=['dev','heldout','all'],required=True);a=ap.parse_args();analyze(a.raw,a.out,a.split)
